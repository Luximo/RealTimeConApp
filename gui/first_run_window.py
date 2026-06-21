"""First-run window: detects missing HuggingFace model cache and downloads it."""

import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar


def _chatterbox_cache_exists() -> bool:
    """Return True if the Chatterbox model snapshots folder exists and is non-empty."""
    import os

    cache_root = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    snapshots = cache_root / "models--ResembleAI--chatterbox" / "snapshots"
    return snapshots.exists() and any(snapshots.iterdir())


class FirstRunWindow(QWidget):
    """Shown on first launch when model weights are not yet cached."""

    download_finished = pyqtSignal()  # emitted on success
    download_failed = pyqtSignal(str)  # emitted on error, carries message

    def __init__(self, on_complete):
        super().__init__()
        self._on_complete = on_complete  # callable — proceed to normal app flow
        self._thread = None
        self._setup_ui()
        self.download_finished.connect(self._handle_success)
        self.download_failed.connect(self._handle_failure)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("RealTimeConApp — First Launch")
        self.setFixedSize(480, 280)
        self.setStyleSheet("background-color: #1a1a2e; color: #e0e0e0;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("First Launch Setup")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4ecca3;")
        layout.addWidget(title)

        info = QLabel(
            "RealTimeConApp needs to download the voice model (~1.5 GB).\n"
            "This happens once. An internet connection is required.\n"
            "Subsequent launches will start immediately."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; color: #b0b0b0;")
        layout.addWidget(info)

        self._status = QLabel("Ready to download.")
        self._status.setStyleSheet("font-size: 12px; color: #e0e0e0;")
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate spinner
        self._bar.setVisible(False)
        self._bar.setStyleSheet("""
            QProgressBar { border: 1px solid #333; border-radius: 4px;
                           background: #0f3460; height: 14px; }
            QProgressBar::chunk { background: #4ecca3; border-radius: 4px; }
        """)
        layout.addWidget(self._bar)

        self._btn = QPushButton("Download Now")
        self._btn.setFixedHeight(40)
        self._btn.setStyleSheet("""
            QPushButton { background: #4ecca3; color: #1a1a2e; border-radius: 6px;
                          font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #38b28a; }
            QPushButton:disabled { background: #2a5a4a; color: #666; }
        """)
        self._btn.clicked.connect(self._start_download)
        layout.addWidget(self._btn)

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self):
        self._btn.setEnabled(False)
        self._bar.setVisible(True)
        self._status.setText("Downloading model weights — please wait...")
        self._thread = threading.Thread(target=self._download_worker, daemon=True)
        self._thread.start()

    def _download_worker(self):
        try:
            from chatterbox.tts import ChatterboxTTS
            import torch

            _orig_load = torch.load

            def _cpu_load(*args, **kwargs):
                kwargs.setdefault("map_location", "cpu")
                return _orig_load(*args, **kwargs)

            torch.load = _cpu_load

            ChatterboxTTS.from_pretrained(device="cpu")
            self.download_finished.emit()
        except Exception as exc:
            self.download_failed.emit(str(exc))

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _handle_success(self):
        self._bar.setVisible(False)
        self._status.setText("Download complete! Starting app...")
        # Brief pause so the user sees the success message
        QTimer.singleShot(1200, self._proceed)

    def _handle_failure(self, message: str):
        self._bar.setVisible(False)
        self._status.setText(f"Download failed: {message}")
        self._status.setStyleSheet("font-size: 12px; color: #e05555;")
        self._btn.setEnabled(True)
        self._btn.setText("Retry")

    def _proceed(self):
        self.close()
        self._on_complete()
