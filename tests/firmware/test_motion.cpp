#include "Arduino.h"
#include "motor_control.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <cstring>
SerialMock Serial;
static unsigned long clockUs=0,nextHeartbeat=0,stopAt=0;
static bool keepalive=true, autoSwitch=true, forceX=false;
static long physicalA=0,physicalB=0,pulsesA=0,pulsesB=0;
static int levels[64]={};
static unsigned long lastRiseA=0,lastRiseB=0;
static float px(){return (physicalA+physicalB)/(2*STEPS_PER_MM);}
static float pz(){return (physicalA-physicalB)/(2*STEPS_PER_MM);}
unsigned long millis(){return clockUs/1000;}
unsigned long micros(){clockUs+=5; return clockUs;}
void delay(unsigned long ms){clockUs+=ms*1000;}
void delayMicroseconds(unsigned long us){clockUs+=us;}
void pinMode(int pin,int){assert(pin>=0 && pin<64);}
int digitalRead(int pin){
    assert(pin>=0 && pin<64);
    if(pin==X_MIN_LIMIT_PIN) return (forceX||(autoSwitch&&px()<=0))?LOW:HIGH;
    if(pin==Z_MIN_LIMIT_PIN) return (autoSwitch&&pz()<=0)?LOW:HIGH;
    return HIGH;
}
void digitalWrite(int pin,int val){
    assert(pin>=0 && pin<64);
    if(val==HIGH && levels[pin]==LOW) {
        if(pin==MOTOR_A_STEP_PIN) {physicalA+=levels[MOTOR_A_DIR_PIN]==LOW?1:-1; ++pulsesA; lastRiseA=clockUs;}
        if(pin==MOTOR_B_STEP_PIN) {physicalB+=levels[MOTOR_B_DIR_PIN]==LOW?1:-1; ++pulsesB; lastRiseB=clockUs;}
    } else if(val==LOW && levels[pin]==HIGH){
        if(pin==MOTOR_A_STEP_PIN) assert(clockUs-lastRiseA>=STEP_PULSE_US);
        if(pin==MOTOR_B_STEP_PIN) assert(clockUs-lastRiseB>=STEP_PULSE_US);
    }
    levels[pin]=val;
}
int SerialMock::available(){
    if(stopAt && clockUs>=stopAt){input.push_back('!'); stopAt=0;}
    if(keepalive && clockUs>=nextHeartbeat){input.push_back('~'); nextHeartbeat=clockUs+250000;}
    return input.size();
}
int SerialMock::read(){int c=input.front(); input.pop_front(); return c;}
void reset(float x,float z){
    physicalA=lroundf((x+z)*STEPS_PER_MM); physicalB=lroundf((x-z)*STEPS_PER_MM);
    clockUs=0; nextHeartbeat=0; stopAt=0; keepalive=true; autoSwitch=true; forceX=false;
    Serial.input.clear(); pulsesA=pulsesB=0; std::memset(levels,0,sizeof(levels));
}
int main(){
    reset(20,30); CoreXZController c; c.begin();
    assert(!c.moveTo(1,1,60)); assert(pulsesA==0&&pulsesB==0);
    if(!MOTION_ENABLED){assert(!c.home()); assert(pulsesA==0&&pulsesB==0); std::cout<<"Default motion lock passed\n"; return 0;}
    assert(c.home()); assert(c.isHomed()); assert(c.getXPositionMM()==0&&c.getZPositionMM()==0);
    assert(std::fabs(px()-2)<.01&&std::fabs(pz()-2)<.01);
    long a=pulsesA,b=pulsesB; assert(c.moveTo(10,0,600)); assert(pulsesA-a==1600&&pulsesB-b==1600);
    a=pulsesA;b=pulsesB; assert(c.moveTo(20,10,600)); assert(pulsesA-a==3200&&pulsesB-b==0);
    assert(c.moveTo(0,0,600)); assert(std::fabs(px()-2)<.01&&std::fabs(pz()-2)<.01);
    assert(!c.moveTo(341,0,600)); assert(!c.isHomed());
    assert(c.home()); stopAt=clockUs+100000; assert(!c.moveTo(100,50,600)); assert(!c.isHomed()); assert(!strcmp(c.error(),"STOPPED"));
    assert(c.home()); keepalive=false; assert(!c.moveTo(100,50,600)); assert(!strcmp(c.error(),"HOST_TIMEOUT"));
    reset(0,0); CoreXZController pressed; pressed.begin(); assert(pressed.home()); assert(std::fabs(px()-2)<.01&&std::fabs(pz()-2)<.01);
    forceX=true; assert(!pressed.moveTo(10,0,60)); assert(!strcmp(pressed.error(),"MIN_LIMIT"));
    reset(10,10); forceX=true; CoreXZController stuck; stuck.begin(); assert(!stuck.home()); assert(!strcmp(stuck.error(),"SWITCH_DID_NOT_RELEASE"));
    reset(10,10); autoSwitch=false; CoreXZController missing; missing.begin(); assert(!missing.home()); assert(!strcmp(missing.error(),"HOME_SWITCH_NOT_FOUND"));
    std::cout<<"Enabled logic: homing, pure/diagonal step counts, round trip, bounds, stop, watchdog, starting pressed, hard limit, stuck and missing switch passed\n";
}
