# excel_writer.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def _normalise_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, float):
        return round(value, 10)
    return value


def _apply_header_style(ws, start_col: int, end_col: int, fill_color: str, title: str, border: bool = True):
    start_letter = get_column_letter(start_col)
    end_letter = get_column_letter(end_col)
    merge_range = f"{start_letter}1:{end_letter}1"
    if not any(str(rng) == merge_range for rng in ws.merged_cells.ranges):
        ws.merge_cells(merge_range)

    title_cell = ws.cell(1, start_col)
    title_cell.value = title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    title_cell.fill = PatternFill(fill_type="solid", fgColor=fill_color)
    title_cell.font = Font(bold=True, color="FFFFFF")
    if border:
        title_cell.border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

    for col in range(start_col, end_col + 1):
        cell = ws.cell(2, col)
        cell.fill = PatternFill(fill_type="solid", fgColor=fill_color)
        cell.font = Font(bold=True, color="FFFFFF")
        if border:
            cell.border = Border(
                left=Side(style="thin", color="000000"),
                right=Side(style="thin", color="000000"),
                top=Side(style="thin", color="000000"),
                bottom=Side(style="thin", color="000000"),
            )


def write_excel(filename: str | Path, rows: Iterable[Dict[str, Any]] | Mapping[str, Iterable[Dict[str, Any]]]):
    """Write a workbook from one or more row-dictionary collections."""
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    if isinstance(rows, Mapping):
        sheet_specs = rows
    else:
        sheet_specs = {"matrix_layer": list(rows)}

    first_sheet = True
    for sheet_name, sheet_rows in sheet_specs.items():
        sheet_rows = list(sheet_rows)
        if not sheet_rows:
            continue
        if first_sheet:
            ws = wb.active
            ws.title = str(sheet_name)
            first_sheet = False
        else:
            ws = wb.create_sheet(title=str(sheet_name))

        headers = list(sheet_rows[0].keys())
        component_count = 0
        for header in headers:
            if header.startswith(("Xc_", "Xs_", "Xliq_")):
                component_count = max(component_count, int(header.split("_")[-1]))

        ws.cell(1, 1, value="")
        ws.cell(2, 1, value="Mixture_id")

        header_labels = {
            "Mixture_id": "Mixture_id",
            "R": "Recovery",
            "RelSolVol": "Rel. Sol. Volume",
            "RelSolVol(Rmax)": "Rel. Sol. Volume @ Rmax",
        }
        for idx, header in enumerate(headers, start=1):
            if header in header_labels:
                ws.cell(2, idx, value=header_labels[header])
            elif header.startswith("Xc_"):
                component_index = header.split("_")[-1]
                ws.cell(2, idx, value=f"Component {component_index}")
            elif header.startswith("Xs_"):
                component_index = header.split("_")[-1]
                ws.cell(2, idx, value=f"Component {component_index}")
            elif header.startswith("Xliq_"):
                component_index = header.split("_")[-1]
                ws.cell(2, idx, value=f"Component {component_index}")
            else:
                ws.cell(2, idx, value=header)

        if component_count <= 0:
            component_count = 2

        composition_group_width = component_count
        group_start_col = 2
        group_end_col = group_start_col + composition_group_width - 1
        for group_idx, (title, fill_color) in enumerate([
            ("Starting Composition", "5B9BD5"),
            ("Solid Composition", "70AD47"),
            ("Liquor Composition", "FFC000"),
        ], start=1):
            start_col = group_start_col + (group_idx - 1) * composition_group_width
            end_col = start_col + composition_group_width - 1
            if start_col > 1:
                ws.cell(1, start_col, value=title)
                _apply_header_style(ws, start_col, end_col, fill_color, title)

        metrics_start_col = group_start_col + (3 * composition_group_width)
        for col in range(metrics_start_col, metrics_start_col + 4):
            ws.cell(1, col, value="")

        for col in range(metrics_start_col, metrics_start_col + 4):
            cell = ws.cell(1, col)
            cell.fill = PatternFill(fill_type="solid", fgColor="D9D9D9")
            cell.font = Font(bold=True)
            cell.border = Border(
                left=Side(style="thin", color="000000"),
                right=Side(style="thin", color="000000"),
                top=Side(style="thin", color="000000"),
                bottom=Side(style="thin", color="000000"),
            )

        for row_idx, row in enumerate(sheet_rows, start=3):
            ws.append([_normalise_value(row.get(h)) for h in headers])

        for row_idx in range(3, ws.max_row + 1):
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row_idx, col_idx)
                if col_idx in range(2, metrics_start_col):
                    cell.number_format = "0.00000%"
                elif col_idx in {metrics_start_col, metrics_start_col + 2}:
                    cell.number_format = "0.00%"
                elif col_idx in {metrics_start_col + 1, metrics_start_col + 3}:
                    cell.number_format = "0.000"
                if col_idx in range(2, metrics_start_col):
                    cell.alignment = Alignment(horizontal="center")

        ws.freeze_panes = "A3"
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 14
        for row in ws.iter_rows(min_row=1, max_row=2):
            for cell in row:
                cell.font = Font(bold=True)

        for row in ws.iter_rows(min_row=1, max_row=2):
            for cell in row:
                if cell.coordinate in ws.merged_cells and cell.value is None:
                    continue
                if cell.value is None:
                    cell.value = ""

    if wb.sheetnames and not wb.active.max_row and not wb.active.max_column:
        wb.remove(wb.active)

    wb.save(output_path)
    print(f"[Excel] Wrote workbook to {output_path}")
    return output_path
