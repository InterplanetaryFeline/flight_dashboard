"""
Drives sim-time forward from a real QTimer tick, independent of the GUI
widgets. Emits `time_updated(t)` each tick; main_window turns that into a
FlightState and pushes it to every widget.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
import time as _time


class SimulationClock(QObject):
    time_updated = Signal(float)
    finished = Signal()
    state_changed = Signal(str)  # "running" | "paused" | "reset"

    TICK_MS = 33  # ~30 Hz

    def __init__(self, t_end: float, parent=None):
        super().__init__(parent)
        self.t_end = t_end
        self.speed = 1.0
        self.sim_time = 0.0
        self._running = False
        self._last_wall = None

        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    # -- controls ----------------------------------------------------
    def start(self):
        if self._running:
            return
        self._running = True
        self._last_wall = _time.monotonic()
        self._timer.start()
        self.state_changed.emit("running")

    def pause(self):
        if not self._running:
            return
        self._running = False
        self._timer.stop()
        self.state_changed.emit("paused")

    def reset(self):
        self._running = False
        self._timer.stop()
        self.sim_time = 0.0
        self.time_updated.emit(self.sim_time)
        self.state_changed.emit("reset")

    def set_speed(self, speed: float):
        self.speed = speed

    @property
    def running(self) -> bool:
        return self._running

    # -- internal ------------------------------------------------------
    def _on_tick(self):
        now = _time.monotonic()
        real_dt = now - self._last_wall
        self._last_wall = now
        self.sim_time = min(self.t_end, self.sim_time + real_dt * self.speed)
        self.time_updated.emit(self.sim_time)
        if self.sim_time >= self.t_end:
            self.pause()
            self.finished.emit()
