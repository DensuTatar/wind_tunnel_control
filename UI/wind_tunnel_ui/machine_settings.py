"""PC-side bounds, in FluidNC MACHINE coordinates, not GPIO/firmware settings.
These are the original UI's unverified design bounds. Edit to match the
actual homed coordinate range before arming any physical movement.
"""
X_MIN, X_MAX = 0.0, 340.0
Z_MIN, Z_MAX = 0.0, 300.0
INITIAL_FEED = 60.0  # mm/min; initial commissioning, not validated max
