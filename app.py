from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from src.core.config import load_config
from src.ui.main_window import MainWindow


def main() -> int:
    root = Path(__file__).resolve().parent
    config = load_config(root / "config.yaml")

    app = QApplication(sys.argv)
    app.setApplicationName(config.app.name)

    window = MainWindow(root=root, config=config)
    window.resize(1280, 780)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
