#include "motor_control.h"
#include <math.h>

// ============================================================
// A brief README
// ============================================================
//
// This file controls the mechanical movement of the wind-tunnel
// traverser.
//
// Main functions:
//
// - begin()
//   Sets up motor and end-switch GPIO pins.
//
// - xzToMotorSteps()
//   Converts requested X/Z movement into Motor A/B movement
//   using the CoreXZ equations.
//
// - moveMotorStepsCoordinated()
//   Moves Motor A and Motor B together.
//
// - moveRelative()
//   Moves by a requested change in X and Z.
//
// - moveTo()
//   Moves to an absolute X/Z coordinate.
//
// - homeX() / homeZ() / home()
//   Finds the physical zero positions using the end switches.
//
// - xMinTriggered(), xMaxTriggered(),
//   zMinTriggered(), zMaxTriggered()
//   Read the four physical limit switches.
//
// Motor A and Motor B both contribute to X and Z movement.
// There is no separate X motor or Z motor.
// ============================================================




// ============================================================
// CONSTRUCTOR
// ============================================================

// Sets the initial software state of the CoreXZ controller.
//
// When the ESP32 first starts, it does not yet know the
// physical X and Z positions. Therefore both axes are
// initially marked as not homed.

CoreXZController::CoreXZController()
    : _xPositionMM(0.0),
      _zPositionMM(0.0),
      _xHomed(false),
      _zHomed(false),
      _stopRequested(false)
{
}


// ============================================================
// INITIALIZATION
// ============================================================

void CoreXZController::begin()
{
    // Tells ESP32 which pins are outputs for the motor drivers
    // and which pins are inputs for the four end switched


    // --------------------------------------------------------
    // MOTOR PINS
    // --------------------------------------------------------

    pinMode(
        MOTOR_A_STEP_PIN,
        OUTPUT
    );

    pinMode(
        MOTOR_A_DIR_PIN,
        OUTPUT
    );

    pinMode(
        MOTOR_B_STEP_PIN,
        OUTPUT
    );

    pinMode(
        MOTOR_B_DIR_PIN,
        OUTPUT
    );


    // Start STEP signals LOW.

    digitalWrite(
        MOTOR_A_STEP_PIN,
        LOW
    );

    digitalWrite(
        MOTOR_B_STEP_PIN,
        LOW
    );


    // --------------------------------------------------------
    // LIMIT SWITCHES
    // --------------------------------------------------------

    // The switches are assumed to use INPUT_PULLUP.
    // This is a way of configuring ESP32 pin as an input whi;e
    // also turning on a small internal resistor that keeps the pin
    // at known HIGH voltage when the switch is not pressed.
    // so the ESP32 holds it HIGH until switch deliberately pulls it LOW
    // when pressed.
    // Therefore:
    // HIGH = switch not pressed
    // LOW  = switch pressed

    pinMode(
        X_MIN_LIMIT_PIN,
        INPUT_PULLUP
    );

    pinMode(
        X_MAX_LIMIT_PIN,
        INPUT_PULLUP
    );

    pinMode(
        Z_MIN_LIMIT_PIN,
        INPUT_PULLUP
    );

    pinMode(
        Z_MAX_LIMIT_PIN,
        INPUT_PULLUP
    );
}


// ============================================================
// LIMIT SWITCH READING
// ============================================================

bool CoreXZController::limitTriggered(
    int pin
) const
{
    int state = digitalRead(pin);

    if (LIMIT_ACTIVE_LOW)
    {
        return state == LOW;
    }

    return state == HIGH;
}


// These next functions allow the code to ask simple questions
// such as has the left horizontal switch been pressed? and
// has the top vertical switch been pressed for example.

bool CoreXZController::xMinTriggered() const
{
    return limitTriggered(
        X_MIN_LIMIT_PIN
    );
}


bool CoreXZController::xMaxTriggered() const
{
    return limitTriggered(
        X_MAX_LIMIT_PIN
    );
}


bool CoreXZController::zMinTriggered() const
{
    return limitTriggered(
        Z_MIN_LIMIT_PIN
    );
}


bool CoreXZController::zMaxTriggered() const
{
    return limitTriggered(
        Z_MAX_LIMIT_PIN
    );
}


