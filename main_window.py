from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from data_interface import DataSource
from sim_clock import SimulationClock
from event_manager import EventManager
from widgets.event_panel import EventPanel
from widgets.plot_panel import PlotPanel
from widgets.trajectory_3d import Trajectory3D
from widgets.rocket_widget import RocketWidget
from widgets.status_bar import StatusBar

WINDOW_BG = "#080c11"
PANEL_BORDER = "#26313c"
LEFT_COLUMN_PX = 340    # fixed width: events + rocket schematic
TRAJECTORY_COLUMN_PX = 300   # fixed width: 3D view, full height (tall rectangle)


class MainWindow(QMainWindow):
    def __init__(self, data_source: DataSource):
        super().__init__()
        self.setWindowTitle("Flight Dashboard")
        self.setStyleSheet(f"background-color:{WINDOW_BG};")

        self.dataset = data_source.load()
        self.event_mgr = EventManager(self.dataset.events)
        self.clock = SimulationClock(self.dataset.t_end)

        self._build_ui()
        self._wire_signals()

    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 10, 14, 0)
        outer.setSpacing(10)

        header = QLabel("FLIGHT DASHBOARD")
        header.setStyleSheet(
            "color:#cfd8e3; font-size:20px; font-weight:800; letter-spacing:4px; padding:2px 4px;"
        )
        outer.addWidget(header)

        main_row = QHBoxLayout()
        main_row.setSpacing(10)
        outer.addLayout(main_row, 1)

        self.event_panel = EventPanel(self.event_mgr)
        self.rocket_widget = RocketWidget(self.dataset.propellant_initial)
        self.trajectory = Trajectory3D(self.dataset)
        self.plot_panel = PlotPanel(self.dataset)

        # --- left column: events + rocket, fixed width so they can never
        # get compressed by whatever else is competing for space ---
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._panel("EVENTS", self.event_panel, show_title=False), 2)
        left_col.addWidget(self._panel("ROCKET / PROPULSION", self.rocket_widget), 3)

        left_widget = QWidget()
        left_widget.setLayout(left_col)
        left_widget.setFixedWidth(LEFT_COLUMN_PX)

        # --- center: the flight-data plots, dominant, fills all remaining space ---
        plot_box = self._panel("FLIGHT DATA", self.plot_panel)

        # --- right column: 3D trajectory, fixed width, full height -> tall rectangle ---
        traj_box = self._panel("3D TRAJECTORY", self.trajectory, show_title=False)
        traj_box.setFixedWidth(TRAJECTORY_COLUMN_PX)

        main_row.addWidget(left_widget)
        main_row.addWidget(plot_box, 1)
        main_row.addWidget(traj_box)

        self.status_bar = StatusBar()
        outer.addWidget(self.status_bar)

    def _panel(self, title: str, widget: QWidget, show_title: bool = True) -> QWidget:
        box = QWidget()
        box.setStyleSheet(f"background-color:#0f151c; border:1px solid {PANEL_BORDER}; border-radius:8px;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)
        if show_title:
            lbl = QLabel(title)
            lbl.setStyleSheet("color:#8fa3b8; font-size:12px; font-weight:700; letter-spacing:2px; border:none;")
            lay.addWidget(lbl)
        lay.addWidget(widget, 1)
        return box

    # ------------------------------------------------------------------
    def _wire_signals(self):
        self.clock.time_updated.connect(self._on_time_updated)
        self.status_bar.start_clicked.connect(self.clock.start)
        self.status_bar.pause_clicked.connect(self.clock.pause)
        self.status_bar.reset_clicked.connect(self._on_reset)
        self.status_bar.speed_changed.connect(self.clock.set_speed)

        self._max_alt_seen = 0.0
        self._max_vel_seen = 0.0
        self._max_acc_seen = 0.0

        self._on_time_updated(0.0)  # paint the pre-launch state

    def _on_reset(self):
        self.clock.reset()
        self.event_mgr.reset()
        self._max_alt_seen = self._max_vel_seen = self._max_acc_seen = 0.0

    def _on_time_updated(self, t: float):
        state = self.dataset.sample_at(t)

        self._max_alt_seen = max(self._max_alt_seen, state.altitude)
        self._max_vel_seen = max(self._max_vel_seen, state.velocity)
        self._max_acc_seen = max(self._max_acc_seen, state.acceleration)

        self.event_mgr.update(t)
        self.event_panel.refresh(t)
        self.plot_panel.update_time(t)
        self.trajectory.update_time(t)
        self.rocket_widget.update_state(state)
        self.status_bar.update_state(state, self._max_alt_seen, self._max_vel_seen, self._max_acc_seen)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.showNormal()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Space:
            self.clock.pause() if self.clock.running else self.clock.start()
        super().keyPressEvent(event)
