from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QLinearGradient
from PySide6.QtCore import Qt, QRectF, QPointF

from data_interface import FlightState

BG = "#0d1218"
BODY = "#3a4552"
BODY_LIGHT = "#4a5568"
OXIDIZER_COLOR = "#4fc3f7"
FUEL_COLOR = "#66bb6a"
LEFT_COLOR = "#ffb74d"
RIGHT_COLOR = "#ba68c8"
EMPTY_COLOR = "#232b34"
TEXT = "#cfd8e3"
SUBTEXT = "#8fa3b8"


class RocketWidget(QWidget):
    """Custom-painted schematic: central hybrid stage (separate oxidizer and
    fuel tanks) + two solid boosters, each with a propellant fill bar that
    drains as it burns."""

    def __init__(self, propellant_initial: dict, parent=None):
        super().__init__(parent)
        self.initial = propellant_initial
        self.remaining = dict(propellant_initial)
        self.setMinimumHeight(260)
        self.setStyleSheet(f"background-color:{BG};")

    def update_state(self, state: FlightState):
        self.remaining = state.propellant
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(BG))

        w, h = self.width(), self.height()
        cx = w * 0.5
        top = h * 0.08
        bottom = h * 0.92
        body_w = w * 0.16
        body_h = bottom - top
        nose_h = body_h * 0.18

        # --- central hybrid stage body ---
        body_rect = QRectF(cx - body_w / 2, top + nose_h, body_w, body_h - nose_h)
        p.setPen(QPen(QColor(BODY_LIGHT), 2))
        p.setBrush(QBrush(QColor(BODY)))
        p.drawRoundedRect(body_rect, 4, 4)

        # nose cone
        nose = QPolygonF([
            QPointF(cx, top),
            QPointF(cx - body_w / 2, top + nose_h),
            QPointF(cx + body_w / 2, top + nose_h),
        ])
        p.setBrush(QBrush(QColor(BODY_LIGHT)))
        p.drawPolygon(nose)

        # fins
        fin_w = body_w * 0.9
        fin_h = body_h * 0.16
        p.setBrush(QBrush(QColor(BODY)))
        left_fin = QPolygonF([
            QPointF(cx - body_w / 2, bottom - fin_h),
            QPointF(cx - body_w / 2 - fin_w, bottom),
            QPointF(cx - body_w / 2, bottom),
        ])
        right_fin = QPolygonF([
            QPointF(cx + body_w / 2, bottom - fin_h),
            QPointF(cx + body_w / 2 + fin_w, bottom),
            QPointF(cx + body_w / 2, bottom),
        ])
        p.drawPolygon(left_fin)
        p.drawPolygon(right_fin)

        # main hybrid stage: oxidizer tank (upper) + fuel grain (lower),
        # separated by a thin divider -- each fills/drains independently
        inner = body_rect.adjusted(6, 6, -6, -6)
        ox_h = inner.height() * 0.62
        div_gap = 4
        ox_rect = QRectF(inner.left(), inner.top(), inner.width(), ox_h - div_gap / 2)
        fuel_rect = QRectF(inner.left(), inner.top() + ox_h + div_gap / 2,
                            inner.width(), inner.height() - ox_h - div_gap / 2)
        self._draw_fill_bar(p, ox_rect, self.remaining.get("oxidizer", 0),
                             self.initial.get("oxidizer", 1), OXIDIZER_COLOR)
        self._draw_fill_bar(p, fuel_rect, self.remaining.get("fuel", 0),
                             self.initial.get("fuel", 1), FUEL_COLOR)

        # --- side boosters ---
        boost_w = body_w * 0.55
        boost_h = body_h * 0.62
        boost_top = bottom - boost_h
        gap = body_w * 0.35

        left_rect = QRectF(cx - body_w / 2 - gap - boost_w, boost_top, boost_w, boost_h)
        right_rect = QRectF(cx + body_w / 2 + gap, boost_top, boost_w, boost_h)

        for rect, color, key in ((left_rect, LEFT_COLOR, "left"), (right_rect, RIGHT_COLOR, "right")):
            p.setPen(QPen(QColor(BODY_LIGHT), 2))
            p.setBrush(QBrush(QColor(BODY)))
            p.drawRoundedRect(rect, 3, 3)
            # booster nose tip
            tip = QPolygonF([
                QPointF(rect.center().x(), rect.top() - boost_w * 0.35),
                QPointF(rect.left(), rect.top()),
                QPointF(rect.right(), rect.top()),
            ])
            p.setBrush(QBrush(QColor(BODY_LIGHT)))
            p.drawPolygon(tip)
            self._draw_fill_bar(p, rect.adjusted(4, 4, -4, -4),
                                 self.remaining.get(key, 0), self.initial.get(key, 1), color)

        # connecting struts
        p.setPen(QPen(QColor(BODY_LIGHT), 3))
        strut_y = boost_top + boost_h * 0.3
        p.drawLine(QPointF(left_rect.right(), strut_y), QPointF(cx - body_w / 2, strut_y))
        p.drawLine(QPointF(right_rect.left(), strut_y), QPointF(cx + body_w / 2, strut_y))

        # --- labels ---
        p.setFont(QFont("Consolas", 10))
        self._label(p, left_rect, "left", LEFT_COLOR)
        self._label(p, right_rect, "right", RIGHT_COLOR)
        self._main_label(p, body_rect)

        p.end()

    def _draw_fill_bar(self, p: QPainter, rect: QRectF, remaining: float, initial: float, color: str):
        frac = 0.0 if initial <= 0 else max(0.0, min(1.0, remaining / initial))
        p.setBrush(QBrush(QColor(EMPTY_COLOR)))
        p.setPen(Qt.NoPen)
        p.drawRect(rect)
        fill_h = rect.height() * frac
        fill_rect = QRectF(rect.left(), rect.bottom() - fill_h, rect.width(), fill_h)
        grad = QLinearGradient(0, fill_rect.top(), 0, fill_rect.bottom())
        c = QColor(color)
        grad.setColorAt(0, c.lighter(130))
        grad.setColorAt(1, c)
        p.setBrush(QBrush(grad))
        p.drawRect(fill_rect)

    def _label(self, p: QPainter, rect: QRectF, key: str, color: str):
        remaining = self.remaining.get(key, 0)
        initial = self.initial.get(key, 0)
        text = f"{key.upper()}\n{remaining:4.1f} / {initial:.0f} kg"
        p.setPen(QColor(color))
        x = rect.center().x() - 45
        y = rect.bottom() + 26
        p.drawText(QRectF(x, y, 90, 34), Qt.AlignCenter, text)

    def _main_label(self, p: QPainter, body_rect: QRectF):
        ox_rem, ox_init = self.remaining.get("oxidizer", 0), self.initial.get("oxidizer", 0)
        fuel_rem, fuel_init = self.remaining.get("fuel", 0), self.initial.get("fuel", 0)
        x = body_rect.center().x() - 60
        y = body_rect.bottom() + 34
        p.setPen(QColor(OXIDIZER_COLOR))
        p.drawText(QRectF(x, y, 120, 16), Qt.AlignCenter, f"OXIDIZER  {ox_rem:4.1f} / {ox_init:.0f} kg")
        p.setPen(QColor(FUEL_COLOR))
        p.drawText(QRectF(x, y + 16, 120, 16), Qt.AlignCenter, f"FUEL  {fuel_rem:4.1f} / {fuel_init:.0f} kg")
