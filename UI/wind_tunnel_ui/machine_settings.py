"""PC-side limits; must match arduino/base_esp32/config.h."""
X_MIN, X_MAX = 0.0, 340.0
Z_MIN, Z_MAX = 0.0, 300.0
INITIAL_FEED = 60.0
MAX_FEED = 3000.0  # configured cap, NOT experimentally validated for custom firmware
