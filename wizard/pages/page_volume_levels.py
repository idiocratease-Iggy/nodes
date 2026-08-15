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
    QWizardPage,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QSpinBox,
    QGroupBox,
    QRadioButton,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QWidget,
)
from PyQt6.QtCore import Qt

class PageVolumeLevels(QWizardPage):
    def __init__(self, model):
        super().__init__()
        self.setTitle("Define Volume Levels")

        self.model = model

        self.setTitle("Solvent Volume Levels")

        # ------------------------------
        # Guidance text
        # ------------------------------
        guidance = QLabel(
            "<b>Guidance:</b><br>"
            "CRYSS experiments should be run <i>highly concentrated</i>, using low solvent volumes "
            "relative to the solid mass. This ensures that after equilibration, both phases "
            "(solid + mother liquor) contain a partially purified mixture.<br>"
            "If an experiment produces no solid phase, or a solid phase consisting of a pure compound, "
            "it provides no useful partitioning information for CRYSS.<br>"
            "Using multiple solvent volumes for the same starting composition improves solubility "
            "modelling and partitioning accuracy."
        )
        guidance.setWordWrap(True)
        # Reduce vertical spacing of guidance text slightly by removing extra <br> tags where possible

        # ------------------------------
        # Number of solvent volume levels
        # ------------------------------
        volumes_label = QLabel("How many solvent volume levels do you want to use?")
        self.spin_volumes = QSpinBox()
        self.spin_volumes.setMinimum(1)
        self.spin_volumes.setMaximum(10)
        self.spin_volumes.setValue(1)
        self.spin_volumes.setFixedWidth(80)

        volumes_layout = QHBoxLayout()
        volumes_layout.addWidget(volumes_label)
        volumes_layout.addWidget(self.spin_volumes)

        # ------------------------------
        # Volume mode (Relative first, default)
        # ------------------------------
        mode_group = QGroupBox("Volume Mode")
        self.radio_relative = QRadioButton("Relative solvent volume (mL solvent / g mixture)")
        self.radio_absolute = QRadioButton("Absolute solvent volume")
        
        font = self.radio_relative.font()
        font.setPointSize(9)
        self.radio_relative.setFont(font)
        self.radio_absolute.setFont(font)
        self.radio_relative.setStyleSheet("font-size: 9pt;")
        self.radio_absolute.setStyleSheet("font-size: 9pt;")

        self.radio_relative.setChecked(True)

        mode_layout = QVBoxLayout()
        mode_layout.addWidget(self.radio_relative)
        mode_layout.addWidget(self.radio_absolute)
        mode_group.setLayout(mode_layout)

        # ------------------------------
        # Unit selector (only visible for absolute mode)
        # ------------------------------
        unit_label = QLabel("Units for absolute solvent volume:")
        self.combo_units = QComboBox()
        self.combo_units.addItems(["mL", "µL", "L", "dL", "dm³"])
        self.combo_units.setCurrentText("mL")
        self.combo_units.setFixedWidth(80)

        unit_layout = QHBoxLayout()
        unit_layout.addWidget(unit_label)
        unit_layout.addWidget(self.combo_units)

        # Hide unit selector initially (relative mode default)
        unit_label.setVisible(False)
        self.combo_units.setVisible(False)

        # Toggle visibility when radio buttons change
        self.radio_absolute.toggled.connect(
            lambda checked: (
                unit_label.setVisible(checked),
                self.combo_units.setVisible(checked)
            )
        )

        # ------------------------------
        # Replicates section
        # ------------------------------
        replicate_group = QGroupBox("Replicates")
        self.chk_replicates = QCheckBox("Include replicates")

        replicate_label = QLabel("Replicate percentage:")
        self.spin_replicate_pct = QSpinBox()
        self.spin_replicate_pct.setRange(0, 100)
        self.spin_replicate_pct.setSuffix("%")
        self.spin_replicate_pct.setValue(0)
        self.spin_replicate_pct.setFixedWidth(80)

        replicate_layout = QHBoxLayout()
        replicate_layout.addWidget(replicate_label)
        replicate_layout.addWidget(self.spin_replicate_pct)

        replicate_box_layout = QVBoxLayout()
        replicate_box_layout.addWidget(self.chk_replicates)
        replicate_box_layout.addLayout(replicate_layout)
        replicate_group.setLayout(replicate_box_layout)

        # Hide replicate percentage until checkbox is ticked
        replicate_label.setVisible(False)
        self.spin_replicate_pct.setVisible(False)

        # Show/hide when checkbox toggled
        self.chk_replicates.toggled.connect(
            lambda checked: (
                replicate_label.setVisible(checked),
                self.spin_replicate_pct.setVisible(checked),
                self.apply_replicate_heuristic() if checked else None
            )
        )

        # ------------------------------
        # Heuristic: adjust replicate % based on number of volume levels
        # ------------------------------
        def update_replicate_default():
            if not self.chk_replicates.isChecked():
                return

            n = self.spin_volumes.value()

            if n == 1:
                default_pct = 35
            elif n == 2:
                default_pct = 25
            elif n == 3:
                default_pct = 15
            else:
                default_pct = 5

            self.spin_replicate_pct.setValue(default_pct)

        # Connect heuristic to volume-level changes
        self.spin_volumes.valueChanged.connect(update_replicate_default)

        # Also expose heuristic as a method for checkbox toggling
        self.apply_replicate_heuristic = update_replicate_default
    
        # ------------------------------
        # Final layout
        # ------------------------------
        layout = QVBoxLayout()
        layout.addWidget(guidance)
        layout.addSpacing(10)
        layout.addLayout(volumes_layout)
        layout.addWidget(mode_group)
        layout.addLayout(unit_layout)
        layout.addSpacing(10)
        layout.addWidget(replicate_group)
        layout.addStretch()

        # Wrap in a scroll area to handle small screens/large lists
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(20, 10, 20, 10)
        container_layout.setSpacing(0)
        container_layout.addLayout(layout)
        scroll_area.setWidget(container_widget)

        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #444;
                background-color: #2b2b2b;
            }
            QScrollBar:vertical {
                border: none;
                background: #3c3c3c;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #718096;
                min-height: 20px;
                border-radius: 5px;
            }
        """)

        # Create a layout for the page and add the scroll area to it
        center_layout = QHBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setContentsMargins(20, 0, 20, 0)
        center_layout.addWidget(scroll_area)

        outer_layout = QVBoxLayout()
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        outer_layout.addLayout(center_layout)
        self.setLayout(outer_layout)
        self.apply_replicate_heuristic()

    def showEvent(self, event):
            """
            Ensures the wizard window is centered on the screen and has a 
            consistent minimum size when first displayed.
            """
            super().showEvent(event)
        
            wizard = self.wizard()
            if wizard is not None:
                # Set standard dimensions for the wizard window
                wizard.setMinimumSize(600, 500)   # ⭐ critical
                wizard.resize(750, 550)
        
                # Center the window on the user's screen
                frame = wizard.frameGeometry()
                center_point = wizard.screen().availableGeometry().center()
                frame.moveCenter(center_point)
                wizard.move(frame.topLeft())
        
        
            if wizard is not None:
            #    wizard.resize(600, 500)   # or your prefer`red size
        
                frame = wizard.frameGeometry()
                center_point = wizard.screen().availableGeometry().center()
                frame.moveCenter(center_point)
                wizard.move(frame.topLeft())

    def validatePage(self):
        # Replicate percentage (already correct)
        self.model.replicate_percentage = self.spin_replicate_pct.value() / 100.0

        # Volume level COUNT
        self.model.number_of_volume_levels = self.spin_volumes.value()
        
        # Populate volume levels based on count (using mnemonics)
        count = self.model.number_of_volume_levels
        self.model.volume_levels = [f"Volume_{i:02d}" for i in range(1, count + 1)]

        # Mode
        if self.radio_relative.isChecked():
            self.model.volume_mode = "relative"
            self.model.volume_unit = None
        else:
            self.model.volume_mode = "absolute"
            self.model.volume_unit = self.combo_units.currentText()

        return True
