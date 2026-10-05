import sys

from config import *

from motor_control import Axis

from sensors import read_all


# ============================================================
# CALCULATE STEPS PER MM
# ============================================================

def calculate_steps_per_mm(
    pulley_teeth,
    calibration
):

    belt_travel_per_rev = (
        BELT_PITCH_MM
        * pulley_teeth
    )

    steps_per_rev = (
        MOTOR_STEPS_PER_REV
        * MICROSTEP
    )

    theoretical_steps_per_mm = (
        steps_per_rev
        / belt_travel_per_rev
    )

    return (
        theoretical_steps_per_mm
        * calibration
    )


X_STEPS_PER_MM = calculate_steps_per_mm(
    X_PULLEY_TEETH,
    X_POSITION_CALIBRATION
)

Z_STEPS_PER_MM = calculate_steps_per_mm(
    Z_PULLEY_TEETH,
    Z_POSITION_CALIBRATION
)


# ============================================================
# CREATE AXES
# ============================================================

x_axis = Axis(
    name="X",
    step_pin=X_STEP_PIN,
    dir_pin=X_DIR_PIN,
    home_pin=X_HOME_PIN,
    steps_per_mm=X_STEPS_PER_MM,
    max_mm=X_MAX_MM,
    home_direction=X_HOME_DIRECTION,
    home_active_level=HOME_ACTIVE_LEVEL,
    dir_invert=X_DIR_INVERT
)

z_axis = Axis(
    name="Z",
    step_pin=Z_STEP_PIN,
    dir_pin=Z_DIR_PIN,
    home_pin=Z_HOME_PIN,
    steps_per_mm=Z_STEPS_PER_MM,
    max_mm=Z_MAX_MM,
    home_direction=Z_HOME_DIRECTION,
    home_active_level=HOME_ACTIVE_LEVEL,
    dir_invert=Z_DIR_INVERT
)


# ============================================================
# COMMAND FUNCTIONS
# ============================================================

def home_system():

    x_axis.home(
        HOME_FAST_MM_S,
        HOME_SLOW_MM_S,
        HOME_BACKOFF_MM
    )

    z_axis.home(
        HOME_FAST_MM_S,
        HOME_SLOW_MM_S,
        HOME_BACKOFF_MM
    )


def move_system(x_mm, z_mm):

    # First X, then Z.
    # Simultaneous movement needs to be looked into if desired to be implemented.

    x_axis.move_to_mm(
        x_mm,
        MOVE_SPEED_MM_S
    )

    z_axis.move_to_mm(
        z_mm,
        MOVE_SPEED_MM_S
    )


def position_string():

    return (
        f"{x_axis.get_position_mm():.3f},"
        f"{z_axis.get_position_mm():.3f}"
    )


# ============================================================
# COMMAND PARSER
# ============================================================

def handle_command(command):

    parts = command.strip().split(",")

    command_name = parts[0].upper()


    # --------------------------------------------------------
    # TEST CONNECTION
    # --------------------------------------------------------

    if command_name == "PING":

        print("OK,PONG")


    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    elif command_name == "HOME":

        home_system()

        print("OK,HOME")


    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    elif command_name == "POS":

        print(
            "OK,POS,"
            + position_string()
        )


    # --------------------------------------------------------
    # MOVE
    # Example:
    # MOVE,100,150
    # --------------------------------------------------------

    elif command_name == "MOVE":

        if len(parts) != 3:    #checking that the command has 3 parts. you need move, x coord, z coord
            raise ValueError(
                "MOVE requires X and Z positions"
            )

        x_target = float(parts[1])

        z_target = float(parts[2])

        move_system(
            x_target,
            z_target
        )

        print(
            "OK,MOVE,"
            + position_string()
        )


    # --------------------------------------------------------
    # MEASURE
    # --------------------------------------------------------

    elif command_name == "MEASURE":

        speed, pressure, temperature = (
            read_all()
        )

        print(
            "OK,MEASURE,"
            f"{speed:.6f},"
            f"{pressure:.6f},"
            f"{temperature:.6f}"
        )

    #after this measuring, you get a line on your PC and the first one is OK, MEASURE, 
    #then speed, pressure, and the final number temperature


    # --------------------------------------------------------
    # UNKNOWN COMMAND
    # --------------------------------------------------------

    else:

        raise ValueError(
            "Unknown command"
        )


# ============================================================
# MAIN LOOP
# ============================================================

# Main program loop.
# Continuously waits for commands from the PC, sends each
# command to the command parser, and reports any errors
# without stopping the ESP32 program.

print("READY")  #means the ESP has started correctly and is ready to receive commands


while True:

    try:

        line = sys.stdin.readline()

        if not line:
            continue

        handle_command(line)

    except Exception as error:

        print(
            "ERR,"
            + str(error)
        )