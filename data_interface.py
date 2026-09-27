"""
Standardized data schema shared by every data source (synthetic, MATLAB, ...).

The GUI only ever talks to a `FlightDataset`. It never knows whether the
data came from synthetic generation or a MATLAB struct.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


@dataclass
class FlightEvent:
    name: str
    t: float          # scheduled/occurred time [s]
    occurred: bool = False  # set at runtime by EventManager, not by the data source


@dataclass
class FlightState:
    """One instantaneous snapshot of the flight, interpolated to time t."""
    t: float
    altitude: float          # m
    velocity: float          # m/s (speed magnitude, along-flight)
    acceleration: float      # m/s^2
    x: float
    y: float
    z: float
    propellant: Dict[str, float]  # {"oxidizer": kg, "fuel": kg, "left": kg, "right": kg}


@dataclass
class FlightDataset:
    """Full flight, standardized. Any DataSource must produce this."""
    time: np.ndarray                 # (N,)
    altitude: np.ndarray             # (N,)
    velocity: np.ndarray             # (N,)
    acceleration: np.ndarray         # (N,)
    x: np.ndarray                    # (N,)
    y: np.ndarray                    # (N,)
    z: np.ndarray                    # (N,)
    propellant: Dict[str, np.ndarray]  # each (N,), keys: oxidizer/fuel/left/right
    propellant_initial: Dict[str, float]
    events: List[FlightEvent] = field(default_factory=list)

    @property
    def t_end(self) -> float:
        return float(self.time[-1])

    def sample_at(self, t: float) -> FlightState:
        """Vectorized linear interpolation to an arbitrary sim time."""
        t = float(np.clip(t, self.time[0], self.time[-1]))
        alt = float(np.interp(t, self.time, self.altitude))
        vel = float(np.interp(t, self.time, self.velocity))
        acc = float(np.interp(t, self.time, self.acceleration))
        x = float(np.interp(t, self.time, self.x))
        y = float(np.interp(t, self.time, self.y))
        z = float(np.interp(t, self.time, self.z))
        prop = {k: float(np.interp(t, self.time, v)) for k, v in self.propellant.items()}
        return FlightState(t=t, altitude=alt, velocity=vel, acceleration=acc,
                            x=x, y=y, z=z, propellant=prop)

    def index_at(self, t: float) -> int:
        """Index of the last sample at or before t — used for the 3D path slice."""
        return int(np.searchsorted(self.time, t, side="right"))

    def max_altitude(self) -> float:
        return float(np.max(self.altitude))

    def max_velocity(self) -> float:
        return float(np.max(self.velocity))

    def max_acceleration(self) -> float:
        return float(np.max(self.acceleration))


class DataSource(ABC):
    """Anything that can produce a standardized FlightDataset."""

    @abstractmethod
    def load(self) -> FlightDataset:
        ...
