"""Application service: GUI knows only these methods and emitted events."""
import csv
import math
from datetime import datetime
from pathlib import Path
import threading
import time
from .contracts import Position, Measurement, MachineLimits, ScanPlan
from .simulators import SimulatedMotion, SimulatedSensor
from .fluidnc_adapter import FluidNCMotion
from .sensor_adapter import SerialSensor


class WindTunnelController:
    def __init__(self, on_event, limits: MachineLimits | None = None, output_dir="measurements"):
        self.notify = on_event
        self.limits = limits or MachineLimits()
        self.output_dir = Path(output_dir)
        self.motion = None
        self.sensor = None
        self.mode = None
        self.cancel = threading.Event()
        self.records = []
        self.homed = False
        self.connected = False
        self._sensor_connected = False

    def connect(self, mode: str, motion_port: str = "", sensor_port: str = ""):
        self.disconnect()
        self.cancel.clear()
        if mode == "Simulation":
            motion = SimulatedMotion()
            sensor = SimulatedSensor(motion)
        elif mode in ("FluidNC movement only", "FluidNC + ESP32-C3"):
            if not motion_port.strip():
                raise ValueError("Select the FluidNC serial port")
            if mode == "FluidNC movement only":
                sensor_port = ""
            elif not sensor_port.strip():
                raise ValueError("Select the sensor serial port, or choose FluidNC movement only")
            if sensor_port and sensor_port == motion_port:
                raise ValueError("The motion and sensor USB ports must be different")
            motion = FluidNCMotion(motion_port)
            sensor = SerialSensor(sensor_port) if sensor_port.strip() else None
        else:
            raise ValueError(f"Unsupported mode {mode}")
        try:
            motion.connect()
            if sensor:
                sensor.connect()
        except Exception:
            motion.disconnect()
            if sensor:
                sensor.disconnect()
            raise
        self.motion, self.sensor = motion, sensor
        self.mode = mode
        self.connected = True
        self._sensor_connected = sensor is not None
        self.homed = False
        self.notify("connected", {"mode": mode, "sensor": self._sensor_connected})

    def disconnect(self):
        self.cancel.set()
        if self.motion:
            self.motion.disconnect()
        if self.sensor:
            self.sensor.disconnect()
        self.motion, self.sensor = None, None
        self.connected = False
        self.homed = False
        self._sensor_connected = False
        self.notify("disconnected", None)

    def home(self):
        self._require_motion()
        self.cancel.clear()
        self.homed = False
        self.notify("activity", "Homing")
        p = self.motion.home(self.cancel)
        self._check_cancel()
        self.limits.validate(p)
        self.homed = True
        self.notify("position", p)
        self.notify("activity", "Ready")

    def move_to(self, x_mm: float, z_mm: float, feed_mm_min: float):
        self._require_homed()
        p = Position(x_mm, z_mm)
        self.limits.validate(p)
        if not (1 <= feed_mm_min <= 2000):
            raise ValueError("Feed must be between 1 and 2000 mm/min")
        self.cancel.clear()
        self.notify("activity", "Moving")
        try:
            actual = self.motion.move_to(p, feed_mm_min, self.cancel)
        except Exception:
            self.homed = False
            raise
        self._check_cancel()
        self.notify("position", actual)
        self.notify("activity", "Ready")

    def read_once(self):
        self._require_motion()
        if not self.sensor:
            raise RuntimeError("No sensor adapter connected")
        reading = self.sensor.sample()
        pos = self.motion.get_status().position
        self.notify("measurement", {"reading": reading, "position": pos})
        return reading

    def run_scan(self, plan: ScanPlan):
        self._require_homed()
        if not self.sensor:
            if self.mode != "FluidNC movement only":
                raise RuntimeError("Connect the sensor ESP32-C3 before scanning")
            return self.run_dry_scan(plan)
        plan.validate(self.limits)
        self.cancel.clear()
        self.records = []
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self.output_dir / ("scan_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
        total = plan.nx * plan.nz
        self.notify("scan_progress", {"done": 0, "total": total})
        self.notify("activity", "Scanning")
        try:
            with filename.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "x_mm", "z_mm", "speed_ms", "pressure_pa", "temperature_c"])
                for i, position in enumerate(plan.points(), 1):
                    self._check_cancel()
                    self.motion.move_to(position, plan.feed_mm_min, self.cancel)
                    self.notify("position", position)
                    self._sleep_interruptibly(plan.settle_s)
                    readings = []
                    for _ in range(plan.samples_per_point):
                        self._check_cancel()
                        readings.append(self.sensor.sample())
                    reading = Measurement(
                        speed_ms=self._mean([r.speed_ms for r in readings]),
                        pressure_pa=self._mean([r.pressure_pa for r in readings]),
                        temperature_c=self._mean([r.temperature_c for r in readings]),
                    )
                    writer.writerow([reading.timestamp, position.x_mm, position.z_mm,
                                     reading.speed_ms, reading.pressure_pa, reading.temperature_c])
                    f.flush()
                    self.records.append((position, reading))
                    self.notify("measurement", {"reading": reading, "position": position})
                    self.notify("scan_progress", {"done": i, "total": total})
            self.notify("scan_finished", {"path": str(filename.resolve()), "count": total})
        except Exception:
            self.homed = False  # conservative on communication or motion failure
            raise
        finally:
            self.notify("activity", "Ready / inspect machine if stopped")

    def run_dry_scan(self, plan: ScanPlan):
        """Traverse the grid without sampling, creating CSVs or plotting data."""
        self._require_homed()
        plan.validate(self.limits)
        self.cancel.clear()
        self.records = []
        total = plan.nx * plan.nz
        self.notify("scan_progress", {"done": 0, "total": total})
        self.notify("activity", "Movement-only grid test")
        try:
            for i, position in enumerate(plan.points(), 1):
                self._check_cancel()
                reported = self.motion.move_to(position, plan.feed_mm_min, self.cancel)
                self.notify("position", reported)
                self._sleep_interruptibly(plan.settle_s)
                self._check_cancel()
                self.notify("scan_progress", {"done": i, "total": total})
            self.notify("dry_scan_finished", {"count": total})
            self.notify("activity", "Ready")
        except Exception:
            self.homed = False
            raise

    def request_hold(self):
        """Thread-safe, best-effort SOFTWARE hold; not an emergency stop."""
        self.cancel.set()
        if self.motion:
            try:
                self.motion.feed_hold()
            except Exception as e:
                self.notify("error", f"Feed hold could not be delivered: {e}")
        self.homed = False  # conservative: re-home or verify state before further motion
        self.notify("activity", "STOP / HOLD — verify before continuing")

    def _require_motion(self):
        if not self.connected or not self.motion:
            raise RuntimeError("Connect the motion controller first")

    def _require_homed(self):
        self._require_motion()
        if not self.homed:
            raise RuntimeError("Home and verify the traverser first")

    def _check_cancel(self):
        if self.cancel.is_set():
            raise InterruptedError("Scan stopped by user")

    def _sleep_interruptibly(self, secs):
        end = time.monotonic() + secs
        while time.monotonic() < end:
            self._check_cancel()
            time.sleep(min(0.05, end - time.monotonic()))

    @staticmethod
    def _mean(values):
        nums = [x for x in values if x is not None and math.isfinite(x)]
        return sum(nums)/len(nums) if nums else None

    def refresh_status(self):
        self._require_motion()
        status = self.motion.get_status()
        if status.state not in ("Idle", "Run", "Home", "Jog") or status.position is None:
            self.homed = False
        self.notify("machine_status", status)
        if status.position is not None:
            self.notify("position", status.position)
