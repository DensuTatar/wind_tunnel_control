# Wind Tunnel Control — FluidNC (starter UI)

A modular PySide6 desktop application for the wind-tunnel Core-XZ traverser. **Simulation works with no hardware.** The hardware adapters are starter implementations based on the known project branch structure, not confirmed drop-in replacements for the team's exact files.

## Installation (Windows / VS Code)

Open this folder in VS Code, open a terminal, and run:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

On macOS/Linux, activate with `source .venv/bin/activate` and use `python3` if necessary.

## First run — safe simulation

1. Choose **Simulation** and click **Connect**.
2. Click **HOME / reference**.
3. Change target X/Z and click **Move to target**.
4. Open **Automatic scan**. For a quick test, use 3 × 3 points, `Settle = 0.0 s`, `Samples/point = 1`. Click **START AUTOMATIC SCAN**.
5. The CSV appears under `measurements/`, the graph under **Live results**.

## Proposed two-board hardware arrangement

- **ESP32 #1:** FluidNC motion controller, connected as one USB serial port.
- **ESP32-C3 #2:** sensor acquisition firmware, connected as a separate USB serial port.
- PC/UI: two independent adapters, shared application controller.

The existing `fluidnc-experiment` branch discussed previously already uses **two wired ESP32 boards** in concept. If the implementation changes from one board to two, change the sensor/motion adapter(s), not the GUI.

### CRITICAL checks before enabling real movement

The prior project branch used `fluidnc_motion.py`, `control_fluidnc.py`, `config.yaml.example`, and `sensor_esp32c3.ino` but those exact source files were **not available** while producing this UI. The adapter below assumes:

- FluidNC can be reached at **115200 baud over USB serial**.
- Logical FluidNC `X` is physical traverser X; **logical FluidNC `Y` is physical traverser Z**.
- The correct CoreXY belt mixing, motor directions, homing inputs, units, travel limits and acceleration are correctly configured in the ESP32's `config.yaml`.
- The machine is safely homed and its **G54 work-coordinate zero** corresponds to the intended 0–400 mm positive travel coordinates used by the UI. The 0–400 values are starting assumptions, **not verified machine limits**. They must be changed to your actual validated machine coordinates. FluidNC may report `MPos` or `WPos`, and these should not be conflated if offsets are nonzero.
- The moving mechanics are safe to operate and a **separate hardware emergency stop** has been installed and tested. The software button sends a `!` feed hold, not an emergency stop.
- The sensor ESP32-C3 responds to `MEASURE\n` with one of the formats listed in `backend/sensor_adapter.py` (unverified; must align with the real `.ino` code).

**Do not test on hardware while the stepper vibration issue remains unresolved.** In real mode, you must explicitly tick the arming box to initiate homing or movement. Connecting alone never automatically moves the machine.

## Code layers

| Layer | File | Responsibility |
| --- | --- | --- |
| UI | `gui.py` | Widgets, actions, live data, plotting |
| Application service | `backend/controller.py` | Coordinates movement and scanning, validation, CSV, events |
| API | `backend/contracts.py` | Stable `Position`, `Measurement`, `ScanPlan` and adapter contracts |
| Sim hardware | `backend/simulators.py` | Deterministic simulation |
| FluidNC adapter | `backend/fluidnc_adapter.py` | `$H`, G-code, status `?`, feed hold `!` |
| Sensor adapter | `backend/sensor_adapter.py` | Reads provisional ESP32-C3 measurement protocol |

The UI **never imports** any of the FluidNC or sensor adapters directly. An architecture change happens in the adapters and `WindTunnelController.connect()` wiring; the event contract remains unchanged.

## Integration with the existing branch

Review your exact existing files, then decide whether to:

1. Replace `backend/fluidnc_adapter.py` calls with your previously written `fluidnc_motion.py` library methods; or
2. Keep this adapter and merge the validated command/safety logic from `fluidnc_motion.py`.

Likewise, use the actual serial packet sent by `sensor_esp32c3.ino` and update only `backend/sensor_adapter.py`. If your team later sends sensor data through the motion ESP32 via ESP-NOW, you can write a *combined sensor adapter* while keeping the same `SensorPort.sample()` contract.

## Notes / limitations

- **No physical hardware has been tested or validated with these files.** The G-code parser and homing behavior may vary with FluidNC versions.
- Software status (`Idle`) is not an independent position sensor. For open-loop stepper motors, missed steps cannot be detected by GUI alone.
- Movement is considered complete when FluidNC returns `Idle`, but this is not proof of physical position or that the machine has no vibration. Validate coordinates against the actual machine, especially if work offsets are active.
- An interrupted homing or move invalidates the app's homed flag; verify machine state before proceeding.
- During a scan, CSV is written incrementally; if interrupted, partial CSV data is retained.
- USB port names may change each time the ESP32 boards are reconnected.
- This is an initial student research prototype, not a certified machine controller.

## Tests

```powershell
python -m unittest discover -s tests -v
```
