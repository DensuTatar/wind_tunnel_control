#pragma once
// Minimal host shim for testing control logic, NOT an ESP32 hardware emulator.
#include <cstdint>
#include <string>
#include <sstream>
#include <iomanip>
#include <deque>
constexpr int LOW=0,HIGH=1,OUTPUT=1,INPUT_PULLUP=2;
unsigned long millis(); unsigned long micros();
void delay(unsigned long ms); void delayMicroseconds(unsigned long us);
void digitalWrite(int pin,int val); int digitalRead(int pin); void pinMode(int pin,int mode);
struct SerialMock {
    std::deque<int> input;
    std::string output;
    void begin(int) {}
    int available();
    int read();
    template<class T> void print(T val) { std::ostringstream s; s<<val; output+=s.str(); }
    void print(float val,int precision) { std::ostringstream s; s<<std::fixed<<std::setprecision(precision)<<val; output+=s.str(); }
    template<class T> void println(T val) { print(val); output+='\n'; }
    void println(float val,int precision) { print(val,precision); output+='\n'; }
    void println() { output+='\n'; }
};
extern SerialMock Serial;
