# Wind Tunnel Control — merged FluidNC UI

The UI uses the group's `fluidnc_link.py` for USB serial motion, through the existing `backend/fluidnc_adapter.py`. The ESP32 already runs FluidNC with its hardware configuration. Do not flash it, upload the example YAML, or change GPIOs for this integration.

## Start on Windows (VS Code / Anaconda)

Open this `UI/wind_tunnel_ui` folder in VS Code, then in the terminal:

```powershell
conda activate windtunnel
python -m pip install -r requirements.txt
python main.py
```

Simulation is the startup default. Test Connect, Home, manual motion and a 2x2 scan first. No physical port is opened in simulation.

## One ESP32 — movement only

1. With machine safely supported and mains terminals covered, connect the FluidNC ESP32 via USB. Close Fluidterm, the CLI demo and any other serial program. Keep wind tunnel off during commissioning.
2. Select **FluidNC movement only**, choose the FluidNC COM port and click Connect. The sensor port and Read sensor are disabled. Connecting is not a move.
3. Click Refresh status. Inspect the existing FluidNC configuration before arming: `$CD` in a separate terminal session (close UI first). Verify working end switches, homing direction, allowed machine coordinates, speed, acceleration, mm reporting and independent physical stop. Do not bypass alarms or home without functioning switches. If no switches are installed, use supervised commissioning procedures outside this UI; the UI deliberately requires homing.
4. Set `machine_settings.py` bounds to the actual verified **machine coordinate** range (original 0–400 mm values are NOT verified; some machines home to negative coordinates). Restart the UI if you edit the file. This does not affect ESP32 firmware. Verify both axis origins and motion signs physically. Tick the hardware checked box only after the checks.
5. Click HOME / reference. The UI shows machine X and Y mapped to physical X and Z. Homing itself is a movement; clear the entire homing path first. If home is outside the PC bounds, the app refuses to mark it homed.
6. Start with a small target from the reported home position, e.g. 5 mm in X with Z unchanged, if clearance allows. Feed defaults to 60 mm/min. Verify actual displacement with a ruler. Then test Z independently and a small diagonal. Use verified coordinates, not automatically the example values.
7. Only after validating the above, choose a small 2x2 grid inside the verified travel area, then START MOVEMENT-ONLY GRID TEST. No sensor requests, fake velocity data, measurement CSVs or plots are generated.
8. Software HOLD sends `!` and invalidates homing. It is NOT an emergency stop and cannot guarantee a stop during homing or a communications fault. Use the independent physical stop for emergencies, and support the vertical load against dropping. Inspect machine before reconnecting or homing again. Never assume a reset releases safely.

## Full experiment / future

Choose **FluidNC + ESP32-C3** with two distinct USB ports. Sensor path is retained; the existing Arduino sensor sketch supports `MEASURE`, but real calibration, sensor demo mode and hardware have not been verified. No changes were made to the sensor firmware. Simulation still generates simulated data only in Simulation mode.

## Files and coordinate decisions

- `gui.py`: same UI, explicit mode and grid-only operation; no raw G-code.
- `backend/controller.py`: application workflow, motion-only scan, real sensor scan and simulation.
- `backend/fluidnc_adapter.py`: retains the motion contract, calls shared threaded link; explicitly sends `G21 G90 G94` and `G53 G1 X... Y... F...` in machine coordinates as the branch's older CLI backend did. Does not assume WPos equals MPos. Checks Idle and reported target (0.05 mm software tolerance, not actual measured accuracy). No automatic origin/offset setting.
- `fluidnc_link.py`: group serial library, with bounded write timeout, cancellable command waiting, serialized status requests and fault handling. Work-coordinate CLI commands explicitly set mm. UI and CLI must not access the same serial port simultaneously.
- `patterns.py`, `demo.py`: group's independent expert test tool. CLI patterns use work coordinates, not the UI machine coordinate frame; do not interchange values unless offsets are known. CLI can send raw commands and unlock alarms; it does not have UI travel/homing guards. Do not use unlock to bypass a safety alarm. Use only under supervision. `python demo.py --list` lists ports without moving.
- `machine_settings.py`: PC travel envelope and default feed. Not firmware settings.
- Existing `fluidnc_experiment/` CLI and `arduino/` files remain intact as historical/alternate implementations. Do not upload the Arduino motion firmware to the FluidNC ESP32.

## Verification and limitations

Run `python -m unittest discover -s tests -v`. Existing simulation tests and new fake-serial/movement-only tests exercise the Python backend. They do not certify machine motion, GPIO assignments, configuration, electrical compatibility, safety, or actual stepper behaviour. The GUI requires PySide6 and pyqtgraph; verify visually on the laptop. The current ESP32 configuration was not supplied and was not changed. The original positive travel bounds must be validated before use. Keep a backup of the actual ESP32 configuration separately.
