import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from gui_main import MainWindow


def test_info_panel_starts_hidden():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )

    assert not window.info_panel.isVisible()
