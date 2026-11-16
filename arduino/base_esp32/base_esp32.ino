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
// - Acquire sensor data through wired connections
// - Read air-speed, pressure and temperature measurements
// - Return sensor measurements to the PC
//
// Most of the actual motor-control logic is located in
// motor_control.cpp.
// ============================================================


#include "config.h"
#include "motor_control.h"
#include "sensors.h"
#include <math.h>

// ============================================================
// CORE XZ CONTROLLER
// ============================================================

// Create one controller object for the complete CoreXZ system.

CoreXZController gantry;

// ============================================================
// MOTION GPIO SAFETY CHECK
// ============================================================

// This function checks whether:
//- All motion-related GPIO pins have been assigned.
//- No two motion-related components have been assigned the same GPIO pin.
static bool motionReady = false;

static bool motionPinsConfigured()
{
    const int pins[] = {
        MOTOR_A_STEP_PIN,
        MOTOR_A_DIR_PIN,
        MOTOR_B_STEP_PIN,
        MOTOR_B_DIR_PIN,
        X_MIN_LIMIT_PIN,
        X_MAX_LIMIT_PIN,
        Z_MIN_LIMIT_PIN,
        Z_MAX_LIMIT_PIN
    };

    for (unsigned int i = 0;
         i < sizeof(pins) / sizeof(pins[0]); i++)
    {
        if (pins[i] < 0)
        {
            return false;
        }

        for (unsigned int j = 0; j < i; j++)
        {
            if (pins[i] == pins[j])
            {
                return false;
            }
        }
    }

    return true;
}


// ============================================================
// SETUP
// ============================================================


void setup()
{
    // Start communication between the ESP32 and the PC.

    Serial.begin(115200);

    // Give the serial connection a moment to start.

    delay(1000);


    // Configure motor-driver pins and end-switch pins.

    motionReady = motionPinsConfigured();

    if (motionReady)
    {
        gantry.begin();
    }
    else
    {
        Serial.println(
            "WARN,Motion GPIOs not configured or duplicated"
        );
    }


    // Check whether simulated sensor readings are enabled.

    if (DEMO_SENSOR_MODE)
    {
        Serial.println(
            "WARN,DEMO_SENSOR_MODE enabled; synthetic readings"
        );
    }


    // Tell the PC that the ESP32 firmware is running.

    Serial.println("READY");
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
    // Check whether the motion GPIO pins are configured.

    if (!motionReady)
    {
        Serial.println("ERR,Motion GPIOs not configured");
        return;
    }

    // Home the traverser.

    gantry.home();

    if (gantry.isHomed())
    {
        Serial.println("OK,HOME");
    }
    else
    {
        Serial.println("ERR,Homing failed");
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

    
    else if (command.startsWith("MOVE,"))
    {
         if (!motionReady)
         {
        Serial.println("ERR,Motion GPIOs not configured");
        return;
         }

    handleMoveCommand(command);
    }
    

// --------------------------------------------------------
// MEASURE
// --------------------------------------------------------


else if (command == "MEASURE")
{
    float speed;
    float pressure;
    float temperature;


    // Read sensors directly using the base ESP32.

    readAll(
        speed,
        pressure,
        temperature
    );


    // Check whether the measurements are valid.

    if (!isfinite(speed) ||
        !isfinite(pressure) ||
        !isfinite(temperature))
    {
        Serial.println(
            "ERR,Sensor measurement not available"
        );

        return;
    }


    // Send measurements to the PC.

    Serial.print("OK,MEASURE,");

    Serial.print(speed, 6);

    Serial.print(",");

    Serial.print(pressure, 6);

    Serial.print(",");

    Serial.println(temperature, 6);
}

// --------------------------------------------------------
// UNKNOWN COMMAND
// --------------------------------------------------------

else
{
    Serial.println("ERR,Unknown command");
}

}


// ============================================================
// MAIN LOOP
// ============================================================

void loop()
{
    // Check whether the PC has sent a serial command.

    if (Serial.available() > 0)
    {
        // Read everything up to the newline character.

        String command =
            Serial.readStringUntil('\n');

        // Process the received command.

        handleCommand(command);
    }
}

