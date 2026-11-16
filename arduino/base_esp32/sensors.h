#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>
#include "config.h"


// ============================================================
// SENSOR READING FUNCTIONS
// ============================================================
//
// These functions provide a simple interface for reading
// the sensors connected to the ESP32-C3.
//
// The actual reading and calibration logic is written
// in sensors.cpp.
// ============================================================


// ------------------------------------------------------------
// AIR SPEED
// ------------------------------------------------------------
//
// Returns air speed in m/s.

float readAirSpeed();


// ------------------------------------------------------------
// PRESSURE
// ------------------------------------------------------------
//
// Returns pressure in Pa.

float readPressure();


// ------------------------------------------------------------
// TEMPERATURE
// ------------------------------------------------------------
//
// Returns temperature in degrees Celsius.

float readTemperature();


// ------------------------------------------------------------
// READ ALL SENSORS
// ------------------------------------------------------------
//
// Reads all available sensors in one function.
//
// The measured values are returned through the variables
// speed, pressure and temperature.

void readAll(
    float &speed,
    float &pressure,
    float &temperature
);


#endif