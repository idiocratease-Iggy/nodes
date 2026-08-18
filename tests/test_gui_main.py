import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication

from gui_main import MainWindow, run_gui
from wizard.pages.page_physchem import PagePhysChem
from wizard.wizard_controller import WizardController
from models.multxeu_model import MultXeuModel


def test_info_panel_starts_hidden():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )

    assert not window.info_panel.isVisible()


def test_main_window_closes_cleanly():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )

    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()


def test_page_physchem_closes_plot_when_closed():
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    page = PagePhysChem(model)
    plot = MainWindow(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )
    page._plot_window = plot

    event = QCloseEvent()
    page.closeEvent(event)

    assert event.isAccepted()
    assert page._plot_window is None
    assert not plot.isVisible()


def test_wizard_closes_physchem_plot_when_terminated():
    app = QApplication.instance() or QApplication([])
    wizard = WizardController()
    plot = MainWindow(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )
    wizard.page_physchem._plot_window = plot

    event = QCloseEvent()
    wizard.closeEvent(event)

    assert event.isAccepted()
    assert wizard.page_physchem._plot_window is None


def test_plot_reuses_window_without_snapping_back_to_page():
    app = QApplication.instance() or QApplication([])
    first = run_gui(
        0.8,
        [(1.0, [0.8, 0.2]), (0.5, [0.6, 0.4])],
        [(1.0, 0.0), (0.5, 0.5)],
    )
    first.move(250, 300)
    first.show()

    second = run_gui(
        0.7,
        [
            (1.0, [0.8, 0.15, 0.05]),
            (0.7, [0.7, 0.20, 0.10]),
            (0.5, [0.6, 0.25, 0.15]),
        ],
        [(1.0, 0.0), (0.7, 0.5), (0.5, 0.8)],
    )

    assert second is first
    assert second.pos().x() == 250
    assert second.pos().y() == 300
    assert len(second.main_components) == 3
    assert len(second.impurity_components) == 0


def test_page_physchem_generates_updated_component_count():
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    page = PagePhysChem(model)
    page.spin_ncomp.setValue(4)
    first = page.generate_single_mixture()

    page.spin_ncomp.setValue(6)
    second = page.generate_single_mixture()

    assert len(first["components"]) == 4
    assert len(second["components"]) == 6
    assert abs(sum(component["Xc"] for component in second["components"]) - 1.0) < 1e-9


def test_page_physchem_generates_ten_component_mixture():
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    page = PagePhysChem(model)
    page.spin_ncomp.setValue(10)
    page.spin_main_level.setValue(80)

    mixture = page.generate_single_mixture()

    assert len(mixture["components"]) == 10
    assert abs(sum(component["Xc"] for component in mixture["components"]) - 1.0) < 1e-9
