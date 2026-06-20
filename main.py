"""Entry point; wires everything together."""

import multiprocessing

multiprocessing.freeze_support()  # MUST be first — before any other logic

import os
import sys

# Prepend bundled ffmpeg (bin/ffmpeg.exe) to PATH so pydub finds it in the
# packaged build. In dev mode, bin/ won't exist and system ffmpeg is used instead.
_bin_dir = os.path.join(os.path.dirname(sys.executable), "bin")
os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

import config


def output_files_exist() -> bool:
    """Return True only if both required output files exist."""
    return (config.OUTPUT_DIR / "conversation_final.wav").exists() and (
        config.OUTPUT_DIR / "captions.json"
    ).exists()


def main():
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    force_setup = "--setup" in sys.argv

    if not force_setup and output_files_exist():
        from gui.player_window import PlayerWindow

        window = PlayerWindow()
    else:
        from gui.setup_window import SetupWindow

        window = SetupWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
