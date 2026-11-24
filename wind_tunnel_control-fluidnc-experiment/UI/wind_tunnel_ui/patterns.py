"""
patterns.py - small G-code test patterns for a CoreXY traverser.

Each function returns a list of G-code lines (absolute coordinates, mm).
Send them with FluidNC.send_program(lines), then FluidNC.wait_until_stopped().
"""

from __future__ import annotations


def _header(feed: float) -> list[str]:
    return ["G21", "G90", f"F{feed:.0f}"]   # mm, absolute, feed rate in mm/min


def square(x0: float, y0: float, size: float, feed: float = 1500) -> list[str]:
    """Square with lower-left corner (x0, y0). Moves pure X and pure Y,
    so both motors turn on every edge (CoreXY)."""
    pts = [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size), (x0, y0)]
    return _header(feed) + [f"G1 X{x:.3f} Y{y:.3f}" for x, y in pts]


def axis_test(x0: float, y0: float, dist: float, feed: float = 1000) -> list[str]:
    """Out and back along X, then along Y. Use it to check direction and steps/mm:
    measure the actual travel with a ruler/caliper against `dist`."""
    return _header(feed) + [
        f"G1 X{x0:.3f} Y{y0:.3f}",
        f"G1 X{x0 + dist:.3f}", f"G4 P1", f"G1 X{x0:.3f}", "G4 P1",
        f"G1 Y{y0 + dist:.3f}", f"G4 P1", f"G1 Y{y0:.3f}",
    ]


def motor_test(x0: float, y0: float, d: float, feed: float = 1000) -> list[str]:
    """CoreXY wiring check. A move of equal +X and +Y turns only ONE motor,
    and +X -Y turns only the OTHER motor. If the wrong motor turns, or the
    carriage moves along the wrong diagonal, swap/invert motors in config.yaml."""
    return _header(feed) + [
        f"G1 X{x0:.3f} Y{y0:.3f}",
        f"G1 X{x0 + d:.3f} Y{y0 + d:.3f}   ; only motor A should turn",
        "G4 P1",
        f"G1 X{x0:.3f} Y{y0:.3f}",
        "G4 P1",
        f"G1 X{x0 + d:.3f} Y{y0 - d:.3f}   ; only motor B should turn",
        "G4 P1",
        f"G1 X{x0:.3f} Y{y0:.3f}",
    ]


def repeatability(p1: tuple[float, float], p2: tuple[float, float],
                  n: int = 10, feed: float = 2000) -> list[str]:
    """Shuttle between p1 and p2 n times and end at p1. Mark p1 (dial gauge,
    pen mark, camera) before and compare after: drift = lost steps or slack."""
    lines = _header(feed) + [f"G1 X{p1[0]:.3f} Y{p1[1]:.3f}"]
    for _ in range(n):
        lines += [f"G1 X{p2[0]:.3f} Y{p2[1]:.3f}", f"G1 X{p1[0]:.3f} Y{p1[1]:.3f}"]
    return lines


def grid(x0: float, y0: float, x1: float, y1: float, nx: int, ny: int,
         dwell: float = 0.5, feed: float = 2000) -> list[str]:
    """Serpentine grid with a dwell at every point - a dry run of a measurement."""
    lines = _header(feed)
    for j in range(ny):
        y = y0 + (y1 - y0) * j / max(ny - 1, 1)
        cols = range(nx) if j % 2 == 0 else range(nx - 1, -1, -1)
        for i in cols:
            x = x0 + (x1 - x0) * i / max(nx - 1, 1)
            lines += [f"G1 X{x:.3f} Y{y:.3f}", f"G4 P{dwell:.3f}"]
    return lines