// ============================================================
// MOTOR DIRECTION
// ============================================================

// setMotorDirection functions controls whether each motor rotates 
// in its positive or negative software direction
void CoreXZController::setMotorADirection(
    int direction
)
{
    // direction must be:
    //
    // +1 = positive motor direction
    // -1 = negative motor direction

    bool level;

    if (direction > 0)
    {
        level = HIGH;
    }
    else
    {
        level = LOW;
    }


    // Reverse direction in software if required.

    if (MOTOR_A_DIR_INVERT)
    {
        level = !level;
    }


    digitalWrite(
        MOTOR_A_DIR_PIN,
        level
    );
}


void CoreXZController::setMotorBDirection(
    int direction
)
{
    bool level;

    if (direction > 0)
    {
        level = HIGH;
    }
    else
    {
        level = LOW;
    }


    if (MOTOR_B_DIR_INVERT)
    {
        level = !level;
    }


    digitalWrite(
        MOTOR_B_DIR_PIN,
        level
    );
}


// ============================================================
// STEP PULSES
// ============================================================

// Generating the STEP signals that actually casue the motor
// drivers to advance the stepper motors

void CoreXZController::pulseMotorA(
    unsigned long halfPeriodUS
)
{
    digitalWrite(
        MOTOR_A_STEP_PIN,
        HIGH
    );

    delayMicroseconds(
        halfPeriodUS
    );


    digitalWrite(
        MOTOR_A_STEP_PIN,
        LOW
    );

    delayMicroseconds(
        halfPeriodUS
    );
}


void CoreXZController::pulseMotorB(
    unsigned long halfPeriodUS
)
{
    digitalWrite(
        MOTOR_B_STEP_PIN,
        HIGH
    );

    delayMicroseconds(
        halfPeriodUS
    );


    digitalWrite(
        MOTOR_B_STEP_PIN,
        LOW
    );

    delayMicroseconds(
        halfPeriodUS
    );
}


// ============================================================
// STEP RATE → DELAY
// ============================================================

unsigned long CoreXZController::stepRateToDelay(
    float stepRateHz
) const
{
    if (stepRateHz <= 0)
    {
        return 10;
    }


    // One complete STEP pulse contains:
    //
    // HIGH period + LOW period
    //
    // 1 second = 1,000,000 microseconds
    //
    // Therefore:
    //
    // half period = 500000 / frequency

    unsigned long halfPeriodUS =
        (unsigned long)(
            500000.0 / stepRateHz
        );


    // Prevent extremely short pulses.

    if (halfPeriodUS < 10)
    {
        halfPeriodUS = 10;
    }


    return halfPeriodUS;
}


// ============================================================
// CORE XZ KINEMATICS
// ============================================================

// converts delta X and delta Z into steps for motor A and B

void CoreXZController::xzToMotorSteps(
    float deltaXMM,
    float deltaZMM,
    long &motorASteps,
    long &motorBSteps
) const
{
    // --------------------------------------------------------
    // CORE XZ EQUATIONS
    // --------------------------------------------------------
    //
    // For this coordinate convention:
    //
    // ΔA = ΔX + ΔZ
    //
    // ΔB = ΔX - ΔZ
    //
    // This means:
    //
    // Pure X movement:
    // Motor A and Motor B move in the same direction.
    //
    // Pure Z movement:
    // Motor A and Motor B move in opposite directions.


    // Apply position-calibration factors.

    float correctedX =
        deltaXMM
        * X_POSITION_CALIBRATION;

    float correctedZ =
        deltaZMM
        * Z_POSITION_CALIBRATION;


    // Convert requested X-Z movement into belt/motor movement.

    float motorAMovementMM =
        correctedX + correctedZ;

    float motorBMovementMM =
        correctedX - correctedZ;


    // --------------------------------------------------------
    // STEPS PER MM FOR EACH MOTOR
    // --------------------------------------------------------

    float motorAStepsPerMM =
        (
            MOTOR_STEPS_PER_REV
            * MICROSTEP
        )
        /
        (
            BELT_PITCH_MM
            * MOTOR_A_DRIVE_PULLEY_TEETH
        );


    float motorBStepsPerMM =
        (
            MOTOR_STEPS_PER_REV
            * MICROSTEP
        )
        /
        (
            BELT_PITCH_MM
            * MOTOR_B_DRIVE_PULLEY_TEETH
        );


    // Convert motor movement in millimetres into
    // the number of STEP pulses required.

    motorASteps = lround(
        motorAMovementMM
        * motorAStepsPerMM
    );


    motorBSteps = lround(
        motorBMovementMM
        * motorBStepsPerMM
    );
}


