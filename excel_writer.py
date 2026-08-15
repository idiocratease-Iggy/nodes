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


import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from PyQt6.QtWidgets import QFileDialog


def save_experiments_to_excel(parent, experiments, num_components=0, volume_mode="relative", volume_unit=None):
    """
    Opens a save-file dialogue, then writes the experiment list
    into a clean, formatted Excel template.
    """



    # -----------------------------
    # 1. Ask user where to save file
    # -----------------------------
    import os
    from PyQt6.QtCore import QStandardPaths

    default_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    if not default_path:
        default_path = os.path.expanduser("~\\Documents")

    filename, _ = QFileDialog.getSaveFileName(
        parent,
        "Save CRYSS Experiment Template",
        default_path,
        "Excel Files (*.xlsx)"
    )

    if not filename:
        return False  # user cancelled

    # -----------------------------
    # 2. Create workbook + sheet
    # -----------------------------
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CRYSS Experiments"

    # -----------------------------
    # 3. Define column headers
    # -----------------------------
    headers = [
        "ID",
        "Origin ID",
        "Origin Plate Ref",
        "Starting Mix",
        "Solvent",
        "Volume Level",
        "Salt Former",
        "Mass (g)",          # NEW FIELD
        "Replicate Status",
        "Plate",
        "Well",
    ]

    # If absolute volume mode is used, append the unit to the Volume Level header
    if volume_mode == "absolute" and volume_unit:
        headers[5] = f"Volume Level ({volume_unit})"

    # Add Component columns dynamically
    for i in range(1, num_components + 1):
        headers.append(f"Component {i}")

    headers.append("Notes")




    ws.append(headers)

    # -----------------------------
    # 4. Write experiment rows
    # -----------------------------
    for exp in experiments:
        row = [
            exp.id,
            exp.origin_id,
            exp.origin_plate_ref,
            exp.starting_mix,
            exp.solvent,
            exp.volume,            # e.g. "Volume_01"
            exp.salt_former,
            "",                    # Mass (g) — blank for chemist
            exp.replicate_status,
            exp.plate,
            exp.well,
        ]

        # Add empty strings for Component columns
        for _ in range(num_components):
            row.append("")

        row.append(exp.notes)
        ws.append(row)

    # -----------------------------
    # 5. Formatting (Auto-adjust column width)
    # -----------------------------
    for col in range(1, ws.max_column + 1):
        column_letter = get_column_letter(col)
        
        # Find the maximum length of any cell content in this column to determine width
        max_length = 0
        for row_idx in range(1, ws.max_row + 1):
            cell_value = str(ws.cell(row=row_idx, column=col).value) if ws.cell(row=row_idx, column=col).value else ""
            if len(cell_value) > max_length:
                max_length = len(cell_value)
        
        # Set width with a small buffer for padding
        ws.column_dimensions[column_letter].width = max_length + 2

        header_cell = ws.cell(row=1, column=col)
        header_cell.font = Font(bold=True)
        header_cell.fill = openpyxl.styles.PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        header_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Save the workbook
    try:
        wb.save(filename)
        return True
    except Exception as e:
        print(f"Error saving excel file: {e}")
        return False


