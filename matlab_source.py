"""
MATLAB-backed data source (future use).

Not wired into the GUI yet -- this is the adapter you fill in once the
real MATLAB structure exists. It reads a .mat file, walks user-supplied
dot-paths to find each signal, and repackages everything into the exact
same `FlightDataset` the synthetic source produces, so nothing else in
the app needs to change.

Horizontal position can come from EITHER local x/y (meters, East/North
relative to the pad) OR latitude/longitude (deg) -- most GPS-based
altimeters/trackers log the latter, so if you give latitude/longitude
dot-paths instead of x/y, they're converted automatically via
launch_site.latlon_array_to_local() using launch_site.LAUNCH_LAT/LON as
the origin. Give one pair or the other, not both.

Usage sketch, once you have a real file (local x/y variant):

    mapping = SignalMap(
        time="flight.time",
        altitude="flight.position.altitude",
        velocity="flight.velocity",
        acceleration="flight.acceleration",
        z="flight.position.z",
        propellant_oxidizer="flight.propulsion.oxidizer.mass",
        propellant_fuel="flight.propulsion.fuel.mass",
        propellant_left="flight.propulsion.left.mass",
        propellant_right="flight.propulsion.right.mass",
        events="flight.events",   # struct array with .name and .time fields
        x="flight.position.x", y="flight.position.y",
    )
    source = MatlabDataSource("flight_001.mat", mapping)
    dataset = source.load()

Or, GPS lat/lon variant -- just swap the last line for:

        latitude="flight.gps.lat", longitude="flight.gps.lon",
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

import launch_site
from data_interface import DataSource, FlightDataset, FlightEvent


@dataclass
class SignalMap:
    """Dot-paths into the loaded MATLAB struct for each standardized field.

    x/y and latitude/longitude are both optional individually, but exactly
    one of the two PAIRS must be given -- see module docstring."""
    time: str
    altitude: str
    velocity: str
    acceleration: str
    z: str
    propellant_oxidizer: str
    propellant_fuel: str
    propellant_left: str
    propellant_right: str
    events: str  # path to a struct array with .name (str) and .time (float)
    x: Optional[str] = None
    y: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    struct_root: str = "flight"  # top-level variable name inside the .mat file

    def __post_init__(self):
        has_xy = bool(self.x) and bool(self.y)
        has_latlon = bool(self.latitude) and bool(self.longitude)
        if has_xy == has_latlon:  # both given, or neither given
            raise ValueError(
                "SignalMap needs exactly one of (x and y) or (latitude and "
                "longitude), not both and not neither."
            )


def _resolve(obj, dotpath: str):
    """Walk a dot-path like 'flight.position.altitude' via getattr chains.

    Works with scipy.io.loadmat(..., struct_as_record=False, squeeze_me=True)
    output, where nested MATLAB structs become mat_struct objects.
    """
    parts = dotpath.split(".")
    cur = obj
    for p in parts[1:]:  # parts[0] is the struct_root variable name, already loaded
        cur = getattr(cur, p)
    return cur


class MatlabDataSource(DataSource):
    def __init__(self, mat_path: str, mapping: SignalMap):
        self.mat_path = mat_path
        self.mapping = mapping

    def load(self) -> FlightDataset:
        try:
            from scipy.io import loadmat
        except ImportError as e:
            raise ImportError(
                "scipy is required for MatlabDataSource (pip install scipy)"
            ) from e

        raw = loadmat(self.mat_path, struct_as_record=False, squeeze_me=True)
        root = raw[self.mapping.struct_root]

        m = self.mapping
        time = np.asarray(_resolve(root, m.time), dtype=float)
        altitude = np.asarray(_resolve(root, m.altitude), dtype=float)
        velocity = np.asarray(_resolve(root, m.velocity), dtype=float)
        acceleration = np.asarray(_resolve(root, m.acceleration), dtype=float)
        z = np.asarray(_resolve(root, m.z), dtype=float)

        if m.latitude and m.longitude:
            lat = np.asarray(_resolve(root, m.latitude), dtype=float)
            lon = np.asarray(_resolve(root, m.longitude), dtype=float)
            x, y = launch_site.latlon_array_to_local(lat, lon)
        else:
            x = np.asarray(_resolve(root, m.x), dtype=float)
            y = np.asarray(_resolve(root, m.y), dtype=float)

        oxidizer = np.asarray(_resolve(root, m.propellant_oxidizer), dtype=float)
        fuel = np.asarray(_resolve(root, m.propellant_fuel), dtype=float)
        left = np.asarray(_resolve(root, m.propellant_left), dtype=float)
        right = np.asarray(_resolve(root, m.propellant_right), dtype=float)

        events_raw = _resolve(root, m.events)
        events = []
        for ev in np.atleast_1d(events_raw):
            events.append(FlightEvent(name=str(ev.name), t=float(ev.time)))

        return FlightDataset(
            time=time, altitude=altitude, velocity=velocity, acceleration=acceleration,
            x=x, y=y, z=z,
            propellant={"oxidizer": oxidizer, "fuel": fuel, "left": left, "right": right},
            propellant_initial={"oxidizer": float(oxidizer[0]), "fuel": float(fuel[0]),
                                 "left": float(left[0]), "right": float(right[0])},
            events=events,
        )
