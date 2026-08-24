import random
from unittest.mock import patch

from models.layout_reference_table import build_layout_reference_table


def build_export_paths(timestamp: str, slice_count: int, include_error: bool, error_percent: int = 5):
    normal_path = f"{timestamp}_Vol{slice_count:02d}.xlsx"
    if not include_error:
        return [normal_path]
    return [normal_path, f"{timestamp}_Vol{slice_count:02d}_err{error_percent}pc.xlsx"]


def test_build_layout_reference_table_orders_replicates_after_base_then_fill_plates():
    with patch("random.sample", side_effect=lambda rows, k: rows[1:3][:k]):
        rows = build_layout_reference_table(
            mixture_ids=["M1", "M2"],
            slice_count=2,
            free_format=False,
            plate_format="2x2",
            rows=2,
            cols=2,
            include_replicates=True,
            replicate_percent=50,
            fill_plates=True,
            include_error=False,
            error_percent=0,
        )

    assert [entry["replicate_status"] for entry in rows[:4]] == ["Base", "Base", "Base", "Base"]
    assert [entry["replicate_status"] for entry in rows[4:6]] == ["Replicate", "Replicate"]
    assert [entry["replicate_status"] for entry in rows[6:8]] == ["Extra replicate (plate filling)", "Extra replicate (plate filling)"]

    assert [entry["origin_id"] for entry in rows[4:6]] == ["EXP002", "EXP003"]
    assert [entry["id"] for entry in rows[4:6]] == ["EXP002R1", "EXP003R2"]
    assert [entry["well_address"] for entry in rows[:6]] == ["A1", "A2", "B1", "B2", "A1", "A2"]
    assert rows[0]["experiment_code"] == "EXP_M1_S1_A1"
    assert rows[4]["experiment_code"] == "EXP_M1_S2_A1"
    assert rows[5]["experiment_code"] == "EXP_M2_S1_A2"
    assert rows[4]["origin_plate_ref"] == "Plate1.A2"
    assert rows[5]["origin_plate_ref"] == "Plate1.B1"


def test_build_export_paths_adds_err_suffix_only_when_error_export_is_requested():
    assert build_export_paths("260823_2255", 1, False) == ["260823_2255_Vol01.xlsx"]
    assert build_export_paths("260823_2255", 1, True, 2) == [
        "260823_2255_Vol01.xlsx",
        "260823_2255_Vol01_err2pc.xlsx",
    ]
    assert build_export_paths("260823_2255", 2, True, 5) == [
        "260823_2255_Vol02.xlsx",
        "260823_2255_Vol02_err5pc.xlsx",
    ]
