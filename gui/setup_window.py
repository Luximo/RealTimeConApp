"""Setup window — file picker UI (stub for Day 2; fully implemented in Day 5)."""

from PyQt6.QtWidgets import QMainWindow, QLabel
from PyQt6.QtCore import Qt


class SetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealTimeConApp — Setup")
        self.resize(600, 400)
        label = QLabel("Setup window — coming in Day 5", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)
