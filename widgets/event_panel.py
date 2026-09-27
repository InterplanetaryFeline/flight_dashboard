from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from event_manager import EventManager

PANEL_BG = "#12181f"
BORDER = "#26313c"
GREEN = "#38d67a"
GRAY = "#5b6673"
ACTIVE_BG = "#1c2b22"


class EventPanel(QWidget):
    def __init__(self, event_mgr: EventManager, parent=None):
        super().__init__(parent)
        self.event_mgr = event_mgr
        self.setStyleSheet(f"background-color:{PANEL_BG}; border:1px solid {BORDER}; border-radius:6px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(4)

        title = QLabel("FLIGHT EVENTS")
        title.setStyleSheet("color:#8fa3b8; font-size:13px; font-weight:600; letter-spacing:2px; border:none;")
        outer.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color:{BORDER}; max-height:1px; border:none;")
        outer.addWidget(line)
        outer.addSpacing(4)

        self._rows = {}
        for ev in self.event_mgr.events:
            row = QLabel()
            row.setFixedHeight(24)
            row.setStyleSheet(
                f"color:{GRAY}; font-size:14px; font-family:Consolas,Menlo,monospace; "
                f"padding:3px 6px; border-radius:3px; border:none;"
            )
            outer.addWidget(row)
            self._rows[ev.name] = row
        outer.addStretch(1)

        # guarantee enough room for every row + title so nothing ever
        # gets compressed to zero height and overlaps
        self.setMinimumHeight(40 + 24 * len(self.event_mgr.events))

        self.refresh(0.0)

    def refresh(self, t: float):
        active = self.event_mgr.most_recent(t)
        for ev in self.event_mgr.events:
            row = self._rows[ev.name]
            name = ev.name.ljust(20)
            mark = "\u2713" if ev.occurred else "\u25cb"
            text = f"{mark}  {name} {ev.t:6.1f}s"
            if ev.occurred:
                color = GREEN
                bg = ACTIVE_BG if active is ev else "transparent"
            else:
                color = GRAY
                bg = "transparent"
            weight = "700" if (active is ev) else "400"
            row.setStyleSheet(
                f"color:{color}; background-color:{bg}; font-weight:{weight}; "
                f"font-size:14px; font-family:Consolas,Menlo,monospace; padding:3px 6px; "
                f"border-radius:3px; border:none;"
            )
            row.setText(text)