// ============================================================
// POSITION INFORMATION
// ============================================================

float CoreXZController::getXPositionMM() const
{
    return _xPositionMM;
}


float CoreXZController::getZPositionMM() const
{
    return _zPositionMM;
}


bool CoreXZController::isHomed() const
{
    return (
        _xHomed
        && _zHomed
    );
}


// ============================================================
// STOP REQUEST
// ============================================================

void CoreXZController::stop()
{
    _stopRequested = true;
}


// ============================================================
// COORDINATED MOTOR MOVEMENT
// ============================================================
//
// Moves Motor A and Motor B together.
//
// Returns:
//
// true  = requested movement completed
// false = movement was interrupted by a stop request
//         or physical limit switch.

bool CoreXZController::moveMotorStepsCoordinated(
    long motorASteps,
    long motorBSteps,
    float deltaXMM,
    float deltaZMM,
    float speedMMs
)
{
    if (speedMMs <= 0)
    {
        return false;
    }


    // --------------------------------------------------------
    // DETERMINE MOTOR DIRECTIONS
    // --------------------------------------------------------

    int directionA =
        (motorASteps >= 0) ? 1 : -1;

    int directionB =
        (motorBSteps >= 0) ? 1 : -1;


    setMotorADirection(
        directionA
    );

    setMotorBDirection(
        directionB
    );


    long stepsA =
        labs(motorASteps);

    long stepsB =
        labs(motorBSteps);


    if (
        stepsA == 0
        && stepsB == 0
    )
    {
        return true;
    }


    // --------------------------------------------------------
    // NUMBER OF MOVEMENT ITERATIONS
    // --------------------------------------------------------

    long totalIterations =
        max(
            stepsA,
            stepsB
        );


    // --------------------------------------------------------
    // CALCULATE MOVEMENT SPEED
    // --------------------------------------------------------

    float pathLengthMM =
        sqrt(
            deltaXMM * deltaXMM
            +
            deltaZMM * deltaZMM
        );


    if (pathLengthMM <= 0)
    {
        return true;
    }


    float movementTimeS =
        pathLengthMM
        / speedMMs;


    float stepRateHz =
        totalIterations
        / movementTimeS;


    unsigned long halfPeriodUS =
        stepRateToDelay(
            stepRateHz
        );


    // --------------------------------------------------------
    // STEP DISTRIBUTION
    // --------------------------------------------------------

    long accumulatorA = 0;
    long accumulatorB = 0;


    // Count how many pulses were actually performed.
    //
    // This is important if an end switch interrupts
    // the movement before the target is reached.

    long executedStepsA = 0;
    long executedStepsB = 0;


    bool completed = true;

    _stopRequested = false;


    // ========================================================
    // MAIN MOVEMENT LOOP
    // ========================================================

    for (
        long i = 0;
        i < totalIterations;
        i++
    )
    {
        // ----------------------------------------------------
        // STOP REQUEST
        // ----------------------------------------------------

        if (_stopRequested)
        {
            completed = false;
            break;
        }


        // ----------------------------------------------------
        // PHYSICAL LIMIT SWITCHES
        // ----------------------------------------------------

        if (
            deltaXMM < 0
            && xMinTriggered()
        )
        {
            completed = false;
            break;
        }


        if (
            deltaXMM > 0
            && xMaxTriggered()
        )
        {
            completed = false;
            break;
        }


        if (
            deltaZMM < 0
            && zMinTriggered()
        )
        {
            completed = false;
            break;
        }


        if (
            deltaZMM > 0
            && zMaxTriggered()
        )
        {
            completed = false;
            break;
        }


        // ----------------------------------------------------
        // DETERMINE WHICH MOTORS STEP
        // ----------------------------------------------------

        accumulatorA += stepsA;
        accumulatorB += stepsB;


        bool stepA = false;
        bool stepB = false;


        if (
            accumulatorA >= totalIterations
        )
        {
            accumulatorA -=
                totalIterations;

            stepA = true;
        }


        if (
            accumulatorB >= totalIterations
        )
        {
            accumulatorB -=
                totalIterations;

            stepB = true;
        }


        // ----------------------------------------------------
        // STEP HIGH
        // ----------------------------------------------------

        if (stepA)
        {
            digitalWrite(
                MOTOR_A_STEP_PIN,
                HIGH
            );
        }


        if (stepB)
        {
            digitalWrite(
                MOTOR_B_STEP_PIN,
                HIGH
            );
        }


        delayMicroseconds(
            halfPeriodUS
        );


        // ----------------------------------------------------
        // STEP LOW
        // ----------------------------------------------------

        if (stepA)
        {
            digitalWrite(
                MOTOR_A_STEP_PIN,
                LOW
            );

            executedStepsA +=
                directionA;
        }


        if (stepB)
        {
            digitalWrite(
                MOTOR_B_STEP_PIN,
                LOW
            );

            executedStepsB +=
                directionB;
        }


        delayMicroseconds(
            halfPeriodUS
        );
    }


    // ========================================================
    // UPDATE POSITION IF MOVEMENT WAS INTERRUPTED
    // ========================================================
    //
    // If the full movement completed, moveRelative() will
    // simply set the position to the requested target.
    //
    // If it stopped early, we estimate the actual travelled
    // X/Z distance from the number of motor pulses completed.

    if (!completed)
    {
        float motorAStepsPerMM =
            (
                MOTOR_STEPS_PER_REV
                * MICROSTEP
            )
            /
            (
                BELT_PITCH_MM
                * MOTOR_A_DRIVE_PULLEY_TEETH
            );


        float motorBStepsPerMM =
            (
                MOTOR_STEPS_PER_REV
                * MICROSTEP
            )
            /
            (
                BELT_PITCH_MM
                * MOTOR_B_DRIVE_PULLEY_TEETH
            );


        float movementA =
            executedStepsA
            / motorAStepsPerMM;


        float movementB =
            executedStepsB
            / motorBStepsPerMM;


        // Inverse CoreXZ equations:
        //
        // X = (A + B) / 2
        // Z = (A - B) / 2

        float correctedDeltaX =
            (
                movementA
                + movementB
            )
            / 2.0;


        float correctedDeltaZ =
            (
                movementA
                - movementB
            )
            / 2.0;


        // Undo the position calibration factors.

        if (
            X_POSITION_CALIBRATION != 0
        )
        {
            _xPositionMM +=
                correctedDeltaX
                / X_POSITION_CALIBRATION;
        }


        if (
            Z_POSITION_CALIBRATION != 0
        )
        {
            _zPositionMM +=
                correctedDeltaZ
                / Z_POSITION_CALIBRATION;
        }
    }


    return completed;
}

