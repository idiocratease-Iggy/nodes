from pathlib import Path

from openpyxl import load_workbook

import layout_reference_table as ref


FREE_FORMAT_HEADERS = [
    "ID",
    "Origin ID",
    "Replicate Status",
    "Mixture ID",
    "Slice Number",
    "Experiment Code",
]

FIXED_FORMAT_HEADERS = [
    "ID",
    "Origin ID",
    "Origin Plate Ref",
    "Replicate Status",
    "Plate",
    "Well",
    "Mixture ID",
    "Slice Number",
    "Experiment Code",
]


def _assert_tracking_headers(filename: str, expected_headers):
    wb = load_workbook(filename)
    tracking = wb["LayoutTracking"]
    actual_headers = [cell.value for cell in tracking[1]]
    assert actual_headers == expected_headers, (actual_headers, expected_headers)


def _assert_free_format_row(filename: str):
    wb = load_workbook(filename)
    row = [cell.value for cell in wb["LayoutTracking"][2]]
    assert row[0] == "EXP001"
    assert row[5].startswith("EXP_")
    assert "Origin Plate Ref" not in row
    assert "Plate" not in row
    assert "Well" not in row


def _assert_fixed_format_row(filename: str):
    wb = load_workbook(filename)
    row = [cell.value for cell in wb["LayoutTracking"][2]]
    assert row[0] == "EXP001"
    assert row[8].startswith("EXP_")
    assert "Origin Plate Ref" in [cell.value for cell in wb["LayoutTracking"][1]]


def run_export_checks():
    original_mode = ref.FREE_FORMAT
    try:
        ref.FREE_FORMAT = True
        output = Path("free_format.xlsx")
        ref.write_excel(str(output))
        _assert_tracking_headers(str(output), FREE_FORMAT_HEADERS)
        _assert_free_format_row(str(output))
        assert output.exists()

        ref.FREE_FORMAT = False
        output = Path("fixed_format.xlsx")
        ref.write_excel(str(output))
        _assert_tracking_headers(str(output), FIXED_FORMAT_HEADERS)
        _assert_fixed_format_row(str(output))
        assert output.exists()
    finally:
        ref.FREE_FORMAT = original_mode


if __name__ == "__main__":
    run_export_checks()
    print("Export checks passed.")
