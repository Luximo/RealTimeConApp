"""Setup window — file picker UI: script files, voice clips, render button."""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
)
from PyQt6.QtCore import Qt

import config


class _FilePickerRow(QWidget):
    """One labelled path field + Browse button."""

    def __init__(self, label: str, filter_str: str, on_change=None, parent=None):
        super().__init__(parent)
        self._filter = filter_str
        self._on_change = on_change

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(140)
        lbl.setStyleSheet("color:#aaaaaa; font-family:'Segoe UI'; font-size:12px;")
        row.addWidget(lbl)

        self._edit = QLineEdit()
        self._edit.setReadOnly(True)
        self._edit.setPlaceholderText("No file selected")
        self._edit.setStyleSheet(
            "QLineEdit { background:#0f3460; color:white; border:none;"
            " border-radius:4px; padding:4px 8px;"
            " font-family:'Segoe UI'; font-size:12px; }"
        )
        row.addWidget(self._edit, stretch=1)

        btn = QPushButton("📂")
        btn.setFixedSize(32, 28)
        btn.setStyleSheet(
            "QPushButton { background:#0f3460; color:white; border-radius:4px;"
            " font-size:14px; }"
            "QPushButton:hover { background:#4ecca3; color:#1a1a2e; }"
        )
        btn.clicked.connect(self._browse)
        row.addWidget(btn)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select file", str(config.BASE_DIR), self._filter
        )
        if path:
            self._edit.setText(path)
            if self._on_change:
                self._on_change()

    def path(self) -> str:
        return self._edit.text().strip()

    def set_path(self, p: str):
        self._edit.setText(str(p))