// ============================================================
// RELATIVE X-Z MOVEMENT
// ============================================================
//
// Moves the carriage by a requested change in X and Z.
//
// Example:
//
// deltaXMM = +20
// deltaZMM = -10
//
// means:
//
// move 20 mm right
// and 10 mm downward.


bool CoreXZController::moveRelative(
    float deltaXMM,
    float deltaZMM,
    float speedMMs
)
{
    // --------------------------------------------------------
    // CALCULATE NEW TARGET POSITION
    // --------------------------------------------------------

    float targetX =
        _xPositionMM
        + deltaXMM;

    float targetZ =
        _zPositionMM
        + deltaZMM;


    // --------------------------------------------------------
    // SOFTWARE TRAVEL LIMITS
    // --------------------------------------------------------

    if (
        targetX < 0
        || targetX > X_MAX_MM
    )
    {
        return false;
    }


    if (
        targetZ < 0
        || targetZ > Z_MAX_MM
    )
    {
        return false;
    }


    // --------------------------------------------------------
    // CORE XZ CONVERSION
    // --------------------------------------------------------

    long motorASteps;
    long motorBSteps;


    xzToMotorSteps(
        deltaXMM,
        deltaZMM,
        motorASteps,
        motorBSteps
    );


    // --------------------------------------------------------
    // PERFORM MOVEMENT
    // --------------------------------------------------------
    bool completed =
        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            deltaXMM,
            deltaZMM,
            speedMMs
        );

    // If the movement completed normally, we know the
    // requested target was reached.

    if (completed)
    {
        _xPositionMM =
            targetX;

        _zPositionMM =
            targetZ;
    }


    return completed;
}


    // --------------------------------------------------------
    // UPDATE SOFTWARE POSITION
    // --------------------------------------------------------
    //
    // For now, this assumes that the commanded movement
    // completed successfully.
    //
    // Later we can improve this so interrupted moves caused
    // by a limit switch do not incorrectly update the position.

    _xPositionMM =
        targetX;

    _zPositionMM =
        targetZ;
}

