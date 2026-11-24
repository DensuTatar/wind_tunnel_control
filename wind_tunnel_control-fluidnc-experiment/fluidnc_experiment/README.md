# FluidNC experiment — separate from the custom wired controller

This folder is an additive prototype for an A/B comparison. It is not commissioned firmware.

## Architecture

PC Python -> USB serial -> base ESP32 running FluidNC -> STEP/DIR drivers + four limit switches.
PC Python -> separate USB serial -> ESP32-C3 -> sensor interface (ADC/conditioning as required).
No ESP-NOW. The same base ESP32 cannot run the original Arduino sketch and stock FluidNC at the same time. Save the current firmware/config and preferably use a spare compatible board for tests.

## Files

- `config.yaml.example`: machine parameters for FluidNC; **not ready to upload**. Motor A = FluidNC x motor0; B = y motor0. Physical Z is logical Y. Verify mapping and motor/switch directions.
- `fluidnc_motion.py`: G-code and status interface (`$H`, `G21 G90`, `G53 G1`, `?`). Waits for Idle and target MPos, not just ok. Reported MPos is open-loop, not independent position feedback.
- `control_fluidnc.py`: independent implementation of our existing 2x2 test grid, settling, averaging, CSV and plots; requires separate serial ports for motion and sensors. Grid coordinates are relative to the confirmed post-homing position, not the switch itself. Match the physical origin when comparing against the old firmware.
- `sensor_esp32c3/`: minimal USB-only sensor sketch. Original sensor functions reused; real readings still return NAN until implemented. Demo mode false; explicitly marked and opt-in if used.

## Before energizing anything

1. Confirm base board/FluidNC version, driver input levels/pulse width, enable polarity, microstep DIP or driver settings. Use the official installer for the matching target: https://installer.fluidnc.com/ ; source: https://github.com/bdring/FluidNC .
2. Copy `config.yaml.example` to `config.yaml` locally and replace NO_PIN with verified GPIO assignments for all four STEP/DIR and all four limit inputs. Do not use the template to operate the gantry. Confirm pullups/polarity, available output pins and no duplicate/share conflicts. Configure enable pins if present. Verify config against the installed version and startup diagnostics, including CoreXY and both axes' travel ranges. 400 mm is nominal only; measure safe post-pull-off travel with clearance to far switches. Configure both axes sequential to avoid coupled homing. 80 steps/mm assumes 400 steps/rev, 8 microsteps, 20 teeth, 2 mm pitch. 25 mm/s², pulse and direction timing are proposed only; tune after verification.
3. Support the vertical carriage against gravity, provide an independent emergency stop and mechanical restraint, and verify switch indications and stopping before powered travel. idle_ms 255 avoids automatic disable but does not protect against power loss, reset, or driver failure. No automatic restart or alarm unlock in the Python script.
4. With the machine secured, verify motor directions, CoreXY mapping, limit inputs and their homing behavior one axis at a time under supervision; establish safe clearances and confirm successful full homing. Confirm machine position (MPos) reports in mm through `?` and the selected G-code dialect. Ensure the post-home origin plus 20 mm fits each verified travel range. Do not use the scan as the initial commissioning procedure.
5. On the separate C3 board select the correct Arduino target and configure USB serial (USB CDC on boot if needed by board). Compile/upload sensor sketch only to the C3. Check sensor voltages, calibration and acquisition. Three finite channels currently required. For speed-only measurements adapt the protocol/CSV deliberately rather than pretending missing channels are zero.

## Running on Windows (from repo root)

    python -m pip install -r fluidnc_experiment/requirements.txt
    python fluidnc_experiment/control_fluidnc.py

Default run prints an offline preview; opens no serial ports.

Only after commissioning, with correct COM ports and a supervisor:

    python fluidnc_experiment/control_fluidnc.py --live --commissioned --motion-only --motion-port COM5
    python fluidnc_experiment/control_fluidnc.py --live --commissioned --motion-port COM5 --sensor-port COM6

COM5/COM6 are examples. Close Arduino serial monitor and other G-code senders. Synthetic-data test requires setting DEMO_SENSOR_MODE true on the C3 and adding --allow-demo; CSV/plots explicitly marked DEMO. Return mode to false before experiments. The scan prechecks measurements before homing. On errors it requests feed hold if possible, which does not guarantee stopping and is not a safety-rated emergency stop. Do not resume automatically.

## Comparison

Same verified physical origin, motion feed, payload and scan points on both controllers; compare measured positioning error/repeatability using an external reference, missed steps, movement and settling time, vibration, and sensor integration complexity. Start with motion-only tests. Select acceleration experimentally. Avoid comparing synthetic samples as experimental data.

## References

- https://github.com/bdring/fluidnc-config-files/blob/main/official/TMC2209_corexy.yaml (CoreXY layout example, not a pinout for our board)
- https://github.com/bdring/FluidNC/blob/main/FluidNC/docs/config_items.yaml (configuration keys)
- https://github.com/bdring/FluidNC/wiki/Serial-Protocol (realtime status)
- https://github.com/bdring/FluidNC/wiki/Machine-Space-and-Homing (machine origin)

Prototype checks: offline Python preview, simulated serial tests, and YAML syntax only. No actual FluidNC flash, Arduino build, or physical validation.
