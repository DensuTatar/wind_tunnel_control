import serial
import time
import csv
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# USER SETTINGS
# ============================================================

# CHANGE THIS TO THE ESP32 COM PORT.
SERIAL_PORT = "COM5"

BAUD_RATE = 115200
#baud rate is the serial communication speed
#115200 basucally means 115200 bits/s
#concerns communication between laptop->USB->ESP
#how do you know if this number works?
#once you run control.py if you are able to send PING and then receive
#OK,PONG then serial communication is working


# ------------------------------------------------------------
# FIRST TEST GRID
# ------------------------------------------------------------
#
# Keep this deliberately small until homing, direction,
# steps/mm and travel limits have been physically verified.
#
# Later this will become the full wind-tunnel measurement grid.

X_POSITIONS_MM = [
    10,
    20
]

Z_POSITIONS_MM = [
    10,
    20
]


# Time allowed for carriage vibration to settle
# before taking measurements.

SETTLE_TIME_S = 2.0


# Number of measurements taken at each position.

SAMPLES_PER_POINT = 20


# Time between individual sensor samples.

SAMPLE_INTERVAL_S = 0.05


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent

DATA_DIRECTORY = (
    PROJECT_ROOT / "data"
)

DATA_DIRECTORY.mkdir(
    exist_ok=True
)


# ============================================================
# SERIAL CONNECTION
# ============================================================

def connect_to_esp32():

    print(
        f"Connecting to ESP32 on "
        f"{SERIAL_PORT}..."
    )

    esp = serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=10
    )

    # Many ESP32 boards reset when serial is opened.
    time.sleep(2)

    esp.reset_input_buffer()

    print("Serial connection opened.")

    return esp


# ============================================================
# SEND COMMAND
# ============================================================

def send_command(
    esp,
    command
):

    message = (
        command + "\n"
    )

    esp.write(
        message.encode()
    )

    response = (
        esp.readline()
        .decode()
        .strip()
    )

    if response == "":
        raise TimeoutError(
            f"No response to command: {command}"
        )

    if response.startswith("ERR"):
        raise RuntimeError(
            response
        )

    return response


# ============================================================
# CONNECTION TEST
# ============================================================

def test_connection(esp):

    response = send_command(
        esp,
        "PING"
    )

    if response != "OK,PONG":
        raise RuntimeError(
            "Unexpected ESP32 response: "
            + response
        )

    print(
        "ESP32 connection successful."
    )


# ============================================================
# HOMING
# ============================================================

def home_system(esp):

    print(
        "Homing X and Z axes..."
    )

    response = send_command(
        esp,
        "HOME"
    )

    if response != "OK,HOME":
        raise RuntimeError(
            "Unexpected homing response: "
            + response
        )

    print(
        "Homing complete."
    )


# ============================================================
# MOVEMENT
# ============================================================

def move_to(
    esp,
    x_mm,
    z_mm
):

    print(
        f"Moving to "
        f"X={x_mm:.1f} mm, "
        f"Z={z_mm:.1f} mm"
    )

    command = (
        f"MOVE,{x_mm},{z_mm}"
    )

    response = send_command(
        esp,
        command
    )

    if not response.startswith(
        "OK,MOVE"
    ):
        raise RuntimeError(
            "Unexpected movement response: "
            + response
        )


# ============================================================
# SINGLE MEASUREMENT
# ============================================================

def measure_once(esp):

    response = send_command(
        esp,
        "MEASURE"
    )

    parts = response.split(",")

    if (
        len(parts) != 5
        or parts[0] != "OK"
        or parts[1] != "MEASURE"
    ):

        raise RuntimeError(
            "Invalid measurement response: "
            + response
        )

    speed = float(
        parts[2]
    )

    pressure = float(
        parts[3]
    )

    temperature = float(
        parts[4]
    )

    return (
        speed,
        pressure,
        temperature
    )


# ============================================================
# AVERAGED MEASUREMENT
# ============================================================

def measure_average(esp):

    speeds = []
    pressures = []
    temperatures = []

    for _ in range(
        SAMPLES_PER_POINT
    ):

        (
            speed,
            pressure,
            temperature
        ) = measure_once(esp)

        speeds.append(
            speed
        )

        pressures.append(
            pressure
        )

        temperatures.append(
            temperature
        )

        time.sleep(
            SAMPLE_INTERVAL_S
        )


    average_speed = (
        sum(speeds)
        / len(speeds)
    )

    average_pressure = (
        sum(pressures)
        / len(pressures)
    )

    average_temperature = (
        sum(temperatures)
        / len(temperatures)
    )


    return (
        average_speed,
        average_pressure,
        average_temperature
    )