// ============================================================
// ABSOLUTE X-Z MOVEMENT
// ============================================================
//
// Moves the carriage to a requested X-Z coordinate.
//
// Example:
//
// moveTo(100, 150, 20)
//
// means:
//
// move to:
// X = 100 mm
// Z = 150 mm
//
// at approximately 20 mm/s.


bool CoreXZController::moveTo(
    float targetXMM,
    float targetZMM,
    float speedMMs
)
{
    // The machine must know where zero is before
    // absolute positioning can be trusted.

    if (!isHomed())
    {
        return false;
    }


    // --------------------------------------------------------
    // CHECK SOFTWARE TRAVEL LIMITS
    // --------------------------------------------------------

    if (
        targetXMM < 0
        || targetXMM > X_MAX_MM
    )
    {
        return false;
    }


    if (
        targetZMM < 0
        || targetZMM > Z_MAX_MM
    )
    {
        return false;
    }


    // --------------------------------------------------------
    // CALCULATE REQUIRED CHANGE IN POSITION
    // --------------------------------------------------------

    float deltaX =
        targetXMM
        - _xPositionMM;

    float deltaZ =
        targetZMM
        - _zPositionMM;


    // Use the relative movement function to execute it.
     return moveRelative(
        deltaX,
        deltaZ,
        speedMMs
    );

    
}

// ============================================================
// HOME X AXIS
// ============================================================
//
// Homes the horizontal axis using the X_MIN switch.
//
// Sequence:
//
// 1. If the X_MIN switch is already pressed, move away from it.
// 2. Move toward X_MIN at the fast homing speed.
// 3. Back away slightly.
// 4. Approach X_MIN again slowly.
// 5. Define this position as X = 0 mm.


void CoreXZController::homeX()
{
    // X has not yet been successfully homed.
    _xHomed = false;


    // --------------------------------------------------------
    // IF SWITCH IS ALREADY PRESSED, MOVE AWAY
    // --------------------------------------------------------

    int safetyCounter = 0;

    while (
        xMinTriggered()
        && safetyCounter < 100
    )
    {
        long motorASteps;
        long motorBSteps;

        xzToMotorSteps(
            HOME_FINE_INCREMENT_MM,
            0.0,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            HOME_FINE_INCREMENT_MM,
            0.0,
            HOME_SLOW_SPEED_MM_S
        );

        safetyCounter++;
    }


    // --------------------------------------------------------
    // FAST APPROACH TOWARD X MINIMUM
    // --------------------------------------------------------

    safetyCounter = 0;

    int maxSearchIterations =
        (int)(
            X_MAX_MM
            / HOME_SEARCH_INCREMENT_MM
        )
        + 20;


    while (
        !xMinTriggered()
        && safetyCounter < maxSearchIterations
    )
    {
        long motorASteps;
        long motorBSteps;

        xzToMotorSteps(
            -HOME_SEARCH_INCREMENT_MM,
            0.0,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            -HOME_SEARCH_INCREMENT_MM,
            0.0,
            HOME_FAST_SPEED_MM_S
        );

        safetyCounter++;
    }


    // If the switch was never found, homing failed.

    if (!xMinTriggered())
    {
        return;
    }


    // --------------------------------------------------------
    // BACK AWAY FROM SWITCH
    // --------------------------------------------------------

    long motorASteps;
    long motorBSteps;

    xzToMotorSteps(
        HOME_BACKOFF_MM,
        0.0,
        motorASteps,
        motorBSteps
    );

    moveMotorStepsCoordinated(
        motorASteps,
        motorBSteps,
        HOME_BACKOFF_MM,
        0.0,
        HOME_SLOW_SPEED_MM_S
    );


    // --------------------------------------------------------
    // SLOW FINAL APPROACH
    // --------------------------------------------------------

    safetyCounter = 0;

    while (
        !xMinTriggered()
        && safetyCounter < 100
    )
    {
        xzToMotorSteps(
            -HOME_FINE_INCREMENT_MM,
            0.0,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            -HOME_FINE_INCREMENT_MM,
            0.0,
            HOME_SLOW_SPEED_MM_S
        );

        safetyCounter++;
    }


    if (!xMinTriggered())
    {
        return;
    }


    // --------------------------------------------------------
    // DEFINE X ZERO
    // --------------------------------------------------------

    _xPositionMM = 0.0;
    _xHomed = true;
}

