import csv
import tempfile
import unittest
from pathlib import Path
from backend.contracts import Position, MachineLimits, ScanPlan
from backend.fluidnc_adapter import parse_status
from backend.sensor_adapter import parse_measurement
from backend.controller import WindTunnelController


class BackendTests(unittest.TestCase):
    def test_status_parser(self):
        s = parse_status('<Idle|MPos:1.500,22.250,0.000|FS:0,0>')
        self.assertEqual(s.state, 'Idle')
        self.assertEqual(s.position, Position(1.5, 22.25))
        self.assertEqual(parse_status('ok'), None)

    def test_sensor_parser(self):
        for line in ('OK,MEASURE,12.4,101.2,22', 'SENSOR,12.4,101.2,22', '12.4,101.2,22',
                     '{"speed_ms":12.4,"pressure_pa":101.2,"temperature_c":22}'):
            m = parse_measurement(line)
            self.assertIsNotNone(m)
            self.assertEqual(m.speed_ms, 12.4)

    def test_scan_points_serpentine(self):
        p = ScanPlan(0, 10, 0, 20, 3, 2, 0, 1, 400)
        self.assertEqual(list(p.points()), [Position(0,0), Position(5,0), Position(10,0),
                                             Position(10,20), Position(5,20), Position(0,20)])

    def test_sim_scan_produces_csv(self):
        events = []
        with tempfile.TemporaryDirectory() as d:
            ctrl = WindTunnelController(lambda k,v: events.append((k,v)), MachineLimits(), d)
            ctrl.connect('Simulation')
            ctrl.home()
            ctrl.run_scan(ScanPlan(0, 20, 0, 20, 3, 2, 0.0, 1, 400))
            self.assertEqual(len(ctrl.records), 6)
            csv_files = list(Path(d).glob('scan_*.csv'))
            self.assertEqual(len(csv_files), 1)
            with csv_files[0].open(newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 6)
            ctrl.disconnect()

    def test_reject_move_before_home(self):
        ctrl = WindTunnelController(lambda k,v: None)
        ctrl.connect('Simulation')
        with self.assertRaises(RuntimeError):
            ctrl.move_to(20, 20, 400)
        ctrl.disconnect()

if __name__ == '__main__':
    unittest.main()
