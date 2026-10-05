# Wind-tunnel traverser control

This project moves a probe through a wind tunnel and records measurements.

- The **ESP32** controls the X and Z stepper motors and reads the sensors.
- The **laptop** tells the ESP32 where to move and saves the measurements.
- The system communicates using simple text commands over USB serial.

This is commissioning software. Check the wiring, switches, travel limits, and calibration before collecting real experimental data.

## Project layout


wind_tunnel_control/
├── firmware (runs ON ESP32)/
│   ├── config.py
│   ├── main.py
│   ├── motor_control.py
│   └── sensors.py
├── pc (runs ON LAPTOP)/
│   └── control.py
├── data/       generated CSV files and plots
├── docs/       wiring drawings and test notes
├── .gitignore
└── README.md
```

### What each file does

| File/folder | Purpose |
|---|---|
| `firmware (runs ON ESP32)/config.py` | The main settings file: GPIO pins, motor settings, travel limits, speeds, and sensor test mode. |
| `firmware (runs ON ESP32)/motor_control.py` | Contains the `Axis` class. It sends motor pulses, changes direction, checks the home switch, homes an axis, and tracks position. |
| `firmware (runs ON ESP32)/sensors.py` | Reads air speed, pressure, and temperature. The sensor functions are currently placeholders. |
| `firmware (runs ON ESP32)/main.py` | Starts the ESP32, creates the two axes, receives commands, and sends replies. |
| `pc (runs ON LAPTOP)/control.py` | Connects to the ESP32, homes it, scans positions, averages readings, writes CSV data, and creates plots. |
| `data/` | Output folder created/used by the laptop program. |
| `docs/` | Empty folder for wiring diagrams, calibration records, and test results. |
| `.gitignore` | Prevents temporary Python files and environments from being added to Git. |

## Important limitations right now

- The values in `config.py` are starting values. They must be checked against the assembled machine.
- The axes must be homed after every ESP32 restart.
- The position is open-loop: the code assumes every motor step worked. A skipped step or loose belt causes position error.
- Only the home switches are used. Positive-end protection is currently a software limit, not a hardware safety system.
- X moves first and Z moves second. The axes do not move together yet.
- `DEMO_SENSOR_MODE = True` means every sensor reading is zero. These readings must not be used as experimental results.
- If demo mode is set to `False` before the sensor code is completed, `MEASURE` will return an error.

## Before connecting power: safety warnings

### TB6600 and ESP32 wiring

Always turn off the motor-driver power before connecting, disconnecting, or changing wires. Wait for the driver capacitors to discharge.

- Never connect the ESP32 to the TB6600 motor terminals `A+`, `A-`, `B+`, or `B-`.
- Never connect or disconnect a stepper motor while the TB6600 is powered.
- Never connect the motor supply voltage to an ESP32 pin.
- Never apply 5 V directly to an ESP32 GPIO. ESP32 GPIOs use 3.3 V logic.
- Use the exact TB6600 manual for `PUL/STEP`, `DIR`, `ENA`, and their `+/-` terminals. Different driver models use different common-anode/common-cathode wiring.
- Check whether the TB6600 inputs accept 3.3 V signals. If they do not, use the required interface circuit; do not guess.
- Use separate, correctly rated power supplies for the ESP32 and motor driver unless the electrical design specifically says otherwise.
- Confirm the driver current, motor voltage, and microstep DIP switches are suitable for the motor.
- Keep an emergency power disconnect nearby and keep hands clear of belts, rails, and the moving carriage.

The code currently expects home switches to use the ESP32 internal pull-up:

- switch open = GPIO reads high;
- switch activated = GPIO reads low;
- `HOME_ACTIVE_LEVEL = 0`.

Test each switch by hand before automatic homing. If a normally closed or fail-safe switch circuit is used, update the wiring and software together.

## Settings to check after assembly

Edit `firmware (runs ON ESP32)/config.py` after checking the real hardware.

| Setting | Current value | What to check |
|---|---:|---|
| `X_STEP_PIN`, `X_DIR_PIN`, `X_HOME_PIN` | `2`, `3`, `1` | Match the actual X wiring and ESP32-C3 board pinout. |
| `Z_STEP_PIN`, `Z_DIR_PIN`, `Z_HOME_PIN` | `6`, `8`, `9` | Match the actual Z wiring and board pinout. |
| `HOME_ACTIVE_LEVEL` | `0` | Match the electrical level when the switch is pressed. |
| `X_HOME_DIRECTION`, `Z_HOME_DIRECTION` | `-1`, `-1` | Point toward the physical home switches. |
| `X_DIR_INVERT`, `Z_DIR_INVERT` | `False`, `False` | Change only if an axis moves opposite to the expected direction. |
| `MOTOR_STEPS_PER_REV` | `400` | `400` is for a 0.9° motor; `200` is common for a 1.8° motor. |
| `MICROSTEP` | `8` | Must match the TB6600 DIP-switch setting. |
| `BELT_PITCH_MM` | `2.0` | Match the installed belt. |
| `X_PULLEY_TEETH`, `Z_PULLEY_TEETH` | `20`, `20` | Count the actual pulley teeth. |
| `X_POSITION_CALIBRATION`, `Z_POSITION_CALIBRATION` | `1.0`, `1.0` | Update after measuring real movement. |
| `X_MAX_MM`, `Z_MAX_MM` | `400.0`, `400.0` | Use safe measured travel, with clearance from hard stops. |
| `MOVE_SPEED_MM_S` | `10.0` | Increase only after safe low-speed testing. |
| `HOME_FAST_MM_S`, `HOME_SLOW_MM_S` | `5.0`, `1.0` | Keep homing slow and repeatable. |
| `HOME_BACKOFF_MM` | `5.0` | Must release the switch before the second approach. |
| `DEMO_SENSOR_MODE` | `True` | Set to `False` only after all sensor functions work. |

With the current motor and belt values, the theoretical calculation is:

```text
steps/mm = (400 motor steps × 8 microsteps) / (2.0 mm × 20 teeth)
         = 80 steps/mm
