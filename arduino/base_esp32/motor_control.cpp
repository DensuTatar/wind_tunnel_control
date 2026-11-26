#include "motor_control.h"
#include <math.h>
#include <stdlib.h>

namespace {
float minf(float a,float b) { return a < b ? a : b; }
void direction(int pin,long steps,bool invert) {
    if (steps) digitalWrite(pin, ((steps > 0) != invert) ? HIGH : LOW);
}
}

void CoreXZController::begin() {
    // Set output latches low before switching to outputs.
    const int outputs[] = {MOTOR_A_STEP_PIN,MOTOR_B_STEP_PIN,MOTOR_A_DIR_PIN,MOTOR_B_DIR_PIN};
    for (int p : outputs) { digitalWrite(p,LOW); pinMode(p,OUTPUT); }
    const int inputs[] = {X_MIN_LIMIT_PIN,Z_MIN_LIMIT_PIN,X_MAX_LIMIT_PIN,Z_MAX_LIMIT_PIN};
    for (int p : inputs) if (p >= 0) pinMode(p,INPUT_PULLUP);
}
bool CoreXZController::limit(int pin) {
    return pin >= 0 && digitalRead(pin) == (LIMIT_ACTIVE_LOW ? LOW : HIGH);
}
float CoreXZController::getXPositionMM() const {
    return (a+b)/(2.0f*STEPS_PER_MM*X_POSITION_CALIBRATION);
}
float CoreXZController::getZPositionMM() const {
    return (a-b)/(2.0f*STEPS_PER_MM*Z_POSITION_CALIBRATION);
}
bool CoreXZController::fail(const char* reason) {
    homed = false; fault = reason;
    digitalWrite(MOTOR_A_STEP_PIN,LOW); digitalWrite(MOTOR_B_STEP_PIN,LOW);
    return false;
}
void CoreXZController::stop() { stopped = true; fail("STOPPED"); }
bool CoreXZController::start() {
    if (!MOTION_ENABLED) return fail("MOTION_DISABLED_IN_CONFIG");
    stopped = false; heartbeat = lastYield = millis(); fault = "NONE";
    return service();
}
// Poll the same UART during every motion and during waiting periods. Only realtime
// heartbeat and stop bytes are allowed while busy; any other non-newline input faults.
bool CoreXZController::service() {
    while (Serial.available()) {
        int c = Serial.read();
        if (c == '!') { stop(); }
        else if (c == '~') heartbeat = millis();
        else if (c != '\r' && c != '\n') { stopped = true; fault = "UNEXPECTED_BUSY_INPUT"; }
    }
    if (stopped) return fail(fault);
    if (millis()-heartbeat >= HEARTBEAT_TIMEOUT_MS) return fail("HOST_TIMEOUT");
    // Yield to FreeRTOS occasionally. Software pulse generation is not hard real time.
    if (millis()-lastYield >= 20) { delay(1); lastYield = millis(); }
    return true;
}
bool CoreXZController::waitUs(unsigned long us) {
    unsigned long t = micros();
    while ((unsigned long)(micros()-t) < us) {
        if (!service()) return false;
        unsigned long elapsed = micros()-t;
        if (elapsed < us) {
            unsigned long left = us-elapsed;
            if (left > 2000) delay(1);
            else if (left > 100) delayMicroseconds(100);
        }
    }
    return service();
}
// Check both physical minimum switches on all normal moves; during homing, the
// selected switch may be active. A stationary other switch already pressed at
// the start of a homing phase is tolerated (e.g. power-up at the corner).
bool CoreXZController::check(Phase phase,bool otherInitiallyPressed,bool& hit) {
    hit = false;
    if (!service()) return false;
    if (xMaxTriggered() || zMaxTriggered()) return fail("MAX_LIMIT");
    bool x = xMinTriggered(), z = zMinTriggered();
    if (phase == NORMAL) return (!x && !z) || fail("MIN_LIMIT");
    bool selectedX = phase == SEEK_X || phase == RELEASE_X;
    if ((selectedX ? z : x) && !otherInitiallyPressed) return fail("OTHER_AXIS_LIMIT");
    if (phase == SEEK_X || phase == SEEK_Z) hit = selectedX ? x : z;
    return true;
}
// Bresenham/DDA interpolation, absolute motor steps and path-based trapezoid/
// triangle. Midpoint speed avoids singularity at zero; time is never shortened
// to catch up if software timing overruns. No acceleration across separate moves.
bool CoreXZController::segment(long da,long db,float feed,Phase phase,bool& hit) {
    long na=labs(da), nb=labs(db), n=na>nb?na:nb;
    int sa=(da>0)-(da<0), sb=(db>0)-(db<0);
    bool selectedX = phase == SEEK_X || phase == RELEASE_X;
    bool other = phase != NORMAL && (selectedX ? zMinTriggered() : xMinTriggered());
    if (!check(phase,other,hit)) return false;
    if (hit || !n) return true;
    float dx=(da+db)/(2.0f*STEPS_PER_MM*X_POSITION_CALIBRATION);
    float dz=(da-db)/(2.0f*STEPS_PER_MM*Z_POSITION_CALIBRATION);
    float distance=hypotf(dx,dz), ds=distance/n, vmax=feed/60.0f;
    direction(MOTOR_A_DIR_PIN,da,MOTOR_A_DIR_INVERT);
    direction(MOTOR_B_DIR_PIN,db,MOTOR_B_DIR_INVERT);
    if (!waitUs(DIR_SETUP_US)) return false;
    long ea=0,eb=0;
    for (long i=0;i<n;++i) {
        // If the stationary switch releases, do not allow it to re-trigger.
        if (other && !(selectedX ? zMinTriggered() : xMinTriggered())) other=false;
        if (!check(phase,other,hit)) return false;
        if (hit) return true;
        float s=(i+0.5f)*ds;
        float v=minf(vmax,sqrtf(2*ACCELERATION_MM_S2*minf(s,distance-s)));
        unsigned long period=(unsigned long)ceilf(1e6f*ds/v);
        if (period < 2*STEP_PULSE_US) period=2*STEP_PULSE_US;
        // Poll during wait, then recheck switches immediately before issuing pulses.
        unsigned long t=micros();
        while ((unsigned long)(micros()-t) < period-STEP_PULSE_US) {
            if (!check(phase,other,hit)) return false;
            if (hit) return true;
            unsigned long elapsed=micros()-t;
            if (elapsed < period-STEP_PULSE_US) {
                unsigned long left=period-STEP_PULSE_US-elapsed;
                if (left>2000) delay(1); else if (left>100) delayMicroseconds(100);
            }
        }
        if (!check(phase,other,hit)) return false;
        if (hit) return true;
        ea+=na; eb+=nb;
        bool pa=ea>=n,pb=eb>=n;
        if (pa) { ea-=n; digitalWrite(MOTOR_A_STEP_PIN,HIGH); a+=sa; }
        if (pb) { eb-=n; digitalWrite(MOTOR_B_STEP_PIN,HIGH); b+=sb; }
        delayMicroseconds(STEP_PULSE_US);
        if (pa) digitalWrite(MOTOR_A_STEP_PIN,LOW);
        if (pb) digitalWrite(MOTOR_B_STEP_PIN,LOW);
    }
    return check(phase,other,hit);
}
bool CoreXZController::axisSegment(bool xAxis,float distance,float feed,Phase phase,bool& hit) {
    long s=lroundf(distance*STEPS_PER_MM*(xAxis?X_POSITION_CALIBRATION:Z_POSITION_CALIBRATION));
    return segment(s,xAxis?s:-s,feed,phase,hit);
}
bool CoreXZController::homeAxis(bool xAxis) {
    Phase seek=xAxis?SEEK_X:SEEK_Z, release=xAxis?RELEASE_X:RELEASE_Z;
    bool hit=false;
    auto pressed=[&](){return xAxis?xMinTriggered():zMinTriggered();};
    auto pullOff=[&](){
        if (!axisSegment(xAxis,HOME_PULLOFF_MM,HOME_FEED_MM_MIN,release,hit)) return false;
        if (!waitUs(HOME_SETTLE_MS*1000UL)) return false;
        return !pressed() || fail("SWITCH_DID_NOT_RELEASE");
    };
    // Recover from starting on a pressed switch, then seek within a bounded distance.
    if (pressed() && !pullOff()) return false;
    float maxTravel=xAxis?X_MAX_MM:Z_MAX_MM;
    if (!axisSegment(xAxis,-(maxTravel+HOME_PULLOFF_MM),HOME_SEEK_MM_MIN,seek,hit)) return false;
    if (!hit) return fail("HOME_SWITCH_NOT_FOUND");
    if (!waitUs(HOME_SETTLE_MS*1000UL)) return false;
    if (!pressed()) return fail("UNSTABLE_HOME_SWITCH");
    if (!pullOff()) return false;
    if (!axisSegment(xAxis,-(HOME_PULLOFF_MM+1.0f),HOME_FEED_MM_MIN,seek,hit)) return false;
    if (!hit) return fail("FINE_HOME_SWITCH_NOT_FOUND");
    if (!waitUs(HOME_SETTLE_MS*1000UL)) return false;
    if (!pressed()) return fail("UNSTABLE_HOME_SWITCH");
    return pullOff();
}
bool CoreXZController::home() {
    homed=false;
    if (!start()) return false;
    if (!homeAxis(false) || !homeAxis(true)) return false; // Z first, then X
    if (xMinTriggered() || zMinTriggered() || xMaxTriggered() || zMaxTriggered()) return fail("LIMIT_STILL_ACTIVE");
    a=b=0; homed=true; fault="NONE"; return true;
}
bool CoreXZController::moveTo(float x,float z,float feed) {
    if (!homed) return fail("HOME_REQUIRED");
    if (!isfinite(x)||!isfinite(z)||!isfinite(feed)||x<0||x>X_MAX_MM||z<0||z>Z_MAX_MM||feed<1||feed>MAX_FEED_MM_MIN)
        return fail("TARGET_OR_FEED_OUT_OF_RANGE");
    if (!start()) return false;
    // Quantise Cartesian targets first; this preserves the exact logical travel
    // boundary and avoids cumulative rounding drift across relative moves.
    long xs=lroundf(x*STEPS_PER_MM*X_POSITION_CALIBRATION), zs=lroundf(z*STEPS_PER_MM*Z_POSITION_CALIBRATION);
    bool hit=false;
    return segment(xs+zs-a,xs-zs-b,feed,NORMAL,hit);
}
