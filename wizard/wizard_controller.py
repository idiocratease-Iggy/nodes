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

from PyQt6.QtWidgets import QWizard
from PyQt6.QtGui import QPalette
from PyQt6.QtCore import Qt
from wizard.pages.page_physchem import PagePhysChem
from wizard.pages.page_generate_matrix import PageGenerateMatrix
from models.multxeu_model import MultXeuModel


class WizardController(QWizard):
    def __init__(self):
        super().__init__()

        self.model = MultXeuModel()

        # Add pages in order
        self.addPage(PagePhysChem(self.model))
        self.addPage(PageGenerateMatrix(self.model))

        self.setWindowTitle("MultXeu Wizard")
        self.resize(900, 700)



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

