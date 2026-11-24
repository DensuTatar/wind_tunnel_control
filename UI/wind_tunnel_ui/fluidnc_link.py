"""
fluidnc_link.py - minimal USB-serial link to a FluidNC (GRBL-compatible) controller.

Designed for a CoreXY probe traverser: one command in flight at a time,
so every call returns only after FluidNC has answered 'ok' (or raises).

    from fluidnc_link import FluidNC
    with FluidNC("COM5") as cnc:          # or "/dev/ttyUSB0"
        cnc.home()
        cnc.move_to(50, 50, feed=1500)
        cnc.wait_until_stopped()          # G4 P0: returns when motion is done
        print(cnc.status())

Requires: pip install pyserial
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from dataclasses import dataclass, field

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # allow import for testing without pyserial
    serial = None

log = logging.getLogger("fluidnc")

# Realtime commands (sent as single bytes, no newline, bypass the queue)
RT_STATUS = b"?"
RT_FEED_HOLD = b"!"
RT_CYCLE_START = b"~"
RT_SOFT_RESET = b"\x18"
RT_JOG_CANCEL = b"\x85"


class FluidNCError(Exception):
    """FluidNC answered 'error:N' to a command."""


class FluidNCAlarm(FluidNCError):
    """FluidNC went into an ALARM state (e.g. homing failed, limit hit)."""


@dataclass
class Status:
    state: str                       # Idle, Run, Jog, Hold:0, Alarm, Home, ...
    mpos: tuple[float, ...] | None   # machine position
    wpos: tuple[float, ...] | None   # work position (if computable)
    raw: str = ""
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def is_idle(self) -> bool:
        return self.state.startswith("Idle")

    @property
    def x(self) -> float | None:
        p = self.wpos or self.mpos
        return p[0] if p else None

    @property
    def y(self) -> float | None:
        p = self.wpos or self.mpos
        return p[1] if p and len(p) > 1 else None


def _parse_xyz(s: str) -> tuple[float, ...]:
    return tuple(float(v) for v in s.split(","))


def list_ports() -> list[str]:
    """Return a list of serial port names with descriptions."""
    if serial is None:
        return []
    return [f"{p.device}  ({p.description})" for p in serial.tools.list_ports.comports()]


class FluidNC:
    def __init__(self, port: str | None = None, baud: int = 115200,
                 boot_wait: float = 3.0, ser=None):
        """
        port      : 'COM5', '/dev/ttyUSB0', ... (ignored if `ser` is given)
        boot_wait : seconds to wait for the ESP32 to reboot after the port opens
        ser       : optional pre-made serial-like object (used for testing)
        """
        if ser is None:
            if serial is None:
                raise RuntimeError("pyserial is not installed: pip install pyserial")
            ser = serial.Serial(port, baud, timeout=0.1, write_timeout=1)
        self._ser = ser
        self._write_lock = threading.Lock()
        self._cmd_lock = threading.Lock()
        self._responses: queue.Queue[str] = queue.Queue()
        self._statuses: queue.Queue[str] = queue.Queue()
        self._wco: tuple[float, ...] | None = None
        self.messages: list[str] = []          # [MSG:..] and other info lines
        self.on_line = None                    # optional callback(line) for every line
        self._running = True
        self._fault = None
        self._ready = False
        self._status_lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        try:
            self._wait_for_controller(boot_wait)
            self._ready = True
        except Exception:
            self.close()
            raise

    # ------------------------------------------------------------------ I/O
    def _read_loop(self):
        buf = b""
        while self._running:
            try:
                chunk = self._ser.read(256)
            except Exception as e:  # port closed / unplugged
                log.error("serial read failed: %s", e)
                if self._running:
                    self._fault = f"Serial read failed: {e}"
                break
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode(errors="replace").strip()
                if line:
                    self._dispatch(line)

    def _dispatch(self, line: str):
        if self._ready and line.lower().startswith(("grbl", "fluidnc")):
            self._fault = "Controller restarted; reconnect and home"
        if line.startswith("ALARM"):
            self._fault = line
        if self.on_line:
            try:
                self.on_line(line)
            except Exception:
                pass
        if line.startswith("<") and line.endswith(">"):
            self._statuses.put(line)
        elif line == "ok" or line.startswith("error") or line.startswith("ALARM"):
            log.debug("<< %s", line)
            self._responses.put(line)
        else:
            log.info("<< %s", line)
            self.messages.append(line)
            if len(self.messages) > 1000:
                del self.messages[:-1000]

    def _write(self, data: bytes, cancelled=None):
        with self._write_lock:
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError("Movement cancelled before command was sent")
            self._ser.write(data)

    def _wait_for_controller(self, boot_wait: float):
        """ESP32 often reboots when the port opens; wait until it answers '?'."""
        deadline = time.time() + boot_wait + 10
        time.sleep(boot_wait)
        while time.time() < deadline:
            try:
                st = self.status(timeout=0.5)
                log.info("connected, state=%s", st.state)
                return
            except TimeoutError:
                self._write(b"\n")
        raise TimeoutError("FluidNC did not answer a status request - check port/baud")

    # ------------------------------------------------------------ commands
    def send(self, line: str, timeout: float = 30.0, cancelled=None) -> None:
        """Send one line of G-code / $-command and wait for 'ok'.
        Raises FluidNCError on 'error:N', FluidNCAlarm on 'ALARM:N'."""
        line = line.strip()
        if not line:
            return
        with self._cmd_lock:
            if self._fault and self._ready:
                raise FluidNCAlarm(self._fault)
            while True:
                try:
                    self._responses.get_nowait()
                except queue.Empty:
                    break
            log.debug(">> %s", line)
            self._write((line + "\n").encode(), cancelled)
            deadline = time.monotonic() + timeout
            while True:
                if cancelled is not None and cancelled.is_set():
                    self._fault = "Command interrupted; reconnect and verify machine"
                    raise InterruptedError(self._fault)
                if self._fault and self._ready:
                    raise FluidNCAlarm(self._fault)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._fault = f"No reply to {line!r}; reconnect and verify machine"
                    raise TimeoutError(self._fault)
                try:
                    reply = self._responses.get(timeout=min(0.1, remaining))
                    break
                except queue.Empty:
                    continue
        if reply == "ok":
            return
        if reply.startswith("ALARM"):
            raise FluidNCAlarm(f"{reply} after {line!r}")
        raise FluidNCError(f"{reply} after {line!r}")

    def send_program(self, lines, timeout: float = 120.0) -> None:
        """Send several G-code lines in order, each waiting for 'ok'."""
        for ln in lines:
            ln = ln.split(";", 1)[0].strip()   # strip comments
            if ln:
                self.send(ln, timeout=timeout)

    def realtime(self, byte: bytes) -> None:
        """Send a realtime command byte (status, hold, resume, reset, jog cancel)."""
        self._write(byte)

    def status(self, timeout: float = 1.0) -> Status:
        """Ask for and parse a status report, e.g. <Idle|MPos:0.000,0.000,0.000|FS:0,0>"""
        with self._status_lock:
            while True:
                try:
                    self._statuses.get_nowait()
                except queue.Empty:
                    break
            self._write(RT_STATUS)
            try:
                raw = self._statuses.get(timeout=timeout)
            except queue.Empty:
                raise TimeoutError("no status report")
            return self._parse_status(raw)

    def _parse_status(self, raw: str) -> Status:
        parts = raw[1:-1].split("|")
        state, fields = parts[0], {}
        for p in parts[1:]:
            if ":" in p:
                k, v = p.split(":", 1)
                fields[k] = v
        if "WCO" in fields:
            self._wco = _parse_xyz(fields["WCO"])
        mpos = wpos = None
        if "MPos" in fields:
            mpos = _parse_xyz(fields["MPos"])
            if self._wco:
                wpos = tuple(m - w for m, w in zip(mpos, self._wco))
        if "WPos" in fields:
            wpos = _parse_xyz(fields["WPos"])
            if self._wco:
                mpos = tuple(w + o for w, o in zip(wpos, self._wco))
        return Status(state, mpos, wpos, raw, fields)

    # -------------------------------------------------------- convenience
    def home(self, timeout: float = 120.0, cancelled=None):
        """Run the homing cycle ($H)."""
        if self._fault and self._fault.startswith("ALARM"):
            self._fault = None
        self.send("$H", timeout=timeout, cancelled=cancelled)

    def unlock(self):
        """Clear an alarm lock ($X) - only use when you know where the machine is."""
        self._fault = None
        self.send("$X")

    def move_to(self, x: float | None = None, y: float | None = None,
                feed: float | None = None, rapid: bool = False):
        """Absolute move (mm). Queues the move; use wait_until_stopped() to block."""
        words = ["G21", "G90", "G0" if rapid else "G1"]
        if x is not None:
            words.append(f"X{x:.3f}")
        if y is not None:
            words.append(f"Y{y:.3f}")
        if feed is not None and not rapid:
            words.append(f"F{feed:.0f}")
        self.send(" ".join(words))

    def move_by(self, dx: float = 0.0, dy: float = 0.0, feed: float = 1000.0):
        """Relative move (mm), then back to absolute mode."""
        self.send(f"G21 G91 G1 X{dx:.3f} Y{dy:.3f} F{feed:.0f}")
        self.send("G90")

    def wait_until_stopped(self, settle: float = 0.0, timeout: float = 300.0):
        """Block until all queued motion is finished (G4 P0), plus optional settle seconds."""
        self.send(f"G4 P{settle:.3f}", timeout=timeout)

    def jog(self, dx: float = 0.0, dy: float = 0.0, feed: float = 1000.0):
        """Jog relative (mm) using $J=. Jogs can be cancelled with jog_cancel()."""
        self.send(f"$J=G91 G21 X{dx:.3f} Y{dy:.3f} F{feed:.0f}")

    def jog_cancel(self):
        self.realtime(RT_JOG_CANCEL)

    def wait_idle(self, timeout: float = 300.0, poll: float = 0.1) -> Status:
        """Poll status until Idle (use after jogs - G4 is not allowed while jogging)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            st = self.status()
            if st.is_idle:
                return st
            if st.state.startswith("Alarm"):
                raise FluidNCAlarm(f"machine in alarm: {st.raw}")
            time.sleep(poll)
        raise TimeoutError("machine did not become idle")

    def feed_hold(self):
        self.realtime(RT_FEED_HOLD)

    def resume(self):
        self.realtime(RT_CYCLE_START)

    def soft_reset(self):
        """Stop immediately and clear the planner. Position may be lost -> re-home."""
        self.realtime(RT_SOFT_RESET)
        time.sleep(1.0)
        self._fault = None  # explicit reset; UI does not call this automatically

    def close(self):
        self._running = False
        try:
            self._ser.close()
        except Exception:
            pass

        if self._reader is not threading.current_thread():
            self._reader.join(timeout=1)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
