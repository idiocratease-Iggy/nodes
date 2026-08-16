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
    QWidget, QPushButton, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QFont
import string

from models.multxeu_model import MultXeuModel


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
        left_panel.setFixedWidth(640)
        main_layout.addWidget(left_panel, alignment=Qt.AlignmentFlag.AlignLeft)

        # Plate format group (unchanged)
        format_group = QGroupBox("Plate Format")
        format_layout = QVBoxLayout()

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

        format_layout.addWidget(self.rb_4x3)
        format_layout.addWidget(self.rb_3x5)
        format_layout.addWidget(self.rb_6x4)
        format_layout.addWidget(self.rb_8x6)
        format_layout.addWidget(self.rb_12x8)
        format_layout.addWidget(self.rb_free)
        format_layout.addLayout(free_layout)

        format_group.setLayout(format_layout)
        left_layout.addWidget(format_group)

        # -----------------------------------------------------
        # Lower options: matrix behavior, replicates, and analytical error
        # -----------------------------------------------------
        options_group = QGroupBox("Experimental Options")
        options_layout = QVBoxLayout()
        self.chk_randomize = QCheckBox("Randomize experiment order across reactors")
        self.checkbox_fill_full = QCheckBox("Fill up to full plates")
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
        self.chk_repl = QCheckBox("Include replicates")
        self.spin_repl = QSpinBox()
        self.spin_repl.setRange(0, 100)
        self.spin_repl.setValue(0)
        repl_layout.addWidget(self.chk_repl)
        repl_layout.addWidget(QLabel("Replicate %:"))
        repl_layout.addWidget(self.spin_repl)
        repl_group.setLayout(repl_layout)
        repl_group.setMaximumHeight(150)

        # Analytical Error group
        err_group = QGroupBox("Analytical Error")
        err_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        err_layout = QVBoxLayout()
        self.chk_error = QCheckBox("Include analytical error")
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
        # RIGHT SIDE — Plate preview (unchanged)
        # -----------------------------------------------------
        self.preview = PlatePreview()
        self.preview.setMinimumSize(420, 420)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.preview)

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

        self.btn_write.clicked.connect(self.generate_matrix)

        # Default plate
        self.rb_6x4.setChecked(True)
        self.update_preview(4, 6)

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
    # Generate matrix + write Excel (MultXeu logic later)
    # ---------------------------------------------------------
    def generate_matrix(self):
        # Store new MultXeu metadata
        self.model.replicate_percent = self.spin_repl.value() if self.chk_repl.isChecked() else 0
        self.model.analytical_error_percent = self.spin_error.value() if self.chk_error.isChecked() else 0

        # Store plate metadata
        self.validatePage()

        print("[MultXeu] Ready to generate synthetic experimental matrix.")
        print(f"  Replicates: {self.model.replicate_percent}%")
        print(f"  Analytical error: ±{self.model.analytical_error_percent}%")
        print(f"  Plate: {self.model.plate_rows} × {self.model.plate_cols}")
        print(f"  Randomize: {self.model.randomize_design}")
        print(f"  Fill full plates: {self.model.fill_to_full_plates}")

        # TODO: integrate test_run.py, slicing, mass balance, Excel writing

        QMessageBox.information(self, "MultXeu", "Synthetic experimental matrix generated (placeholder).")

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

        return True
