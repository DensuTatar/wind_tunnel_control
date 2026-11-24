"""FluidNC/Grbl-compatible serial adapter.

This is an adapter to the known G-code approach, not a replacement for an
uninspected copy of the project's original fluidnc_motion.py.
Logical FluidNC X = physical traverser X; logical FluidNC Y = physical Z.
CoreXY motor mixing must be configured and validated in FluidNC config.yaml.
"""
import re
import threading
import time
from .contracts import MachineStatus, Position

_STATUS_RE = re.compile(r"^<([^|>]+)(?:\|([^>]*))?>$")
_POS_RE = re.compile(r"(?:^|\|)(MPos|WPos):(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def parse_status(line: str) -> MachineStatus | None:
    match = _STATUS_RE.match(line.strip())
    if not match:
        return None
    body = match.group(2) or ""
    position = _POS_RE.search("|" + body)
    pos = Position(float(position.group(2)), float(position.group(3))) if position else None
    return MachineStatus(match.group(1).split(":")[0], pos)


class FluidNCMotion:
    def __init__(self, port: str, baud: int = 115200):
        self.port, self.baud = port, baud
        self.ser = None
        self.homed = False
        self._write_lock = threading.Lock()
        self._last_status = MachineStatus("Disconnected")

    def connect(self):
        import serial
        self.ser = serial.Serial(self.port, self.baud, timeout=0.2, write_timeout=1)
        # Do not assume an already-homed machine after connecting.
        time.sleep(0.35)
        self._last_status = MachineStatus("Unknown")

    def disconnect(self):
        if self.ser:
            self.ser.close()
            self.ser = None
        self.homed = False
        self._last_status = MachineStatus("Disconnected")

    def _write(self, message: bytes):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("FluidNC serial port not connected")
        with self._write_lock:
            self.ser.write(message)

    def _read(self) -> str:
        if not self.ser:
            raise RuntimeError("FluidNC not connected")
        return self.ser.readline().decode("utf-8", errors="replace").strip()

    def _command(self, line: str, timeout_s: float = 8):
        self._write((line + "\n").encode("ascii"))
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            msg = self._read()
            if not msg:
                continue
            status = parse_status(msg)
            if status:
                self._last_status = status
                continue
            if msg.startswith("error:") or msg.startswith("ALARM:") or msg.startswith("[MSG:ERR"):
                raise RuntimeError(f"FluidNC rejected {line!r}: {msg}")
            if msg == "ok":
                return
        raise TimeoutError(f"No acknowledgment for FluidNC command {line!r}")

    def get_status(self) -> MachineStatus:
        self._write(b"?")  # Grbl real-time status request; no newline
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            msg = self._read()
            parsed = parse_status(msg)
            if parsed:
                self._last_status = parsed
                return parsed
            if msg.startswith("ALARM:"):
                self._last_status = MachineStatus("Alarm")
                return self._last_status
        raise TimeoutError("No FluidNC status response")

    def _wait_idle(self, cancelled: threading.Event, timeout_s: float):
        deadline = time.monotonic() + timeout_s
        time.sleep(0.10)
        while time.monotonic() < deadline:
            if cancelled.is_set():
                raise InterruptedError("Movement interrupted; homing state must be rechecked")
            status = self.get_status()
            if status.state in ("Alarm", "Door"):
                self.homed = False
                raise RuntimeError(f"FluidNC entered {status.state} state")
            if status.state == "Idle":
                return status
            if status.state == "Hold":
                raise InterruptedError("FluidNC is on hold")
            time.sleep(0.15)
        raise TimeoutError("FluidNC did not return to Idle")

    def home(self, cancelled: threading.Event) -> Position:
        self.homed = False
        self._command("$H", timeout_s=100)
        state = self._wait_idle(cancelled, timeout_s=100)
        self.homed = True
        return state.position or Position(0, 0)

    def move_to(self, position: Position, feed_mm_min: float, cancelled: threading.Event) -> Position:
        if not self.homed:
            raise RuntimeError("Home and validate the machine before movement")
        state = self.get_status()
        if state.state != "Idle":
            raise RuntimeError(f"FluidNC not Idle: {state.state}")
        self._command("G21")
        self._command("G90")
        # G-code Y is physical Z. Requires verified work coordinate origin.
        self._command(f"G1 X{position.x_mm:.3f} Y{position.z_mm:.3f} F{feed_mm_min:.2f}")
        end_state = self._wait_idle(cancelled, timeout_s=120)
        # FluidNC can report machine or work coordinates; never infer target
        # attainment without a verified coordinate offset.
        return end_state.position or position

    def feed_hold(self):
        if self.ser and self.ser.is_open:
            self._write(b"!")  # Software feed hold, NOT an emergency stop.
