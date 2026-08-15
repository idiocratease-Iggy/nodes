import json
import os

from PyQt6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QSpinBox, QCheckBox, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt

from models.multxeu_model import MultXeuModel


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
        comp_layout.addWidget(self.spin_ncomp)
        single_layout.addLayout(comp_layout)

        main_layout2 = QHBoxLayout()
        main_layout2.addWidget(QLabel("Main component level [%]:"))
        self.spin_main = QSpinBox()
        self.spin_main.setRange(50, 99)
        self.spin_main.setValue(self.model.main_component_level)
        main_layout2.addWidget(self.spin_main)
        single_layout.addLayout(main_layout2)

        self.btn_plot = QPushButton("Plot purification profile")
        single_layout.addWidget(self.btn_plot)

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

        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Allow 1:1 addition compounds:"))
        self.spin_addition = QSpinBox()
        self.spin_addition.setRange(0, 5)
        self.spin_addition.setValue(self.model.allow_addition)
        add_layout.addWidget(self.spin_addition)
        multi_layout.addLayout(add_layout)

        slice_layout = QHBoxLayout()
        slice_layout.addWidget(QLabel("Maximum solvent volumes per mixture:"))
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(1, 10)
        self.spin_slices.setValue(self.model.max_slices)
        slice_layout.addWidget(self.spin_slices)
        multi_layout.addLayout(slice_layout)

        mod_layout = QHBoxLayout()
        mod_layout.addWidget(QLabel("Stochastic Variance Factor: [%]:"))
        self.spin_modulation = QSpinBox()
        self.spin_modulation.setRange(0, 100)
        self.spin_modulation.setValue(self.model.modulation_percent)
        mod_layout.addWidget(self.spin_modulation)
        multi_layout.addLayout(mod_layout)

        sys_layout = QHBoxLayout()
        sys_layout.addWidget(QLabel("Number of unique mixture:"))
        self.spin_systems = QSpinBox()
        self.spin_systems.setRange(1, 100)
        self.spin_systems.setValue(self.model.num_systems)
        sys_layout.addWidget(self.spin_systems)
        multi_layout.addLayout(sys_layout)

        pd_layout = QHBoxLayout()
        pd_layout.addWidget(QLabel("PD / SVL [%]:"))
        self.spin_pd = QSpinBox()
        self.spin_pd.setRange(0, 100)
        self.spin_pd.setValue(50)
        pd_layout.addWidget(self.spin_pd)
        multi_layout.addLayout(pd_layout)

        self.btn_generate_matrix = QPushButton("Generate \"PhysChem Inputs\" data set:")
        multi_layout.addWidget(self.btn_generate_matrix)

        json2_layout = QHBoxLayout()
        self.btn_write_matrix_json = QPushButton("Save matrix JSON")
        self.btn_read_matrix_json = QPushButton("Load matrix JSON")
        json2_layout.addWidget(self.btn_write_matrix_json)
        json2_layout.addWidget(self.btn_read_matrix_json)
        multi_layout.addLayout(json2_layout)

        multi_group.setLayout(multi_layout)
        main_layout.addWidget(multi_group)

        self.btn_plot.clicked.connect(self.show_plot)
        self.btn_generate_matrix.clicked.connect(self.generate_matrix)
        self.btn_write_json.clicked.connect(self.write_single_json)
        self.btn_read_json.clicked.connect(self.read_single_json)
        self.btn_write_matrix_json.clicked.connect(self.write_multi_json)
        self.btn_read_matrix_json.clicked.connect(self.read_multi_json)




    # ---------------------------------------------------------
    # Show stacked plot popup (wired to test_run.py)
    # ---------------------------------------------------------
    def show_plot(self):
        import test_run
        fig = test_run.main()  # must return a matplotlib Figure
        popup = PlotPopup(fig)
        popup.show()
        self._popup = popup

    # ---------------------------------------------------------
    # Read-Write single system JSON (wired to write_single_json)
    # ---------------------------------------------------------
    
    def write_single_json(self):
        data = {
            "n_components": self.spin_ncomp.value(),
            "main_component_level": self.spin_main.value()
        }

        path = os.path.join(DATA_DIR, "single_system.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

        print(f"[PhysChem] Wrote single_system.json → {path}")

    def read_single_json(self):
        path = os.path.join(DATA_DIR, "single_system.json")
        if not os.path.exists(path):
            print("[PhysChem] single_system.json not found.")
            return

        with open(path, "r") as f:
            data = json.load(f)

        # Update widgets
        self.spin_ncomp.setValue(data.get("n_components", 4))
        self.spin_main.setValue(data.get("main_component_level", 80))

        # Update model
        self.model.n_components = self.spin_ncomp.value()
        self.model.main_component_level = self.spin_main.value()

        print(f"[PhysChem] Loaded single_system.json ← {path}")


    # ---------------------------------------------------------
    # Read-Write multi system JSON (wired to write_multi_json)
    # ---------------------------------------------------------

    def write_multi_json(self):
        data = {
            "use_auto": self.chk_auto.isChecked(),
            "allow_addition": self.spin_addition.value(),
            "max_slices": self.spin_slices.value(),
            "modulation_percent": self.spin_modulation.value(),
            "num_systems": self.spin_systems.value()
        }

        path = os.path.join(DATA_DIR, "physchem_matrix.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

        print(f"[PhysChem] Wrote physchem_matrix.json → {path}")

    def read_multi_json(self):
        path = os.path.join(DATA_DIR, "physchem_matrix.json")
        if not os.path.exists(path):
            print("[PhysChem] physchem_matrix.json not found.")
            return

        with open(path, "r") as f:
            data = json.load(f)

        # Update widgets
        self.chk_auto.setChecked(data.get("use_auto", True))
        self.spin_addition.setValue(data.get("allow_addition", 0))
        self.spin_slices.setValue(data.get("max_slices", 3))
        self.spin_modulation.setValue(data.get("modulation_percent", 20))
        self.spin_systems.setValue(data.get("num_systems", 10))

        # Update model
        self.model.use_auto = self.chk_auto.isChecked()
        self.model.allow_addition = self.spin_addition.value()
        self.model.max_slices = self.spin_slices.value()
        self.model.modulation_percent = self.spin_modulation.value()
        self.model.num_systems = self.spin_systems.value()

        print(f"[PhysChem] Loaded physchem_matrix.json ← {path}")

    def generate_matrix(self):
        """Placeholder to match the button wiring in __init__."""
        print("[PhysChem] Generate matrix requested.")

    def _toggle_matrix_buttons(self):
        is_auto = self.chk_auto.isChecked()
        self.btn_read_matrix_json.setVisible(not is_auto)
        self.btn_write_matrix_json.setVisible(not is_auto)
