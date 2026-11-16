
# Wind Tunnel Control

## Project Description

Control software for a Core XZ probe traverser designed for 
velocity measurements in a low-speed wind tunnel.

The software is responsible for movement control, homing,
position tracking, sensor data acquisition, automated grid
scanning, data storage and visualization.

## Software Implementations

Two alternative implementations are currently being developed.

### Branch 1: main

Custom wired single-ESP32 configuration.

- One ESP32 for movement control and sensor acquisition.
- Custom Core XZ kinematics and motor control.
- Wired communication through USB serial.
- Homing and limit-switch monitoring.
- Automated measurement grid using Python.
- CSV data storage and visualization.

### Branch 2: fluidnc-experiment

Alternative implementation using FluidNC firmware.

- Base ESP32 running FluidNC.
- Built-in acceleration and deceleration.
- Built-in homing, kinematics and motion planning.
- Communication through G-code.
- Separate wired ESP32-C3 for sensor acquisition.
- Python-based measurement and data processing.

Both implementations will be investigated and compared
experimentally before selecting the final configuration.

## Repository Structure

- `arduino/` — ESP32 firmware and configuration.
- `pc (runs ON LAPTOP)/` — Python control software.
- `fluidnc_experiment/` — Alternative implementation,
  available on the fluidnc-experiment branch.

## Software Requirements

- Arduino IDE
- ESP32 board package
- Python 3
- PySerial
- Pandas
- Matplotlib
- FluidNC (alternative implementation only)

## Current Development Status

- [x] Initial motion control software
- [x] Core XZ kinematics
- [x] Homing and position tracking logic
- [x] Transition to wired communication
- [x] Initial FluidNC implementation
- [ ] GPIO assignment and verification
- [ ] Sensor calibration
- [ ] Firmware compilation and hardware testing
- [ ] Positioning accuracy and repeatability testing
- [ ] Experimental comparison of both implementations
- [ ] Final system validation

## Project

4CBLC10 Engineering Design 2

Group 02 — Eindhoven University of Technology