# ============================================================
# CREATE OUTPUT FILE
# ============================================================

def create_output_file():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        DATA_DIRECTORY
        / f"wind_tunnel_{timestamp}.csv"
    )

    return filename


# ============================================================
# AUTOMATED SCAN
# ============================================================
# Automatically moves the probe through all defined X-Z positions,
# waits for the carriage to settle, takes averaged sensor measurements,
# and saves the position, time, air speed, pressure, and temperature
# to a CSV file.


def run_scan(
    esp,
    output_file
):

    print(
        "\nStarting measurement scan.\n"
    )

    with open(
        output_file,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow([
            "timestamp",
            "x_mm",
            "z_mm",
            "speed_ms",
            "pressure_pa",
            "temperature_c"
        ])


        for z_mm in Z_POSITIONS_MM:

            for x_mm in X_POSITIONS_MM:

                move_to(
                    esp,
                    x_mm,
                    z_mm
                )

                print(
                    f"Waiting "
                    f"{SETTLE_TIME_S} s "
                    "for carriage to settle..."
                )

                time.sleep(
                    SETTLE_TIME_S
                )


                (
                    speed,
                    pressure,
                    temperature
                ) = measure_average(
                    esp
                )

                
                timestamp = (
                    datetime.now()
                    .isoformat(
                        timespec="seconds"
                    )
                )


                writer.writerow([
                    timestamp,
                    x_mm,
                    z_mm,
                    speed,
                    pressure,
                    temperature
                ])


                # Immediately write the newest data to the file.
                file.flush()


                print(
                    f"X={x_mm:.1f} mm | "
                    f"Z={z_mm:.1f} mm | "
                    f"U={speed:.3f} m/s | "
                    f"P={pressure:.3f} Pa | "
                    f"T={temperature:.3f} °C"
                )


    print(
        "\nScan complete."
    )

    print(
        f"Data saved to:\n"
        f"{output_file}"
    )


# ============================================================
# PLOTTING
# ============================================================

def plot_distribution(
    data,
    column,
    label,
    title,
    output_name
):

    plt.figure(
        figsize=(7, 6)
    )

    plot = plt.scatter(
        data["x_mm"],
        data["z_mm"],
        c=data[column],
        s=180
    )

    plt.colorbar(
        plot,
        label=label
    )

    plt.xlabel(
        "X position [mm]"
    )

    plt.ylabel(
        "Z position [mm]"
    )

    plt.title(
        title
    )

    plt.axis(
        "equal"
    )

    plt.grid(
        True
    )

    plt.tight_layout()


    figure_path = (
        DATA_DIRECTORY
        / output_name
    )

    plt.savefig(
        figure_path,
        dpi=300
    )

    plt.show()


# ============================================================
# CREATE ALL PLOTS
# ============================================================

def create_plots(
    output_file
):

    data = pd.read_csv(
        output_file
    )


    plot_distribution(
        data=data,
        column="speed_ms",
        label="Air speed [m/s]",
        title="Air Speed Distribution",
        output_name="speed_distribution.png"
    )


    plot_distribution(
        data=data,
        column="pressure_pa",
        label="Pressure [Pa]",
        title="Pressure Distribution",
        output_name="pressure_distribution.png"
    )


    plot_distribution(
        data=data,
        column="temperature_c",
        label="Temperature [°C]",
        title="Temperature Distribution",
        output_name="temperature_distribution.png"
    )


# ============================================================
# MAIN PROGRAM
# ============================================================
# Main PC-side program.
# Connects to the ESP32, checks communication, homes the traverser,
# creates the output file, performs the automated measurement scan,
# generates plots, and safely closes the serial connection.
def main():

    esp = None

    try:

        esp = connect_to_esp32()

        test_connection(
            esp
        )

        home_system(
            esp
        )

        output_file = (
            create_output_file()
        )

        run_scan(
            esp,
            output_file
        )

        create_plots(
            output_file
        )


        print(
            "\nWind tunnel measurement "
            "procedure completed."
        )


    except KeyboardInterrupt:

        print(
            "\nProgram stopped by user."
        )


    except Exception as error:

        print(
            "\nERROR:"
        )

        print(
            error
        )


    finally:

        if esp is not None:
            esp.close()

            print(
                "Serial connection closed."
            )


if __name__ == "__main__":

    main()