"""Application bootstrap — creates the QApplication and MainWindow."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.config.settings import load_config
from app.ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Entry point for the RobCo greeter application."""
    config = load_config(argv)

    app = QApplication(sys.argv)
    app.setApplicationName("RobCo Industries Terminal")
    app.setApplicationDisplayName("ROBCO INDUSTRIES (TM) TERMLINK")

    # Ensure custom font is available
    import os
    import urllib.request
    from PyQt6.QtGui import QFontDatabase
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_dir = os.path.join(project_root, 'app', 'assets', 'fonts')
    font_path = os.path.join(font_dir, 'ShareTechMono-Regular.ttf')
    
    if not os.path.exists(font_path):
        print("Downloading Share Tech Mono font...")
        os.makedirs(font_dir, exist_ok=True)
        # Direct raw link to the ttf file
        url = 'https://raw.githubusercontent.com/google/fonts/main/ofl/sharetechmono/ShareTechMono-Regular.ttf'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(font_path, 'wb') as f:
                    f.write(response.read())
        except Exception as e:
            print(f"Failed to download font: {e}")

    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)

    from app.ui.theme import set_active_scheme
    set_active_scheme(config.display.scheme)

    window = MainWindow(config)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
