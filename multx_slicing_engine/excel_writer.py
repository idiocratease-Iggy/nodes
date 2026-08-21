# excel_writer.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from openpyxl import Workbook
from openpyxl.styles import Font


def _normalise_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, float):
        return round(value, 10)
    return value


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
        ws.append([_normalise_value(h) for h in headers])
        for row in sheet_rows:
            ws.append([_normalise_value(row.get(h)) for h in headers])

        for cell in ws[1]:
            cell.font = Font(bold=True)

    if wb.sheetnames and not wb.active.max_row and not wb.active.max_column:
        wb.remove(wb.active)

    wb.save(output_path)
    print(f"[Excel] Wrote workbook to {output_path}")
    return output_path
