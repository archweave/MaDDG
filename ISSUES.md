# MaDDG — Known Issues (archweave fork)

## 1. GroundOpticalSensor.observe() crashes due to AstroForge Numba bug

**Date**: 2025-03-02
**Severity**: High — all ground sensor observations fail
**Commit**: `66be96e` (main, latest)
**Upstream**: https://github.com/mit-ll/MaDDG
**Root cause**: AstroForge `ITRSToTETED` (see `vendor/AstroForge/ISSUES.md` #1)

### Description

`GroundOpticalSensor.observe()` calls `_site_loc_TETED()` which uses `afc.PosVelConversion(afc.ITRSToTETED, ...)`. The AstroForge `ITRSToTETED` function is `@njit`-decorated but internally calls the non-jitted `ITRSToTIRS`, causing a Numba `TypingError`.

### Reproduction

```python
import madlib
import numpy as np

sat = madlib.Satellite.from_keplerian(
    epoch=51544.5, semi_major_axis_km=6878.137, ecc=0.001,
    inclination_rad=0.9, raan_rad=0.0, argp_rad=0.0, mean_anomaly_rad=0.0,
)

sensor = madlib.GroundOpticalSensor(
    id='Test', lat=30.5, lon=-86.5, alt=0.0,
    dra=10.0, ddec=10.0,
    obs_per_collect=1, obs_time_spacing=0,
    collect_gap_mean=60, collect_gap_std=0,
    obs_limits={'el': (10, 90)},
)

# This crashes:
obs = sensor.observe(target_satellite=sat, times=(51544.5, 51544.5 + 1))
```

### Workaround (won-sbss)

Use MaDDG only for propagation (`Satellite.propagate()`), then compute ground visibility with our own `compute_ground_visibility()` which uses a self-contained GMST rotation instead of AstroForge's frame conversion.

## 2. `8-constellation-scale-space-based-sensors` branch not merged

**Date**: 2025-03-02
**Severity**: Low — feature branch, WIP

### Description

The branch `8-constellation-scale-space-based-sensors` adds:
- `_space_sensors.py`: Hydra+submitit parallel sensor propagation for large constellations
- `Satellite.pre_propagate()` + `interp_from_pre_propagate()`: pre-compute ephemeris, then interpolate (performance optimization)
- Starlink CSV orbital element loading

These features would be useful for constellation-scale SBSS simulations but are not yet merged to main.
