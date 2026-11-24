#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H


#include <Arduino.h>
#include "config.h"


// ============================================================
// CORE XZ CONTROLLER
// ============================================================
//
// The traverser uses a CoreXZ mechanism.
//
// The way it works is such that:
//
// Motor A + Motor B
//        ↓
// CoreXZ kinematics
//        ↓
// X and Z carriage motion
//
// For the selected coordinate convention:
//
//     ΔA = ΔX + ΔZ
//     ΔB = ΔX - ΔZ
//
// Therefore:
//
//     ΔX = (ΔA + ΔB) / 2
//     ΔZ = (ΔA - ΔB) / 2
//
// The exact motor rotation directions can later be reversed
// using MOTOR_A_DIR_INVERT and MOTOR_B_DIR_INVERT in config.h if necessary.
//
// In the CoreXZ mechanism, both motors move together for
// one axis and in opposite directions for the other axis.
// ============================================================


class CoreXZController {

public:

    // --------------------------------------------------------
    // CONSTRUCTOR
    // --------------------------------------------------------

    CoreXZController();


    // --------------------------------------------------------
    // INITIALIZATION
    // --------------------------------------------------------

    // Configure motor and limit-switch GPIO pins.
    void begin();


    // --------------------------------------------------------
    // HOMING
    // --------------------------------------------------------

    // Home both physical axes.
    void home();


    // Home only the X-axis using the X_MIN switch.
    void homeX();


    // Home only the Z-axis using the Z_MIN switch.
    void homeZ();


    // --------------------------------------------------------
    // MOVEMENT
    // --------------------------------------------------------

    // Move to an absolute X-Z position in millimetres.
    bool moveTo(
        float targetXMM,
        float targetZMM,
        float speedMMs
    );


    // Move by a relative amount from the current position.
    bool moveRelative(
        float deltaXMM,
        float deltaZMM,
        float speedMMs
    );


    // --------------------------------------------------------
    // POSITION
    // --------------------------------------------------------

    float getXPositionMM() const;

    float getZPositionMM() const;


    // Returns true once both X and Z have been homed.
    bool isHomed() const;


    // --------------------------------------------------------
    // LIMIT SWITCHES
    // --------------------------------------------------------

    bool xMinTriggered() const;

    bool xMaxTriggered() const;

    bool zMinTriggered() const;

    bool zMaxTriggered() const;


    // --------------------------------------------------------
    // SAFETY
    // --------------------------------------------------------

    // Stops the current movement routine.
    void stop();


private:

    // ========================================================
    // CURRENT SYSTEM STATE
    // ========================================================

    // Current software position of the carriage.

    float _xPositionMM;
    float _zPositionMM;


    // Homing status of each physical axis.

    bool _xHomed;
    bool _zHomed;


    // Used to request that an active movement stops.

    bool _stopRequested;


    // ========================================================
    // MOTOR CONTROL
    // ========================================================

    // Set the direction of Motor A.
    void setMotorADirection(
        int direction
    );


    // Set the direction of Motor B.
    void setMotorBDirection(
        int direction
    );


    // Generate one STEP pulse for Motor A.
    void pulseMotorA(
        unsigned long halfPeriodUS
    );


    // Generate one STEP pulse for Motor B.
    void pulseMotorB(
        unsigned long halfPeriodUS
    );


    // ========================================================
    // CORE XZ KINEMATICS
    // ========================================================

    // Converts a requested X-Z displacement into the
    // required Motor A and Motor B step counts.
    //
    // CoreXZ relation:
    //
    // ΔA = ΔX + ΔZ
    // ΔB = ΔX - ΔZ

    void xzToMotorSteps(
        float deltaXMM,
        float deltaZMM,
        long &motorASteps,
        long &motorBSteps
    ) const;


    // ========================================================
    // COORDINATED MOTOR MOVEMENT
    // ========================================================

    // Moves Motor A and Motor B together while keeping their
    // step pulses synchronized.
    //
    // This is required because a CoreXZ move may require
    // different numbers of steps from Motor A and Motor B.

    bool moveMotorStepsCoordinated(
        long motorASteps,
        long motorBSteps,
        float deltaXMM,
        float deltaZMM,
        float speedMMs
    );


    // ========================================================
    // LIMIT-SWITCH HELPER
    // ========================================================

    bool limitTriggered(
        int pin
    ) const;


    // ========================================================
    // STEP TIMING
    // ========================================================

    // Converts a step frequency into the delay used for
    // each half of the STEP pulse.

    unsigned long stepRateToDelay(
        float stepRateHz
    ) const;
};


#endif