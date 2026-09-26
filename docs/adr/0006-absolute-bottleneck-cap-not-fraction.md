# Scenarios 3/4A/4B cap the target service by an absolute millicore value, not a fraction of its normal quota

Scenarios 3/4A/4B used `cpu_limit_fraction: 0.1` against each target's *already Ron-config-trimmed* paper quota (checkout 615m, productcatalog 1535m, payment 155m), yielding small, differing, and — critically — **untested** absolutes (61.5m / 153.5m / 15.5m). We switch to a real `cpu_limit_millicores: 50` constraint kind, applied identically to all three targets, matching the one CPU point each service already has trustworthy `mu_sat` saturation data for from the frozen-capacity calibration battery.

**Status:** proposed (design only — see [2026-09-21-s1-s6-methodology-and-calibration-design.md](../superpowers/specs/2026-09-21-s1-s6-methodology-and-calibration-design.md) §2a/§2b/§5).

**Considered options:** keep `cpu_limit_fraction: 0.1` as-is and just fix the stale docstrings; pick a different fraction (0.2–0.3) sized to avoid an implausibly tiny absolute; keep the fraction mechanism but special-case each service's fraction to independently land near 50m (mathematically equivalent to the adopted option, but reverse-engineered per-service fractions carry no shared meaning across services and are harder to read).

**Consequences:** `mu_per_millicore` was found not to extrapolate across CPU values (checkoutservice's own two-point comparison diverged 67× between a 50m and a 1000m hold, paymentservice ~37×, same direction both times — a real small-CPU nonlinearity, not noise). An absolute cap lets the recalibration battery's `mu_sat` numbers be used directly rather than extrapolated. This requires a small mechanism addition (`cpu_limit_millicores` alongside the existing `cpu_limit_fraction` in `topfull_cpu_quotas.py`'s `scale_constraints` handling) — not yet implemented.

Detail: [2026-09-21-s1-s6-methodology-and-calibration-design.md](../superpowers/specs/2026-09-21-s1-s6-methodology-and-calibration-design.md) §2a/§2b/§5, §6 (implementation checklist).
