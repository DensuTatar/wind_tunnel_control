#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>


// ============================================================
// ESP-NOW WIRELESS COMMUNICATION
// ============================================================
//
// This file defines the wireless communication functions
// used by the moving ESP32-C3 sensor node.
//
// Communication path:
//
// ESP32-C3 sensor node
//        ⇅ ESP-NOW
// Base ESP32
//        ⇅ USB
// Computer
//
// The actual ESP-NOW implementation is located in
// communication.cpp.
// ============================================================


// ------------------------------------------------------------
// INITIALIZE COMMUNICATION
// ------------------------------------------------------------
//
// Starts ESP-NOW, configures the Wi-Fi channel and prepares
// communication with the base ESP32.
//
// Returns:
// true  = initialization successful
// false = initialization failed

bool beginWirelessCommunication();


// ------------------------------------------------------------
// PROCESS RECEIVED COMMANDS
// ------------------------------------------------------------
//
// Checks whether the base ESP32 has requested something.
//
// For example:
//
// MEASURE
//
// This function should be called repeatedly from loop().

void processWirelessCommunication();


// ------------------------------------------------------------
// SEND MESSAGE
// ------------------------------------------------------------
//
// Sends a text message from the ESP32-C3 to the base ESP32.
//
// Example:
//
// OK,MEASURE,12.4,83.2,22.7

bool sendWirelessMessage(
    const char* message
);


// ------------------------------------------------------------
// COMMUNICATION STATUS
// ------------------------------------------------------------
//
// Returns true after ESP-NOW has been initialized successfully.

bool wirelessCommunicationReady();


#endif