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

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QIcon
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    return os.path.join(BASE_DIR, *parts)


def parse_solver(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if "--halley" in args:
        return "halley"
    return "vba"


def main(argv=None):
    solver = parse_solver(argv)
    os.environ["MULTXEU_SOLVER"] = solver

    app = QApplication(sys.argv)

    # Load stylesheet and icon (optional)
    stylesheet_path = resource_path("styles.qss")
    icon_path = resource_path("icons", "nodes.ico")

    app.setStyle("Fusion")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Load stylesheet if present
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        pass

    from wizard.wizard_controller import WizardController

    wizard = WizardController()
    wizard.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main(sys.argv[1:])
