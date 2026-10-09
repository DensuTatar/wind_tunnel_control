#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>


// ============================================================
// ESP-NOW COMMUNICATION - BASE ESP32
// ============================================================
//
// Handles wireless communication between:
//
// Base ESP32
//     ⇅ ESP-NOW
// Sensor ESP32-C3
//
// Main purpose:
// Ask the sensor ESP32-C3 for a measurement and receive
// air speed, pressure and temperature.
// ============================================================


// Starts ESP-NOW and registers the ESP32-C3 as a peer.
//
// true  = successful
// false = failed

bool beginWirelessCommunication();


// Sends a MEASURE request to the ESP32-C3.
//
// If a valid response is received, the measured values are
// returned through speed, pressure and temperature.
//
// true  = measurement received successfully
// false = communication failed or timed out

bool requestSensorMeasurement(
    float &speed,
    float &pressure,
    float &temperature
);


// Returns whether ESP-NOW initialization succeeded.

bool wirelessCommunicationReady();


#endif