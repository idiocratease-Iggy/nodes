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

from pathlib import Path

from PyQt6.QtWidgets import QWizard
from PyQt6.QtGui import QPalette, QIcon, QPixmap
from PyQt6.QtCore import Qt
from wizard.pages.page_physchem import PagePhysChem
from wizard.pages.page_generate_matrix import PageGenerateMatrix
from models.multxeu_model import MultXeuModel


class WizardController(QWizard):
    def __init__(self):
        super().__init__()

        icon_path = Path(__file__).resolve().parent.parent / "nodes.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)
            logo_pixmap = icon.pixmap(128, 128)
            self.setPixmap(QWizard.WizardPixmap.LogoPixmap, logo_pixmap)

        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setStyleSheet("""
            QWizard {
                background-color: #1f1f1f;
                color: white;
            }
            QWizard::title {
                color: white;
                background: #2a2a2a;
                font-weight: bold;
                font-size: 22px;
            }
            QWizard QLabel {
                color: white;
                font-size: 14px;
            }
            QLabel, QCheckBox, QRadioButton, QSpinBox,
            QGroupBox, QWizardPage, QAbstractButton {
                color: white;
            }
            QWizard > QLabel {
                color: white;
            }
        """)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setPalette(palette)

        self.model = MultXeuModel()

        self.page_physchem = PagePhysChem(self.model)
        self.page_generate_matrix = PageGenerateMatrix(self.model)

        # print("DEBUG: WizardController same model instance =", self.model is self.page_physchem.model and self.model is self.page_generate_matrix.model)

        # Add pages in order
        self.addPage(self.page_physchem)
        self.addPage(self.page_generate_matrix)

        self.page_sizes = {
            0: (700, 620),
            1: (720, 620),
        }

        self.setWindowTitle("NODES")
        self.currentIdChanged.connect(self._apply_page_size)
        self.currentIdChanged.connect(self._sync_page_button_labels)
        self.currentIdChanged.connect(self._sync_page_button_visibility)
        self._apply_page_size(self.currentId())
        self._sync_page_button_labels(self.currentId())
        self._sync_page_button_visibility(self.currentId())

    def closeEvent(self, event):
        if hasattr(self, "page_physchem"):
            self.page_physchem._close_plot_window()
        super().closeEvent(event)

    def _apply_page_size(self, page_id):
        width, height = self.page_sizes.get(page_id, (700, 620))
        self.resize(width, height)

    def _sync_page_button_labels(self, page_id):
        if self.currentPage() is self.page_generate_matrix:
            if not self.page_generate_matrix.isFinalPage():
                self.page_generate_matrix.update_next_button_text()
        elif self.currentPage() is self.page_physchem:
            self.page_physchem.update_next_button_text()

    def _sync_page_button_visibility(self, page_id):
        next_button = self.button(QWizard.WizardButton.NextButton)
        back_button = self.button(QWizard.WizardButton.BackButton)

        if self.currentPage() is self.page_generate_matrix:
            if next_button is not None:
                next_button.setVisible(False)
                next_button.setEnabled(False)
            if back_button is not None:
                back_button.setVisible(True)
                back_button.setEnabled(True)
            return

        valid = self._is_navigation_ready()

        if next_button is not None:
            next_button.setVisible(valid)
            next_button.setEnabled(valid)
        if back_button is not None:
            back_button.setVisible(valid)
            back_button.setEnabled(valid)

    def _is_navigation_ready(self):
        matrix_ready = bool(getattr(self.model, "physchem_matrix", None))
        json_ready = bool(getattr(self.model, "loaded_json_path", None))
        return matrix_ready or json_ready


class DesignWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Mixture-centric DoE Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.fill_to_full_plates = False


        pal = self.palette()
        pal.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(pal)

        self.model = DesignModel()

        # Load descriptors once
        dm = DescriptorManager(self.model.descriptor_filename)
        self.model.descriptor_df = dm.load()

        # Load salt formers
        from models.salt_former_manager import SaltFormerManager
        sfm = SaltFormerManager(self.model.salt_former_filename)
        self.model.salt_former_data = sfm.load()

        self.setWindowTitle("Mixture-centric DoE Wizard")

        # Pages (updated)
        self.page_components = PageComponents(self.model)
        self.page_solvent_picker = PageSolventPicker(self.model)
        self.page_pca = PagePCA(self.model)
        self.page_salt_formers = PageSaltFormers(self.model)
        self.page_volume_levels = PageVolumeLevels(self.model)
        self.page_plate_picker = PagePlatePicker(self.model)
       

        # Add pages in order
        self.addPage(self.page_components)
        self.addPage(self.page_solvent_picker)
        self.addPage(self.page_pca)
        self.addPage(self.page_salt_formers)
        self.addPage(self.page_volume_levels)
        self.addPage(self.page_plate_picker)


    def accept(self):
        super().accept()

