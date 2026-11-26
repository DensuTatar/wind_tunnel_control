"""One serial transport for both motion and sensors; no FluidNC dependency."""
import math
import threading
import time
from .contracts import MachineStatus, Measurement, Position
from machine_settings import X_MAX, Z_MAX, MAX_FEED

class CustomESP32:
    def __init__(self, port, serial_factory=None, boot_wait=2.0):
        self.port = port
        self.factory = serial_factory
        self.boot_wait = boot_wait
        self.ser = None
        self.homed = False
        self.position = None
        self.sensor_mode = None
        self.motion_enabled = False
        self._write_lock = threading.Lock()
        self._transaction = threading.Lock()
        self._buffer = bytearray()
        self._broken = False

    def connect(self):
        if self.factory is None:
            import serial
            self.factory = serial.Serial
        self.ser = self.factory(self.port, 115200, timeout=0.05, write_timeout=0.5)
        try:
            time.sleep(self.boot_wait)
            self.ser.reset_input_buffer()
            self._buffer.clear(); self._broken = False
            if self._ask('PING', 'PONG') != ['WINDTUNNEL_CUSTOM_V2']:
                raise RuntimeError('Wrong firmware: upload custom base_esp32 sketch (not FluidNC)')
            caps = self._ask('CAPS', 'CAPS')
            if len(caps) != 4 or caps[0] not in ('ENABLED','LOCKED') or tuple(map(float,caps[1:])) != (X_MAX,Z_MAX,MAX_FEED):
                raise RuntimeError('Firmware limits disagree with machine_settings.py')
            self.motion_enabled = caps[0] == 'ENABLED'
            mode = self._ask('MODE', 'MODE')
            if mode not in (['DEMO'],['REAL']):
                raise RuntimeError('Unknown sensor mode')
            self.sensor_mode = mode[0]
            self.homed = False; self.position = None
            self.feed_hold() # invalidate any reference left over from earlier session
        except Exception:
            self.disconnect()
            raise

    def disconnect(self):
        self.homed = False; self.position = None
        if self.ser is not None:
            try:
                self._send(b'!')
            except Exception:
                pass
            finally:
                self.ser.close(); self.ser = None

    def _send(self, data, cancelled=None):
        with self._write_lock:
            if self.ser is None:
                raise RuntimeError('ESP32 not connected')
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError('Cancelled before command was sent')
            if self.ser.write(data) != len(data):
                raise IOError('Incomplete serial write')

    def _ask(self, command, expected, timeout=3.0, cancelled=None, moving=False):
        with self._transaction:
            if self._broken:
                raise RuntimeError('Serial session uncertain; disconnect and reconnect before retrying')
            deadline = time.monotonic() + timeout
            next_heartbeat = 0.0
            try:
                self._send((command+'\n').encode('ascii'), cancelled)
                while time.monotonic() < deadline:
                    if cancelled is not None and cancelled.is_set():
                        raise InterruptedError('Operation stopped; reconnect and re-home')
                    if moving and time.monotonic() >= next_heartbeat:
                        self._send(b'~', cancelled)
                        next_heartbeat = time.monotonic()+0.25
                    chunk = self.ser.readline()
                    if not chunk:
                        continue
                    self._buffer.extend(chunk)
                    if len(self._buffer)>4096:
                        raise IOError('Serial response too long')
                    while b'\n' in self._buffer:
                        raw, _, tail = self._buffer.partition(b'\n'); self._buffer = bytearray(tail)
                        fields = raw.decode('ascii','replace').strip().split(',')
                        if fields[0] == 'ERR':
                            raise FirmwareError(','.join(fields[1:]))
                        if fields[:2] == ['OK',expected]:
                            return fields[2:]
                        if fields[0] == 'READY' and moving:
                            raise IOError('ESP32 reset during motion')
                        # Ignore boot chatter; never treat stale/unmatched OK as success.
                        if fields[0] == 'OK':
                            raise IOError('Unexpected serial response: '+','.join(fields))
                raise TimeoutError('No '+expected+' response; reconnect and re-home')
            except FirmwareError:
                if moving:
                    self.homed=False; self.position=None
                raise
            except Exception:
                self._broken=True
                self.feed_hold()
                raise

    def _position(self, fields):
        if len(fields)!=3:
            raise ValueError('Malformed position response')
        if fields==['NA','NA','UNHOMED']:
            self.homed=False; self.position=None
            return None
        x,z=map(float,fields[:2])
        if fields[2]!='HOMED' or not (math.isfinite(x) and math.isfinite(z) and 0<=x<=X_MAX and 0<=z<=Z_MAX):
            raise ValueError('Invalid reported position')
        self.homed=True; self.position=Position(x,z)
        return self.position

    def home(self, cancelled):
        if not self.motion_enabled:
            raise RuntimeError('Motion locked in config.h; complete bench checks first')
        self.homed=False; self.position=None
        try:
            p=self._position(self._ask('HOME','HOME',180,cancelled,True))
            if p is None: raise RuntimeError('Homing did not establish reference')
            return p
        except Exception:
            self.feed_hold(); raise

    def move_to(self, position, feed_mm_min, cancelled):
        if not self.homed or self.position is None:
            raise RuntimeError('Home required')
        if not (0<=position.x_mm<=X_MAX and 0<=position.z_mm<=Z_MAX and 1<=feed_mm_min<=MAX_FEED):
            raise ValueError('Target or feed outside configured limits')
        distance=math.hypot(position.x_mm-self.position.x_mm,position.z_mm-self.position.z_mm)
        timeout=max(10, distance*60/feed_mm_min*2+10)
        try:
            p=self._position(self._ask(f'MOVE,{position.x_mm:.4f},{position.z_mm:.4f},{feed_mm_min:.3f}', 'MOVE', timeout,cancelled,True))
            if p is None or math.hypot(p.x_mm-position.x_mm,p.z_mm-position.z_mm)>0.01:
                raise RuntimeError('Unexpected reported target position')
            return p
        except Exception:
            self.feed_hold(); raise

    def get_status(self):
        p=self._position(self._ask('POS','POS'))
        return MachineStatus('Idle' if p is not None else 'Unhomed',p)

    def feed_hold(self):
        self.homed=False; self.position=None
        if self.ser is not None:
            self._send(b'!')

    def read_measurement(self):
        fields=self._ask('MEASURE','MEASURE')
        if len(fields)!=3:
            raise ValueError('Malformed measurement response')
        values=[None if field=='NA' else float(field) for field in fields]
        if values[0] is None or any(v is not None and not math.isfinite(v) for v in values):
            raise ValueError('Invalid measurement')
        return Measurement(*values)

class FirmwareError(RuntimeError):
    """Explicit negative reply; no timeout or unacknowledged movement."""

class SharedSensor:
    """SensorPort facade; CustomESP32 owns the only open serial port."""
    def __init__(self, device): self.device=device
    def connect(self):
        if self.device.ser is None: raise RuntimeError('Connect shared ESP32 first')
    def disconnect(self): pass
    def sample(self): return self.device.read_measurement()
