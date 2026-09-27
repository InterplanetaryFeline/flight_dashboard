"""
Synthetic flight data source.

Produces a plausible high-power rocket flight profile (launch -> powered
ascent -> booster burnout -> main burn -> coast -> apogee -> descent under
drogue/main -> landing) reaching roughly 10 km altitude.

Approach: build a *velocity* profile from waypoints via a monotone-safe
PCHIP spline (velocity is naturally 0 at launch and 0 at apogee, so the
two spline pieces join with no cusp), then integrate to get altitude.
The descent segment's magnitude is then auto-corrected so the integral
brings altitude back to exactly 0 at the landing event time, regardless
of the exact waypoint values chosen -- this guarantees a clean landing
without manual trial and error. The whole curve is then rescaled to hit
the target apogee.

Note: to reach ~10 km apogee and land within the illustrative event
timeline supplied (apogee at 48.2 s, landing at 120 s), descent rates
end up faster than a real drogue+main parachute would produce -- the
physics here favors matching the requested timeline and altitude over
strict realism, as called out in the requirements.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.integrate import cumulative_trapezoid

from data_interface import DataSource, FlightDataset, FlightEvent

# --- Phase timings (s) ------------------------------------------------
T_LAUNCH = 0.0
T_BOOSTER_IGNITE = 0.5
T_MAIN_IGNITE = 1.2
T_MAX_Q = 8.4
T_BOOSTER_BURNOUT = 12.5
T_STAGE_SEP = 15.0
T_MAIN_BURNOUT = 34.0
T_APOGEE = 48.2
T_MAIN_DEPLOY = 55.0
T_LANDING = 120.0

OXIDIZER_KG = 17.0   # hybrid main stage: liquid/gaseous oxidizer (e.g. N2O)
FUEL_KG = 3.0        # hybrid main stage: solid fuel grain (e.g. HTPB)
BOOSTER_PROP_KG = 8.0
APOGEE_ALT = 10200.0


class SyntheticDataSource(DataSource):
    def __init__(self, dt: float = 0.05, seed: int = 42):
        self.dt = dt
        self.rng = np.random.default_rng(seed)

    def load(self) -> FlightDataset:
        dt = self.dt
        t = np.arange(0.0, T_LANDING + dt, dt)
        n = len(t)

        altitude, velocity = self._build_altitude_and_velocity(t)
        acceleration = np.gradient(velocity, t)

        # finite-difference acceleration is a bit jagged -- smooth it, and
        # add light vibration jitter only during powered flight
        kernel = np.ones(5) / 5
        acceleration = np.convolve(acceleration, kernel, mode="same")
        powered = t < T_MAIN_BURNOUT
        acceleration[powered] += self.rng.normal(0, 0.5, int(powered.sum()))

        # mild downrange drift so the 3D trajectory isn't a straight vertical line
        drift_angle = np.radians(6.0)
        horiz = altitude * np.tan(drift_angle) * 0.15
        x = horiz + np.cumsum(self.rng.normal(0, 0.3, n)) * 0.05
        y = horiz * 0.3 + np.cumsum(self.rng.normal(0, 0.3, n)) * 0.04
        z = altitude

        # propellant burn: boosters deplete by their burnout; the hybrid main
        # stage burns oxidizer and fuel together over the same burn window,
        # each depleting proportionally to its own initial mass
        left = np.clip(
            BOOSTER_PROP_KG * (1 - (t - T_BOOSTER_IGNITE) / (T_BOOSTER_BURNOUT - T_BOOSTER_IGNITE)),
            0, BOOSTER_PROP_KG,
        )
        left[t < T_BOOSTER_IGNITE] = BOOSTER_PROP_KG
        right = left.copy()

        burn_frac = np.clip((t - T_MAIN_IGNITE) / (T_MAIN_BURNOUT - T_MAIN_IGNITE), 0, 1)
        burn_frac[t < T_MAIN_IGNITE] = 0.0
        oxidizer = OXIDIZER_KG * (1 - burn_frac)
        fuel = FUEL_KG * (1 - burn_frac)

        events = [
            FlightEvent("Launch", T_LAUNCH),
            FlightEvent("Booster ignition", T_BOOSTER_IGNITE),
            FlightEvent("Main ignition", T_MAIN_IGNITE),
            FlightEvent("Max Q", T_MAX_Q),
            FlightEvent("Booster burnout", T_BOOSTER_BURNOUT),
            FlightEvent("Stage separation", T_STAGE_SEP),
            FlightEvent("Main burnout", T_MAIN_BURNOUT),
            FlightEvent("Apogee", T_APOGEE),
            FlightEvent("Main deployment", T_MAIN_DEPLOY),
            FlightEvent("Landing", T_LANDING),
        ]

        return FlightDataset(
            time=t, altitude=altitude, velocity=velocity, acceleration=acceleration,
            x=x, y=y, z=z,
            propellant={"oxidizer": oxidizer, "fuel": fuel, "left": left, "right": right},
            propellant_initial={"oxidizer": OXIDIZER_KG, "fuel": FUEL_KG,
                                 "left": BOOSTER_PROP_KG, "right": BOOSTER_PROP_KG},
            events=events,
        )

    @staticmethod
    def _build_altitude_and_velocity(t: np.ndarray):
        asc_mask = t <= T_APOGEE

        # ascent velocity waypoints: 0 at launch pad, ramps up through both
        # burns, eases toward 0 exactly at apogee
        asc_t = np.array([0.0, T_BOOSTER_IGNITE, T_MAIN_IGNITE, T_MAX_Q,
                           T_BOOSTER_BURNOUT, T_STAGE_SEP, 20.0, T_MAIN_BURNOUT, T_APOGEE])
        asc_v = np.array([0.0, 0.0, 8.0, 95.0, 140.0, 120.0, 100.0, 55.0, 0.0])
        asc_spline = PchipInterpolator(asc_t, asc_v)

        # descent velocity waypoints: freefall-ish right after apogee, then
        # progressively slower once the main deploys. Magnitudes here are a
        # starting shape only -- they get uniformly rescaled below so the
        # rocket lands at exactly 0 m.
        desc_t = np.array([T_APOGEE, T_MAIN_DEPLOY, 58.0, 70.0, 100.0, 119.0, T_LANDING])
        desc_v = np.array([0.0, -70.0, -35.0, -30.0, -25.0, -18.0, -8.0])
        desc_spline = PchipInterpolator(desc_t, desc_v)

        v_raw = np.empty_like(t)
        v_raw[asc_mask] = asc_spline(t[asc_mask])
        v_raw[~asc_mask] = desc_spline(t[~asc_mask])

        alt_raw = cumulative_trapezoid(v_raw, t, initial=0)
        apogee_idx = int(np.argmax(alt_raw))
        raw_apogee = alt_raw[apogee_idx]

        # correct the descent magnitude so it returns exactly to 0 at t_end
        raw_descent_total = alt_raw[-1] - raw_apogee
        k = (-raw_apogee) / raw_descent_total
        v_corrected = v_raw.copy()
        v_corrected[~asc_mask] *= k

        alt_corrected = cumulative_trapezoid(v_corrected, t, initial=0)
        alt_corrected = np.clip(alt_corrected, 0.0, None)
        alt_corrected[-1] = 0.0

        scale = APOGEE_ALT / raw_apogee
        altitude = alt_corrected * scale
        velocity = v_corrected * scale
        return altitude, velocity
