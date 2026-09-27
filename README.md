# Flight Dashboard

Real-time flight-visualization dashboard for a high-power model rocket,
using synthetic data for now and built to swap in real MATLAB telemetry
later without touching the GUI.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Opens fullscreen. Press **F11** to toggle fullscreen, **Esc** to exit it,
**Space** to toggle Start/Pause.

For windowed development, edit the bottom of `main.py`:
comment out `window.showFullScreen()` and uncomment the `window.resize(...)`
line.

## Controls

- **START** — begins the flight animation from wherever `sim_time` is
- **PAUSE** — freezes the animation
- **RESET** — returns to the pre-launch state
- **Speed dropdown** — 0.25x / 0.5x / 1x / 2x / 5x playback

## Layout

- Left column (fixed width, ~340px): events list (top), rocket/propulsion
  schematic (bottom) — sized generously so neither ever gets compressed
- Center (dominant — fills all remaining width): altitude/velocity/
  acceleration strip charts, the primary flight-data view
- Right column (fixed width, ~300px, full height): 3D trajectory as a
  tall rectangle
- Bottom bar: live numeric readouts + running maxima + controls

- Events: gray -> green as they occur, most recent one bolded; each row
  has a fixed height and the panel enforces its own minimum height so
  rows can never overlap regardless of window size
- Rocket schematic: central hybrid stage with **separate oxidizer and fuel
  fill bars**, plus two solid boosters (left/right), each with its own
  propellant fill bar
- 3D trajectory: over a stylized ground map (see below), full path shown
  faint, flown-so-far path bright, rocket marker at current position
- Strip charts: revealed progressively as the flight plays, each given
  generous room since they're the primary flight-data view

`LEFT_COLUMN_PX` and `TRAJECTORY_COLUMN_PX` at the top of `main_window.py`
control the two fixed side-column widths if you want to resize either.

## Launch site / ground map

The 3D trajectory's ground plane is a schematic coastline map, not a real
survey: sea to the north, land to the south, with a small river-mouth
accent, grounded at **Ustka, Poland** (`launch_site.py` — lat/lon and
orientation live there, change it to relocate). The rocket's actual
horizontal drift is only tens of meters against a ~10 km apogee, which on
a true-to-scale plot reads as a flat vertical line — so the trajectory's
on-screen x/y (only, never altitude, and never the numbers shown anywhere
else) is exaggerated by `HORIZONTAL_EXAGGERATION` in
`widgets/trajectory_3d.py` (7x by default) purely so the path is visually
legible. Turn it down toward 1.0 if you'd rather see the true-scale path.
The map itself is sized to frame this exaggerated span, not the raw one.
If you'd rather use a real satellite/street map tile there instead of the
stylized one, that's a fairly contained
swap inside `widgets/trajectory_3d.py::_build_map`.

## Architecture (see file headers for details)

| File | Role |
|---|---|
| `data_interface.py` | Standardized `FlightDataset`/`FlightEvent`/`FlightState` schema + abstract `DataSource` |
| `synthetic_source.py` | Concrete `DataSource`: generates the demo flight |
| `matlab_source.py` | Concrete `DataSource` stub: dot-path signal mapping into a `.mat` struct -> same schema |
| `launch_site.py` | Launch-site metadata (name, lat/lon, coastline orientation) used by the map |
| `sim_clock.py` | `SimulationClock`: QTimer-driven sim time, play/pause/reset/speed |
| `event_manager.py` | Tracks which events have fired as of the current sim time |
| `widgets/` | Presentation only — each widget takes a `FlightState`/`FlightDataset` and draws it |
| `main_window.py` | Assembles the dashboard, owns the single tick -> update-all-widgets loop |
| `main.py` | Entry point; this is the one line you change to switch data sources |

## Propellant model

The hybrid main stage tracks **oxidizer** and **fuel** as two independent
quantities (both deplete over the same burn window, at their own initial
masses) rather than one combined "main" number. The two solid boosters
(`left`, `right`) are unchanged.

## Swapping in real MATLAB data later

In `main.py`, replace:

```python
data_source = SyntheticDataSource(dt=0.05)
```

with, if your struct has local x/y position:

```python
from matlab_source import MatlabDataSource, SignalMap

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
    events="flight.events",
    x="flight.position.x", y="flight.position.y",
)
data_source = MatlabDataSource("flight_001.mat", mapping)
```

or, if your struct has GPS latitude/longitude instead (common for
altimeter/tracker telemetry), swap the last line for:

```python
    latitude="flight.gps.lat", longitude="flight.gps.lon",
```

`SignalMap` converts lat/lon to the same local East/North meters the app
uses internally, anchored at `launch_site.LAUNCH_LAT`/`LAUNCH_LON`. Give
one pair or the other — mixing both or giving neither raises an error at
construction time rather than failing silently later.

Adjust the dot-paths to match your actual MATLAB struct field names — the
rest of the app is unaffected.

## Known limitation of this environment

This was built and unit-tested (data generation, event timing, propellant
burn, landing-altitude correctness) in a headless container without a
display, so the Qt/OpenGL rendering itself — including the new map mesh
and text labels — could not be visually verified here. `GLTextItem`'s
constructor signature has varied slightly across pyqtgraph versions, so
the map labels are wrapped in a try/except and the map still renders
without them if that call doesn't match your installed version. Please
run it locally and flag anything that looks off; the architecture keeps
each widget easy to adjust in isolation.
