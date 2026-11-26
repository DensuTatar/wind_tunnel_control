# Wind tunnel control UI — custom ESP32

See the [repository README](../../README.md) for commissioning, protocol, hardware safety and testing. Run `python -m pip install -r requirements.txt`, then `python main.py` from this folder. Simulation requires no ESP32. The two custom modes share a single USB serial connection. Do not upload custom firmware to your working FluidNC board unless you intend to replace FluidNC.

Data in `measurements/simulation/` and `measurements/demo/` is not experimental data. `measurements/real/` is reserved for implemented, validated physical sensor readings. Real sensor acquisition remains a placeholder.
