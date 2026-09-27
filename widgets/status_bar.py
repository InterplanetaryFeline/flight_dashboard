from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal

from data_interface import FlightState

BG = "#12181f"
BORDER = "#26313c"
TEXT = "#e8edf3"
SUBTEXT = "#7d8b9a"


def _stat_block(label_text: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(10, 4, 10, 4)
    lay.setSpacing(0)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color:{SUBTEXT}; font-size:10px; letter-spacing:1px;")
    val = QLabel("--")
    val.setStyleSheet(f"color:{TEXT}; font-size:20px; font-weight:700; font-family:Consolas,Menlo,monospace;")
    lay.addWidget(lbl)
    lay.addWidget(val)
    return box, val


class StatusBar(QWidget):
    start_clicked = Signal()
    pause_clicked = Signal()
    reset_clicked = Signal()
    speed_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG}; border-top:1px solid {BORDER};")
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 6, 18, 6)
        root.setSpacing(18)

        self.time_box, self.time_val = _stat_block("TIME (s)")
        self.alt_box, self.alt_val = _stat_block("ALTITUDE (m)")
        self.vel_box, self.vel_val = _stat_block("VELOCITY (m/s)")
        self.acc_box, self.acc_val = _stat_block("ACCEL (m/s\u00b2)")
        self.maxalt_box, self.maxalt_val = _stat_block("MAX ALT (m)")
        self.maxvel_box, self.maxvel_val = _stat_block("MAX VEL (m/s)")
        self.maxacc_box, self.maxacc_val = _stat_block("MAX ACCEL (m/s\u00b2)")

        for box in (self.time_box, self.alt_box, self.vel_box, self.acc_box,
                    self.maxalt_box, self.maxvel_box, self.maxacc_box):
            root.addWidget(box)

        root.addStretch(1)

        # speed selector
        speed_lbl = QLabel("SPEED")
        speed_lbl.setStyleSheet(f"color:{SUBTEXT}; font-size:10px; letter-spacing:1px;")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "5x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.setStyleSheet(
            f"QComboBox {{ background-color:#1a222b; color:{TEXT}; border:1px solid {BORDER}; "
            f"border-radius:4px; padding:4px 8px; font-family:Consolas,Menlo,monospace; }}"
        )
        self.speed_combo.currentTextChanged.connect(
            lambda text: self.speed_changed.emit(float(text.rstrip("x")))
        )
        speed_col = QVBoxLayout()
        speed_col.setSpacing(2)
        speed_col.addWidget(speed_lbl)
        speed_col.addWidget(self.speed_combo)
        speed_wrap = QWidget()
        speed_wrap.setLayout(speed_col)
        root.addWidget(speed_wrap)

        # controls
        self.btn_start = self._make_button("\u25b6  START", "#2e7d32", "#43a047")
        self.btn_pause = self._make_button("\u23f8  PAUSE", "#8c6d1f", "#b8912b")
        self.btn_reset = self._make_button("\u21bb  RESET", "#5c2b2b", "#7a3a3a")

        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_pause.clicked.connect(self.pause_clicked)
        self.btn_reset.clicked.connect(self.reset_clicked)

        for b in (self.btn_start, self.btn_pause, self.btn_reset):
            root.addWidget(b)

    def _make_button(self, text: str, base: str, hover: str) -> QPushButton:
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{base}; color:white; font-weight:700;
                border:none; border-radius:6px; padding:10px 18px; font-size:13px;
            }}
            QPushButton:hover {{ background-color:{hover}; }}
        """)
        return b

    def update_state(self, state: FlightState, max_alt: float, max_vel: float, max_acc: float):
        self.time_val.setText(f"{state.t:6.2f}")
        self.alt_val.setText(f"{state.altitude:7.1f}")
        self.vel_val.setText(f"{state.velocity:7.1f}")
        self.acc_val.setText(f"{state.acceleration:6.1f}")
        self.maxalt_val.setText(f"{max_alt:7.1f}")
        self.maxvel_val.setText(f"{max_vel:7.1f}")
        self.maxacc_val.setText(f"{max_acc:6.1f}")
