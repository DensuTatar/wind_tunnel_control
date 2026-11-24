import queue
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.contracts import Position, ScanPlan
from backend.controller import WindTunnelController
from backend.fluidnc_adapter import FluidNCMotion, parse_status
from backend.simulators import SimulatedMotion
from fluidnc_link import FluidNC


class FakeSerial:
    """Scripted serial peer, not a mechanical or firmware simulation."""
    def __init__(self):
        self.rx = queue.Queue()
        self.writes = []
        self.pos = (0.0, 0.0)
        self.closed = False

    def write(self, data):
        self.writes.append(data)
        if data == b'?':
            self.rx.put(f'<Idle|MPos:{self.pos[0]},{self.pos[1]},0|WCO:10,20,0>\n'.encode())
        elif data.startswith(b'G53'):
            parts = data.decode().split()
            self.pos = tuple(float(next(p[1:] for p in parts if p.startswith(axis))) for axis in ('X','Y'))
            self.rx.put(b'ok\n')
        elif data.endswith(b'\n'):
            self.rx.put(b'ok\n')
        return len(data)

    def read(self, count):
        try:
            return self.rx.get(timeout=0.02)
        except queue.Empty:
            return b''

    def close(self):
        self.closed = True


class IntegrationTests(unittest.TestCase):
    def test_real_transport_and_adapter_with_fake_serial(self):
        ser = FakeSerial()
        motion = FluidNCMotion('FAKE', link_factory=lambda *a: FluidNC(ser=ser, boot_wait=0))
        motion.connect()
        try:
            self.assertEqual(motion.home(threading.Event()), Position(0,0))
            self.assertEqual(motion.move_to(Position(5,7),60,threading.Event()), Position(5,7))
            self.assertIn(b'G21 G90 G94\n', ser.writes)
            self.assertIn(b'G53 G1 X5.000 Y7.000 F60.000\n', ser.writes)
            motion.feed_hold()
            self.assertIn(b'!', ser.writes)
            self.assertFalse(motion.homed)
        finally:
            motion.disconnect()
        self.assertTrue(ser.closed)

    def test_cancelled_command_not_written(self):
        ser = FakeSerial()
        with FluidNC(ser=ser, boot_wait=0) as link:
            stop = threading.Event(); stop.set()
            with self.assertRaises(InterruptedError):
                link.send('G53 G1 X5 Y5 F60', cancelled=stop)
            self.assertNotIn(b'G53 G1 X5 Y5 F60\n', ser.writes)

    def test_machine_coordinate_conversion(self):
        self.assertIsNone(parse_status('<Idle|WPos:1,2,0>').position)
        self.assertEqual(parse_status('<Idle|WPos:1,2,0|WCO:10,20,0>').position, Position(11,22))

    def test_movement_only_grid_no_sensor_or_csv(self):
        events = []
        with tempfile.TemporaryDirectory() as folder:
            with patch('backend.controller.FluidNCMotion', return_value=SimulatedMotion()), patch('backend.controller.SerialSensor') as sensor:
                ctrl = WindTunnelController(lambda k,v: events.append((k,v)), output_dir=folder)
                ctrl.connect('FluidNC movement only', 'FAKE', 'IGNORED')
                self.assertIsNone(ctrl.sensor)
                sensor.assert_not_called()
                ctrl.home()
                ctrl.run_scan(ScanPlan(0,5,0,5,2,2,0,1,60))
                self.assertEqual(ctrl.records, [])
                self.assertEqual(list(Path(folder).glob('*.csv')), [])
                self.assertIn(('dry_scan_finished', {'count':4}), events)
                self.assertFalse(any(k=='measurement' for k,v in events))
                ctrl.disconnect()

    def test_full_mode_requires_sensor_port(self):
        ctrl = WindTunnelController(lambda *a: None)
        with self.assertRaises(ValueError):
            ctrl.connect('FluidNC + ESP32-C3', 'FAKE')

if __name__ == '__main__':
    unittest.main()
