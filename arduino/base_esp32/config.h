// This file contains settings specific to the ESP32
// connected to the base plate.
//
// It contains:
// - Motor A and Motor B pins
// - End-switch pins
// - Steps per revolution
// - Microstepping
// - Belt pitch
// - Drive pulley teeth
// - Travel limits
// - Position calibration
// - Movement speeds

#ifndef CONFIG_H
#define CONFIG_H


// ============================================================
// MOTOR AND MOTION SETTINGS
// ============================================================

// NEMA 17 motor:
// 0.9 degrees per full step
// 360 / 0.9 = 400 full steps per revolution
const int MOTOR_STEPS_PER_REV = 400;


// Microstepping setting used on the motor driver.
// IMPORTANT:
// This value must later match the physical DIP-switch
// setting on the motor driver.
const int MICROSTEP = 8;


// GT2 timing belt pitch
const float BELT_PITCH_MM = 2.0;


// ------------------------------------------------------------
// DRIVE PULLEYS
// ------------------------------------------------------------

// Number of teeth on the toothed pulley attached
// directly to the motor.
//
// Do NOT include the toothless idler/tensioner pulleys here.
//
// TODO:
// Replace these numbers once the actual drive-pulley
// tooth counts have been physically verified.
const int MOTOR_A_DRIVE_PULLEY_TEETH = 20;
const int MOTOR_B_DRIVE_PULLEY_TEETH = 20;


// ------------------------------------------------------------
// TRAVEL LIMITS
// ------------------------------------------------------------

// TODO:
// Verify actual usable travel experimentally.
const float X_MAX_MM = 400.0;
const float Z_MAX_MM = 400.0;


// ------------------------------------------------------------
// POSITION CALIBRATION
// ------------------------------------------------------------

// Start at 1.0.
// These values can later be adjusted after measuring
// the actual travelled distance.
const float X_POSITION_CALIBRATION = 1.0;
const float Z_POSITION_CALIBRATION = 1.0;


// ============================================================
// MOTOR DIRECTION SETTINGS
// ============================================================

// These allow us to reverse a motor's direction in software
// if the physical motor wiring/orientation causes the motor
// to rotate opposite to the expected direction.
//
// These should be verified experimentally tho.

const bool MOTOR_A_DIR_INVERT = false;
const bool MOTOR_B_DIR_INVERT = false;



// ============================================================
// MOTOR GPIO PINS
// ============================================================

// Motor A
const int MOTOR_A_STEP_PIN = -1;  // assign actual GPIO pin number
const int MOTOR_A_DIR_PIN = -1;   // assign actual GPIO pin number

// Motor B
const int MOTOR_B_STEP_PIN = -1;  // assign actual GPIO pin number
const int MOTOR_B_DIR_PIN = -1;   // assign actual GPIO pin number


// ============================================================
// LIMIT SWITCH GPIO PINS
// ============================================================

// Four physical end switches:
//
// X_MIN = left horizontal end
// X_MAX = right horizontal end
//
// Z_MIN = bottom of left vertical rail
// Z_MAX = top of left vertical rail


// Physical X-axis limits
const int X_MIN_LIMIT_PIN = -1;
const int X_MAX_LIMIT_PIN = -1;

// Physical Z-axis limits
const int Z_MIN_LIMIT_PIN = -1;
const int Z_MAX_LIMIT_PIN = -1;

// ============================================================
// HOMING SETTINGS
// ============================================================

// Faster speed used while searching for the home switch.
const float HOME_FAST_SPEED_MM_S = 10.0;

// Slower speed used for the final accurate approach.
const float HOME_SLOW_SPEED_MM_S = 2.0;

// Distance moved away from the switch before the
// final slow approach.
const float HOME_BACKOFF_MM = 3.0;

// Size of each movement while searching for the switch.
const float HOME_SEARCH_INCREMENT_MM = 1.0;

// Smaller increment used during the final slow approach.
const float HOME_FINE_INCREMENT_MM = 0.25;


// ============================================================
// MOVEMENT SPEED
// ============================================================

// Default carriage speed used for normal MOVE commands.
// This is an initial value and should be verified experimentally.

const float DEFAULT_MOVE_SPEED_MM_S = 10.0;

// ============================================================
// ESP-NOW WIRELESS COMMUNICATION
// ============================================================

// Both ESP32 devices must use the same Wi-Fi channel.

const int ESPNOW_WIFI_CHANNEL = 1;


// ============================================================
// SENSOR ESP32-C3 MAC ADDRESS
// ============================================================
//
// Replace these zeros with the real MAC address printed
// by the ESP32-C3.
//
// Example:
//
// AA:BB:CC:DD:EE:FF
//
// becomes:
//
// {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF}

const uint8_t SENSOR_ESP32C3_MAC[6] = {
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00
};


// Maximum time the base ESP32 waits for a sensor response.

const unsigned long SENSOR_RESPONSE_TIMEOUT_MS = 2000;


#endif