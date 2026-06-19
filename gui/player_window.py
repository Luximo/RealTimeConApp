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
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl

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
        self._duration_ms = 0  # set once durationChanged fires
        self._user_seeking = False  # True while user drags the progress slider
        self._build_ui()
        self._setup_player()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Caption display area
        self.caption_display = CaptionDisplay()
        root.addWidget(self.caption_display)

        # Controls bar
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

        # Wire transport buttons
        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_play.clicked.connect(self._on_play_pause)
        self.btn_stop.clicked.connect(self._on_stop)

        # Wire progress slider seeking
        self.progress.sliderPressed.connect(self._on_seek_start)
        self.progress.sliderReleased.connect(self._on_seek_end)

    def _setup_player(self):
        """Initialise QMediaPlayer and point it at conversation_final.wav."""
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)

        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        audio_path = config.OUTPUT_DIR / "conversation_final.wav"
        self._player.setSource(QUrl.fromLocalFile(str(audio_path)))

        # Connect player signals
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    # ── Transport slots ───────────────────────────────────────────────────────

    def _on_play_pause(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_stop(self):
        self._player.stop()
        self.progress.setValue(0)

    def _on_restart(self):
        self._player.setPosition(0)
        self._player.play()

    # ── Player signal handlers ────────────────────────────────────────────────

    def _on_duration_changed(self, duration_ms: int):
        """Called once when media loads and duration becomes known."""
        self._duration_ms = duration_ms

    def _on_position_changed(self, position_ms: int):
        """Called ~every 100ms by QMediaPlayer during playback."""
        if self._user_seeking or self._duration_ms == 0:
            return
        slider_val = int(position_ms / self._duration_ms * 1000)
        self.progress.setValue(slider_val)

    def _on_state_changed(self, state):
        """Flip play/pause button icon to match actual player state."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    # ── Progress slider seeking ───────────────────────────────────────────────

    def _on_seek_start(self):
        self._user_seeking = True

    def _on_seek_end(self):
        self._user_seeking = False
        if self._duration_ms > 0:
            target_ms = int(self.progress.value() / 1000 * self._duration_ms)
            self._player.setPosition(target_ms)

    # ── Speed slider ─────────────────────────────────────────────────────────

    def _on_speed_changed(self, value: int):
        factor = value / 10.0
        self.speed_value_label.setText(f"{factor:.1f}x")
        self._player.setPlaybackRate(factor)
