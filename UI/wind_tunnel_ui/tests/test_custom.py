import csv
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.contracts import Position, MachineLimits, ScanPlan
from backend.controller import WindTunnelController
from backend.custom_esp32_adapter import CustomESP32, SharedSensor, FirmwareError

class FakeSerial:
    def __init__(self, mode='DEMO', enabled=True):
        self.mode=mode; self.enabled=enabled; self.pos=None; self.writes=[]
        self.rx=queue.Queue(); self.closed=False; self.defer=False
    def reset_input_buffer(self): pass
    def write(self,data):
        self.writes.append(data)
        cmd=data.decode().strip()
        if cmd=='!': self.pos=None; return len(data)
        if cmd=='~': return len(data)
        if cmd=='PING': r='OK,PONG,WINDTUNNEL_CUSTOM_V2'
        elif cmd=='CAPS': r='OK,CAPS,'+('ENABLED' if self.enabled else 'LOCKED')+',340.0,300.0,3000.0'
        elif cmd=='MODE': r='OK,MODE,'+self.mode
        elif cmd=='HOME':
            if self.defer: return len(data)
            self.pos=(0,0); r='OK,HOME,0,0,HOMED'
        elif cmd.startswith('MOVE,'):
            if self.defer: return len(data)
            _,x,z,f=cmd.split(','); self.pos=(float(x),float(z)); r=f'OK,MOVE,{x},{z},HOMED'
        elif cmd=='POS': r='OK,POS,NA,NA,UNHOMED' if self.pos is None else f'OK,POS,{self.pos[0]},{self.pos[1]},HOMED'
        elif cmd=='MEASURE': r='OK,MEASURE,0,NA,NA' if self.mode=='DEMO' else 'ERR,AIR_SPEED_NOT_IMPLEMENTED_OR_UNAVAILABLE'
        else: r='ERR,UNKNOWN'
        # Split reply to verify partial-line assembly.
        self.rx.put(r[:5].encode()); self.rx.put((r[5:]+'\n').encode()); return len(data)
    def readline(self):
        try: return self.rx.get(timeout=.01)
        except queue.Empty: return b''
    def close(self): self.closed=True

class Tests(unittest.TestCase):
    def adapter(self, fake=None):
        fake=fake or FakeSerial(); a=CustomESP32('FAKE',lambda *args,**kwargs:fake,0); a.connect(); self.addCleanup(a.disconnect); return a,fake
    def test_one_port_home_move_measure(self):
        a,f=self.adapter(); sensor=SharedSensor(a); sensor.connect()
        self.assertEqual(a.home(threading.Event()),Position(0,0))
        self.assertEqual(a.move_to(Position(20,30),1200,threading.Event()),Position(20,30))
        self.assertIn(b'MOVE,20.0000,30.0000,1200.000\n',f.writes)
        self.assertEqual(sensor.sample().speed_ms,0); self.assertIsNone(sensor.sample().pressure_pa)
        sensor.disconnect(); self.assertFalse(f.closed)
        self.assertEqual(a.get_status().position,Position(20,30))
    def test_locked_firmware(self):
        a,f=self.adapter(FakeSerial(enabled=False))
        with self.assertRaises(RuntimeError): a.home(threading.Event())
        self.assertNotIn(b'HOME\n',f.writes)
    def test_real_sensor_unavailable_not_zero(self):
        a,f=self.adapter(FakeSerial(mode='REAL'))
        with self.assertRaises(FirmwareError): a.read_measurement()
    def test_stop_during_motion(self):
        a,f=self.adapter(); a.home(threading.Event()); f.defer=True; cancelled=threading.Event(); errors=[]
        def run():
            try: a.move_to(Position(10,10),60,cancelled)
            except Exception as e: errors.append(e)
        t=threading.Thread(target=run); t.start(); time.sleep(.04); cancelled.set(); a.feed_hold(); t.join(1)
        self.assertFalse(t.is_alive()); self.assertIsInstance(errors[0],InterruptedError); self.assertFalse(a.homed)
        self.assertIn(b'~',f.writes); self.assertIn(b'!',f.writes)
        with self.assertRaises(RuntimeError): a.get_status()
    def test_reject_out_of_bounds(self):
        a,f=self.adapter(); a.home(threading.Event())
        with self.assertRaises(ValueError): a.move_to(Position(341,0),60,threading.Event())
        with self.assertRaises(ValueError): a.move_to(Position(1,1),3001,threading.Event())
        self.assertFalse(any(x.startswith(b'MOVE') for x in f.writes))
    def test_simulation_scan(self):
        with tempfile.TemporaryDirectory() as d:
            c=WindTunnelController(lambda *a:None,output_dir=d); c.connect('Simulation'); c.home()
            c.run_scan(ScanPlan(0,5,0,5,2,2,0,1,1200))
            file=next(Path(d).glob('simulation/*.csv'))
            with file.open() as f: rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),4); self.assertTrue(all(r['source']=='SIMULATION' for r in rows)); c.disconnect()
    def test_demo_scan_separate_csv(self):
        with tempfile.TemporaryDirectory() as d:
            f=FakeSerial(); a=CustomESP32('FAKE',lambda *args,**kwargs:f,0)
            with patch('backend.controller.CustomESP32',return_value=a):
                c=WindTunnelController(lambda *a:None,output_dir=d); c.connect('Custom ESP32 + sensors','FAKE'); c.home()
                c.run_scan(ScanPlan(0,5,0,5,2,2,0,1,1200))
                with next(Path(d).glob('demo/*.csv')).open() as file: rows=list(csv.DictReader(file))
                self.assertEqual(len(rows),4); self.assertTrue(all(r['source']=='DEMO' for r in rows)); c.disconnect()
    def test_dry_scan_no_csv(self):
        with tempfile.TemporaryDirectory() as d:
            f=FakeSerial(); a=CustomESP32('FAKE',lambda *args,**kwargs:f,0)
            with patch('backend.controller.CustomESP32',return_value=a):
                c=WindTunnelController(lambda *a:None,output_dir=d); c.connect('Custom ESP32 movement only','FAKE'); c.home()
                c.run_scan(ScanPlan(0,5,0,5,2,2,0,1,60)); self.assertFalse(list(Path(d).rglob('*.csv'))); self.assertNotIn(b'MEASURE\n',f.writes); c.disconnect()
    def test_stop_before_dispatch(self):
        a,f=self.adapter(); a.home(threading.Event()); ev=threading.Event(); ev.set()
        with self.assertRaises(InterruptedError): a.move_to(Position(5,5),60,ev)
        self.assertFalse(any(x.startswith(b'MOVE') for x in f.writes))
    def test_grid_and_limits(self):
        p=ScanPlan(0,10,0,20,3,2,0,1,3000); p.validate(MachineLimits()); self.assertEqual(list(p.points())[-1],Position(0,20))
        with self.assertRaises(ValueError): ScanPlan(0,341,0,20,2,2).validate(MachineLimits())
if __name__=='__main__': unittest.main()
