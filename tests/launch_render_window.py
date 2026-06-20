"""
Day 4 manual test — launches RenderWindow directly for visual verification.

Tests to perform:
  1. Window opens, shows correct turn/chunk counts, elapsed timer ticks
  2. Click Cancel after model loading — UI shows "Render cancelled",
     no new chunk_*.wav files appear in output/

IMPORTANT: if __name__ guard is mandatory on Windows.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from gui.render_window import RenderWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RenderWindow()  # uses config default script + ref clip paths
    window.show()
    sys.exit(app.exec())
