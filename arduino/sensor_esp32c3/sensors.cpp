// ============================================================
// SENSOR READING - ESP32-C3
// ============================================================
//
// This file contains the actual sensor-reading functions.
//
// The final sensor interfaces and calibration equations are
// going to be put in once determined.
//
// DEMO_SENSOR_MODE can be used while developing the rest of
// the software without treating placeholder values as real data.
// ============================================================


#include "sensors.h"
#include <math.h>


// ============================================================
// AIR SPEED
// ============================================================

float readAirSpeed()
{
    // --------------------------------------------------------
    // DEMO MODE
    // --------------------------------------------------------

    if (DEMO_SENSOR_MODE)
    {
        return 0.0;
    }


    // --------------------------------------------------------
    // SAFETY CHECK
    // --------------------------------------------------------

    if (AIR_SPEED_SENSOR_PIN < 0)
    {
        // GPIO has not yet been assigned.
        return NAN;
    }


    // --------------------------------------------------------
    // TODO: REAL AIR-SPEED SENSOR
    // --------------------------------------------------------
    //
    // Eventually this function should:
    //
    // 1. Read the raw sensor signal
    //
    // 2. Convert the ADC reading to voltage
    //
    // 3. Correct for the voltage divider
    //
    //       V_sensor =
    //       V_ESP32 * VOLTAGE_DIVIDER_RATIO
    //
    // 4. Apply the air-speed calibration equation
    //
    //       U = f(V_sensor)
    //
    // 5. Return air speed in m/s
    //
    // The exact ADC conversion and calibration equation
    // depend on the final selected sensor.


    return NAN;
}


// ============================================================
// PRESSURE
// ============================================================

float readPressure()
{
    if (DEMO_SENSOR_MODE)
    {
        return 0.0;
    }


    if (PRESSURE_SENSOR_PIN < 0)
    {
        return NAN;
    }


    // --------------------------------------------------------
    // TODO: REAL PRESSURE SENSOR
    // --------------------------------------------------------
    //
    // Eventually:
    //
    // 1. Read raw pressure-sensor signal
    // 2. Convert ADC value to voltage if required
    // 3. Apply the pressure calibration equation
    // 4. Return pressure in Pa


    return NAN;
}


// ============================================================
// TEMPERATURE
// ============================================================

float readTemperature()
{
    if (DEMO_SENSOR_MODE)
    {
        return 0.0;
    }


    if (TEMPERATURE_SENSOR_PIN < 0)
    {
        return NAN;
    }


    // --------------------------------------------------------
    // TODO: REAL TEMPERATURE SENSOR
    // --------------------------------------------------------
    //
    // The exact implementation depends on the final
    // temperature sensor.
    //
    // Eventually this function should return temperature
    // in degrees Celsius.


    return NAN;
}


// ============================================================
// READ ALL SENSORS
// ============================================================

void readAll(
    float &speed,
    float &pressure,
    float &temperature
)
{
    speed =
        readAirSpeed();

    pressure =
        readPressure();

    temperature =
        readTemperature();
}