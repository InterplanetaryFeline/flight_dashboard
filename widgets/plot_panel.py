from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from data_interface import FlightDataset

BG = "#0d1218"
GRID_ALPHA = 0.15
ACCENT = {
    "altitude": "#4fc3f7",
    "velocity": "#ffb74d",
    "acceleration": "#ef5350",
}


def _make_plot(title: str, ylabel: str, color: str) -> pg.PlotWidget:
    pw = pg.PlotWidget(background=BG)
    pw.showGrid(x=True, y=True, alpha=GRID_ALPHA)
    pw.setLabel("left", ylabel, color="#8fa3b8")
    pw.setLabel("bottom", "time", units="s", color="#8fa3b8")
    pw.getAxis("left").setTextPen("#8fa3b8")
    pw.getAxis("bottom").setTextPen("#8fa3b8")
    pw.setTitle(title, color="#cfd8e3", size="11pt")
    pw.setMinimumHeight(180)
    return pw


class PlotPanel(QWidget):
    """Three stacked real-time strip charts: altitude, velocity, acceleration."""

    def __init__(self, dataset: FlightDataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.plot_alt = _make_plot("ALTITUDE", "m", ACCENT["altitude"])
        self.plot_vel = _make_plot("VELOCITY", "m/s", ACCENT["velocity"])
        self.plot_acc = _make_plot("ACCELERATION", "m/s\u00b2", ACCENT["acceleration"])

        self.curve_alt = self.plot_alt.plot(pen=pg.mkPen(ACCENT["altitude"], width=2))
        self.curve_vel = self.plot_vel.plot(pen=pg.mkPen(ACCENT["velocity"], width=2))
        self.curve_acc = self.plot_acc.plot(pen=pg.mkPen(ACCENT["acceleration"], width=2))

        self.marker_alt = self.plot_alt.plot([0], [0], pen=None, symbol="o",
                                              symbolSize=8, symbolBrush=ACCENT["altitude"])
        self.marker_vel = self.plot_vel.plot([0], [0], pen=None, symbol="o",
                                              symbolSize=8, symbolBrush=ACCENT["velocity"])
        self.marker_acc = self.plot_acc.plot([0], [0], pen=None, symbol="o",
                                              symbolSize=8, symbolBrush=ACCENT["acceleration"])

        for pw in (self.plot_alt, self.plot_vel, self.plot_acc):
            layout.addWidget(pw, 1)

        # fix x-range to the whole flight so the timeline reveals progressively
        for pw in (self.plot_alt, self.plot_vel, self.plot_acc):
            pw.setXRange(0, dataset.t_end, padding=0.02)
        self.plot_alt.setYRange(0, dataset.max_altitude() * 1.1)
        vmin, vmax = dataset.velocity.min(), dataset.velocity.max()
        self.plot_vel.setYRange(vmin * 1.1 - 1, vmax * 1.1 + 1)
        amin, amax = dataset.acceleration.min(), dataset.acceleration.max()
        self.plot_acc.setYRange(amin * 1.15 - 1, amax * 1.15 + 1)

    def update_time(self, t: float):
        idx = self.dataset.index_at(t)
        idx = max(idx, 1)
        tt = self.dataset.time[:idx]
        self.curve_alt.setData(tt, self.dataset.altitude[:idx])
        self.curve_vel.setData(tt, self.dataset.velocity[:idx])
        self.curve_acc.setData(tt, self.dataset.acceleration[:idx])

        state = self.dataset.sample_at(t)
        self.marker_alt.setData([t], [state.altitude])
        self.marker_vel.setData([t], [state.velocity])
        self.marker_acc.setData([t], [state.acceleration])
