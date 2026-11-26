#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "motor_control.h"
#include "sensors.h"

CoreXZController motion;
char line[96];
size_t used=0;
bool overflow=false;

void setup() {
    motion.begin();
    Serial.begin(115200);
    Serial.println("READY,WINDTUNNEL_CUSTOM_V2");
}
void position(const char* type) {
    Serial.print("OK,"); Serial.print(type); Serial.print(',');
    if (!motion.isHomed()) { Serial.println("NA,NA,UNHOMED"); return; }
    Serial.print(motion.getXPositionMM(),4); Serial.print(',');
    Serial.print(motion.getZPositionMM(),4); Serial.println(",HOMED");
}
void error(const char* reason) { Serial.print("ERR,"); Serial.println(reason); }
void value(float x) { if (isfinite(x)) Serial.print(x,6); else Serial.print("NA"); }
bool number(const char* s,float& out) {
    char* end; out=strtof(s,&end); return end!=s && *end=='\0' && isfinite(out);
}
void command(char* cmd) {
    if (!strcmp(cmd,"PING")) Serial.println("OK,PONG,WINDTUNNEL_CUSTOM_V2");
    else if (!strcmp(cmd,"MODE")) Serial.println(DEMO_SENSOR_MODE?"OK,MODE,DEMO":"OK,MODE,REAL");
    else if (!strcmp(cmd,"CAPS")) {
        Serial.print("OK,CAPS,"); Serial.print(MOTION_ENABLED?"ENABLED":"LOCKED");
        Serial.print(','); Serial.print(X_MAX_MM,1); Serial.print(','); Serial.print(Z_MAX_MM,1);
        Serial.print(','); Serial.println(MAX_FEED_MM_MIN,1);
    } else if (!strcmp(cmd,"LIMITS")) {
        Serial.print("OK,LIMITS,"); Serial.print(int(motion.xMinTriggered())); Serial.print(','); Serial.println(int(motion.zMinTriggered()));
    } else if (!strcmp(cmd,"POS")) position("POS");
    else if (!strcmp(cmd,"HOME")) {
        if (motion.home()) position("HOME"); else error(motion.error());
    } else if (!strncmp(cmd,"MOVE,",5)) {
        char* x=cmd+5; char* z=strchr(x,',');
        if (!z) { error("MOVE_FORMAT"); return; } *z++='\0';
        char* f=strchr(z,','); if (f) *f++='\0';
        float xv,zv,feed=DEFAULT_FEED_MM_MIN;
        if (!number(x,xv)||!number(z,zv)||(f&&!number(f,feed))) { error("MOVE_FORMAT"); return; }
        if (motion.moveTo(xv,zv,feed)) position("MOVE"); else error(motion.error());
    } else if (!strcmp(cmd,"MEASURE")) {
        float u,p,t; readAll(u,p,t);
        // The UI can display demo values, but unavailable real readings are NA.
        if (!isfinite(u)) { error("AIR_SPEED_NOT_IMPLEMENTED_OR_UNAVAILABLE"); return; }
        Serial.print("OK,MEASURE,"); value(u); Serial.print(','); value(p); Serial.print(','); value(t); Serial.println();
    } else if (!strcmp(cmd,"STOP")) { motion.stop(); Serial.println("OK,STOP"); }
    else error("UNKNOWN_COMMAND");
}
void loop() {
    while (Serial.available()) {
        char c=char(Serial.read());
        if (c=='!') { motion.stop(); used=0; overflow=false; continue; } // no unsolicited reply
        if (c=='~'||c=='\r') continue;
        if (c=='\n') {
            if (overflow) error("COMMAND_TOO_LONG");
            else if (used) { line[used]='\0'; used=0; command(line); }
            used=0; overflow=false;
        } else if (!overflow) {
            if (used<sizeof(line)-1) line[used++]=c; else overflow=true;
        }
    }
    delay(1);
}
