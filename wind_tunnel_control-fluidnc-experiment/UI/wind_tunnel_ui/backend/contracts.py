"""Stable API boundaries: no Qt, pyserial, or hardware specifics here."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Callable
import threading


@dataclass(frozen=True)
class Position:
    x_mm: float
    z_mm: float


@dataclass(frozen=True)
class Measurement:
    speed_ms: float
    pressure_pa: float | None = None
    temperature_c: float | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat(timespec="seconds"))


@dataclass(frozen=True)
class MachineStatus:
    state: str
    position: Position | None = None


@dataclass(frozen=True)
class MachineLimits:
    x_min: float = 0.0
    x_max: float = 400.0
    z_min: float = 0.0
    z_max: float = 400.0

    def validate(self, pos: Position) -> None:
        if not (self.x_min <= pos.x_mm <= self.x_max and self.z_min <= pos.z_mm <= self.z_max):
            raise ValueError(f"Target ({pos.x_mm}, {pos.z_mm}) mm outside configured limits")


@dataclass(frozen=True)
class ScanPlan:
    x_start: float
    x_end: float
    z_start: float
    z_end: float
    nx: int
    nz: int
    settle_s: float = 2.0
    samples_per_point: int = 5
    feed_mm_min: float = 400.0

    def validate(self, limits: MachineLimits) -> None:
        if self.nx < 2 or self.nz < 2 or self.nx > 51 or self.nz > 51:
            raise ValueError("Grid counts must be between 2 and 51")
        if self.x_start > self.x_end or self.z_start > self.z_end:
            raise ValueError("Scan start must not exceed scan end")
        for x in (self.x_start, self.x_end):
            for z in (self.z_start, self.z_end):
                limits.validate(Position(x, z))
        if not 0 <= self.settle_s <= 120 or not 1 <= self.samples_per_point <= 100:
            raise ValueError("Invalid settling time or sample count")
        if not 1 <= self.feed_mm_min <= 2000:
            raise ValueError("Requested feed must be 1–2000 mm/min")

    def points(self):
        xs = [self.x_start + (self.x_end-self.x_start)*i/(self.nx-1) for i in range(self.nx)]
        zs = [self.z_start + (self.z_end-self.z_start)*j/(self.nz-1) for j in range(self.nz)]
        for j, z in enumerate(zs):
            for x in (xs if j % 2 == 0 else xs[::-1]):
                yield Position(x, z)


class MotionPort(Protocol):
    homed: bool
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def home(self, cancelled: threading.Event) -> Position: ...
    def move_to(self, position: Position, feed_mm_min: float, cancelled: threading.Event) -> Position: ...
    def get_status(self) -> MachineStatus: ...
    def feed_hold(self) -> None: ...


class SensorPort(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def sample(self) -> Measurement: ...


EventHandler = Callable[[str, object], None]
