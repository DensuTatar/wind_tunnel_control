#pragma once
#include <Arduino.h>
#include "config.h"

// Signed motor step counts; A = X + Z, B = X - Z (in belt mm).
// A positive X move rotates both motors in the same logical direction.
class CoreXZController {
public:
    void begin();
    bool home();
    bool moveTo(float x, float z, float feedMMMin);
    bool isHomed() const { return homed; }
    float getXPositionMM() const;
    float getZPositionMM() const;
    bool xMinTriggered() const { return limit(X_MIN_LIMIT_PIN); }
    bool zMinTriggered() const { return limit(Z_MIN_LIMIT_PIN); }
    bool xMaxTriggered() const { return limit(X_MAX_LIMIT_PIN); }
    bool zMaxTriggered() const { return limit(Z_MAX_LIMIT_PIN); }
    void stop();
    const char* error() const { return fault; }
private:
    enum Phase { NORMAL, SEEK_X, SEEK_Z, RELEASE_X, RELEASE_Z };
    long a = 0, b = 0;
    bool homed = false, stopped = false;
    unsigned long heartbeat = 0, lastYield = 0;
    const char* fault = "UNHOMED";
    static bool limit(int pin);
    bool start();
    bool fail(const char* reason);
    bool service();
    bool waitUs(unsigned long us);
    bool check(Phase phase, bool otherInitiallyPressed, bool& hit);
    bool segment(long da, long db, float feed, Phase phase, bool& hit);
    bool axisSegment(bool xAxis, float distance, float feed, Phase phase, bool& hit);
    bool homeAxis(bool xAxis);
};
