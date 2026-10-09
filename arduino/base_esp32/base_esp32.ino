// ============================================================
// BASE ESP32 - WIND TUNNEL TRAVERSER
// ============================================================
//
// This is the main program for the ESP32 mounted on the
// stationary base plate.
//
// Main responsibilities:
//
// - Communicate with the PC through USB serial
// - Control the CoreXZ traverser
// - Home the X and Z axes
// - Move to requested X/Z coordinates
// - Report the current position
//
// - Communicate wirelessly with the ESP32-C3 sensor node
// - Request air-speed, pressure and temperature measurements
//
// Most of the actual motor-control logic is located in
// motor_control.cpp.
// ============================================================


#include "config.h"
#include "motor_control.h"
#include "communication.h"
#include <WiFi.h>

// ============================================================
// CORE XZ CONTROLLER
// ============================================================

// Create one controller object for the complete CoreXZ system.

CoreXZController gantry;


// ============================================================
// SETUP
// ============================================================

void setup()
{
    // Start communication between the ESP32 and the PC.

    Serial.begin(115200);

    // Give the serial connection a moment to start.

    delay(1000);


    // --------------------------------------------------------
    // ESP-NOW SETUP
    // --------------------------------------------------------

    WiFi.mode(
        WIFI_STA
    );


    // Print the base ESP32 MAC address.
    //
    // The ESP32-C3 needs this address in its config.h.

    Serial.print(
        "Base ESP32 MAC address: "
    );

    Serial.println(
        WiFi.macAddress()
    );


    // Start wireless communication with the sensor ESP32-C3.

    bool wirelessReady =
    beginWirelessCommunication();
    if (!wirelessReady)
    {
        Serial.println(
            "WARN,Wireless sensor communication unavailable"
        );
    }


    // Configure motor-driver pins and end-switch pins.

    gantry.begin();


    // Tell the PC that the ESP32 firmware is running.

    Serial.println(
        "READY"
    );
}


// ============================================================
// POSITION RESPONSE
// ============================================================

void sendPosition()
{
    Serial.print("OK,POS,");

    Serial.print(
        gantry.getXPositionMM(),
        3
    );

    Serial.print(",");

    Serial.println(
        gantry.getZPositionMM(),
        3
    );
}


// ============================================================
// MOVE COMMAND
// ============================================================

void handleMoveCommand(
    String command
)
{
    // Expected command:
    //
    // MOVE,100,150
    //
    // means:
    //
    // X = 100 mm
    // Z = 150 mm


    // --------------------------------------------------------
    // FIND COMMAS
    // --------------------------------------------------------

    int firstComma =
        command.indexOf(',');

    int secondComma =
        command.indexOf(
            ',',
            firstComma + 1
        );


    // Check that both coordinates were supplied.

    if (
        firstComma < 0
        || secondComma < 0
    )
    {
        Serial.println(
            "ERR,MOVE requires X and Z positions"
        );

        return;
    }


    // --------------------------------------------------------
    // EXTRACT X AND Z VALUES
    // --------------------------------------------------------

    String xText =
        command.substring(
            firstComma + 1,
            secondComma
        );

    String zText =
        command.substring(
            secondComma + 1
        );


    float targetX =
        xText.toFloat();

    float targetZ =
        zText.toFloat();


    // --------------------------------------------------------
    // CHECK HOMING
    // --------------------------------------------------------

    if (!gantry.isHomed())
    {
        Serial.println(
            "ERR,System must be homed before MOVE"
        );

        return;
    }


    // --------------------------------------------------------
    // MOVE
    // --------------------------------------------------------

    bool movementCompleted =
    gantry.moveTo(
        targetX,
        targetZ,
        DEFAULT_MOVE_SPEED_MM_S
    );


if (!movementCompleted)
{
    Serial.println(
        "ERR,Movement interrupted or invalid"
    );

    return;
}

Serial.print("OK,MOVE,");

    Serial.print(
        gantry.getXPositionMM(),
        3
    );

    Serial.print(",");

    Serial.println(
        gantry.getZPositionMM(),
        3
    );
}


// ============================================================
// COMMAND PARSER
// ============================================================

void handleCommand(
    String command
)
{
    // Remove spaces and newline characters.

    command.trim();


    // --------------------------------------------------------
    // PING
    // --------------------------------------------------------
    //
    // Used by control.py to check that communication works.

    if (command == "PING")
    {
        Serial.println(
            "OK,PONG"
        );
    }


    // --------------------------------------------------------
    // HOME
    // --------------------------------------------------------

    else if (command == "HOME")
    {
        gantry.home();


        if (gantry.isHomed())
        {
            Serial.println(
                "OK,HOME"
            );
        }

        else
        {
            Serial.println(
                "ERR,Homing failed"
            );
        }
    }


    // --------------------------------------------------------
    // POSITION
    // --------------------------------------------------------

    else if (command == "POS")
    {
        sendPosition();
    }


    // --------------------------------------------------------
    // MOVE
    // --------------------------------------------------------

    else if (
        command.startsWith("MOVE,")
    )
    {
        handleMoveCommand(
            command
        );
    }


// --------------------------------------------------------
// MEASURE
// --------------------------------------------------------

else if (command == "MEASURE")
{
    float speed;
    float pressure;
    float temperature;


    bool success =
        requestSensorMeasurement(
            speed,
            pressure,
            temperature
        );


    if (!success)
    {
        Serial.println(
            "ERR,Sensor measurement failed"
        );

        return;
    }


    // Send the measurement to the PC using the same
    // format expected by control.py.

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
    // Check whether the PC has sent a serial command.

    if (
        Serial.available() > 0
    )
    {
        // Read everything up to the newline character.

        String command =
            Serial.readStringUntil('\n');


        // Process the received command.

        handleCommand(
            command
        );
    }
}