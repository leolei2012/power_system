"""Inverter first-pass electrical parameters.

Values match inverter/docs/spec.md. Simulation and later firmware
should import this module instead of scattering magic numbers.
"""

# DC bus
V_DC_NOM = 100.0  # V
V_DC_MIN = 80.0
V_DC_MAX = 120.0
V_DC_UV = 75.0
V_DC_OV = 130.0

# AC output
V_LL_RMS_MAX = 60.0  # V, line-to-line
F_OUT_NOM = 50.0  # Hz
F_OUT_MAX = 100.0  # Hz

# Ratings
P_RATED = 1000.0  # W
I_RMS_RATED = 10.0  # A

# Switching
F_SW = 20_000.0  # Hz
DEADTIME = 1e-6  # s

# Simulation step (20 points per switching period)
T_STEP = 1.0 / F_SW / 20.0
