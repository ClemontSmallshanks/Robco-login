#!/usr/bin/env python3
"""Launch the RobCo greeter in development mode with mock auth."""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from app.config.settings import load_config
from app.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    config = load_config(['--development', '--mock-auth'])
    window = MainWindow(config)
    window.resize(1280, 800)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