```

If a motor, belt, pulley, or driver setting is different, fix that setting first. Do not use the calibration factor to hide an incorrect hardware value.

## Safe first test

1. Check the mechanical assembly with all power off. The carriage should move freely by hand.
2. Confirm the switches are mounted before the carriage can hit a hard stop.
3. Check every wire against the board and driver manuals.
4. Copy these four files to the ESP32: `config.py`, `motor_control.py`, `sensors.py`, and `main.py`.
5. Reset the ESP32 and check that it prints `READY`.
6. With motor power off, connect the laptop and test `PING`.
7. Confirm the reply is `OK,PONG`.
8. Test each home switch by hand. A switch that is always active or never active must be fixed first.
9. Use low speeds and home one axis at a time. Keep the power disconnect within reach.
10. If an axis moves away from its switch, stop immediately. Check the motor wiring, `*_HOME_DIRECTION`, and `*_DIR_INVERT`.
11. After homing, send `POS`. It should report positions close to `0.000,0.000`.
12. Test small moves before testing the full travel.

Never test the travel limit by deliberately driving into a hard stop.

## Position calibration

Do this separately for X and Z.

1. Check the motor angle, pulley teeth, belt pitch, and microstep setting.
2. Leave the relevant calibration factor at `1.0`.
3. Home the axis.
4. Command a safe known distance, for example 100 mm.
5. Measure the actual distance with a ruler, dial indicator, or linear scale.
6. Calculate:

   ```text
   calibration factor = commanded distance / measured distance
   ```

7. Put the result in `X_POSITION_CALIBRATION` or `Z_POSITION_CALIBRATION`.
8. Restart the ESP32 so `main.py` recalculates steps/mm.
9. Repeat the test several times and in both directions.
10. Record the result and any backlash or repeatability error.

Example: if 100 mm commanded gives 99.2 mm actual:

```text
100 / 99.2 = 1.0081
```

Use measured values from the real machine. If the error changes depending on direction, investigate belt tension, pulley slip, backlash, or missed steps instead of only changing the calibration factor.

## Sensor setup and calibration

The sensor code is not finished yet. First record the exact part number, range, supply voltage, output type, interface, and units for each sensor. Check that its output is safe for the ESP32.

### Air speed

The code comments suggest this process for a hot-wire sensor:

1. Set several known wind-tunnel speeds using a calibrated reference anemometer.
2. At each speed, record the sensor voltage/ADC value and the reference speed.
3. Include zero flow and the normal operating range.
4. Plot the results and fit a calibration equation.
5. A hot-wire sensor may follow `E² = A + B·Uⁿ`, but determine `A`, `B`, and `n` from measurements.
6. Put the inverse equation into `read_air_speed()` and return m/s.
7. Test the equation with new reference points.

### Pressure

1. Confirm whether the sensor measures absolute, gauge, or differential pressure.
2. Label the high- and low-pressure ports.
3. Record the zero reading with equal pressure on both sides.
4. Apply several known pressures across the working range.
5. Fit the conversion, for example `pressure = a × voltage + b` only if the data supports it.
6. Put the conversion into `read_pressure()` and return Pa.

Do not exceed the pressure sensor's rated pressure. Check tubing for leaks.

### Temperature

Identify the sensor type first: analogue, thermistor, RTD, thermocouple, or digital. Implement the correct interface in `read_temperature()`. Compare it with a reference at several temperatures and allow the sensor to reach thermal equilibrium.

When all three sensors work, set `DEMO_SENSOR_MODE = False`, test `MEASURE`, and confirm the values are plausible before a scan.

## Running the laptop program

Install the laptop packages once:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pyserial pandas matplotlib
```

