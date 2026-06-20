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
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor, QLinearGradient

import config
from captions import load_captions

# ── Speaker identity ──────────────────────────────────────────────────────────
_SPEAKER_COLORS = {
    "S1": QColor("#4ecca3"),  # teal  — male
    "S2": QColor("#f5a623"),  # amber — female
}
_SPEAKER_NAMES = {
    "S1": "Speaker 1",
    "S2": "Speaker 2",
}


def _fmt_time(ms: int) -> str:
    """Format milliseconds as M:SS."""
    s = max(0, ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


# ── Caption display widget ────────────────────────────────────────────────────


class ScrollingCaptionWidget(QWidget):
    """
    Custom QPainter widget.

    Visual features:
      - Words are coloured by speaker (teal = S1, amber = S2)
      - Older lines fade in opacity so the newest line always pops
      - A gradient fades words out as they approach the left edge
      - Speaker label flashes on transition and fades over 1 s
      - An error overlay replaces all content when a file is missing
    """

    FADE_WIDTH = 60  # px — left-edge gradient width
    LEFT_MARGIN = 55  # px — wrap trigger (just inside the fade zone)
    BOTTOM_PADDING = 16  # px — gap between bottom line and widget edge
    WORD_SPACING = 14  # px — minimum gap between consecutive words

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1a1a2e;")

        self._font = QFont(config.CAPTION_FONT_FAMILY, config.CAPTION_FONT_SIZE)
        self._words = []  # [{"text", "x", "y", "spk"}, ...]
        self._base_y = 0.0
        self._line_h = 0
        self._ready = False

        # Speaker label fade
        self._spk_label = ""
        self._spk_color = QColor("#ffffff")
        self._spk_ticks = 0
        self._spk_total = 1

        # Error overlay — set by show_error(), cleared by clear_error()
        self._error_msg = ""

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

    def add_word(self, text: str, speaker: str = "S1"):
        if not self._ready:
            self._init_geometry()

        fm = QFontMetrics(self._font)

        # Wrap: leftmost bottom-line word has reached the fade zone
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

        self._words.append(
            {
                "text": text,
                "x": entry_x,
                "y": float(self._base_y),
                "spk": speaker,
            }
        )

    def show_speaker_label(self, speaker: str):
        self._spk_label = _SPEAKER_NAMES.get(speaker, speaker)
        self._spk_color = _SPEAKER_COLORS.get(speaker, QColor("#ffffff"))
        total = max(1, int(config.SPEAKER_LABEL_DISPLAY_DURATION * 1000 / 30))
        self._spk_ticks = total
        self._spk_total = total
        self.update()

    def tick(self, pixels: float):
        for w in self._words:
            w["x"] -= pixels
        self._words = [w for w in self._words if w["x"] > -400]
        if self._spk_ticks > 0:
            self._spk_ticks -= 1
        self.update()

    def clear_words(self):
        """Clear scrolling words. Does NOT clear the error overlay."""
        self._words.clear()
        self.update()

    def show_error(self, message: str):
        """Replace the display with a styled error message."""
        self._error_msg = message
        self._words.clear()
        self.update()

    def clear_error(self):
        self._error_msg = ""
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Error overlay ─────────────────────────────────────────────────────
        if self._error_msg:
            err_font = QFont(config.CAPTION_FONT_FAMILY, 14)
            painter.setFont(err_font)
            painter.setPen(QColor("#e94560"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self._error_msg,
            )
            painter.end()
            return

        # ── Speaker label (fades over SPEAKER_LABEL_DISPLAY_DURATION) ─────────
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
        fm = QFontMetrics(self._font)

        for w in self._words:
            x = int(w["x"])
            if x > self.width() + 50 or x < -400:
                continue

            # Older lines fade: bottom line = 1.0, each line above loses 0.28
            lines_above = (
                round((self._base_y - w["y"]) / self._line_h) if self._line_h else 0
            )
            line_opacity = max(0.25, 1.0 - lines_above * 0.28)

            word_color = QColor(
                _SPEAKER_COLORS.get(w.get("spk", "S1"), QColor("#ffffff"))
            )
            word_color.setAlphaF(line_opacity)
            painter.setPen(word_color)
            painter.drawText(x, int(w["y"]) + fm.ascent(), w["text"])

        # ── Left-edge gradient fade (drawn over words) ────────────────────────
        grad = QLinearGradient(0, 0, self.FADE_WIDTH, 0)
        grad.setColorAt(0.0, QColor(26, 26, 46, 255))
        grad.setColorAt(1.0, QColor(26, 26, 46, 0))
        painter.fillRect(0, 0, self.FADE_WIDTH, self.height(), grad)

        painter.end()


# ── Main window ───────────────────────────────────────────────────────────────


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
        self._current_speaker = None
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

        # Live time counter
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(
            "color:#aaaaaa; font-size:11px; font-family:'Segoe UI';"
        )
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFixedWidth(82)
        bar.addWidget(self.time_label)

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
        if not audio_path.exists():
            self.caption_display.show_error(
                "⚠   conversation_final.wav not found\n\n"
                "Run the render pipeline first to generate audio."
            )
            return

        self._player.setSource(QUrl.fromLocalFile(str(audio_path)))
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

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
            self.caption_display.show_error(
                "⚠   captions.json not found\n\n"
                "Run the render pipeline first to generate captions."
            )
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
        self.time_label.setText(f"0:00 / {_fmt_time(self._duration_ms)}")
        self._reset_captions()

    def _on_restart(self):
        self._reset_captions()
        self._player.setPosition(0)
        self._player.play()

    # ── Player signal handlers ────────────────────────────────────────────────

    def _on_duration_changed(self, duration_ms: int):
        self._duration_ms = duration_ms
        self.time_label.setText(f"0:00 / {_fmt_time(duration_ms)}")

    def _on_position_changed(self, position_ms: int):
        if self._user_seeking or self._duration_ms == 0:
            return
        self.progress.setValue(int(position_ms / self._duration_ms * 1000))
        self.time_label.setText(
            f"{_fmt_time(position_ms)} / {_fmt_time(self._duration_ms)}"
        )

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
            self._caption_timer.start()
        else:
            self.btn_play.setText("▶")
            self._caption_timer.stop()

    def _on_media_status_changed(self, status):
        """Handle end of audio cleanly."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.progress.setValue(1000)
            self.time_label.setText(
                f"{_fmt_time(self._duration_ms)} / {_fmt_time(self._duration_ms)}"
            )
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
            self._current_speaker = None  # force transition label on next word

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
            if speaker != self._current_speaker:
                self.caption_display.clear_words()
                self.caption_display.show_speaker_label(speaker)
                self._current_speaker = speaker
            self.caption_display.add_word(entry["word"], speaker)
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
