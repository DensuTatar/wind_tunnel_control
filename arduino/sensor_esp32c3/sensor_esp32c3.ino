// ============================================================
// ESP32-C3 SENSOR NODE - WIND TUNNEL
// ============================================================
//
// This is the main program for the ESP32-C3 mounted on the
// moving part of the traverser.
//
// Main responsibilities:
//
// - Read the wind-tunnel sensors
// - Return air speed, pressure and temperature
// - Allow simple testing through USB serial
//
// Later:
// - Receive measurement requests wirelessly from the base ESP32
// - Send measurement results wirelessly back to the base ESP32
//
// The actual sensor-reading functions are located in sensors.cpp.
// ============================================================


#include "config.h"
#include "sensors.h"
#include <WiFi.h>
#include "communication.h"


// ============================================================
// SETUP
// ============================================================

void setup()
{
    // Start serial communication.
    //
    // For now this is mainly used to test the ESP32-C3
    // directly from a computer.

    Serial.begin(
        SERIAL_BAUD_RATE
    );


    // Give the serial connection time to start.

    delay(1000);

    // --------------------------------------------------------
    // PREPARE WI-FI FOR ESP-NOW
    // --------------------------------------------------------
    //
    // ESP-NOW uses the ESP32 Wi-Fi hardware.
    // WIFI_STA means Station Mode.
    //
    // We are NOT connecting to a normal Wi-Fi network here.

    WiFi.mode(
        WIFI_STA
    );


    // --------------------------------------------------------
    // PRINT ESP32-C3 MAC ADDRESS
    // --------------------------------------------------------
    //
    // Every ESP32 has its own MAC address.
    // The base ESP32 will later use this address to identify
    // and communicate with this sensor ESP32-C3.

    Serial.print(
        "Sensor ESP32-C3 MAC address: "
    );

    Serial.println(
        WiFi.macAddress()
    );

    // Start ESP-NOW communication with the base ESP32.

     beginWirelessCommunication();


    // Tell the user that the ESP32-C3 is running.

    Serial.println(
        "SENSOR_READY"
    );
}


// ============================================================
// MEASUREMENT RESPONSE
// ============================================================

void sendMeasurement()
{
    float speed;
    float pressure;
    float temperature;


    // Read all available sensors.

    readAll(
        speed,
        pressure,
        temperature
    );


    // --------------------------------------------------------
    // CHECK FOR INVALID SENSOR VALUES
    // --------------------------------------------------------

    if (
        isnan(speed)
        || isnan(pressure)
        || isnan(temperature)
    )
    {
        Serial.println(
            "ERR,Sensor measurement not available"
        );

        return;
    }


    // --------------------------------------------------------
    // SEND MEASUREMENT
    // --------------------------------------------------------
    //
    // Response format:
    //
    // OK,MEASURE,speed,pressure,temperature
    //
    // Example:
    //
    // OK,MEASURE,12.450000,84.200000,22.700000

    Serial.print(
        "OK,MEASURE,"
    );


    Serial.print(
        speed,
        6
    );

    Serial.print(",");


    Serial.print(
        pressure,
        6
    );

    Serial.print(",");


    Serial.println(
        temperature,
        6
    );
}


// ============================================================
// COMMAND PARSER
// ============================================================
//
// For now this command parser is used for direct USB testing.
//
// Later the same commands can also be received from the
// base ESP32 through wireless communication.

void handleCommand(
    String command
)
{
    // Remove extra spaces and newline characters.

    command.trim();


    // --------------------------------------------------------
    // PING
    // --------------------------------------------------------

    if (command == "PING")
    {
        Serial.println(
            "OK,PONG"
        );
    }


    // --------------------------------------------------------
    // MEASURE
    // --------------------------------------------------------

    else if (command == "MEASURE")
    {
        sendMeasurement();
    }


    // --------------------------------------------------------
    // UNKNOWN COMMAND
    // --------------------------------------------------------

    else
    {
        Serial.println(
            "ERR,Unknown command"
        );
    }
}


// ============================================================
// MAIN LOOP
// ============================================================

void loop()
{
    // For now, check whether a command has arrived through
    // the USB serial connection.

    if (
        Serial.available() > 0
    )
    {
        String command =
            Serial.readStringUntil('\n');


        handleCommand(
            command
        );
    }


    // --------------------------------------------------------
    // ESP-NOW COMMUNICATION
    // --------------------------------------------------------

    processWirelessCommunication();
}