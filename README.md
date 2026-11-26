# Wind tunnel control — custom single-ESP32 main branch

This version updates the original `main` branch (Arduino C++ + laptop control) with the previously developed PySide6 UI, using **one ESP32 and one USB connection**. It does not use FluidNC. Your separate FluidNC branch is unaffected; the ZIP is a local working tree, not a Git commit or remote push.

## Quick start (no hardware)

Open PowerShell in `UI/wind_tunnel_ui`:

```powershell
conda run -n windtunnel python -m pip install -r requirements.txt
conda run --no-capture-output -n windtunnel python main.py
```

If you do not already have the `windtunnel` conda environment, create one with `conda create -n windtunnel python=3.11` first. Choose **Simulation**, Connect, HOME, Move to target, and then Automatic scan or Live results. Simulation does not require an ESP32. Simulated CSVs are labelled and stored in `measurements/simulation/`.

## Architecture

`main.py` → `gui.py` → `backend/controller.py` → `backend/custom_esp32_adapter.py` → USB serial → `arduino/base_esp32/base_esp32.ino` → `motor_control.cpp` and `sensors.cpp`. The `SharedSensor` facade uses the exact same serial connection as motion. `contracts.py` defines the UI-independent interface; `simulators.py` provides an offline backend. `machine_settings.py` is the PC limits configuration. The older `pc (runs ON LAPTOP)/control.py` now launches the UI; the original script is archived as text in `legacy/` because the former command protocol is not safe to run against this firmware unchanged.

## Before uploading

**Experimental firmware, not a certified motion/safety controller.** Keep the working FluidNC ESP32 intact and use a spare ESP32 DevKit for this alternative. If there is no spare, back up your working configuration and verify that you can restore FluidNC before overwriting it. Uploading the sketch replaces whatever firmware was installed on the selected ESP32. No ESP32 board compilation or physical testing was performed for this package.

The `reference/fluidnc-tested-config.yaml` file is the earlier tested config(3).yaml snapshot (not loaded by the new firmware). Its legacy comments on microstepping and switches were inconsistent with the active values; use the verified active values, not the comments. The custom config starts conservatively at 60 mm/min, 200 mm/s² acceleration, 500/100 mm/min homing speeds and a 3000 mm/min configured upper bound. These choices are **not verified custom-firmware performance**. The 160 steps/mm calibration was measured on FluidNC; verify both driver DIP switches and motion calibration again. Positive direction output is provisionally LOW on both motors to match the tested direction inversion; verify independently. Minimum switches are active-low, with internal pull-ups; maximum switches are absent. Active-low normally-open wiring may not detect a disconnected switch. Do not rely on software travel limits alone.

## Bench commissioning — first upload (motion locked)

1. Mechanically secure the vertical axis against falling, turn off the wind tunnel, isolate driver power and disconnect STEP/DIR signals from drivers before changing wiring. Verify an independent physical stop and safe vertical holding arrangement. Do not disconnect energized motor wiring. Keep exposed mains covered.
2. In Arduino IDE, install the Espressif ESP32 board package and select the correct **ESP32 Dev Module or exact matching DevKit board**, not ESP32-C3. Open `arduino/base_esp32/base_esp32.ino` (all six sketch files must remain together). Verify/compile. Select the spare ESP32's port, then upload. `MOTION_ENABLED = false` in `config.h` by default, so HOME and MOVE cannot generate pulses.
3. With the drivers isolated, open Serial Monitor at 115200 baud, Newline. Send `PING`, `CAPS`, `LIMITS`, `MODE`, `POS`. Expected PING: `OK,PONG,WINDTUNNEL_CUSTOM_V2`; CAPS: `OK,CAPS,LOCKED,340.0,300.0,3000.0`. LIMITS reports X-min,Z-min as `0` released and `1` pressed. Verify both switches individually (and both released). POS reports `NA,NA,UNHOMED`. HOME must fail while locked. Close Serial Monitor before opening the UI.
4. Test USB/GUI with **Custom ESP32 movement only**. Select the actual port. Connect; the UI displays MOTION LOCKED. It deliberately disables movement. For demo sensor communication change `DEMO_SENSOR_MODE` to `true`, leave motion locked, re-upload, and choose **Custom ESP32 + sensors**. Read sensor should return labelled DEMO zeros. These are not measurements. Return demo mode to false before experiments.

## Controlled motion commissioning

Only after the bench checks, with the motor outputs **still isolated from the drivers**, set `MOTION_ENABLED = true` in `config.h` and recompile/upload. Connect in the UI with **Custom ESP32 movement only**. Check signal timing/polarity with a scope or logic analyser, and manually operate the selected switches to exercise the homing sequence. The first Z seek should command opposite motor directions, followed by opposite pull-off; X seek should command same motor directions. Verify directions against the working FluidNC signals or safe uncoupled motor tests, not only the assumed polarity. Stop/reconnect if any unexpected behavior occurs. Verify that stop interrupts pulse generation and heartbeat loss stops the firmware. After confirming correct wiring, polarity, timing and independent stop, reconnect drivers with power isolated and recheck mechanical clearance and vertical restraint. Home only under supervision, at low speeds with physical stop within reach. If needed, lower `HOME_SEEK_MM_MIN` to 100 and `HOME_FEED_MM_MIN` to 50 for first physical tests. Do not arm the UI before these checks.

