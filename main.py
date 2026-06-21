"""Entry point; wires everything together."""

import multiprocessing
import os
import sys

# Suppress console windows for all child processes (ffmpeg, workers) in frozen build.
# Must happen BEFORE freeze_support() so it applies inside worker processes too.
if getattr(sys, "frozen", False) and sys.platform == "win32":
    import subprocess as _sp

    _orig_Popen = _sp.Popen

    def _silent_Popen(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = _sp.CREATE_NO_WINDOW
        return _orig_Popen(*args, **kwargs)

    _sp.Popen = _silent_Popen

multiprocessing.freeze_support()  # MUST be before any other logic

# Prepend bundled ffmpeg to PATH so pydub finds it in the packaged build.
if getattr(sys, "frozen", False):
    _bin_dir = os.path.join(sys._MEIPASS, "bin")
else:
    _bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

# Ensure required runtime directories exist next to the exe
for _d in [
    os.path.join(os.path.dirname(sys.executable), "output"),
    os.path.join(os.path.dirname(sys.executable), "config"),
]:
    os.makedirs(_d, exist_ok=True)

import config


def output_files_exist() -> bool:
    """Return True only if both required output files exist."""
    return (config.OUTPUT_DIR / "conversation_final.wav").exists() and (
        config.OUTPUT_DIR / "captions.json"
    ).exists()


def _chatterbox_cached() -> bool:
    """Return True if Chatterbox model weights are already in HuggingFace cache."""
    import os
    from pathlib import Path

    snapshots = (
        Path(os.path.expanduser("~/.cache/huggingface/hub"))
        / "models--ResembleAI--chatterbox"
        / "snapshots"
    )
    return snapshots.exists() and any(snapshots.iterdir())


def main():
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    force_setup = "--setup" in sys.argv

    def launch_app():
        if not force_setup and output_files_exist():
            from gui.player_window import PlayerWindow

            window = PlayerWindow()
        else:
            from gui.setup_window import SetupWindow

            window = SetupWindow()
        window.show()

    if not _chatterbox_cached():
        from gui.first_run_window import FirstRunWindow

        window = FirstRunWindow(on_complete=launch_app)
        window.show()
    else:
        launch_app()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
