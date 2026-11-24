"""Provisional ESP32-C3 serial protocol adapter.

Accepted response examples:
  OK,MEASURE,12.4,101.2,22.0
  SENSOR,12.4,101.2,22.0
  12.4,101.2,22.0
  {"speed_ms":12.4,"pressure_pa":101.2,"temperature_c":22.0}

The group's actual .ino firmware must be checked before real use.
"""
import json
import time
from .contracts import Measurement


def parse_measurement(line: str) -> Measurement | None:
    line = line.strip()
    if not line:
        return None
    try:
        if line.startswith("{"):
            obj = json.loads(line)
            return Measurement(float(obj["speed_ms"]), _optional(obj.get("pressure_pa")), _optional(obj.get("temperature_c")))
        fields = [s.strip() for s in line.split(",")]
        if fields[0].upper() == "OK" and len(fields) >= 5 and fields[1].upper() == "MEASURE":
            fields = fields[2:]
        elif fields[0].upper() in ("SENSOR", "MEASURE"):
            fields = fields[1:]
        if len(fields) >= 1 and len(fields) <= 3:
            return Measurement(float(fields[0]), _optional(fields[1]) if len(fields)>1 else None,
                               _optional(fields[2]) if len(fields)>2 else None)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, IndexError):
        return None
    return None


def _optional(val):
    return None if val in (None, "", "NA", "nan", "None") else float(val)


class SerialSensor:
    def __init__(self, port: str, baud: int = 115200, request: str = "MEASURE"):
        self.port, self.baud, self.request = port, baud, request
        self.ser = None

    def connect(self):
        import serial
        self.ser = serial.Serial(self.port, self.baud, timeout=0.25, write_timeout=1)
        time.sleep(0.25)

    def disconnect(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def sample(self) -> Measurement:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Sensor ESP32-C3 not connected")
        if self.request:
            self.ser.write((self.request + "\n").encode("ascii"))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            result = parse_measurement(self.ser.readline().decode("utf-8", "replace"))
            if result is not None:
                return result
        raise TimeoutError("No recognized sensor packet from ESP32-C3")
