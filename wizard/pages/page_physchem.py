import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QSpinBox, QCheckBox, QWidget, QSizePolicy, QTextEdit
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
    def __init__(self, model: MultXeuModel):
        super().__init__()
        self.model = model
        self.setTitle("PhysChem Generator")

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
        single_layout.addLayout(comp_layout)

        main_layout2 = QHBoxLayout()
        main_layout2.addWidget(QLabel("Main component level [%]:"))
        self.spin_main_level = QSpinBox()
        self.spin_main_level.setRange(0, 100)
        self.spin_main_level.setValue(self.model.main_component_level)
        main_layout2.addWidget(self.spin_main_level)
        single_layout.addLayout(main_layout2)

        self.btn_plot = QPushButton("Plot purification profile")
        single_layout.addWidget(self.btn_plot)
        self.btn_plot.clicked.connect(self.show_plot)

        json_layout = QHBoxLayout()
        self.btn_write_json = QPushButton("Save JSON single mixture data file")
        self.btn_read_json = QPushButton("Load JSON single mixture data file")
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
        multi_layout.addLayout(slice_layout)

        variance_layout = QHBoxLayout()
        variance_layout.addWidget(QLabel("Stochastic Variance Factor [%]:"))
        self.spin_variance = QSpinBox()
        self.spin_variance.setRange(0, 100)
        self.spin_variance.setValue(self.model.modulation_percent)
        variance_layout.addWidget(self.spin_variance)
        multi_layout.addLayout(variance_layout)

        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("Number of unique mixture:"))
        self.spin_systems = QSpinBox()
        self.spin_systems.setRange(1, 100)
        self.spin_systems.setValue(self.model.num_systems)
        sys_layout.addWidget(self.spin_systems)
        multi_layout.addLayout(sys_layout)

        addition_layout = QHBoxLayout()
        addition_layout.addWidget(QLabel("Maximum addition compounds:"))
        self.spin_addition = QSpinBox()
        max_addition_allowed = max(0, self.spin_ncomp.value() // 2)
        self.spin_addition.setRange(0, max_addition_allowed)
        self.spin_addition.setValue(min(getattr(self.model, "max_addition", 0), max_addition_allowed))
        addition_layout.addWidget(self.spin_addition)
        multi_layout.addLayout(addition_layout)

        tm_layout = QHBoxLayout()
        tm_layout.addWidget(QLabel("Base melting point:"))
        self.spin_tm_base = QSpinBox()
        self.spin_tm_base.setRange(0, 500)
        self.spin_tm_base.setValue(130)
        tm_layout.addWidget(self.spin_tm_base)
        multi_layout.addLayout(tm_layout)


        self.btn_generate_matrix = QPushButton("Generate \"PhysChem Inputs\" data set")
        multi_layout.addWidget(self.btn_generate_matrix)
        self.btn_generate_matrix.clicked.connect(self.generate_matrix_data)

        json2_layout = QHBoxLayout()
        self.btn_write_matrix_json = QPushButton("Save matrix JSON")
        self.btn_read_matrix_json = QPushButton("Load matrix JSON")
        self.btn_read_matrix_json.setVisible(not self.chk_auto.isChecked())
        json2_layout.addWidget(self.btn_write_matrix_json)
        json2_layout.addWidget(self.btn_read_matrix_json)
        multi_layout.addLayout(json2_layout)

        multi_group.setLayout(multi_layout)
        main_layout.addWidget(multi_group)

        self._toggle_matrix_buttons()

        self.current_mixture = None
        self.current_config = None

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
    
    def generate_single_mixture(self):
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
        self.current_mixture = mixtures[0]
        self.current_config = config
        print("[Single] Generated mixture:", self.current_mixture)
        return self.current_mixture

    def write_single_json(self):
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
        self.current_mixture = mixtures[0]
        self.current_config = config

        path = DATA_DIR / "single_mixture.json"
        with open(path, "w") as f:
            json.dump(self.current_mixture, f, indent=4)

        print(f"[Single] Wrote → {path}")
        return self.current_mixture

    def read_single_json(self):
        path = DATA_DIR / "single_mixture.json"
        if not path.exists():
            print("[Single] No JSON file found.")
            return

        with open(path, "r") as f:
            mixture = json.load(f)

        self.current_mixture = mixture
        self.current_config = mixture

        components = mixture.get("components", [])
        if components:
            self.spin_ncomp.setValue(len(components))
            main_x = float(components[0].get("Xc", components[0].get("x", 0.0))) if isinstance(components[0], dict) else 0.0
            self.spin_main_level.setValue(int(round(main_x * 100)))
        print("[Single] Loaded mixture config.")
        return mixture

    def write_multi_json(self):
        params = Params(
            n_components=self.spin_ncomp.value(),
            main_component_index=0,
            main_component_level=self.spin_main_level.value() / 100.0,
            stochastic_variance=self.spin_variance.value() / 100.0,
            max_addition_compounds=self.spin_addition.value(),
            tm_base=float(self.spin_tm_base.value()),
            tm_sd_factor=1.0,
            dh_sd_factor=1.0,
            max_solvent_volumes=self.spin_slices.value(),
            
        )

        json_data = build_configuration_json(params)
        path = str(DATA_DIR / "physchem_config.json")
        write_json(path, json_data)
        print(f"[PhysChem] Wrote physchem_config.json → {path}")
        return path

    def generate_matrix_data(self):
        config_path = self.write_multi_json()
        if self.wizard() is not None and hasattr(self.wizard(), "page_generate_matrix"):
            self.wizard().page_generate_matrix.generate_mixtures(config_path=config_path)
        return config_path

    def _sync_max_addition_spin(self):
        self.model.n_components = self.spin_ncomp.value()
        max_allowed = max(0, self.spin_ncomp.value() // 2)
        self.spin_addition.setRange(0, max_allowed)
        if self.spin_addition.value() > max_allowed:
            self.spin_addition.setValue(max_allowed)
        self.model.max_addition = self.spin_addition.value()

    def _toggle_matrix_buttons(self):
        is_auto = self.chk_auto.isChecked()
        self.btn_read_matrix_json.setVisible(not is_auto)
        self.btn_write_matrix_json.setVisible(True)

    def show_plot(self):
        from gui_main import run_gui
        from single_mixture_solver import run_single_mixture

        if not hasattr(self, "current_mixture") or self.current_mixture is None:
            self.write_single_json()

        Rmax, composition_profile, solvent_profile = run_single_mixture(self.current_mixture)

        self._plot_window = run_gui(Rmax, composition_profile, solvent_profile)

    def run_multxeu_gui(self):
        import single_mixture_solver

        if not hasattr(self, "current_mixture") or self.current_mixture is None:
            self.write_single_json()

        Rmax, composition_profile, solvent_profile = run_single_mixture(self.current_mixture)

        run_gui(Rmax, composition_profile, solvent_profile)
        
