"""Stable motion API over the team's threaded FluidNC serial transport.
UI positions are machine coordinates in mm, X = X, physical Z = FluidNC Y.
No GPIO assignments or motor kinematics are performed on the PC.
"""
import math
import threading
import time
from .contracts import Position, MachineStatus
from fluidnc_link import FluidNC, Status


def _machine_status(st):
    p = st.mpos
    pos = Position(p[0], p[1]) if p and len(p) >= 2 and all(map(math.isfinite, p[:2])) else None
    return MachineStatus(st.state.split(':')[0], pos)


def parse_status(line):
    """Standalone parser for existing tests; no assumption that WPos is MPos."""
    if not (line.startswith('<') and line.endswith('>')):
        return None
    state, *parts = line[1:-1].split('|')
    fields = dict(p.split(':', 1) for p in parts if ':' in p)
    mpos = tuple(map(float, fields['MPos'].split(','))) if 'MPos' in fields else None
    if mpos is None and 'WPos' in fields and 'WCO' in fields:
        mpos = tuple(a+b for a,b in zip(map(float, fields['WPos'].split(',')), map(float, fields['WCO'].split(','))))
    return _machine_status(Status(state, mpos, None, line, fields))


class FluidNCMotion:
    def __init__(self, port, baud=115200, link_factory=FluidNC):
        self.port, self.baud = port, baud
        self.link_factory = link_factory
        self.link = None
        self.homed = False

    def connect(self):
        self.link = self.link_factory(self.port, self.baud)
        self.homed = False

    def disconnect(self):
        self.homed = False
        if self.link:
            self.link.close()
            self.link = None

    def get_status(self):
        if not self.link:
            raise RuntimeError('FluidNC not connected')
        result = _machine_status(self.link.status(timeout=2))
        fault = getattr(self.link, '_fault', None)
        if fault and not (fault.startswith('ALARM') and result.state == 'Alarm'):
            self.homed = False
            raise RuntimeError(fault)
        if result.state != 'Idle' and result.state not in ('Run', 'Home', 'Jog'):
            self.homed = False
        return result

    def _wait_idle(self, cancelled, timeout, target=None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if cancelled.is_set():
                raise InterruptedError('Movement cancelled')
            st = self.get_status()
            if st.state not in ('Idle', 'Run', 'Home', 'Jog'):
                raise RuntimeError(f'Unexpected FluidNC state: {st.state}')
            if st.state == 'Idle' and st.position is not None:
                if target is None or max(abs(st.position.x_mm-target.x_mm), abs(st.position.z_mm-target.z_mm)) <= 0.05:
                    return st.position
            cancelled.wait(0.15)
        raise TimeoutError('FluidNC did not report Idle at requested machine position')

    def _failure(self):
        self.homed = False
        try:
            self.link.feed_hold()
        except Exception:
            pass  # original exception is reported; physical stop is independent

    def home(self, cancelled: threading.Event):
        self.homed = False
        try:
            if self.get_status().state not in ('Idle', 'Alarm'):
                raise RuntimeError('Inspect machine state before homing')
            self.link.home(timeout=600, cancelled=cancelled)
            p = self._wait_idle(cancelled, 30)
            if cancelled.is_set():
                raise InterruptedError('Homing cancelled')
            self.homed = True
            return p
        except Exception:
            self._failure()
            raise

    def move_to(self, position, feed_mm_min, cancelled):
        if not self.homed:
            raise RuntimeError('Home and verify the machine first')
        if not all(map(math.isfinite, (position.x_mm, position.z_mm, feed_mm_min))) or feed_mm_min <= 0:
            raise ValueError('Invalid movement request')
        try:
            state = self.get_status()
            if state.state != 'Idle' or state.position is None:
                raise RuntimeError('Motion requires Idle and a known machine position (MPos or WPos+WCO)')
            # Explicit mm, absolute, feed/min and machine coordinates; ignore inherited work offsets.
            self.link.send('G21 G90 G94', cancelled=cancelled)
            self.link.send(f'G53 G1 X{position.x_mm:.3f} Y{position.z_mm:.3f} F{feed_mm_min:.3f}', cancelled=cancelled)
            distance = math.hypot(position.x_mm-state.position.x_mm, position.z_mm-state.position.z_mm)
            return self._wait_idle(cancelled, max(30, distance/feed_mm_min*60*2+15), position)
        except Exception:
            self._failure()
            raise

    def feed_hold(self):
        self.homed = False
        if self.link:
            self.link.feed_hold()
