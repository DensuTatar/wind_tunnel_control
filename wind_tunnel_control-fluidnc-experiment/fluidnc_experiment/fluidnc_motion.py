"""FluidNC USB serial interface. Physical Z maps to FluidNC Y."""
import math
import time


class FluidNC:
    def __init__(self, port):
        self.port = port
        self.homed = False

    def _read(self):
        raw = self.port.readline()
        if not raw:
            return ""
        if not raw.endswith(b'\n'):
            raise RuntimeError('Incomplete serial line; stop and investigate')
        line = raw.decode('ascii', errors='replace').strip()
        if line.lower().startswith(('error:', 'alarm:', '[msg:error')):
            self.homed = False
            raise RuntimeError(line)
        if line.lower().startswith(('grbl', 'fluidnc')) and self.homed:
            self.homed = False
            raise RuntimeError('Controller restarted; re-home required')
        return line

    def command(self, cmd, timeout=10):
        """Wait for acknowledgement, NOT necessarily for motion completion."""
        self.port.write((cmd + '\n').encode('ascii'))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._read()
            if line.lower() == 'ok':
                return
            if line.startswith(('<Alarm', '<Door', '<Hold', '<Sleep')):
                raise RuntimeError(line)
        self.homed = False
        raise TimeoutError(f'No acknowledgement for {cmd}')

    def status(self):
        self.port.write(b'?')  # realtime command, no newline or ok expected
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            line = self._read()
            if line.startswith('<') and line.endswith('>'):
                fields = line[1:-1].split('|')
                state = fields[0].split(':')[0]
                if state in {'Alarm', 'Hold', 'Door', 'Sleep', 'Check', 'ConfigAlarm'}:
                    self.homed = False
                    raise RuntimeError(f'Unexpected state: {line}')
                for field in fields[1:]:
                    if field.startswith('MPos:'):
                        values = [float(v) for v in field[5:].split(',')]
                        if len(values) < 2 or not all(map(math.isfinite, values)):
                            raise RuntimeError(f'Invalid machine position: {line}')
                        return state, values[0], values[1]
                raise RuntimeError('MPos required; configure FluidNC status to report machine position')
        raise TimeoutError('No FluidNC status response')

    def wait_idle(self, target=None, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state, x, z = self.status()
            if state == 'Idle':
                if target is None or max(abs(x-target[0]), abs(z-target[1])) <= 0.05:
                    # Reported step-count estimate, not measured actual position.
                    return x, z
            time.sleep(0.15)
        self.homed = False
        raise TimeoutError('Motion did not reach the requested idle position')

    def home(self):
        self.homed = False
        self.command('$H', timeout=180)
        pos = self.wait_idle(timeout=30)
        self.command('G21 G90')  # mm, absolute coordinates
        self.homed = True
        return pos

    def move_to(self, x, z, feed=600):
        if not self.homed:
            raise RuntimeError('Home both axes first')
        if not all(map(math.isfinite, (x, z, feed))) or feed <= 0:
            raise ValueError('Invalid coordinates or feed')
        # Use machine coordinates to avoid inherited work coordinate offsets.
        self.command(f'G53 G1 X{x:.3f} Y{z:.3f} F{feed:.3f}')
        return self.wait_idle((x, z))

    def request_hold(self):
        self.homed = False
        self.port.write(b'!')  # best-effort feed hold, NOT emergency stop
