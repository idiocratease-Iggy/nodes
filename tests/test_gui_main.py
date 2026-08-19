import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QWizard

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


def test_wizard_hides_navigation_until_matrix_or_json_ready():
    app = QApplication.instance() or QApplication([])
    wizard = WizardController()
    next_button = wizard.button(QWizard.WizardButton.NextButton)
    back_button = wizard.button(QWizard.WizardButton.BackButton)

    assert next_button is not None
    assert back_button is not None
    assert not next_button.isVisible()
    assert not back_button.isVisible()

    wizard.model.loaded_json_path = "data/test.json"
    wizard._sync_page_button_visibility()

    assert next_button.isVisible()
    assert back_button.isVisible()
    assert wizard.buttonText(QWizard.WizardButton.NextButton) == "Build Data (JSON) >"


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
    assert len(second.main_components) == 1
    assert second.main_components == [0]
    assert len(second.impurity_components) == 2


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


def test_plot_selection_uses_dynamic_purified_component_for_degenerate_profiles():
    app = QApplication.instance() or QApplication([])
    profile = [
        (1.0, [0.10, 0.20, 0.70]),
        (0.85, [0.05, 0.15, 0.80]),
        (0.60, [0.02, 0.08, 0.90]),
        (0.00, [0.00, 0.00, 1.00]),
    ]

    window = MainWindow(0.6, profile, [(1.0, 0.0), (0.85, 0.5), (0.60, 0.8), (0.0, 1.0)])

    assert window.purified_component_index == 2
    assert window.main_components == [2]
    assert window.impurity_components == [0, 1]


def test_plot_selection_uses_final_summary_row_for_multiple_dominant_components():
    app = QApplication.instance() or QApplication([])
    profile = [
        (1.0, [0.10, 0.10, 0.10, 0.35, 0.35]),
        (0.75, [0.08, 0.08, 0.08, 0.38, 0.38]),
        (0.50, [0.06, 0.06, 0.06, 0.41, 0.41]),
        (0.10, [0.05, 0.05, 0.05, 0.42, 0.42]),
        (0.00, [1.0, 0.0, 0.0, 0.0, 0.0]),
    ]

    window = MainWindow(0.1, profile, [(1.0, 0.0), (0.75, 0.5), (0.50, 0.8), (0.10, 1.2), (0.00, 1.6)])

    assert window.main_components == [3, 4]
    assert window.impurity_components == [0, 1, 2]
    assert set(window.main_components).isdisjoint(window.impurity_components)


def test_plot_selection_keeps_near_equal_product_components_together():
    app = QApplication.instance() or QApplication([])
    profile = [
        (1.0, [0.01, 0.48, 0.50, 0.01]),
        (0.75, [0.02, 0.49, 0.49, 0.00]),
        (0.50, [0.03, 0.50, 0.47, 0.00]),
        (0.00, [0.00, 0.50, 0.50, 0.00]),
    ]

    window = MainWindow(0.5, profile, [(1.0, 0.0), (0.75, 0.5), (0.50, 0.8), (0.00, 1.0)])

    assert window.main_components == [1, 2]
    assert window.impurity_components == [0, 3]
    assert set(window.main_components).isdisjoint(window.impurity_components)


def test_plot_selection_uses_rmax_row_for_real_two_pair_profile():
    app = QApplication.instance() or QApplication([])
    with open("data/single_mixture-7 Comp 2 pair ent V2.json", "r") as f:
        mixture = __import__("json").load(f)

    from single_mixture_solver import run_single_mixture
    Rmax, composition_profile, solvent_profile = run_single_mixture(mixture)

    window = MainWindow(Rmax, composition_profile, solvent_profile)

    assert window.main_components == [3, 4]
    assert set([0, 1, 2, 5, 6]).issubset(set(window.impurity_components))
    assert set(window.main_components).isdisjoint(window.impurity_components)


def test_degnerate_main_pair_stays_constant_below_rmax():
    app = QApplication.instance() or QApplication([])
    profile = [
        (1.0, [0.01, 0.01, 0.48, 0.50]),
        (0.95, [0.01, 0.01, 0.49, 0.49]),
        (0.92, [0.01, 0.01, 0.50, 0.48]),
        (0.80, [0.00, 0.00, 0.00, 0.00]),
        (0.00, [0.00, 0.00, 0.00, 0.00]),
    ]

    window = MainWindow(0.92, profile, [(1.0, 0.0), (0.95, 0.1), (0.92, 0.2), (0.80, 1.0), (0.00, 1.5)])
    window.plot_profiles()

    data_items = window.comp1_plot.plot_widget.listDataItems()
    assert len(data_items) >= 2
    for item in data_items[:2]:
        x_data, y_data = item.getData()
        assert any(x <= 0.92 for x in x_data)
        if any(x <= 0.92 for x in x_data):
            assert max(y_data) <= 50.5
            assert min(y_data) >= 47.5