// ============================================================
// HOME Z AXIS
// ============================================================
//
// Homes the vertical axis using the Z_MIN switch.
//
// The bottom switch defines Z = 0 mm.


void CoreXZController::homeZ()
{
    _zHomed = false;


    // --------------------------------------------------------
    // IF SWITCH IS ALREADY PRESSED, MOVE UPWARD
    // --------------------------------------------------------

    int safetyCounter = 0;

    while (
        zMinTriggered()
        && safetyCounter < 100
    )
    {
        long motorASteps;
        long motorBSteps;

        xzToMotorSteps(
            0.0,
            HOME_FINE_INCREMENT_MM,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            0.0,
            HOME_FINE_INCREMENT_MM,
            HOME_SLOW_SPEED_MM_S
        );

        safetyCounter++;
    }


    // --------------------------------------------------------
    // FAST APPROACH TOWARD Z MINIMUM
    // --------------------------------------------------------

    safetyCounter = 0;

    int maxSearchIterations =
        (int)(
            Z_MAX_MM
            / HOME_SEARCH_INCREMENT_MM
        )
        + 20;


    while (
        !zMinTriggered()
        && safetyCounter < maxSearchIterations
    )
    {
        long motorASteps;
        long motorBSteps;

        xzToMotorSteps(
            0.0,
            -HOME_SEARCH_INCREMENT_MM,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            0.0,
            -HOME_SEARCH_INCREMENT_MM,
            HOME_FAST_SPEED_MM_S
        );

        safetyCounter++;
    }


    if (!zMinTriggered())
    {
        return;
    }


    // --------------------------------------------------------
    // BACK AWAY FROM SWITCH
    // --------------------------------------------------------

    long motorASteps;
    long motorBSteps;

    xzToMotorSteps(
        0.0,
        HOME_BACKOFF_MM,
        motorASteps,
        motorBSteps
    );

    moveMotorStepsCoordinated(
        motorASteps,
        motorBSteps,
        0.0,
        HOME_BACKOFF_MM,
        HOME_SLOW_SPEED_MM_S
    );


    // --------------------------------------------------------
    // SLOW FINAL APPROACH
    // --------------------------------------------------------

    // The reason for the fast approach - backoff - slow approach is
    // repeatability. the first fast approach finds the general switch 
    // location; the second slower approach gives you a more consistent 
    // zero point. 

    safetyCounter = 0;

    while (
        !zMinTriggered()
        && safetyCounter < 100
    )
    {
        xzToMotorSteps(
            0.0,
            -HOME_FINE_INCREMENT_MM,
            motorASteps,
            motorBSteps
        );

        moveMotorStepsCoordinated(
            motorASteps,
            motorBSteps,
            0.0,
            -HOME_FINE_INCREMENT_MM,
            HOME_SLOW_SPEED_MM_S
        );

        safetyCounter++;
    }


    if (!zMinTriggered())
    {
        return;
    }


    // --------------------------------------------------------
    // DEFINE Z ZERO
    // --------------------------------------------------------

    _zPositionMM = 0.0;
    _zHomed = true;
}

// ============================================================
// HOME COMPLETE SYSTEM
// ============================================================
//
// Homes both physical axes so the controller knows where
// X = 0 mm and Z = 0 mm are located.


void CoreXZController::home()
{
    homeX();

    // Only continue if X homing succeeded.
    if (!_xHomed)
    {
        return;
    }


    homeZ();

    // If both succeeded, isHomed() will now return true.
}

