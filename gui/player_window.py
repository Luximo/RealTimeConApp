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
from PyQt6.QtCore import Qt, QUrl, QTimer

import config
from captions import load_captions


class CaptionDisplay(QWidget):
    """Caption display area — dark background with a centred word label.
    Day 4 will replace the label with the full scrolling painter widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1a1a2e;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.word_label = QLabel("")
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet(
            f"color: white;"
            f" font-size: {config.CAPTION_FONT_SIZE}pt;"
            f" font-family: '{config.CAPTION_FONT_FAMILY}';"
            f" background: transparent;"
        )
        layout.addWidget(self.word_label)


class PlayerWindow(QMainWindow):
    """Main playback window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealTimeConApp")
        self.resize(900, 520)
        self._duration_ms = 0
        self._user_seeking = False
        self._captions = []
        self._word_idx = 0
        self._build_ui()
        self._setup_player()
        self._setup_caption_timer()
        self._load_captions()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.caption_display = CaptionDisplay()
        root.addWidget(self.caption_display)

        controls = QWidget()
        controls.setStyleSheet("background-color: #16213e;")
        controls.setFixedHeight(70)
        bar = QHBoxLayout(controls)
        bar.setContentsMargins(12, 8, 12, 8)
        bar.setSpacing(10)

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

        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_play.clicked.connect(self._on_play_pause)
        self.btn_stop.clicked.connect(self._on_stop)
        self.progress.sliderPressed.connect(self._on_seek_start)
        self.progress.sliderReleased.connect(self._on_seek_end)

    def _setup_player(self):
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)

        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        audio_path = config.OUTPUT_DIR / "conversation_final.wav"
        self._player.setSource(QUrl.fromLocalFile(str(audio_path)))

        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    def _setup_caption_timer(self):
        self._caption_timer = QTimer()
        self._caption_timer.setInterval(30)  # ms
        self._caption_timer.timeout.connect(self._on_caption_tick)

    def _load_captions(self):
        try:
            self._captions = load_captions()
            print(f"[captions] loaded {len(self._captions)} words")
        except FileNotFoundError:
            self._captions = []
            print("[captions] captions.json not found — captions disabled")

    # ── Transport slots ───────────────────────────────────────────────────────

    def _on_play_pause(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_stop(self):
        self._player.stop()
        self.progress.setValue(0)
        self._reset_captions()

    def _on_restart(self):
        self._reset_captions()
        self._player.setPosition(0)
        self._player.play()

    # ── Player signal handlers ────────────────────────────────────────────────

    def _on_duration_changed(self, duration_ms: int):
        self._duration_ms = duration_ms

    def _on_position_changed(self, position_ms: int):
        if self._user_seeking or self._duration_ms == 0:
            return
        slider_val = int(position_ms / self._duration_ms * 1000)
        self.progress.setValue(slider_val)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
            self._caption_timer.start()
        else:
            self.btn_play.setText("▶")
            self._caption_timer.stop()

    # ── Progress slider seeking ───────────────────────────────────────────────

    def _on_seek_start(self):
        self._user_seeking = True

    def _on_seek_end(self):
        self._user_seeking = False
        if self._duration_ms > 0:
            target_ms = int(self.progress.value() / 1000 * self._duration_ms)
            self._player.setPosition(target_ms)
            # Rewind word pointer to match the seek target
            target_s = target_ms / 1000.0
            self._word_idx = 0
            while (
                self._word_idx < len(self._captions)
                and self._captions[self._word_idx]["start"] <= target_s
            ):
                self._word_idx += 1

    # ── Caption timer tick ────────────────────────────────────────────────────

    def _on_caption_tick(self):
        if not self._captions:
            return
        pos_s = self._player.position() / 1000.0

        # Advance past all words whose start time has been reached
        while (
            self._word_idx < len(self._captions)
            and self._captions[self._word_idx]["start"] <= pos_s
        ):
            self._word_idx += 1

        # The active word is the last one we passed
        display_idx = self._word_idx - 1
        if display_idx >= 0:
            self.caption_display.word_label.setText(self._captions[display_idx]["word"])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reset_captions(self):
        self._word_idx = 0
        self.caption_display.word_label.setText("")

    # ── Speed slider ─────────────────────────────────────────────────────────

    def _on_speed_changed(self, value: int):
        factor = value / 10.0
        self.speed_value_label.setText(f"{factor:.1f}x")
        self._player.setPlaybackRate(factor)
