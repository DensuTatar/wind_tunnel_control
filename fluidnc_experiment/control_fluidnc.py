"""Experimental FluidNC scan; default is offline preview, no hardware access."""
import argparse
import csv
import math
import time
from datetime import datetime
from pathlib import Path
from contextlib import ExitStack
from fluidnc_motion import FluidNC

# Same first test grid and sample settings as our original control.py.
X_POSITIONS_MM = [10, 20]
Z_POSITIONS_MM = [10, 20]
SETTLE_TIME_S = 2.0
SAMPLES_PER_POINT = 20
SAMPLE_INTERVAL_S = 0.05
FEED_MM_MIN = 600.0
BAUD_RATE = 115200
DATA_DIRECTORY = Path(__file__).resolve().parent / 'data'


def sensor_command(port, command):
    port.write((command + '\n').encode('ascii'))
    raw = port.readline()
    if not raw.endswith(b'\n'):
        raise TimeoutError(f'No complete sensor reply for {command}')
    response = raw.decode('ascii').strip()
    if response.startswith('ERR'):
        raise RuntimeError(response)
    return response


def measure_once(port):
    parts = sensor_command(port, 'MEASURE').split(',')
    if len(parts) != 5 or parts[:2] != ['OK', 'MEASURE']:
        raise RuntimeError(f'Invalid measurement: {parts}')
    values = tuple(float(v) for v in parts[2:])
    if not all(map(math.isfinite, values)):
        raise RuntimeError('Non-finite measurement')
    return values


def measure_average(port):
    samples = []
    for _ in range(SAMPLES_PER_POINT):
        samples.append(measure_once(port))
        time.sleep(SAMPLE_INTERVAL_S)
    return tuple(sum(col)/len(col) for col in zip(*samples))


def run_scan(motion, sensor, output_file, origin, mode):
    with output_file.open('x', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'x_mm', 'z_mm', 'speed_ms',
                         'pressure_pa', 'temperature_c', 'measurement_mode'])
        for z in Z_POSITIONS_MM:
            for x in X_POSITIONS_MM:
                # Offset from the confirmed post-homing position (pulloff).
                motion.move_to(origin[0] + x, origin[1] + z, FEED_MM_MIN)
                time.sleep(SETTLE_TIME_S)
                speed, pressure, temperature = measure_average(sensor)
                writer.writerow([datetime.now().isoformat(timespec='seconds'),
                                 x, z, speed, pressure, temperature, mode])
                file.flush()
                print(f'X={x}, Z={z}: U={speed}, P={pressure}, T={temperature} ({mode})')


def create_plots(path):
    import pandas as pd
    import matplotlib.pyplot as plt
    data = pd.read_csv(path)
    for column, label in [('speed_ms', 'Air speed [m/s]'),
                          ('pressure_pa', 'Pressure [Pa]'),
                          ('temperature_c', 'Temperature [°C]')]:
        fig, ax = plt.subplots(figsize=(7, 6))
        plot = ax.scatter(data.x_mm, data.z_mm, c=data[column], s=180)
        fig.colorbar(plot, ax=ax, label=label)
        ax.set(xlabel='X [mm]', ylabel='Z [mm]', title=f'{label} — {data.measurement_mode.iloc[0]}')
        ax.set_aspect('equal')
        fig.tight_layout()
        fig.savefig(path.with_name(f'{path.stem}_{column}.png'), dpi=300)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Enable hardware access')
    parser.add_argument('--commissioned', action='store_true', help='Confirm supervised hardware commissioning completed')
    parser.add_argument('--motion-port')
    parser.add_argument('--sensor-port')
    parser.add_argument('--motion-only', action='store_true', help='Home and move test grid without recording measurements')
    parser.add_argument('--allow-demo', action='store_true', help='Explicitly allow synthetic sensor readings')
    args = parser.parse_args()
    if not args.live:
        print('OFFLINE PREVIEW: no ports opened; no motion or measurements.')
        print('$H; G21 G90; determine machine position after homing')
        for z in Z_POSITIONS_MM:
            for x in X_POSITIONS_MM:
                print(f'G53 G1 X(home_x+{x}) Y(home_y+{z}) F{FEED_MM_MIN:g} -> wait Idle + MPos -> settle -> sample')
        return
    if not args.commissioned or not args.motion_port:
        parser.error('--live requires --commissioned and --motion-port')
    if not args.motion_only and (not args.sensor_port or args.sensor_port == args.motion_port):
        parser.error('Provide a separate --sensor-port, or choose --motion-only')
    import serial
    output = None
    with ExitStack() as stack:
        sensor = None
        mode = None
        if not args.motion_only:
            sensor = stack.enter_context(serial.Serial(args.sensor_port, BAUD_RATE, timeout=3, write_timeout=3))
            time.sleep(2)
            sensor.reset_input_buffer()
            if sensor_command(sensor, 'PING') != 'OK,PONG':
                raise RuntimeError('Wrong sensor controller response')
            mode = sensor_command(sensor, 'MODE').split(',')
            if mode not in (['OK','MODE','DEMO'], ['OK','MODE','REAL']):
                raise RuntimeError('Unexpected sensor mode')
            mode = mode[2]
            if mode == 'DEMO' and not args.allow_demo:
                raise RuntimeError('Demo readings blocked; use --allow-demo only for testing')
            measure_once(sensor)  # fail before homing if real acquisition is unfinished
        port = stack.enter_context(serial.Serial(args.motion_port, BAUD_RATE, timeout=0.5, write_timeout=3))
        time.sleep(2)
        port.reset_input_buffer()
        motion = FluidNC(port)
        try:
            motion.command('$I')
            origin = motion.home()
            print(f'Homed. Machine position at scan origin: {origin}')
            if args.motion_only:
                for z in Z_POSITIONS_MM:
                    for x in X_POSITIONS_MM:
                        print(motion.move_to(origin[0]+x, origin[1]+z, FEED_MM_MIN))
                        time.sleep(SETTLE_TIME_S)
            else:
                DATA_DIRECTORY.mkdir(exist_ok=True)
                stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                output = DATA_DIRECTORY / f'fluidnc_{mode.lower()}_{stamp}.csv'
                run_scan(motion, sensor, output, origin, mode)
        except (Exception, KeyboardInterrupt):
            try:
                motion.request_hold()
            except Exception:
                pass
            print('Scan aborted. Hold requested if possible; verify physical stop and re-home.')
            raise
    if output is not None:
        create_plots(output)
        print(f'Saved {output}')


if __name__ == '__main__':
    main()
