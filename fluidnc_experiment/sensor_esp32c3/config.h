#ifndef CONFIG_H
#define CONFIG_H
// Sensor-only USB controller. Assign after checking interface and ratings.
const int AIR_SPEED_SENSOR_PIN = -1;
const int PRESSURE_SENSOR_PIN = -1;
const int TEMPERATURE_SENSOR_PIN = -1;
const float VOLTAGE_DIVIDER_RATIO = 5.0; // placeholder; verify hardware
const bool DEMO_SENSOR_MODE = false;
#endif
