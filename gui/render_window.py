"""Render progress window — turn/chunk progress, ETA, and cancel button."""

import queue
import threading
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
import multiprocessing

import config
from script_parser import parse_script


class RenderWindow(QMainWindow):
    """
    Launched by setup_window after the user clicks Generate.

    Runs render_conversation() in a background daemon thread and polls
    progress every 500ms via a QTimer. On completion, opens PlayerWindow
    and closes itself. On cancel, shows cancelled state.

    IPC primitives:
        _progress_queue  — multiprocessing.Queue: workers push turn events
        _cancel_event    — multiprocessing.Event: GUI sets on cancel
        _result_queue    — queue.SimpleQueue: render thread pushes final sentinel
    """

    def __init__(
        self,
        s1_script=None,
        s2_script=None,
        s1_ref=None,
        s2_ref=None,
        setup_ref=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("RealTimeConApp — Generating ...")
        self.resize(520, 360)
        self.setStyleSheet("background-color: #1a1a2e; color: white;")

        # ── IPC primitives ────────────────────────────────────────────────────
        self._progress_queue = multiprocessing.Queue()
        self._cancel_event = multiprocessing.Event()
        self._result_queue = queue.SimpleQueue()

        # ── State ─────────────────────────────────────────────────────────────
        self._turns_done = 0
        self._start_time = None
        self._cancelled = False
        self._setup_ref = setup_ref

        # ── Parse script (uses config defaults if paths not provided) ─────────
        self._chunks = parse_script(s1_path=s1_script, s2_path=s2_script)
        if s1_ref or s2_ref:
            for chunk in self._chunks:
                if s1_ref:
                    chunk["speaker1_ref"] = str(s1_ref)
                if s2_ref:
                    chunk["speaker2_ref"] = str(s2_ref)

        self._total_turns = sum(len(c["turns"]) for c in self._chunks)

        # ── Build UI ──────────────────────────────────────────────────────────
        self._build_ui()

        # ── 500ms poll timer ──────────────────────────────────────────────────
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

        # ── Start render in background thread ─────────────────────────────────
        self._start_time = time.time()
        self._render_thread = threading.Thread(target=self._render_worker, daemon=True)
        self._render_thread.start()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(36, 30, 36, 24)
        root.setSpacing(12)

        _head = (
            "color:#4ecca3; font-family:'Segoe UI'; font-size:16px; font-weight:bold;"
        )
        _lbl = "color:white;   font-family:'Segoe UI'; font-size:14px;"
        _dim = "color:#aaaaaa; font-family:'Segoe UI'; font-size:12px;"

        self._heading = QLabel("Generating conversation ...")
        self._heading.setStyleSheet(_head)
        root.addWidget(self._heading)

        root.addSpacing(4)

        self._turn_label = QLabel(f"Turn 0 of {self._total_turns}")
        self._turn_label.setStyleSheet(_lbl)
        root.addWidget(self._turn_label)

        self._chunk_label = QLabel(f"Chunk — of {len(self._chunks)}")
        self._chunk_label.setStyleSheet(_dim)
        root.addWidget(self._chunk_label)

        root.addSpacing(4)

        self._elapsed_label = QLabel("Elapsed:  0:00")
        self._elapsed_label.setStyleSheet(_dim)
        root.addWidget(self._elapsed_label)

        self._eta_label = QLabel("ETA:      estimating ...")
        self._eta_label.setStyleSheet(_dim)
        root.addWidget(self._eta_label)

        root.addSpacing(4)

        self._last_label = QLabel("Waiting for first turn ...")
        self._last_label.setStyleSheet(_dim)
        self._last_label.setWordWrap(True)
        root.addWidget(self._last_label)

        root.addSpacing(10)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, self._total_turns)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background:#0f3460; border-radius:4px; }"
            "QProgressBar::chunk { background:#4ecca3; border-radius:4px; }"
        )
        root.addWidget(self._progress_bar)

        self._progress_count = QLabel(f"0 / {self._total_turns} turns")
        self._progress_count.setStyleSheet(_dim)
        self._progress_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self._progress_count)

        root.addStretch()

        # Cancel button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedSize(110, 36)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background:#0f3460; color:white; border-radius:6px;"
            " font-size:13px; font-family:'Segoe UI'; }"
            "QPushButton:hover { background:#e94560; }"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # ── Render thread ─────────────────────────────────────────────────────────

    def _render_worker(self):
        """Daemon thread: calls render_conversation, pushes sentinel when done."""
        try:
            from orchestrator import render_conversation

            path = render_conversation(
                self._chunks,
                progress_queue=self._progress_queue,
                cancel_event=self._cancel_event,
            )
            self._result_queue.put({"path": str(path) if path else None})
        except Exception as exc:
            self._result_queue.put({"path": None, "error": str(exc)})

    # ── Poll ──────────────────────────────────────────────────────────────────

    def _poll(self):
        """Called every 500ms. Drains progress queue, checks for sentinel."""
        # Drain all available progress events
        while True:
            try:
                event = self._progress_queue.get_nowait()
                self._turns_done += 1
                self._on_progress(event)
            except Exception:
                break

        # Check for render completion sentinel
        try:
            result = self._result_queue.get_nowait()
            self._poll_timer.stop()
            error = result.get("error")
            final_path = result.get("path")
            if error:
                self._on_render_error(error)
            elif final_path:
                self._on_render_complete(Path(final_path))
            else:
                self._on_render_cancelled()
            return
        except Exception:
            pass  # no sentinel yet — keep polling

        # Update elapsed every tick regardless
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            self._elapsed_label.setText(f"Elapsed:  {self._fmt_time(elapsed)}")

    def _on_progress(self, event: dict):
        chunk_idx = event.get("chunk_idx", 0)
        speaker = event.get("speaker", "?")
        text = event.get("text", "")

        self._turn_label.setText(f"Turn {self._turns_done} of {self._total_turns}")
        self._chunk_label.setText(f"Chunk {chunk_idx + 1} of {len(self._chunks)}")
        self._last_label.setText(
            f"Last completed:  {speaker} — "
            f"\"{text[:55]}{'...' if len(text) > 55 else ''}\""
        )
        self._progress_bar.setValue(self._turns_done)
        self._progress_count.setText(f"{self._turns_done} / {self._total_turns} turns")

        # ETA: elapsed / turns_done * turns_remaining
        if self._start_time and self._turns_done > 0:
            elapsed = time.time() - self._start_time
            remaining = self._total_turns - self._turns_done
            eta_s = int(elapsed / self._turns_done * remaining)
            self._eta_label.setText(f"ETA:      ~{self._fmt_time(eta_s)}")

    # ── Completion / cancel ───────────────────────────────────────────────────

    def _on_render_complete(self, final_path: Path):
        self._heading.setText("✓  Render complete!")
        self._heading.setStyleSheet(
            "color:#4ecca3; font-family:'Segoe UI';"
            " font-size:16px; font-weight:bold;"
        )
        self._cancel_btn.setEnabled(False)
        self._last_label.setText(f"Output: {final_path.name}")
        self._eta_label.setText("")

        from gui.player_window import PlayerWindow

        self._player_win = PlayerWindow()
        self._player_win.show()
        self.close()

    def _on_render_cancelled(self):
        self._cancelled = True
        # If launched from SetupWindow, hand control back to it
        if self._setup_ref:
            self._setup_ref.show_render_cancelled()
            self.close()
            return
        # Standalone launch — show cancelled state for manual close
        self._heading.setText("Render cancelled.")
        self._heading.setStyleSheet(
            "color:#e94560; font-family:'Segoe UI';"
            " font-size:16px; font-weight:bold;"
        )
        self._eta_label.setText("")
        self._last_label.setText("No output was written.")
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText("Close")
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(lambda: self.close())

    def _on_render_error(self, error: str):
        self._heading.setText("Render error")
        self._heading.setStyleSheet(
            "color:#e94560; font-family:'Segoe UI';"
            " font-size:16px; font-weight:bold;"
        )
        self._last_label.setText(f"Error: {error[:120]}")
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText("Close")
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(lambda: self.close())

    def _on_cancel(self):
        self._cancel_event.set()
        self._cancel_btn.setEnabled(False)
        self._heading.setText("Cancelling — waiting for workers ...")
        self._heading.setStyleSheet(
            "color:#f5a623; font-family:'Segoe UI';"
            " font-size:16px; font-weight:bold;"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_time(seconds: int) -> str:
        s = max(0, seconds)
        return f"{s // 60}:{s % 60:02d}"

    def closeEvent(self, event):
        """Ensure workers are stopped if window is closed mid-render."""
        if not self._cancelled:
            self._cancel_event.set()
        self._poll_timer.stop()
        super().closeEvent(event)
