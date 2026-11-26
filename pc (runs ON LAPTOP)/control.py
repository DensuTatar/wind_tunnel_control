"""Compatibility launcher for the original PC entry point; now uses the UI."""
from pathlib import Path
import sys
import os
ui = Path(__file__).resolve().parents[1] / 'UI' / 'wind_tunnel_ui'
sys.path.insert(0, str(ui))
os.chdir(ui)
from gui import main
if __name__ == '__main__':
    main()
