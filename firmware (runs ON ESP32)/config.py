#Which GPIO controls STEP?
#Which GPIO controls DIR?
#Which pin reads the home switch?
#How many motor steps are one revolution?
#What microstepping setting is used?
#How many pulley revolutions correspond to 1 mm?
#What is the allowed travel?


# ============================================================
# WIND TUNNEL TRAVERSER CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# ESP32 GPIO PINS
# ------------------------------------------------------------

#X-axis TB6600


X_STEP_PIN = 2 #ESP32 GPIO connected to the TB6600 STEP/PUL input
X_DIR_PIN = 3 #ESP32 GPIO connected to the TB6600 DIR input
X_HOME_PIN = 1#ESP32 GPIO connected to the X-axis home/end switch

#Z-axis TB6600
Z_STEP_PIN = 6 #ESP32 GPIO connected to the TB6600 STEP/PUL input
Z_DIR_PIN = 8 #ESP32 GPIO connected to the TB6600 DIR input
Z_HOME_PIN = 9 #ESP32 GPIO connected to the Z-axis home/end switch


# ------------------------------------------------------------
# HOME / END SWITCHES
# ------------------------------------------------------------

# Electrical logic level that means the switch is triggered
HOME_ACTIVE_LEVEL = 0

# Direction in which each axis must move to find its home switch
# might change later but for x-axis:
# left = -1
# right = +1
# depends on where we put the switches again but for z-axis
#down = -1
# up = +1
X_HOME_DIRECTION = -1
Z_HOME_DIRECTION = -1

#in the end contains info about:
# which GPIO is connected to the swtich?
# how should that switch behave?


# ------------------------------------------------------------
# MOTOR DIRECTION
# ------------------------------------------------------------

# Change these if the physical movement is opposite to
# the direction expected by the software.

X_DIR_INVERT = False
Z_DIR_INVERT = False

# ------------------------------------------------------------
# MOTOR AND BELT GEOMETRY
# ------------------------------------------------------------

# Selected motor:
# 0.9 degrees per full step
# 360 / 0.9 = 400 full steps per revolution

MOTOR_STEPS_PER_REV = 400

# IMPORTANT:
# Must match the DIP switch microstepping setting on TB6600.
#
# Example:
# 1 = full step
# 2 = 1/2
# 4 = 1/4
# 8 = 1/8
# 16 = 1/16
# 32 = 1/32

MICROSTEP = 8

# GT2 belt:
BELT_PITCH_MM = 2.0

# VERIFY THESE VALUES ON THE REAL PULLEYS.
X_PULLEY_TEETH = 20
Z_PULLEY_TEETH = 20

# ------------------------------------------------------------
# POSITION CALIBRATION
# ------------------------------------------------------------

# Initially 1.0.
# These can later be corrected after measuring actual travel.
# so these are callibration factors that need to be changed later on:
# command the carriage to move in one direction for example horizontal 100 mm,
# then measure how far it has moved IRL and then divide the commanded distance by
# the real life one. and there you have your callibration factor for X direction.
# need to do the same for Z axis of course.
X_POSITION_CALIBRATION = 1.0  
Z_POSITION_CALIBRATION = 1.0

# ------------------------------------------------------------
# TRAVEL LIMITS
# ------------------------------------------------------------

# VERIFY THESE ON THE REAL TRAVERSER. Might also be 350 mm
# Example values based on approximately 400 mm usable travel.

X_MAX_MM = 400.0
Z_MAX_MM = 400.0

# ------------------------------------------------------------
# MOVEMENT SPEEDS
# ------------------------------------------------------------

# Initial conservative values.
# These can be increased after testing.

MOVE_SPEED_MM_S = 10.0

HOME_FAST_MM_S = 5.0
HOME_SLOW_MM_S = 1.0

# Distance moved away from switch before slow second approach.
HOME_BACKOFF_MM = 5.0

# ------------------------------------------------------------
# SENSOR TEST MODE
# ------------------------------------------------------------

# True = software can be tested before real sensors are ready.
# Measurements will return zero and MUST NOT be treated as
# experimental data.
#
# Set to False after actual sensor functions are implemented.

DEMO_SENSOR_MODE = True