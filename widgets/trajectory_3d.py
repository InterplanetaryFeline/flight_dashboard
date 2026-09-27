from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QFont

from data_interface import FlightDataset
import launch_site

SEA_COLOR = (0.09, 0.28, 0.42, 1.0)
SEA_COLOR_FAR = (0.06, 0.20, 0.34, 1.0)
LAND_COLOR = (0.24, 0.30, 0.18, 1.0)
BEACH_COLOR = (0.55, 0.48, 0.32, 1.0)

# Real horizontal drift is only tens of meters against a ~10 km apogee, so
# the true-scale path renders as a near-vertical stick. This factor scales
# ONLY the on-screen x/y of the trajectory/marker so the flight reads as a
# recognizable arc -- it never touches the underlying dataset, so every
# other widget (plots, status bar, event timing) still shows real numbers.
HORIZONTAL_EXAGGERATION = 7.0


def _quad_mesh(x0, x1, y0, y1, z, color):
    """A single flat-colored rectangular GLMeshItem lying in the XY plane."""
    verts = np.array([
        [x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z],
    ])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    colors = np.array([color, color])
    md = gl.MeshData(vertexes=verts, faces=faces, faceColors=colors)
    item = gl.GLMeshItem(meshdata=md, smooth=False, drawEdges=False, shader="shaded")
    item.setGLOptions("opaque")
    return item


class Trajectory3D(QWidget):
    """Fast-updating 3D trajectory over a stylized coastline map: full
    ground track drawn dim, flown-so-far path drawn bright, current rocket
    position as a marker. Ground plane represents the Baltic coast at
    Ustka, Poland, with the sea to the north and land to the south.

    Horizontal motion is exaggerated on-screen only (see
    HORIZONTAL_EXAGGERATION) purely so the path is visually legible instead
    of reading as a single vertical line -- it doesn't change any actual
    numbers shown elsewhere."""

    def __init__(self, dataset: FlightDataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("3D TRAJECTORY")
        title.setStyleSheet("color:#8fa3b8; font-size:13px; font-weight:600; letter-spacing:2px;")
        header.addWidget(title)
        header.addStretch(1)
        site_lbl = QLabel(f"\u25b2 N   \u2022  {launch_site.LAUNCH_SITE_NAME}")
        site_lbl.setStyleSheet("color:#6c7a89; font-size:11px;")
        header.addWidget(site_lbl)
        layout.addLayout(header)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(pg.mkColor("#0d1218"))
        layout.addWidget(self.view, 1)

        # display-space points: real z (altitude), exaggerated x/y
        ex = HORIZONTAL_EXAGGERATION
        pts = np.column_stack([dataset.x * ex, dataset.y * ex, dataset.z])
        self._pts = pts

        max_alt = dataset.max_altitude()
        raw_span = max(float(np.abs(dataset.x).max()), float(np.abs(dataset.y).max()), 30.0)
        disp_span = raw_span * ex
        self.view.opts["distance"] = max_alt * 2.3
        self.view.opts["center"] = pg.Vector(0, 0, max_alt / 2)
        self.view.setCameraPosition(elevation=20, azimuth=40)

        self._build_map(disp_span)

        # faint full trajectory (ghost of the whole simulated path)
        ghost_color = (0.55, 0.75, 0.9, 0.4)
        self.ghost = gl.GLLinePlotItem(pos=pts, color=ghost_color, width=1.5, antialias=True)
        self.view.addItem(self.ghost)

        # bright flown-so-far path
        self.flown = gl.GLLinePlotItem(pos=pts[:1], color=(0.31, 0.76, 0.97, 1.0),
                                        width=3, antialias=True)
        self.view.addItem(self.flown)

        # launch pad marker
        pad = gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]), size=14,
                                    color=(1.0, 1.0, 1.0, 1.0))
        self.view.addItem(pad)

        # current rocket position marker
        self.rocket_marker = gl.GLScatterPlotItem(pos=np.array([pts[0]]), size=18,
                                                    color=(1.0, 0.45, 0.3, 1.0))
        self.view.addItem(self.rocket_marker)

        # faint vertical drop-line from the rocket down to its ground shadow
        self.alt_line = gl.GLLinePlotItem(pos=np.array([pts[0], [pts[0][0], pts[0][1], 0]]),
                                           color=(1.0, 0.45, 0.3, 0.3), width=1)
        self.view.addItem(self.alt_line)

        self._add_map_labels(disp_span)

    def _build_map(self, disp_span: float):
        """Two-tone ground plane: Baltic Sea to the north (+y), land/dunes
        to the south (-y), with a soft beach strip along the coastline and
        a gentle meander for the coastline itself (not a straight ruler
        line) plus a small river mouth for visual interest. Sized to the
        exaggerated (on-screen) trajectory span so the path stays framed."""
        half = max(disp_span * 3.0, 400.0)
        z = -1.0  # sit just below the trajectory/markers

        # coastline meanders gently around y=0 -- approximate it as a few
        # flat segments along x so we can still use simple rectangular quads
        segments = np.linspace(-half, half, 7)
        for i in range(len(segments) - 1):
            x0, x1 = segments[i], segments[i + 1]
            wobble = 0.04 * half * np.sin(i * 1.7)  # gentle, deterministic meander
            coast_y = wobble
            # sea (north of coast)
            self.view.addItem(_quad_mesh(x0, x1, coast_y, half, z, SEA_COLOR))
            # thin beach strip
            self.view.addItem(_quad_mesh(x0, x1, coast_y - half * 0.02, coast_y, z + 0.05, BEACH_COLOR))
            # land (south of beach)
            self.view.addItem(_quad_mesh(x0, x1, -half, coast_y - half * 0.02, z, LAND_COLOR))

        # a small river mouth cutting through the land, roughly where the
        # Slupia river meets the sea at Ustka
        river_x = -half * 0.22
        river_w = half * 0.035
        self.view.addItem(_quad_mesh(river_x - river_w, river_x + river_w, -half, half * 0.02, z + 0.02, SEA_COLOR_FAR))

        # faint grid over the land for scale reference
        grid = gl.GLGridItem()
        grid.setSize(x=half * 2, y=half * 2)
        grid.setSpacing(x=half * 0.15, y=half * 0.15)
        grid.translate(0, 0, z + 0.1)
        grid.setColor((1, 1, 1, 0.06))
        self.view.addItem(grid)

    def _add_map_labels(self, disp_span: float):
        try:
            font = QFont("Consolas", 12, QFont.Bold)
            sea_label = gl.GLTextItem(pos=(0, disp_span * 1.6, 5), text="BALTIC SEA",
                                       color=(200, 220, 235, 200), font=font)
            self.view.addItem(sea_label)
            land_label = gl.GLTextItem(pos=(0, -disp_span * 1.6, 5), text="USTKA",
                                        color=(210, 205, 180, 200), font=font)
            self.view.addItem(land_label)
        except Exception:
            # GLTextItem availability/signature varies slightly by pyqtgraph
            # version -- the map still reads fine without the text labels.
            pass

    def update_time(self, t: float):
        idx = max(self.dataset.index_at(t), 1)
        flown_pts = self._pts[:idx]
        self.flown.setData(pos=flown_pts)

        state = self.dataset.sample_at(t)
        ex = HORIZONTAL_EXAGGERATION
        pos = np.array([state.x * ex, state.y * ex, state.z])
        self.rocket_marker.setData(pos=np.array([pos]))
        self.alt_line.setData(pos=np.array([pos, [pos[0], pos[1], 0]]))