Edit the top of `pc (runs ON LAPTOP)/control.py`:

```python
SERIAL_PORT = "COM5"       # change to the ESP32 port
X_POSITIONS_MM = [10, 20]  # small test grid
Z_POSITIONS_MM = [10, 20]
SETTLE_TIME_S = 2.0
SAMPLES_PER_POINT = 20
SAMPLE_INTERVAL_S = 0.05
```

Change `SERIAL_PORT` if Windows assigns a different COM number. Keep the small grid until motion and limits are proven. Then run from the project root:

```powershell
python ".\pc (runs ON LAPTOP)\control.py"
```

The program will:

1. connect to the ESP32;
2. test the connection with `PING`;
3. home X and Z;
4. move to each X-Z position;
5. wait for the carriage to settle;
6. average the sensor readings;
7. save a CSV file and three plots.

The CSV is saved in `data/` with columns for timestamp, X, Z, speed, pressure, and temperature. The plot files are named `speed_distribution.png`, `pressure_distribution.png`, and `temperature_distribution.png`; each new scan overwrites the previous plots.

## Serial commands

These can be sent manually from a serial terminal:

| Command | Example reply | Meaning |
|---|---|---|
| `PING` | `OK,PONG` | Test communication. |
| `HOME` | `OK,HOME` | Home X, then Z. |
| `POS` | `OK,POS,0.000,0.000` | Show tracked position. |
| `MOVE,100,150` | `OK,MOVE,...` | Move to X=100 mm, Z=150 mm. |
| `MEASURE` | `OK,MEASURE,0,0,0` | Read speed, pressure, and temperature. |

Commands must end with a newline. Any error begins with `ERR,`.

## Common problems

| Problem | First things to check |
|---|---|
| No response | COM port, USB cable, baud rate, board reset, and whether another program has the port open. |
| `MOVE` rejected | The axes have not been homed, or the target is outside the configured limits. |
| Axis moves the wrong way | Motor wiring, `*_HOME_DIRECTION`, and `*_DIR_INVERT`. |
| Home switch not found | GPIO number, switch wiring, pull-up logic, active level, and switch position. |
| Position is wrong | Motor steps/rev, microstep DIP switches, belt pitch, pulley teeth, and calibration factor. |
| Measurements are all zero | This is expected with `DEMO_SENSOR_MODE = True`. |
| Sensor error after demo mode | Sensor functions are still placeholders. |
| Old plots disappear | Plot filenames are fixed and overwritten by the next run. |

## Future improvements

Before using the system as a finished experimental instrument, consider adding:

- physical positive-end switches and a hardware emergency stop;
- a home-switch diagnostic command;
- driver enable control and a safe state if serial communication is lost;
- acceleration/deceleration to reduce missed steps;
- coordinated X-Z movement;
- encoder or other position verification;
- completed sensor drivers, range checks, and calibration records;
- standard deviation and outlier reporting in the laptop program;
- timestamped plot filenames;
- automated tests and a dry-run simulation mode;
- wiring diagrams and calibration reports in `docs/`.

Keep a short record of the board, driver settings, motor, pulley/belt values, calibration factors, travel limits, sensor coefficients, and the date of the last successful test.