class SetupWindow(QMainWindow):
    """
    Entry point when no output files exist (or --setup flag used).

    Four file pickers → validate → launch RenderWindow.
    Paths persist to config/last_session.json between runs.
    'Open Last Render' active only when both output files exist.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RealTimeConApp — Setup")
        self.resize(640, 380)
        self.setStyleSheet("background-color: #1a1a2e; color: white;")

        self._build_ui()
        self._load_session()
        self._refresh_open_button()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(36, 30, 36, 24)
        root.setSpacing(10)

        title = QLabel("RealTimeConApp")
        title.setStyleSheet(
            "color:#4ecca3; font-family:'Segoe UI';"
            " font-size:20px; font-weight:bold;"
        )
        root.addWidget(title)

        sub = QLabel("Select script files and voice clips, then generate.")
        sub.setStyleSheet("color:#aaaaaa; font-family:'Segoe UI'; font-size:12px;")
        root.addWidget(sub)

        root.addSpacing(10)

        # File pickers
        self._s1_script = _FilePickerRow(
            "Speaker 1 Script:",
            "Text files (*.txt);;All files (*)",
            on_change=self._on_path_changed,
        )
        self._s2_script = _FilePickerRow(
            "Speaker 2 Script:",
            "Text files (*.txt);;All files (*)",
            on_change=self._on_path_changed,
        )
        self._s1_ref = _FilePickerRow(
            "Speaker 1 Voice:",
            "WAV files (*.wav);;All files (*)",
            on_change=self._on_path_changed,
        )
        self._s2_ref = _FilePickerRow(
            "Speaker 2 Voice:",
            "WAV files (*.wav);;All files (*)",
            on_change=self._on_path_changed,
        )

        for picker in (self._s1_script, self._s2_script, self._s1_ref, self._s2_ref):
            root.addWidget(picker)

        root.addSpacing(6)

        # Status / validation label
        self._status = QLabel("")
        self._status.setStyleSheet(
            "color:#e94560; font-family:'Segoe UI'; font-size:12px;"
        )
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()

        self._open_btn = QPushButton("▶  Open Last Render")
        self._open_btn.setFixedHeight(36)
        self._open_btn.setStyleSheet(
            "QPushButton         { background:#0f3460; color:#555577;"
            " border-radius:6px; font-size:13px; font-family:'Segoe UI'; }"
            "QPushButton:enabled { color:white; }"
            "QPushButton:enabled:hover { background:#4ecca3; color:#1a1a2e; }"
        )
        self._open_btn.clicked.connect(self._on_open_last)
        btn_row.addWidget(self._open_btn)

        btn_row.addSpacing(12)

        self._gen_btn = QPushButton("Generate Conversation")
        self._gen_btn.setFixedHeight(36)
        self._gen_btn.setStyleSheet(
            "QPushButton { background:#4ecca3; color:#1a1a2e; border-radius:6px;"
            " font-size:13px; font-weight:bold; font-family:'Segoe UI'; }"
            "QPushButton:hover { background:#38b089; }"
        )
        self._gen_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self._gen_btn)

        root.addLayout(btn_row)

    # ── Session persistence ───────────────────────────────────────────────────

    def _load_session(self):
        """Pre-fill pickers from last_session.json; warn on stale paths."""
        try:
            data = json.loads(config.SESSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            # No session yet — use config defaults
            self._s1_script.set_path(config.SPEAKER1_SCRIPT)
            self._s2_script.set_path(config.SPEAKER2_SCRIPT)
            self._s1_ref.set_path(config.SPEAKER1_REF)
            self._s2_ref.set_path(config.SPEAKER2_REF)
            return

        mapping = {
            "s1_script": self._s1_script,
            "s2_script": self._s2_script,
            "s1_ref": self._s1_ref,
            "s2_ref": self._s2_ref,
        }
        stale = []
        for key, widget in mapping.items():
            p = data.get(key, "")
            if p and Path(p).exists():
                widget.set_path(p)
            elif p:
                stale.append(Path(p).name)

        if stale:
            self._set_status(
                f"⚠  Previously saved path(s) no longer found: " f"{', '.join(stale)}",
                "#f5a623",
            )

    def _save_session(self):
        """Write current paths to config/last_session.json."""
        try:
            config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "s1_script": self._s1_script.path(),
                "s2_script": self._s2_script.path(),
                "s1_ref": self._s1_ref.path(),
                "s2_ref": self._s2_ref.path(),
            }
            config.SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[setup] Could not save session: {exc}")

    def _on_path_changed(self):
        self._save_session()
        self._set_status("", "#e94560")
        self._refresh_open_button()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#e94560"):
        self._status.setText(text)
        self._status.setStyleSheet(
            f"color:{color}; font-family:'Segoe UI'; font-size:12px;"
        )

    def _refresh_open_button(self):
        both = (config.OUTPUT_DIR / "conversation_final.wav").exists() and (
            config.OUTPUT_DIR / "captions.json"
        ).exists()
        self._open_btn.setEnabled(both)

    def _validate(self) -> str | None:
        """Return an error string if any picker is invalid, else None."""
        checks = [
            ("Speaker 1 Script", self._s1_script.path()),
            ("Speaker 2 Script", self._s2_script.path()),
            ("Speaker 1 Voice", self._s1_ref.path()),
            ("Speaker 2 Voice", self._s2_ref.path()),
        ]
        for label, p in checks:
            if not p:
                return f"{label}: no file selected."
            path = Path(p)
            if not path.exists():
                return f"{label}: file not found — {path.name}"
            if path.stat().st_size == 0:
                return f"{label}: file is empty — {path.name}"
        return None

    # ── Public (called by RenderWindow on cancel) ─────────────────────────────

    def show_render_cancelled(self):
        """Called by RenderWindow when the user cancels a render."""
        self._set_status("Render cancelled — choose files and try again.", "#f5a623")
        self.show()

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_open_last(self):
        from gui.player_window import PlayerWindow

        self._player_win = PlayerWindow()
        self._player_win.show()
        self.hide()

    def _on_generate(self):
        error = self._validate()
        if error:
            self._set_status(f"⚠  {error}")
            return

        self._set_status("")
        self.hide()

        from gui.render_window import RenderWindow

        self._render_win = RenderWindow(
            s1_script=self._s1_script.path(),
            s2_script=self._s2_script.path(),
            s1_ref=self._s1_ref.path(),
            s2_ref=self._s2_ref.path(),
            setup_ref=self,
        )
        self._render_win.show()
