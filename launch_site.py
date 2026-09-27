"""
Launch site metadata, used to ground the local flight coordinate frame
(x=East, y=North, z=Up, meters, origin at the pad) to a real place and to
draw a schematic coastline under the 3D trajectory.
"""
from __future__ import annotations

import math
import numpy as np

LAUNCH_SITE_NAME = "Ustka, Poland"
LAUNCH_LAT = 54.5808   # deg N
LAUNCH_LON = 16.8618   # deg E

# The coast at Ustka runs roughly west-to-east with the Baltic Sea to the
# north and the town/dunes to the south. This is a schematic approximation
# for the ground-plane map, not a georeferenced survey.
COASTLINE_BEARING_DEG = 0.0   # 0 = coastline runs due east-west
SEA_IS_NORTH = True

EARTH_RADIUS_M = 6_371_000.0


def latlon_to_local(lat: float, lon: float) -> tuple[float, float]:
    """Convert a single lat/lon (deg) to local (east, north) meters relative
    to LAUNCH_LAT/LAUNCH_LON, using a flat-Earth (equirectangular)
    approximation. That approximation is essentially exact at the scale a
    rocket flight actually covers horizontally (tens to a few thousand
    meters) -- it would need replacing with a proper geodesic projection
    for anything covering many kilometers or spanning the poles/date line.
    """
    lat0_rad = math.radians(LAUNCH_LAT)
    north = math.radians(lat - LAUNCH_LAT) * EARTH_RADIUS_M
    east = math.radians(lon - LAUNCH_LON) * EARTH_RADIUS_M * math.cos(lat0_rad)
    return east, north


def latlon_array_to_local(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized form of latlon_to_local, for a full flight's worth of
    GPS samples at once."""
    lat0_rad = math.radians(LAUNCH_LAT)
    north = np.radians(lat - LAUNCH_LAT) * EARTH_RADIUS_M
    east = np.radians(lon - LAUNCH_LON) * EARTH_RADIUS_M * math.cos(lat0_rad)
    return east, north
