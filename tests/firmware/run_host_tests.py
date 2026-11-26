"""Run portable C++ logic checks using g++ and a small Arduino API shim.
Does not build an ESP32 binary or validate physical signals/timing.
"""
from pathlib import Path
import shutil, subprocess, tempfile
here=Path(__file__).resolve().parent
source=here.parents[1]/'arduino'/'base_esp32'
with tempfile.TemporaryDirectory() as d:
    build=Path(d)
    for file in source.iterdir():
        if file.is_file(): shutil.copy(file,build/file.name)
    for file in ['Arduino.h','test_motion.cpp']: shutil.copy(here/file,build/file)
    # Parse the whole .ino as C++ with the host API shim; actual Arduino toolchain still required.
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-I',d,'-x','c++','-fsyntax-only',str(build/'base_esp32.ino'),str(build/'motor_control.cpp'),str(build/'sensors.cpp')],check=True)
    for enable in (False,True):
        config=build/'config.h'
        if enable: config.write_text(config.read_text().replace('MOTION_ENABLED = false','MOTION_ENABLED = true'))
        exe=build/'motion_test'
        subprocess.run(['g++','-std=c++11','-O2','-Wall','-Wextra','-Werror','-I',d,str(build/'test_motion.cpp'),str(build/'motor_control.cpp'),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
