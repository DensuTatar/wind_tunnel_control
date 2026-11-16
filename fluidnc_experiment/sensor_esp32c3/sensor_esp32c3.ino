#include <Arduino.h>
#include <math.h>
#include "sensors.h"

void setup() {
    Serial.begin(115200);
    Serial.println("READY");
}

void loop() {
    if (!Serial.available()) return;
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command == "PING") {
        Serial.println("OK,PONG");
    } else if (command == "MODE") {
        Serial.println(DEMO_SENSOR_MODE ? "OK,MODE,DEMO" : "OK,MODE,REAL");
    } else if (command == "MEASURE") {
        float speed, pressure, temperature;
        readAll(speed, pressure, temperature);
        if (!isfinite(speed) || !isfinite(pressure) || !isfinite(temperature)) {
            Serial.println("ERR,Sensor measurement not available");
            return;
        }
        Serial.print("OK,MEASURE,"); Serial.print(speed, 6);
        Serial.print(','); Serial.print(pressure, 6);
        Serial.print(','); Serial.println(temperature, 6);
    } else {
        Serial.println("ERR,Unknown command");
    }
}
