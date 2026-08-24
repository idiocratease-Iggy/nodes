import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QSpinBox, QCheckBox, QWidget, QSizePolicy, QTextEdit,
    QFileDialog, QRadioButton, QWizard, QToolButton, QMessageBox
)
from PyQt6.QtCore import Qt
from gui_main import run_gui

from single_mixture_solver import run_single_mixture

from models.multxeu_model import MultXeuModel
from mixture_generator import generate_mixture_set


from input_writer import Params, build_configuration_json, write_json

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Optional: Stacked plot popup (wired later)
# ---------------------------------------------------------
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class PlotPopup(QWidget):
    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Purification Profile")
        layout = QVBoxLayout(self)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        self.resize(900, 700)


# ---------------------------------------------------------
# Page 1 — PhysChem Generator
# ---------------------------------------------------------
class PagePhysChem(QWizardPage):
    @staticmethod
    def _make_help_button(summary: str, parent=None):
        button = QToolButton(parent)
        button.setText("?")
        button.setFixedSize(22, 22)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(summary)
        button.setWhatsThis(summary)
        button.setStyleSheet(
            """
            QToolButton {
                border: 1px solid rgba(132, 141, 155, 0.45);
                border-radius: 11px;
                background: transparent;
                color: rgba(58, 67, 81, 0.75);
                font-weight: bold;
                padding: 0;
            }
            QToolButton:hover {
                background: rgba(118, 144, 214, 0.10);
                border-color: rgba(87, 120, 210, 0.75);
                color: rgba(38, 55, 89, 0.95);
            }
            """
        )
        button.clicked.connect(
            lambda: QMessageBox.information(parent or button, "Help", summary)
        )
        return button

    def __init__(self, model: MultXeuModel):
        super().__init__()
        self.model = model
        self.setTitle("PhysChem Generator")
        self._plot_window_pos = None
        self._plot_window = None
        self.destroyed.connect(self._close_plot_window)

        main_layout = QVBoxLayout(self)

        # =====================================================
        # LAYER 1 — Explore: Single
        # =====================================================
        single_group = QGroupBox("Explore: Single")
        single_layout = QVBoxLayout()

        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("No. components in mixture (max. 10):"))
        self.spin_ncomp = QSpinBox()
        self.spin_ncomp.setRange(2, 10)
        self.spin_ncomp.setValue(self.model.n_components)
        self.spin_ncomp.valueChanged.connect(self._sync_max_addition_spin)
        comp_layout.addWidget(self.spin_ncomp)
        comp_layout.addWidget(
            self._make_help_button(
                "Number of components in the starting mixture(s)."
            )
        )
        single_layout.addLayout(comp_layout)

        main_layout2 = QHBoxLayout()
        main_layout2.addWidget(QLabel("Main component level [%]:"))
        self.spin_main_level = QSpinBox()
        self.spin_main_level.setRange(0, 100)
        self.spin_main_level.setValue(self.model.main_component_level)
        main_layout2.addWidget(self.spin_main_level)
        main_layout2.addWidget(
            self._make_help_button(
                "Sets a base value for a main component."
            )
        )
        single_layout.addLayout(main_layout2)

        plot_buttons_layout = QHBoxLayout()
        self.btn_generate_single_plot = QPushButton("Generate New Single Mixture Plot")
        self.btn_plot_loaded_data = QPushButton("Plot from Loaded Single Mixture Data")
        plot_buttons_layout.addWidget(self.btn_generate_single_plot)
        plot_buttons_layout.addWidget(self.btn_plot_loaded_data)
        single_layout.addLayout(plot_buttons_layout)

        self.btn_generate_single_plot.clicked.connect(self.generate_single_plot)
        self.btn_plot_loaded_data.clicked.connect(self.plot_loaded_data)

        json_layout = QHBoxLayout()
        self.btn_write_json = QPushButton("Save Current Single Mixture PhysChem Data")
        self.btn_read_json = QPushButton("Load Single Mixture PhysChem Data")
        json_layout.addWidget(self.btn_write_json)
        json_layout.addWidget(self.btn_read_json)
        single_layout.addLayout(json_layout)

        single_group.setLayout(single_layout)
        main_layout.addWidget(single_group)

        # =====================================================
        # LAYER 2 — Explore: Multi
        # =====================================================
        multi_group = QGroupBox("Explore: Multi")
        multi_layout = QVBoxLayout()

        self.model.loaded_json_path = getattr(self.model, "loaded_json_path", None)

        self.chk_auto = QCheckBox("Auto generate PhysChem data")
        self.chk_auto.setChecked(self.model.use_auto)
        self.chk_auto.stateChanged.connect(self._toggle_matrix_buttons)
        multi_layout.addWidget(self.chk_auto)

        slice_layout = QHBoxLayout()
        slice_layout.addWidget(QLabel("Maximum solvent volumes per mixture:"))
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(1, 10)
        self.spin_slices.setValue(self.model.max_slices)
        slice_layout.addWidget(self.spin_slices)
        slice_layout.addWidget(
            self._make_help_button(
                "Upper limit for different solvent volumes applied to each mixture (more solvents → more data → more accurate CRYSS prediction)."
            )
        )
        multi_layout.addLayout(slice_layout)

        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("Number of unique mixture:"))
        self.spin_systems = QSpinBox()
        self.spin_systems.setRange(1, 100)
        self.spin_systems.setValue(self.model.num_systems)
        self.spin_systems.valueChanged.connect(self._sync_model_state)
        sys_layout.addWidget(self.spin_systems)
        sys_layout.addWidget(
            self._make_help_button(
                "Number of unique mixture configurations to generate. This increases diversity of model data set."
            )
        )
        multi_layout.addLayout(sys_layout)

        addition_layout = QHBoxLayout()
        addition_layout.addWidget(QLabel("Maximum addition compounds:"))
        self.spin_addition = QSpinBox()
        max_addition_allowed = max(0, self.spin_ncomp.value() // 2)
        self.spin_addition.setRange(0, max_addition_allowed)
        self.spin_addition.setValue(min(getattr(self.model, "max_addition", 0), max_addition_allowed))
        addition_layout.addWidget(self.spin_addition)
        addition_layout.addWidget(
            self._make_help_button(
                "Think of this as allowing racemic compounds or related 1:1 addition compounds; distorts eutects."
            )
        )
        multi_layout.addLayout(addition_layout)

        variance_layout = QHBoxLayout()
        variance_layout.addWidget(QLabel("Stochastic Variance Factor [%]:"))
        self.spin_variance = QSpinBox()
        self.spin_variance.setRange(0, 100)
        self.spin_variance.setValue(self.model.modulation_percent)
        variance_layout.addWidget(self.spin_variance)
        variance_layout.addWidget(
            self._make_help_button(
                "This drives gaussian diversity of the base PhysChem parameters; percentage translates to 1σ."
            )
        )
        multi_layout.addLayout(variance_layout)

        tm_layout = QHBoxLayout()
        tm_layout.addWidget(QLabel("Base melting point:"))
        self.spin_tm_base = QSpinBox()
        self.spin_tm_base.setRange(0, 500)
        self.spin_tm_base.setValue(130)
        tm_layout.addWidget(self.spin_tm_base)
        tm_layout.addWidget(
            self._make_help_button(
                "Baseline melting point for PhysChem data set; ΔHf values are correlated and subject to gaussian modulation."
            )
        )
        multi_layout.addLayout(tm_layout)


        self.btn_generate_matrix = QPushButton("Generate PhysChem Data Matrix")
        multi_layout.addWidget(self.btn_generate_matrix)
        self.btn_generate_matrix.clicked.connect(self.generate_matrix_data)

        json2_layout = QHBoxLayout()
        self.btn_write_matrix_json = QPushButton("Save PhysChem Matrix (optional)")
        self.btn_read_matrix_json = QPushButton("Load PhysChem Matrix")
        self.btn_read_matrix_json.setVisible(not self.chk_auto.isChecked())
        self.btn_read_matrix_json.clicked.connect(self._open_json_matrix_dialog)
        json2_layout.addWidget(self.btn_write_matrix_json)
        json2_layout.addWidget(self.btn_read_matrix_json)
        multi_layout.addLayout(json2_layout)

        multi_group.setLayout(multi_layout)
        main_layout.addWidget(multi_group)

        self._toggle_matrix_buttons()

        self.current_mixture = None
        self.current_config = None
        self.generated_mixture = None
        self.loaded_mixture = None

        self.btn_write_json.clicked.connect(self.write_single_json)
        self.btn_read_json.clicked.connect(self.read_single_json)
        self.btn_write_matrix_json.clicked.connect(self.write_multi_json)

    def build_single_config(self):
        config = {
            "n_components": self.spin_ncomp.value(),
            "main_component_level": self.spin_main_level.value(),
        }

        generator_config = {
            "metadata": {
                "n_components": self.spin_ncomp.value(),
                "main_component_index": 0,
                "main_component_level": self.spin_main_level.value() / 100.0,
                "max_addition_compounds": 0,
                "stochastic_variance": 0.0,
                "tm_base": 130.0,
                "tm_sd_factor": 1.0,
                "dh_sd_factor": 1.0,
            },
            "physchem_rules": {
                "tm_base": 130.0,
                "tm_sd_factor": 1.0,
                "dh_sd_factor": 1.0,
            },
        }

        mixtures = generate_mixture_set(generator_config, num_systems=1)
        components = mixtures[0]["components"]

        config["Xc"] = [float(component["Xc"]) for component in components]
        config["Tm"] = [float(component["Tm"]) for component in components]
        config["DH"] = [float(component["DH"]) for component in components]
        config["modes"] = [str(component["mode"]) for component in components]
        return config
    
    def _sync_model_state(self):
        self.model.n_components = self.spin_ncomp.value()
        self.model.main_component_level = self.spin_main_level.value() / 100.0
        self.model.max_addition = self.spin_addition.value()
        self.model.use_auto = self.chk_auto.isChecked()
        self.model.num_unique_mixtures = self.spin_systems.value()
        self.model.num_systems = self.spin_systems.value()

    def generate_single_mixture(self):
        self._sync_model_state()

        params = Params(
            n_components=self.spin_ncomp.value(),
            main_component_index=0,
            main_component_level=self.spin_main_level.value() / 100.0,
            stochastic_variance=0.20,
            max_addition_compounds=0,
            tm_base=130.0,
            tm_sd_factor=1.0,
            dh_sd_factor=1.0,
            max_solvent_volumes=3,
        )

        config = build_configuration_json(params)
        mixtures = generate_mixture_set(config, num_systems=1)
        self.generated_mixture = mixtures[0]
        self.current_mixture = self.generated_mixture
        return self.generated_mixture

    def write_single_json(self):
        if self.current_mixture is None:
            self.generate_single_mixture()

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save single mixture JSON",
            str(DATA_DIR / "single_mixture.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return None

        with open(path, "w") as f:
            json.dump(self.current_mixture, f, indent=4)

        print(f"[Single] Wrote → {path}")
        return self.current_mixture

    def read_single_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load single mixture JSON",
            str(DATA_DIR),
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return None

        with open(path, "r") as f:
            self.loaded_mixture = json.load(f)
            self.current_mixture = self.loaded_mixture

        print("[Single] Loaded mixture.")
        return self.loaded_mixture


    def update_next_button_text(self):
        wizard = self.wizard()
        if wizard is None:
            return

        next_button = wizard.button(QWizard.WizardButton.NextButton)
        if next_button is None:
            return

        label = "Build Data (JSON) >" if getattr(self.model, "loaded_json_path", None) else "Build Data (auto) >"
        next_button.setText(label)

    def _refresh_wizard_navigation(self):
        wizard = self.wizard()
        if wizard is None:
            return

        self.update_next_button_text()
        if hasattr(wizard, "_sync_page_button_visibility"):
            wizard._sync_page_button_visibility(wizard.currentId())

    def _switch_to_generated_matrix(self):
        self.model.loaded_json_path = None
        self.model.physchem_matrix = getattr(self.model, "physchem_matrix", [])
        self._refresh_wizard_navigation()

    def _open_json_matrix_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PhysChem Matrix JSON",
            str(DATA_DIR),
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            self._switch_to_generated_matrix()
            return

        self.model.loaded_json_path = path
        try:
            with open(path, "r") as f:
                self.model.physchem_matrix = json.load(f)
        except Exception:
            self.model.physchem_matrix = []
            self.model.loaded_json_path = None
            self._switch_to_generated_matrix()
            raise

        print("DEBUG: JSON file loaded from button, loaded_json_path =", self.model.loaded_json_path)
        print("DEBUG: physchem_matrix set from JSON, len =", len(self.model.physchem_matrix))
        self._refresh_wizard_navigation()

    def write_multi_json(self):
        self._sync_model_state()

        if not getattr(self.model, "physchem_matrix", None):
            config = {
                "metadata": {
                    "n_components": self.spin_ncomp.value(),
                    "main_component_index": 0,
                    "main_component_level": self.spin_main_level.value() / 100.0,
                    "stochastic_variance": self.spin_variance.value() / 100.0,
                    "max_addition_compounds": self.spin_addition.value(),
                    "num_unique_mixtures": self.spin_systems.value(),
                },
                "physchem_rules": {
                    "tm_base": float(self.spin_tm_base.value()),
                    "tm_sd_factor": 1.0,
                    "dh_sd_factor": 1.0,
                },
                "slicing": {
                    "max_solvent_volumes": self.spin_slices.value(),
                },
            }
            self.model.physchem_matrix = generate_mixture_set(
                config,
                num_unique_mixtures=self.spin_systems.value(),
            )

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PhysChem Matrix JSON",
            str(DATA_DIR / "physchem_matrix.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return None

        write_json(path, self.model.physchem_matrix)
        print(f"[PhysChem] Wrote custom matrix → {path}")
        return path

    def generate_matrix_data(self):
        self._sync_model_state()

        config = {
            "metadata": {
                "n_components": self.spin_ncomp.value(),
                "main_component_index": 0,
                "main_component_level": self.spin_main_level.value() / 100.0,
                "stochastic_variance": self.spin_variance.value() / 100.0,
                "max_addition_compounds": self.spin_addition.value(),
                "num_unique_mixtures": self.spin_systems.value(),
            },
            "physchem_rules": {
                "tm_base": float(self.spin_tm_base.value()),
                "tm_sd_factor": 1.0,
                "dh_sd_factor": 1.0,
            },
            "slicing": {
                "max_solvent_volumes": self.spin_slices.value(),
            },
        }

        # Only generate the matrix list and store it on the model here.
        # Do not trigger the canonical-slice pipeline from this button.
        mixtures = generate_mixture_set(config, num_unique_mixtures=self.spin_systems.value())
        self.model.physchem_matrix = mixtures
        self.model.loaded_json_path = None
        print("DEBUG: PagePhysChem generate_matrix_data, len =", len(mixtures))
        print("DEBUG: PagePhysChem model.physchem_matrix set, len =", len(self.model.physchem_matrix))
        self._refresh_wizard_navigation()
        return mixtures

    def _sync_max_addition_spin(self):
        self._sync_model_state()
        max_allowed = max(0, self.spin_ncomp.value() // 2)
        self.spin_addition.setRange(0, max_allowed)
        if self.spin_addition.value() > max_allowed:
            self.spin_addition.setValue(max_allowed)
        self.model.max_addition = self.spin_addition.value()

    def _toggle_matrix_buttons(self):
        is_auto = self.chk_auto.isChecked()
        self.btn_read_matrix_json.setVisible(not is_auto)
        self.btn_write_matrix_json.setVisible(True)
        if is_auto:
            self.model.loaded_json_path = None
            self.model.physchem_matrix = getattr(self.model, "physchem_matrix", [])
        self._refresh_wizard_navigation()

    def _close_plot_window(self):
        if getattr(self, "_plot_window", None) is None:
            return

        try:
            self._plot_window.close()
        except Exception:
            pass

        try:
            self._plot_window.deleteLater()
        except Exception:
            pass

        self._plot_window = None
        self._plot_window_pos = None

    def closeEvent(self, event):
        self._close_plot_window()
        super().closeEvent(event)

    def generate_single_plot(self):
        self._sync_model_state()
        mixture = self.generate_single_mixture()
        Rmax, composition_profile, solvent_profile = run_single_mixture(mixture)
        self._plot_window = run_gui(Rmax, composition_profile, solvent_profile)

    def plot_loaded_data(self):
        if self.loaded_mixture is None:
            print("[Single] No loaded mixture available to plot.")
            return

        Rmax, composition_profile, solvent_profile = run_single_mixture(self.loaded_mixture)
        self._plot_window = run_gui(Rmax, composition_profile, solvent_profile)

    def show_plot(self):
        # Close any existing plot window before generating a new one
        if hasattr(self, "_plot_window") and self._plot_window is not None:
            self._plot_window.close()
            self._plot_window = None

        self.plot_widget.clear()

        self.plot_loaded_data()

    def run_multxeu_gui(self):
        from single_mixture_solver import run_single_mixture
        from gui_main import run_gui

        if self.current_mixture is None:
            self.generate_single_mixture()

        Rmax, composition_profile, solvent_profile = run_single_mixture(self.current_mixture)
        run_gui(Rmax, composition_profile, solvent_profile)
        
