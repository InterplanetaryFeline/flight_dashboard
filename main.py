"""
Real-time flight dashboard — entry point.

Run:
    python main.py

Controls:
    START / PAUSE / RESET buttons, or press Space to toggle start/pause.
    F11 toggles fullscreen, Esc exits fullscreen.

To switch from synthetic data to a real MATLAB structure later, replace
the `SyntheticDataSource()` below with a `MatlabDataSource(path, mapping)`
(see matlab_source.py) — nothing else in the app needs to change.
"""
import sys

from PySide6.QtWidgets import QApplication
import pyqtgraph as pg

from synthetic_source import SyntheticDataSource
from main_window import MainWindow

# from matlab_source import MatlabDataSource, SignalMap  # <- future real-data path


def main():
    pg.setConfigOptions(antialias=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    data_source = SyntheticDataSource(dt=0.05)
    # Future: data_source = MatlabDataSource("flight_001.mat", SignalMap(...))

    window = MainWindow(data_source)
    window.showFullScreen()
    # window.resize(1600, 950); window.show()  # <- use this instead for windowed dev/testing

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
