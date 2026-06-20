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
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor

import config
from captions import load_captions

# Speaker colours — used for the fading label on transition
_SPEAKER_COLORS = {
    "S1": QColor("#4ecca3"),  # teal  — male
    "S2": QColor("#f5a623"),  # amber — female
}
_SPEAKER_NAMES = {
    "S1": "Speaker 1",
    "S2": "Speaker 2",
}


class ScrollingCaptionWidget(QWidget):
    """
    Custom QPainter widget — words enter from the right, scroll left,
    wrap to a new bottom line when the current line fills, older lines
    scroll up and off the top.

    On speaker transition: all words are cleared and a fading speaker
    label appears at the top of the display for SPEAKER_LABEL_DISPLAY_DURATION.
    """

    LEFT_MARGIN = 20  # px — leftmost word reaching here triggers a line wrap
    BOTTOM_PADDING = 16  # px — gap between bottom line and widget edge
    WORD_SPACING = 14  # px — minimum gap between consecutive words

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1a1a2e;")

        self._font = QFont(config.CAPTION_FONT_FAMILY, config.CAPTION_FONT_SIZE)
        self._words = []
        self._base_y = 0.0
        self._line_h = 0
        self._ready = False

        # Speaker label fade state
        self._spk_label = ""
        self._spk_color = QColor("#ffffff")
        self._spk_ticks = 0  # ticks remaining
        self._spk_total = 1  # total ticks (avoid divide-by-zero)

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _init_geometry(self):
        fm = QFontMetrics(self._font)
        self._line_h = fm.height() + 10
        self._base_y = float(self.height() - self._line_h - self.BOTTOM_PADDING)
        self._ready = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._init_geometry()

    # ── Public API ────────────────────────────────────────────────────────────

    def add_word(self, text: str):
        if not self._ready:
            self._init_geometry()

        fm = QFontMetrics(self._font)

        # Wrap check: if leftmost word on bottom line has hit the left margin, wrap
        bottom_words = [w for w in self._words if abs(w["y"] - self._base_y) < 1]
        if bottom_words and min(w["x"] for w in bottom_words) < self.LEFT_MARGIN:
            for w in self._words:
                w["y"] -= self._line_h
            self._words = [w for w in self._words if w["y"] > -self._line_h]
            bottom_words = []

        # Entry x: after rightmost word on current line, never left of right edge
        if bottom_words:
            last = max(bottom_words, key=lambda w: w["x"])
            last_w = fm.horizontalAdvance(last["text"])
            entry_x = max(
                last["x"] + last_w + self.WORD_SPACING,
                self.width() + self.WORD_SPACING,
            )
        else:
            entry_x = float(self.width() + self.WORD_SPACING)

        self._words.append({"text": text, "x": entry_x, "y": float(self._base_y)})

    def show_speaker_label(self, speaker: str):
        """Flash a fading speaker label at the top of the display."""
        self._spk_label = _SPEAKER_NAMES.get(speaker, speaker)
        self._spk_color = _SPEAKER_COLORS.get(speaker, QColor("#ffffff"))
        total = max(1, int(config.SPEAKER_LABEL_DISPLAY_DURATION * 1000 / 30))
        self._spk_ticks = total
        self._spk_total = total
        self.update()

    def tick(self, pixels: float):
        """Shift every word left by pixels. Called every 30 ms."""
        for w in self._words:
            w["x"] -= pixels
        self._words = [w for w in self._words if w["x"] > -400]

        # Countdown speaker label fade
        if self._spk_ticks > 0:
            self._spk_ticks -= 1

        self.update()

    def clear_words(self):
        """Remove all words — speaker transition or stop/restart."""
        self._words.clear()
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Speaker label (fades out over SPEAKER_LABEL_DISPLAY_DURATION) ────
        if self._spk_ticks > 0 and self._spk_label:
            opacity = self._spk_ticks / self._spk_total
            lbl_color = QColor(self._spk_color)
            lbl_color.setAlphaF(opacity)
            painter.setPen(lbl_color)
            lbl_font = QFont(config.CAPTION_FONT_FAMILY, config.CAPTION_FONT_SIZE - 6)
            lbl_font.setBold(True)
            painter.setFont(lbl_font)
            painter.drawText(
                self.rect().adjusted(0, 16, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self._spk_label,
            )

        # ── Scrolling words ───────────────────────────────────────────────────
        painter.setFont(self._font)
        painter.setPen(QColor("#ffffff"))
        fm = QFontMetrics(self._font)
        for w in self._words:
            x = int(w["x"])
            if x > self.width() + 50 or x < -400:
                continue
            painter.drawText(x, int(w["y"]) + fm.ascent(), w["text"])

        painter.end()


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
        self._speed_factor = config.DEFAULT_SPEED
        self._current_speaker = None  # tracks last seen speaker label
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

        self.caption_display = ScrollingCaptionWidget()
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
        self._caption_timer.setInterval(30)
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
        self.progress.setValue(int(position_ms / self._duration_ms * 1000))

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
            target_s = target_ms / 1000.0
            self._word_idx = 0
            while (
                self._word_idx < len(self._captions)
                and self._captions[self._word_idx]["start"] <= target_s
            ):
                self._word_idx += 1
            # Reset speaker tracking so the next word correctly fires a transition
            self._current_speaker = None

    # ── Caption timer tick ────────────────────────────────────────────────────

    def _on_caption_tick(self):
        pixels = config.SCROLL_SPEED_BASE * self._speed_factor * 0.030
        self.caption_display.tick(pixels)

        if not self._captions:
            return

        pos_s = self._player.position() / 1000.0
        while (
            self._word_idx < len(self._captions)
            and self._captions[self._word_idx]["start"] <= pos_s
        ):

            entry = self._captions[self._word_idx]
            speaker = entry["speaker"]

            # Speaker transition — clear display and flash label
            if speaker != self._current_speaker:
                self.caption_display.clear_words()
                self.caption_display.show_speaker_label(speaker)
                self._current_speaker = speaker

            self.caption_display.add_word(entry["word"])
            self._word_idx += 1

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reset_captions(self):
        self._word_idx = 0
        self._current_speaker = None
        self.caption_display.clear_words()

    # ── Speed slider ─────────────────────────────────────────────────────────

    def _on_speed_changed(self, value: int):
        self._speed_factor = value / 10.0
        self.speed_value_label.setText(f"{self._speed_factor:.1f}x")
        self._player.setPlaybackRate(self._speed_factor)
