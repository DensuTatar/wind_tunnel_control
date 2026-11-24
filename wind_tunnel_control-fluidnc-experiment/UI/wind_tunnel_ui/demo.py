"""
demo.py - interactive console to get first movement out of the traverser.

    pip install pyserial
    python demo.py --list               # show serial ports
    python demo.py --port COM5          # Windows
    python demo.py --port /dev/ttyUSB0  # Linux

Type 'help' at the prompt for commands. Ctrl+C stops motion (feed hold + reset).
"""

from __future__ import annotations

import argparse
import logging
import shlex

import patterns
from fluidnc_link import FluidNC, FluidNCError, list_ports

HELP = """
Commands (distances in mm, feed in mm/min):
  status                    show state and position
  home                      run homing cycle ($H)
  unlock                    clear alarm without homing ($X) - only for testing!
  jog <axis> <dist> [feed]  e.g. 'jog x 10', 'jog y -5 500'
  goto <x> <y> [feed]       absolute move, waits until finished
  square <x0> <y0> <size>   draw a square
  axis <x0> <y0> <dist>     out-and-back along X then Y (check steps/mm)
  motors <x0> <y0> <d>      CoreXY wiring check: one motor at a time
  repeat <x1> <y1> <x2> <y2> [n]   shuttle n times, end at point 1
  grid <x0> <y0> <x1> <y1> <nx> <ny>  serpentine grid with dwell
  raw <gcode...>            send any line, e.g. 'raw $$' or 'raw G0 X0 Y0'
  stop                      feed hold + soft reset (re-home afterwards)
  quit
"""


def run(cnc: FluidNC, lines: list[str]):
    for ln in lines:
        print("  >>", ln)
    cnc.send_program(lines)
    cnc.wait_until_stopped()
    print_status(cnc)


def print_status(cnc: FluidNC):
    st = cnc.status()
    pos = st.wpos or st.mpos
    pos_s = f"X={pos[0]:.3f}  Y={pos[1]:.3f}" if pos else "?"
    print(f"  state={st.state}  {pos_s}")


def handle(cnc: FluidNC, args: list[str], default_feed: float) -> bool:
    cmd, a = args[0].lower(), args[1:]
    f = lambda i, d: float(a[i]) if len(a) > i else d   # noqa: E731

    if cmd in ("quit", "exit", "q"):
        return False
    elif cmd == "help":
        print(HELP)
    elif cmd == "status":
        print_status(cnc)
    elif cmd == "home":
        print("  homing...")
        cnc.home()
        print_status(cnc)
    elif cmd == "unlock":
        cnc.unlock()
        print_status(cnc)
    elif cmd == "jog":
        axis, dist = a[0].lower(), float(a[1])
        feed = f(2, default_feed)
        cnc.jog(dx=dist if axis == "x" else 0, dy=dist if axis == "y" else 0, feed=feed)
        cnc.wait_idle()
        print_status(cnc)
    elif cmd == "goto":
        cnc.move_to(float(a[0]), float(a[1]), feed=f(2, default_feed))
        cnc.wait_until_stopped()
        print_status(cnc)
    elif cmd == "square":
        run(cnc, patterns.square(f(0, 10), f(1, 10), f(2, 50), default_feed))
    elif cmd == "axis":
        run(cnc, patterns.axis_test(f(0, 10), f(1, 10), f(2, 50), default_feed))
    elif cmd == "motors":
        run(cnc, patterns.motor_test(f(0, 50), f(1, 50), f(2, 20), default_feed))
    elif cmd == "repeat":
        n = int(a[4]) if len(a) > 4 else 10
        run(cnc, patterns.repeatability((f(0, 10), f(1, 10)), (f(2, 100), f(3, 100)), n, default_feed))
    elif cmd == "grid":
        run(cnc, patterns.grid(f(0, 10), f(1, 10), f(2, 100), f(3, 100),
                               int(f(4, 5)), int(f(5, 5)), feed=default_feed))
    elif cmd == "raw":
        line = " ".join(a)
        cnc.send(line, timeout=120)
        for m in cnc.messages[-40:]:
            print("  ", m)
        cnc.messages.clear()
    elif cmd == "stop":
        cnc.feed_hold()
        cnc.soft_reset()
        print("  stopped - position may be lost, run 'home'")
    else:
        print("  unknown command, type 'help'")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port, e.g. COM5 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--feed", type=float, default=60, help="default feed rate (mm/min)")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("-v", "--verbose", action="store_true", help="show all serial traffic")
    opts = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if opts.verbose else logging.WARNING,
                        format="%(message)s")

    if opts.list or not opts.port:
        print("Serial ports:")
        for p in list_ports():
            print("  ", p)
        if not opts.port:
            print("\nRun again with --port <name>")
        return

    print("Expert test console: verify homing, coordinate frame, bounds and physical stop first. No UI travel guards here.")
    print(f"Connecting to {opts.port} (the ESP32 may reboot, wait a few seconds)...")
    with FluidNC(opts.port, opts.baud) as cnc:
        print_status(cnc)
        print("Type 'help' for commands.")
        while True:
            try:
                line = input("traverser> ").strip()
                if not line:
                    continue
                if not handle(cnc, shlex.split(line), opts.feed):
                    break
            except KeyboardInterrupt:
                print("\n  Ctrl+C: feed hold + reset")
                cnc.feed_hold()
                cnc.soft_reset()
            except (FluidNCError, TimeoutError, ValueError, IndexError) as e:
                print("  !!", e)


if __name__ == "__main__":
    main()