The homing sequence is Z then X. Each axis seeks, retracts 2 mm, approaches at the slower feed, retracts 2 mm again and verifies the switch is released. If already pressed, it first retracts. Both axes must finish before the reference becomes (0,0). Homing search is bounded but can still hit a mechanical end if a switch is missing, incorrectly wired or the motion direction is wrong; the firmware cannot establish physical position before homing.

Begin with 5 mm single-axis moves at 60 mm/min, then 5 mm diagonal, return to zero, measure actual distance/direction, and repeat homing. Use small grids before full travel. Increase speed only in small steps after checking missed steps, noise, stopping and vibrations. The firmware interpolates absolute motor targets via A=X+Z, B=X−Z, and computes a path-based triangular/trapezoidal velocity profile. Pulse timing is software-based, not hardware RMT; actual feed, timing, acceleration and vibration performance must be measured and may differ from FluidNC. Reported position is open-loop commanded motor-step position, not encoder measurement. Position updates after completed commands, not continuously during motion.

## Software stop and heartbeat

The GUI sends `!` to stop, and sends `~` at 250 ms intervals while waiting for HOME/MOVE. During motion the ESP32 checks these bytes and switch states, and stops if the heartbeat is absent for 2 seconds. It invalidates homing on fault or stop, leaving drivers enabled to hold the vertical axis. This stop is abrupt (not controlled deceleration), best effort, and **not an emergency stop**. Mechanical restraint and an independent physical stop remain mandatory. After software stop during an active command, reconnect and re-home to avoid late replies. Do not use a normal Serial Monitor for full movement commands; it does not send ongoing heartbeat. No unattended operation.

## Sensor testing / real sensor implementation

- Simulation: synthetic spatial velocity and pressure, independent of hardware.
- Custom ESP32 movement only: no sensor requests or scan CSVs.
- Custom ESP32 + sensors: one ESP32 handles motion and MEASURE over the same port. `MODE` handshake labels DEMO or REAL. Demo zeros are segregated in `measurements/demo/`; real data would go to `measurements/real/` with an explicit `source` CSV field.
- With `DEMO_SENSOR_MODE=false`, real air speed is **not implemented**: MEASURE returns `ERR,AIR_SPEED_NOT_IMPLEMENTED_OR_UNAVAILABLE` rather than a fake value. The original sensor functions and TODOs remain in `sensors.cpp`; assign verified GPIOs and safe signal conditioning in `config.h`, implement/calibrate `readAirSpeed()`, `readPressure()` and `readTemperature()` after reviewing the actual sensor electronics. Pressure and temperature may be absent (`NA`) without rejecting a valid velocity. The FS7 CTA board output may exceed ESP32 ADC limits; verify before connection. No guessed calibration or sensor library has been introduced.
- Manual measurements appear in Live results; automatic scans save CSV after each point (with reported coordinates, timestamp, velocity, pressure, temperature and source). An interrupted scan may leave a partial CSV; do not treat it as a completed scan.

## Commands (115200 baud, ASCII newline except realtime bytes)

| Request | Successful response |
|---|---|
| `PING` | `OK,PONG,WINDTUNNEL_CUSTOM_V2` |
| `CAPS` | `OK,CAPS,LOCKED,340.0,300.0,3000.0` or ENABLED |
| `MODE` | `OK,MODE,REAL` or DEMO |
| `LIMITS` | `OK,LIMITS,0,0` (X-min,Z-min) |
| `HOME` | `OK,HOME,0.0000,0.0000,HOMED` |
| `MOVE,20,30,60` | `OK,MOVE,20.0000,30.0000,HOMED` (feed mm/min) |
| `POS` | `OK,POS,x,z,HOMED` or `OK,POS,NA,NA,UNHOMED` |
| `MEASURE` | `OK,MEASURE,u,p,t` (NA allowed for optional sensors) |
| `!` | Immediate software stop request, no separate reply |
| `~` | Heartbeat, no reply |

HOME/MOVE respond only when finished or failed. Error responses begin `ERR,`. The original `MOVE,x,z` syntax uses the conservative default feed, but this protocol requires the heartbeat for sustained motion. Do not send queued commands during movement.

## Validation performed

- Python syntax compilation; 10 unit/integration tests pass using simulated and fake serial peers.
- C++11 syntax check of the sketch and both implementation files using a minimal host Arduino API shim. Native C++ tests passed for default motion lock, homing, pure and diagonal step counts, round trip, bounds, stop, heartbeat loss, starting on switches, hard limits, stuck and missing switches. This is not an ESP32 hardware simulation.
- Not performed: Arduino ESP32 toolchain compilation, GUI rendering/interactive test (Qt dependencies not installed in the build environment), physical movement or real sensor validation.

Run tests from the project root (native C++ test needs `g++`):

```powershell
python tests/firmware/run_host_tests.py
cd UI/wind_tunnel_ui
python -m unittest discover -s tests -v
```

## GitHub

Extract the ZIP outside the current Git working tree. In the actual local repository, check out `main`, ensure `git status` is clean and pull the latest changes. Copy the **contents** of the extracted `wind_tunnel_control-main` folder into the repository root, not the enclosing folder, review the diff, commit and push. The ZIP does not contain `.git`; it does not modify any remote branch. Preserve the separate FluidNC branch and do not overwrite unrelated changes that have occurred since the supplied main snapshot.
