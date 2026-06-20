"""Entry point; wires everything together."""

import sys
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
