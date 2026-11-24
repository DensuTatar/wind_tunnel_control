"""Safe, disconnected-from-hardware implementations for UI and scan tests."""
import math
import threading
import time
from .contracts import Position, Measurement, MachineStatus


class SimulatedMotion:
    def __init__(self):
        self.connected = False
        self.homed = False
        self.position = Position(0.0, 0.0)
        self.state = "Disconnected"

    def connect(self):
        self.connected = True
        self.state = "Idle"

    def disconnect(self):
        self.connected = False
        self.homed = False
        self.state = "Disconnected"

    def home(self, cancelled: threading.Event):
        self._check_cancel(cancelled)
        time.sleep(0.15)
        self.position = Position(0.0, 0.0)
        self.homed = True
        self.state = "Idle"
        return self.position

    def move_to(self, position: Position, feed_mm_min: float, cancelled: threading.Event):
        if not self.connected or not self.homed:
            raise RuntimeError("Simulation not connected and homed")
        self.state = "Run"
        try:
            # Short simulated delay, intentionally not representative of physical dynamics.
            for _ in range(6):
                self._check_cancel(cancelled)
                time.sleep(0.025)
            self.position = position
        finally:
            self.state = "Idle"
        return self.position

    def get_status(self):
        return MachineStatus(self.state, self.position)

    def feed_hold(self):
        self.state = "Hold"

    @staticmethod
    def _check_cancel(cancelled):
        if cancelled.is_set():
            raise InterruptedError("Scan stopped by user")


class SimulatedSensor:
    def __init__(self, motion: SimulatedMotion):
        self.motion = motion
        self.connected = False
        self.n = 0

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def sample(self) -> Measurement:
        if not self.connected:
            raise RuntimeError("Simulation sensor not connected")
        self.n += 1
        pos = self.motion.position
        velocity = 11.5 + 1.6 * math.sin(pos.x_mm / 95.0) - 0.75 * math.cos(pos.z_mm / 105.0) + 0.09 * math.sin(self.n * 0.8)
        return Measurement(round(velocity, 3), round(0.5 * 1.2 * velocity**2, 2), 22.0)
