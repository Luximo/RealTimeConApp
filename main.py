"""Entry point; wires everything together."""

import sys
from PyQt6.QtWidgets import QApplication
from gui.player_window import PlayerWindow


def main():
    app = QApplication(sys.argv)
    window = PlayerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
