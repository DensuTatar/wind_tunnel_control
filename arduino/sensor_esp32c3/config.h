// ============================================================
// ESP32-C3 SENSOR NODE CONFIGURATION
// ============================================================
//
// This file contains settings specific to the ESP32-C3
// mounted on the moving part of the traverser.
//
// Main responsibilities of the ESP32-C3:
//
// - Read the air-speed sensor / flow module
// - Read the pressure sensor
// - Read temperature in the future
// - Apply sensor calibration
// - Send measurements wirelessly to the base ESP32
//
// Motor control is NOT handled by this ESP32-C3.
// ============================================================


#ifndef CONFIG_H
#define CONFIG_H


// ============================================================
// DEBUG SERIAL CONNECTION
// ============================================================
//
// Used when the ESP32-C3 is connected directly to a computer
// during testing.

const unsigned long SERIAL_BAUD_RATE = 115200;


// ============================================================
// SENSOR GPIO PINS
// ============================================================
//
// IMPORTANT:
// Replace the placeholder -1 with the actual ESP32-C3 GPIO numbers once
// the final wiring has been confirmed.
//
// Do not guess the GPIO values.


// Air-speed / flow sensor signal
const int AIR_SPEED_SENSOR_PIN = -1;      // TODO


// Pressure sensor signal
const int PRESSURE_SENSOR_PIN = -1;       // TODO


// Temperature sensor
//
// This is included for future expansion.
const int TEMPERATURE_SENSOR_PIN = -1;    // TODO


// ============================================================
// VOLTAGE DIVIDER
// ============================================================
//
// The current electronics design includes a voltage divider
// before the ESP32-C3 analog input.
//
// The flow module may produce a signal higher than the voltage
// that should be applied directly to the ESP32 ADC.
//
// If the divider reduces the sensor voltage by a factor of 5:
//
//     V_ESP32 = V_SENSOR / 5
//
// therefore:
//
//     V_SENSOR = V_ESP32 * 5
//
// TODO:
// Verify the final resistor values and divider ratio before use.

const float VOLTAGE_DIVIDER_RATIO = 5.0;


// ============================================================
// SENSOR CALIBRATION
// ============================================================
//
// The calibration equations are not known yet.
//
// These values/functions will be added once the actual sensors
// have been selected and calibrated.
//
// Example future relationship:
//
// Air speed:
//     U = f(V)
//
// Pressure:
//     P = f(V)


// ============================================================
// DEMO / TEST MODE
// ============================================================
//
// While the real sensors and calibration equations are still
// being developed, demo mode prevents unfinished sensor code
// from being treated as real measurements.
//
// Change to false only when the real sensor interfaces
// have been implemented.

const bool DEMO_SENSOR_MODE = true;

// ============================================================
// ESP-NOW WIRELESS COMMUNICATION
// ============================================================

// Both ESP32 devices must use the same Wi-Fi channel.
// This is an initial value for the direct ESP-NOW connection.

const int ESPNOW_WIFI_CHANNEL = 1;


// ============================================================
// BASE ESP32 MAC ADDRESS
// ============================================================
//
// This identifies the stationary/base ESP32.
//
// Replace these zeros with the real MAC address printed
// by the base ESP32 before testing ESP-NOW.
//
// Example MAC:
// 24:6F:28:AB:CD:EF
//
// becomes:
//
// {0x24, 0x6F, 0x28, 0xAB, 0xCD, 0xEF}

const uint8_t BASE_ESP32_MAC[6] = {
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00
};



#endif