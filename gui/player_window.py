"""Playback UI + scrolling captions, kept fully separate from backend."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

import config


class CaptionDisplay(QWidget):
    """Placeholder caption display area — dark background, no text yet.
    Days 3-4 will replace this with the live scrolling painter widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1a1a2e;")


class PlayerWindow(QMainWindow):
    """Main playback window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealTimeConApp")
        self.resize(900, 520)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Caption display area ──────────────────────────────────────────────
        self.caption_display = CaptionDisplay()
        root.addWidget(self.caption_display)

        # ── Controls bar ─────────────────────────────────────────────────────
        controls = QWidget()
        controls.setStyleSheet("background-color: #16213e;")
        controls.setFixedHeight(70)
        bar = QHBoxLayout(controls)
        bar.setContentsMargins(12, 8, 12, 8)
        bar.setSpacing(10)

        # Transport buttons
        self.btn_restart = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_stop = QPushButton("⏹")
        for btn in (self.btn_restart, self.btn_play, self.btn_stop):
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(
                "QPushButton { background:#0f3460; color:white;"
                " border-radius:6px; font-size:16px; }"
                "QPushButton:hover { background:#e94560; }"
            )
        bar.addWidget(self.btn_restart)
        bar.addWidget(self.btn_play)
        bar.addWidget(self.btn_stop)

        # Progress scrubber
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setStyleSheet(
            "QSlider::groove:horizontal { height:6px; background:#0f3460;"
            " border-radius:3px; }"
            "QSlider::handle:horizontal { width:14px; height:14px; margin:-4px 0;"
            " background:#e94560; border-radius:7px; }"
            "QSlider::sub-page:horizontal { background:#e94560; border-radius:3px; }"
        )
        bar.addWidget(self.progress, stretch=1)

        # Speed control
        speed_lbl = QLabel("Speed")
        speed_lbl.setStyleSheet("color:#aaaaaa; font-size:12px;")
        bar.addWidget(speed_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(
            int(config.MIN_SPEED * 10),
            int(config.MAX_SPEED * 10),
        )
        self.speed_slider.setValue(int(config.DEFAULT_SPEED * 10))
        self.speed_slider.setFixedWidth(110)
        self.speed_slider.setStyleSheet(
            "QSlider::groove:horizontal { height:6px; background:#0f3460;"
            " border-radius:3px; }"
            "QSlider::handle:horizontal { width:14px; height:14px; margin:-4px 0;"
            " background:#4ecca3; border-radius:7px; }"
            "QSlider::sub-page:horizontal { background:#4ecca3; border-radius:3px; }"
        )
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        bar.addWidget(self.speed_slider)

        self.speed_value_label = QLabel(f"{config.DEFAULT_SPEED:.1f}x")
        self.speed_value_label.setStyleSheet("color:white; font-size:13px;")
        self.speed_value_label.setFixedWidth(38)
        bar.addWidget(self.speed_value_label)

        root.addWidget(controls)

    def _on_speed_changed(self, value: int):
        factor = value / 10.0
        self.speed_value_label.setText(f"{factor:.1f}x")
