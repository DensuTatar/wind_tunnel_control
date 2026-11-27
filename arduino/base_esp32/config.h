#pragma once
// Hardware values based on the verified FluidNC config(3).yaml and measured travel.
// This is CUSTOM firmware; none of the FluidNC code executes here.
// Leave false for initial bench testing (PING, LIMITS, MODE, MEASURE).
// Enable only after verifying DIR levels, driver wiring, switch states and physical stop.
constexpr bool MOTION_ENABLED = true;
constexpr int MOTOR_STEPS_PER_REV = 400;
constexpr int MICROSTEP = 16; // inferred from measured 160 steps/mm; check driver DIP table
constexpr float BELT_PITCH_MM = 2.0f;
constexpr int DRIVE_PULLEY_TEETH = 20;
constexpr float STEPS_PER_MM = MOTOR_STEPS_PER_REV * MICROSTEP / (BELT_PITCH_MM * DRIVE_PULLEY_TEETH);
constexpr float X_MAX_MM = 344.0f, Z_MAX_MM = 310.0f;
constexpr float X_POSITION_CALIBRATION = 1.0f, Z_POSITION_CALIBRATION = 1.0f;
// Positive motor direction is LOW with these settings. Verify with drivers disconnected.
constexpr bool MOTOR_A_DIR_INVERT = true, MOTOR_B_DIR_INVERT = true;
constexpr int MOTOR_A_STEP_PIN = 26, MOTOR_A_DIR_PIN = 27;
constexpr int MOTOR_B_STEP_PIN = 32, MOTOR_B_DIR_PIN = 33;
constexpr int X_MIN_LIMIT_PIN = 18, Z_MIN_LIMIT_PIN = 19;
constexpr int X_MAX_LIMIT_PIN = -1, Z_MAX_LIMIT_PIN = -1; // optional, not installed
constexpr bool LIMIT_ACTIVE_LOW = true;
constexpr float MAX_FEED_MM_MIN = 12400.0f;
constexpr float DEFAULT_FEED_MM_MIN = 60.0f;
constexpr float ACCELERATION_MM_S2 = 600.0f;
constexpr float HOME_SEEK_MM_MIN = 1000.0f, HOME_FEED_MM_MIN = 100.0f;
constexpr float HOME_PULLOFF_MM = 2.0f;
constexpr unsigned HOME_SETTLE_MS = 250;
constexpr unsigned STEP_PULSE_US = 10, DIR_SETUP_US = 10;
constexpr unsigned HEARTBEAT_TIMEOUT_MS = 2000; // host sends '~' while moving
// No ENA toggling: drivers remain enabled/holding. Mechanically secure vertical load.
// Real sensor GPIOs/calibration remain unassigned until verified electrically.
constexpr int AIR_SPEED_SENSOR_PIN = -1, PRESSURE_SENSOR_PIN = -1, TEMPERATURE_SENSOR_PIN = -1;
constexpr float VOLTAGE_DIVIDER_RATIO = 5.0f; // placeholder, NOT a wiring recommendation
constexpr bool DEMO_SENSOR_MODE = false;
