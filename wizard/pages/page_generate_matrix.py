# MIT License
#
# Copyright (c) [2026] [Alan A. Smith]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from PyQt6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QRadioButton, QSpinBox, QCheckBox,
    QWidget, QPushButton, QMessageBox, QSizePolicy,
    QFileDialog, QWizard
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QFont
import json
import os
import string
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from models.multxeu_model import MultXeuModel
from mixture_generator import generate_mixture_set
from input_writer import write_json
from multx_slicing_engine.multi_mixture_harness import (
    run_multi_mixture_harness_from_json,
    run_multi_mixture_harness_from_gui,
)
from multx_slicing_engine.excel_writer import write_excel
from multx_slicing_engine.matrix_layer import build_matrix_layer

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_DIR = ROOT_DIR / "models"
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

try:
    import layout_reference_table as layout_ref
except ImportError:  # pragma: no cover
    layout_ref = None


# ---------------------------------------------------------
# Plate Preview Widget (unchanged)
# ---------------------------------------------------------
class PlatePreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = 0
        self.cols = 0
        self.setMinimumSize(600, 600)

    def set_plate(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.update()

    def paintEvent(self, event):
        if self.rows <= 0 or self.cols <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen_plate = QPen(Qt.GlobalColor.white, 2)
        pen_well = QPen(Qt.GlobalColor.white, 1)
        painter.setPen(pen_plate)
        painter.setFont(QFont("Arial", 12))

        margin = 40
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin

        scale_x = avail_w / self.cols
        scale_y = avail_h / self.rows
        scale = min(scale_x, scale_y) * 0.65

        plate_w = self.cols * scale
        plate_h = self.rows * scale

        plate_x = 40
        plate_y = 40

        painter.drawRect(int(plate_x), int(plate_y), int(plate_w), int(plate_h))

        well_spacing_x = scale
        well_spacing_y = scale
        well_diameter = scale * 0.6

        painter.setPen(pen_well)

        for r in range(self.rows):
            for c in range(self.cols):
                cx = plate_x + c * well_spacing_x + well_spacing_x / 2
                cy = plate_y + r * well_spacing_y + well_spacing_y / 2

                painter.drawEllipse(
                    int(cx - well_diameter / 2),
                    int(cy - well_diameter / 2),
                    int(well_diameter),
                    int(well_diameter)
                )

        for r in range(self.rows):
            label = string.ascii_uppercase[r]
            y = plate_y + r * well_spacing_y + well_spacing_y / 2 + 5
            painter.drawText(int(plate_x - 30), int(y), label)

        for c in range(self.cols):
            label = str(c + 1)
            x = plate_x + c * well_spacing_x + well_spacing_x / 2 - 5
            painter.drawText(int(x), int(plate_y - 10), label)


# ---------------------------------------------------------
# Page 2 — Generate Experimental Matrix
# ---------------------------------------------------------
class PageGenerateMatrix(QWizardPage):
    def __init__(self, model: MultXeuModel):
        super().__init__()
        self.model = model
        self.setTitle("Generate Experimental Matrix")
        self.setFinalPage(True)

        main_layout = QHBoxLayout(self)

        # -----------------------------------------------------
        # LEFT SIDE — Plate format + new MultXeu controls
        # -----------------------------------------------------
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(620)
        main_layout.addWidget(left_panel, alignment=Qt.AlignmentFlag.AlignLeft)

        # Plate format group with preview nested inside the box
        format_group = QGroupBox("Plate Format")
        format_layout = QHBoxLayout()
        format_layout.setContentsMargins(10, 10, 10, 10)

        left_column = QVBoxLayout()

        self.rb_4x3 = QRadioButton("4 × 3 (12 wells)")
        self.rb_3x5 = QRadioButton("3 × 5 (15 wells)")
        self.rb_6x4 = QRadioButton("6 × 4 (24 wells)")
        self.rb_8x6 = QRadioButton("8 × 6 (48 wells)")
        self.rb_12x8 = QRadioButton("12 × 8 (96 wells)")
        self.rb_free = QRadioButton("Free format:")

        for rb in [self.rb_4x3, self.rb_3x5, self.rb_6x4, self.rb_8x6, self.rb_12x8, self.rb_free]:
            font = rb.font()
            font.setPointSize(9)
            rb.setFont(font)

        self.spin_rows = QSpinBox()
        self.spin_cols = QSpinBox()
        self.spin_rows.setRange(1, 26)
        self.spin_cols.setRange(1, 50)
        self.spin_rows.setEnabled(False)
        self.spin_cols.setEnabled(False)

        free_layout = QHBoxLayout()
        free_layout.addWidget(QLabel("Rows:"))
        free_layout.addWidget(self.spin_rows)
        free_layout.addWidget(QLabel("Cols:"))
        free_layout.addWidget(self.spin_cols)

        left_column.addWidget(self.rb_4x3)
        left_column.addWidget(self.rb_3x5)
        left_column.addWidget(self.rb_6x4)
        left_column.addWidget(self.rb_8x6)
        left_column.addWidget(self.rb_12x8)
        left_column.addWidget(self.rb_free)
        left_column.addLayout(free_layout)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview = PlatePreview()
        self.preview.setMinimumSize(320, 300)
        self.preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        preview_layout.addWidget(self.preview)

        format_layout.addLayout(left_column)
        format_layout.addWidget(preview_container, alignment=Qt.AlignmentFlag.AlignRight)

        format_group.setLayout(format_layout)
        left_layout.addWidget(format_group)

        # -----------------------------------------------------
        # Lower options: matrix behavior, replicates, and analytical error
        # -----------------------------------------------------
        options_group = QGroupBox("Experimental Options")
        options_layout = QVBoxLayout()
        self.chk_randomize = QCheckBox("Randomize order")
        self.checkbox_fill_full = QCheckBox("Fill plates")
        options_layout.addWidget(self.chk_randomize)
        options_layout.addWidget(self.checkbox_fill_full)
        options_group.setLayout(options_layout)
        options_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        options_group.setMaximumHeight(150)

        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(12)

        # Replicates group
        repl_group = QGroupBox("Replicates")
        repl_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        repl_layout = QVBoxLayout()
        self.chk_repl = QCheckBox("Incl. replicates")
        self.spin_repl = QSpinBox()
        self.spin_repl.setRange(0, 100)
        self.spin_repl.setValue(0)
        repl_layout.addWidget(self.chk_repl)
        repl_layout.addWidget(QLabel("Replicate %:"))
        repl_layout.addWidget(self.spin_repl)
        repl_group.setLayout(repl_layout)
        repl_group.setMaximumHeight(150)

        # Analytical Error group
        err_group = QGroupBox("Experimental Error")
        err_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        err_layout = QVBoxLayout()
        self.chk_error = QCheckBox("Incl. noise")
        self.spin_error = QSpinBox()
        self.spin_error.setRange(1, 10)
        self.spin_error.setValue(5)
        err_layout.addWidget(self.chk_error)
        err_layout.addWidget(QLabel("Error ± [%]:"))
        err_layout.addWidget(self.spin_error)
        err_group.setLayout(err_layout)
        err_group.setMaximumHeight(150)

        # Keep the cluster aligned to the left edge while preserving the internal horizontal layout
        meta_layout.addWidget(options_group)
        meta_layout.addWidget(repl_group)
        meta_layout.addWidget(err_group)

        self.btn_write = QPushButton("Write Excel File")
        self.btn_write.setMinimumWidth(150)
        meta_layout.addWidget(self.btn_write)
        meta_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        left_layout.addLayout(meta_layout)

        # -----------------------------------------------------
        # SIGNALS (unchanged + new ones)
        # -----------------------------------------------------
        self.rb_4x3.toggled.connect(lambda: self.update_preview(3, 4))
        self.rb_3x5.toggled.connect(lambda: self.update_preview(3, 5))
        self.rb_6x4.toggled.connect(lambda: self.update_preview(4, 6))
        self.rb_8x6.toggled.connect(lambda: self.update_preview(6, 8))
        self.rb_12x8.toggled.connect(lambda: self.update_preview(8, 12))

        self.rb_free.toggled.connect(self.enable_free_format)
        self.spin_rows.valueChanged.connect(self.update_free_preview)
        self.spin_cols.valueChanged.connect(self.update_free_preview)

        self.btn_write.clicked.connect(self.write_excel_files)

        # Default plate
        self.rb_free.setChecked(True)
        self.enable_free_format()
        self.update_preview(1, 1)

    def update_next_button_text(self):
        if self.isFinalPage():
            return

        wizard = self.wizard()
        if wizard is None:
            return

        label = "Build Data (JSON) >" if getattr(self.model, "loaded_json_path", None) else "Build Data (auto) >"
        wizard.setButtonText(QWizard.WizardButton.NextButton, label)
        next_button = wizard.button(QWizard.WizardButton.NextButton)
        if next_button is not None:
            next_button.update()
        wizard.update()

    def _handle_json_mode_toggle(self, checked):
        self.update_next_button_text()

    # ---------------------------------------------------------
    # Preview update logic (unchanged)
    # ---------------------------------------------------------
    def enable_free_format(self):
        free = self.rb_free.isChecked()
        self.spin_rows.setEnabled(free)
        self.spin_cols.setEnabled(free)
        if free:
            self.update_free_preview()

    def update_free_preview(self):
        if self.rb_free.isChecked():
            self.preview.set_plate(self.spin_rows.value(), self.spin_cols.value())

    def update_preview(self, rows, cols):
        sender = self.sender()
        if sender is None or sender.isChecked():
            self.preview.set_plate(rows, cols)

    # ---------------------------------------------------------
    # Generate mixtures from physchem_config.json
    # ---------------------------------------------------------

    
    def generate_mixtures(self, config_path=None, config=None):
        self.model.replicate_percent = self.spin_repl.value() if self.chk_repl.isChecked() else 0
        self.model.analytical_error_percent = self.spin_error.value() if self.chk_error.isChecked() else 0

        if config is None:
            if config_path is None:
                config_path = str(DATA_DIR / "physchem_config.json")

            if not os.path.exists(config_path):
                wizard = self.wizard()
                if wizard is not None and hasattr(wizard, "page_physchem"):
                    wizard.page_physchem._sync_model_state()
                    params = wizard.page_physchem.build_single_config() if False else None
                    config = {
                        "metadata": {
                            "n_components": wizard.page_physchem.spin_ncomp.value(),
                            "main_component_index": 0,
                            "main_component_level": wizard.page_physchem.spin_main_level.value() / 100.0,
                            "stochastic_variance": wizard.page_physchem.spin_variance.value() / 100.0,
                            "max_addition_compounds": wizard.page_physchem.spin_addition.value(),
                            "num_unique_mixtures": wizard.page_physchem.spin_systems.value(),
                        },
                        "physchem_rules": {
                            "tm_base": float(wizard.page_physchem.spin_tm_base.value()),
                            "tm_sd_factor": 1.0,
                            "dh_sd_factor": 1.0,
                        },
                        "slicing": {
                            "max_solvent_volumes": wizard.page_physchem.spin_slices.value(),
                        },
                    }
                else:
                    raise FileNotFoundError(f"No config file found at: {config_path}")
            else:
                with open(config_path, "r") as f:
                    config = json.load(f)

        num_unique_mixtures = getattr(self.model, "num_unique_mixtures", getattr(self.model, "num_systems", 1))
        self.model.num_unique_mixtures = int(num_unique_mixtures)
        self.model.num_systems = int(num_unique_mixtures)

        mixtures = generate_mixture_set(config, num_unique_mixtures=num_unique_mixtures)
        self.model.physchem_matrix = mixtures

        # print(f"[Matrix] Generated {len(mixtures)} mixtures in memory")
        return mixtures


    def _get_layout_settings(self):
        free_format = self.rb_free.isChecked()

        if free_format:
            rows = int(self.spin_rows.value())
            cols = int(self.spin_cols.value())
            plate_format = "free"
        else:
            if self.rb_4x3.isChecked():
                rows, cols = 3, 4
            elif self.rb_3x5.isChecked():
                rows, cols = 3, 5
            elif self.rb_6x4.isChecked():
                rows, cols = 4, 6
            elif self.rb_8x6.isChecked():
                rows, cols = 6, 8
            elif self.rb_12x8.isChecked():
                rows, cols = 8, 12
            else:
                rows = int(self.spin_rows.value())
                cols = int(self.spin_cols.value())
            plate_format = f"{rows}x{cols}"

        settings = {
            "free_format": free_format,
            "plate_format": plate_format,
            "rows": rows,
            "cols": cols,
            "fill_plates": bool(self.checkbox_fill_full.isChecked()) and not free_format,
            "randomize_order": bool(self.chk_randomize.isChecked()),
            "include_replicates": bool(self.chk_repl.isChecked()),
            "replicate_percent": int(self.spin_repl.value()) if self.chk_repl.isChecked() else 0,
            "include_error": bool(self.chk_error.isChecked()),
            "error_percent": int(self.spin_error.value()) if self.chk_error.isChecked() else 0,
            "number_of_slices": int(getattr(self.model, "max_slices", getattr(self.model, "num_systems", 3)) or 3),
        }

        self.model.free_format = settings["free_format"]
        self.model.plate_format = settings["plate_format"]
        self.model.rows = settings["rows"]
        self.model.cols = settings["cols"]
        self.model.fill_plates = settings["fill_plates"]
        self.model.randomize_order = settings["randomize_order"]
        self.model.include_replicates = settings["include_replicates"]
        self.model.replicate_percent = settings["replicate_percent"]
        self.model.include_error = settings["include_error"]
        self.model.error_percent = settings["error_percent"]
        self.model.slice_count = settings["number_of_slices"]
        return settings

    def _apply_layout_reference_settings(self, settings):
        if layout_ref is None:
            return

        self.model.free_format = bool(settings["free_format"])
        self.model.plate_format = settings["plate_format"]
        self.model.rows = int(settings["rows"])
        self.model.cols = int(settings["cols"])
        self.model.fill_plates = bool(settings["fill_plates"])
        self.model.randomize_order = bool(settings["randomize_order"])
        self.model.include_replicates = bool(settings["include_replicates"])
        self.model.replicate_percent = int(settings["replicate_percent"])
        self.model.include_error = bool(settings["include_error"])
        self.model.error_percent = int(settings["error_percent"])
        self.model.slice_count = int(settings["number_of_slices"])

    def _merge_layout_metadata(self, metadata_row, slice_row, settings):
        component_count = 0
        for key in list(slice_row.keys()):
            if key.startswith("Xc_"):
                component_count = max(component_count, int(key.split("_")[-1]))
            elif key.startswith("Xs_"):
                component_count = max(component_count, int(key.split("_")[-1]))
            elif key.startswith("Xliq_"):
                component_count = max(component_count, int(key.split("_")[-1]))

        ordered = []
        ordered.append("mixture_id")
        for idx in range(1, component_count + 1):
            ordered.append(f"Xc_{idx}")
        for idx in range(1, component_count + 1):
            ordered.append(f"Xs_{idx}")
        for idx in range(1, component_count + 1):
            ordered.append(f"Xliq_{idx}")
        ordered.extend(["R", "RelSolVol", "Rmax", "RelSolVol(Rmax)"])
        ordered.append("")
        if settings["free_format"]:
            ordered.extend(["id", "origin_id", "replicate_status", "replicate_index", "block_number", "slice_number", "experiment_code"])
        else:
            ordered.extend(["id", "origin_id", "origin_plate_ref", "replicate_status", "replicate_index", "plate_number", "well_address", "block_number", "slice_number", "experiment_code"])

        merged = {header: None for header in ordered}
        merged["mixture_id"] = slice_row.get("mixture_id")
        for idx in range(1, component_count + 1):
            merged[f"Xc_{idx}"] = slice_row.get(f"Xc_{idx}")
            merged[f"Xs_{idx}"] = slice_row.get(f"Xs_{idx}")
            merged[f"Xliq_{idx}"] = slice_row.get(f"Xliq_{idx}")
        merged["R"] = slice_row.get("R")
        merged["RelSolVol"] = slice_row.get("RelSolVol")
        merged["Rmax"] = slice_row.get("Rmax")
        merged["RelSolVol(Rmax)"] = slice_row.get("RelSolVol(Rmax)")
        merged[""] = ""
        merged["id"] = metadata_row.get("id", "")
        merged["origin_id"] = metadata_row.get("origin_id", "")
        if not settings["free_format"]:
            merged["origin_plate_ref"] = metadata_row.get("origin_plate_ref", "")
        merged["replicate_status"] = metadata_row.get("replicate_status", "")
        merged["replicate_index"] = metadata_row.get("replicate_index", "")
        if not settings["free_format"]:
            merged["plate_number"] = metadata_row.get("plate_number", "")
            merged["well_address"] = metadata_row.get("well_address", "")
        merged["block_number"] = metadata_row.get("block_number", "")
        merged["slice_number"] = metadata_row.get("slice_number", slice_row.get("slice_index", 1))
        merged["experiment_code"] = metadata_row.get("experiment_code", "")

        merged["slice_count"] = slice_row.get("slice_count")
        merged["slice_index"] = slice_row.get("slice_index")
        return merged

    def _build_export_rows(self, layer):
        anchors_by_mixture = {
            anchor.get("mixture_id"): anchor
            for anchor in layer.get("mixture_anchors", [])
            if anchor.get("mixture_id")
        }

        settings = self._get_layout_settings()
        self._apply_layout_reference_settings(settings)

        all_slice_rows = []
        for rows in layer.get("slice_arrays", {}).values():
            all_slice_rows.extend(rows)

        mixture_ids = sorted({str(row.get("mixture_id")) for row in all_slice_rows if row.get("mixture_id")})

        if layout_ref is not None:
            metadata_rows = list(layout_ref.build_layout_reference_table(
                mixture_ids=mixture_ids,
                slice_count=int(self.model.slice_count),
                free_format=bool(self.model.free_format),
                plate_format=str(self.model.plate_format),
                rows=int(self.model.rows),
                cols=int(self.model.cols),
                include_replicates=bool(self.model.include_replicates),
                replicate_percent=int(self.model.replicate_percent),
                fill_plates=bool(self.model.fill_plates),
                include_error=bool(self.model.include_error),
                error_percent=int(self.model.error_percent),
                randomize_order=bool(self.model.randomize_order),
            ))
            metadata_lookup = defaultdict(list)
            for metadata_row in metadata_rows:
                mixture_id = metadata_row.get("mixture_id")
                slice_number = metadata_row.get("slice_number")
                if mixture_id and slice_number is not None:
                    metadata_lookup[(str(mixture_id), int(slice_number))].append(metadata_row)
        else:
            metadata_lookup = defaultdict(list)

        export_rows = []
        for scenario_name, rows in sorted(layer.get("slice_arrays", {}).items()):
            slice_count = int(scenario_name.split("_")[-1]) if scenario_name else 0
            for row in rows:
                anchor = anchors_by_mixture.get(row.get("mixture_id"), {})
                x_c = row.get("Xc", []) or anchor.get("Xc", [])
                x_s = row.get("Xs", []) or []
                x_l = row.get("Xliq", []) or []
                row_data = {
                    "mixture_id": row.get("mixture_id"),
                    "Rmax": anchor.get("Rmax"),
                    "RelSolVol(Rmax)": anchor.get("RelSolVol_Rmax"),
                }
                for idx, value in enumerate(x_c, start=1):
                    row_data[f"Xc_{idx}"] = value
                for idx, value in enumerate(x_s, start=1):
                    row_data[f"Xs_{idx}"] = value
                for idx, value in enumerate(x_l, start=1):
                    row_data[f"Xliq_{idx}"] = value
                row_data["R"] = row.get("R")
                row_data["RelSolVol"] = row.get("RelSolVol")
                row_data["slice_count"] = slice_count
                row_data["slice_index"] = row.get("slice_index")

                key = (str(row.get("mixture_id")), int(row.get("slice_index", 1)))
                matching_metadata = metadata_lookup.get(key, [])
                if not matching_metadata:
                    matching_metadata = [{
                        "id": f"{row.get('mixture_id') or 'UNKNOWN'}_S{row.get('slice_index', 1):02d}",
                        "origin_id": "",
                        "origin_plate_ref": "",
                        "replicate_status": "Base",
                        "replicate_index": 1,
                        "plate_number": "",
                        "well_address": "",
                        "block_number": "",
                        "mixture_id": row.get("mixture_id"),
                        "slice_number": row.get("slice_index", 1),
                        "experiment_code": "",
                        "free_format": settings["free_format"],
                    }]

                for metadata_row in matching_metadata:
                    export_rows.append(self._merge_layout_metadata(metadata_row, row_data, settings))
        return export_rows

    def write_matrix_layer_exports(self, layer=None, output_dir=None):
        if layer is None:
            layer = build_matrix_layer(getattr(self.model, "canonical_results", []))

        output_dir = Path(output_dir) if output_dir is not None else DATA_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []
        export_rows = self._build_export_rows(layer)
        grouped_rows = defaultdict(list)
        for row in export_rows:
            grouped_rows[int(row.get("slice_count", 0) or 0)].append(row)

        for slice_count in sorted(grouped_rows):
            rows_for_slice = grouped_rows[slice_count]
            if not rows_for_slice:
                continue

            headers = list(rows_for_slice[0].keys())
            workbook_rows = []
            for row in rows_for_slice:
                workbook_rows.append({header: row.get(header) for header in headers})

            timestamp = datetime.now().strftime("%y%m%d_%H%M")
            output_path = output_dir / f"{timestamp}_Vol{slice_count:02d}.xlsx"
            write_excel(output_path, {"slice_records": workbook_rows})
            written_files.append(str(output_path))

        final_rows = sorted(
            [row for row in export_rows if row.get("ID") is not None],
            key=lambda row: str(row.get("ID", "")),
        )
        final_combined_path = output_dir / "final_combined.xlsx"
        if final_rows:
            final_headers = list(final_rows[0].keys())
            final_export = [{header: row.get(header) for header in final_headers} for row in final_rows]
            write_excel(final_combined_path, {"slice_records": final_export})

        if written_files:
            self.model.last_export_path = written_files[-1]
        return written_files

    def write_excel_files(self):
        if not getattr(self.model, "physchem_matrix", None) and not getattr(self.model, "loaded_json_path", None):
            self.generate_mixtures()
        self.validatePage()

    # ---------------------------------------------------------
    # Save plate metadata into model (unchanged)
    # ---------------------------------------------------------
    def validatePage(self):
        if self.rb_4x3.isChecked():
            rows, cols = 4, 3
        elif self.rb_3x5.isChecked():
            rows, cols = 3, 5
        elif self.rb_6x4.isChecked():
            rows, cols = 4, 6
        elif self.rb_8x6.isChecked():
            rows, cols = 6, 8
        elif self.rb_12x8.isChecked():
            rows, cols = 8, 12
        else:
            rows = self.spin_rows.value()
            cols = self.spin_cols.value()

        self.model.plate_rows = rows
        self.model.plate_cols = cols
        self.model.randomize_design = self.chk_randomize.isChecked()
        self.model.fill_to_full_plates = self.checkbox_fill_full.isChecked()

        #print("DEBUG: NEXT pressed")
        #print("DEBUG: physchem_matrix =", self.model.physchem_matrix)
        #print("DEBUG: loaded_json_path =", getattr(self.model, "loaded_json_path", None))

        json_path = getattr(self.model, "loaded_json_path", None)
        matrix = getattr(self.model, "physchem_matrix", None)

        if json_path:
            if json_path is None:
                json_path = str(DATA_DIR / "physchem_matrix.json")
            if not isinstance(matrix, list) or not matrix:
                try:
                    with open(json_path, "r") as f:
                        matrix = json.load(f)
                    self.model.physchem_matrix = matrix
                except Exception as exc:
                    raise ValueError(f"Could not load matrix JSON '{json_path}': {exc}") from exc
            # print("DEBUG: GUI branch -> run_multi_mixture_harness_from_json, path =", json_path)
            self.model.canonical_results = run_multi_mixture_harness_from_json(json_path)
        else:
            if not isinstance(matrix, list) or not matrix:
                raise ValueError("No matrix data available. Generate a matrix or load a JSON file first.")
            # print("DEBUG: GUI branch -> run_multi_mixture_harness_from_gui, len =", len(matrix))
            self.model.canonical_results = run_multi_mixture_harness_from_gui(matrix)

        layer = build_matrix_layer(self.model.canonical_results)
        self.write_matrix_layer_exports(layer=layer, output_dir=DATA_DIR)

        return True
