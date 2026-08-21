import json
import re
from pathlib import Path

from openpyxl import load_workbook
from PyQt6.QtWidgets import QApplication

from multx_slicing_engine.excel_writer import write_excel

from input_writer import build_configuration_json, Params, write_json
from mixture_generator import generate_mixture_set
from models.multxeu_model import MultXeuModel
from multx_slicing_engine.slice_generator import resolve_slice_count
from wizard.pages.page_generate_matrix import PageGenerateMatrix
from wizard.pages.page_physchem import PagePhysChem


def test_page_physchem_syncs_unique_mixture_count():
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    page = PagePhysChem(model)

    page.spin_systems.setValue(5)
    page._sync_model_state()

    assert model.num_systems == 5


def test_generate_mixture_set_respects_requested_count():
    params = Params(
        n_components=4,
        main_component_index=0,
        main_component_level=0.8,
        stochastic_variance=0.1,
        max_addition_compounds=1,
        tm_base=130.0,
        tm_sd_factor=1.0,
        dh_sd_factor=1.0,
        max_solvent_volumes=3,
    )
    config = build_configuration_json(params)

    mixtures = generate_mixture_set(config, num_systems=5)

    assert len(mixtures) == 5
    assert all(isinstance(item, dict) for item in mixtures)


def test_generate_matrix_populates_model_with_selected_count(tmp_path):
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    model.num_unique_mixtures = 5
    page = PageGenerateMatrix(model)

    config = build_configuration_json(Params(
        n_components=4,
        main_component_index=0,
        main_component_level=0.8,
        stochastic_variance=0.2,
        max_addition_compounds=0,
        tm_base=130.0,
        tm_sd_factor=1.0,
        dh_sd_factor=1.0,
        max_solvent_volumes=3,
    ))
    config_path = tmp_path / "physchem_config.json"
    write_json(str(config_path), config)

    mixtures = page.generate_mixtures(config_path=str(config_path))

    assert len(mixtures) == 5
    assert len(model.physchem_matrix) == 5
    assert model.physchem_matrix == mixtures


def test_export_writes_single_sheet_workbooks_with_slice_count_names(tmp_path):
    app = QApplication.instance() or QApplication([])
    model = MultXeuModel()
    page = PageGenerateMatrix(model)

    layer = {
        "mixture_anchors": [{
            "mixture_id": "mix_1",
            "component_count": 2,
            "Xc": [0.6, 0.4],
            "Rmax": 0.5,
            "RelSolVol_Rmax": 1.0,
            "slice_count": 2,
            "segment_count": 1,
        }],
        "segments": [{
            "mixture_id": "mix_1",
            "segment_index": 0,
            "start_R": 1.0,
            "end_R": 0.5,
            "solvent_start": 0.0,
            "solvent_end": 1.0,
            "Xliq_start": [0.6, 0.4],
            "Xliq_end": [0.5, 0.5],
        }],
        "slice_arrays": {
            "slice_count_1": [{
                "mixture_id": "mix_1",
                "slice_count": 1,
                "slice_index": 1,
                "R": 0.75,
                "RelSolVol": 0.5,
                "Xc": [0.6, 0.4],
                "Xs": [0.7, 0.3],
                "Xliq": [0.5, 0.5],
                "R_check": [0.75, 0.75],
                "mass_balance_ok": True,
                "correction_applied": False,
                "correction_delta_R": 0.0,
                "correction_flagged": False,
            }],
            "slice_count_2": [{
                "mixture_id": "mix_1",
                "slice_count": 2,
                "slice_index": 1,
                "R": 0.6,
                "RelSolVol": 1.0,
                "Xc": [0.6, 0.4],
                "Xs": [0.65, 0.35],
                "Xliq": [0.5, 0.5],
                "R_check": [0.6, 0.6],
                "mass_balance_ok": True,
                "correction_applied": False,
                "correction_delta_R": 0.0,
                "correction_flagged": False,
            }],
        },
    }

    written_files = page.write_matrix_layer_exports(layer=layer, output_dir=tmp_path)

    assert len(written_files) == 2
    assert all(Path(path).exists() for path in written_files)
    for path in written_files:
        assert re.search(r"_Vol\d{2}\.xlsx$", Path(path).name)
        wb = load_workbook(path)
        assert len(wb.worksheets) == 1
        ws = wb.active
        assert ws.title == "slice_records"
        headers = [cell.value for cell in ws[2]]
        assert headers[0] == "Mixture_id"
        assert headers[1] == "Component 1"
        assert headers[-2] == "Rmax"
        assert headers[-1] == "Rel. Sol. Volume @ Rmax"


def test_excel_writer_adds_styled_two_row_headers(tmp_path):
    output_path = tmp_path / "styled.xlsx"
    write_excel(output_path, {
        "slice_records": [
            {
                "Mixture_id": "mix_1",
                "Xc_1": 0.8,
                "Xc_2": 0.2,
                "Xs_1": 0.7,
                "Xs_2": 0.3,
                "Xliq_1": 0.5,
                "Xliq_2": 0.5,
                "R": 0.75,
                "RelSolVol": 1.25,
                "Rmax": 0.6,
                "RelSolVol(Rmax)": 2.5,
            }
        ]
    })

    wb = load_workbook(output_path)
    ws = wb.active

    assert ws.cell(1, 2).value == "Starting Composition"
    assert ws.cell(1, 4).value == "Solid Composition"
    assert ws.cell(1, 6).value == "Liquor Composition"
    assert ws.cell(2, 2).value == "Component 1"
    assert ws.cell(2, 3).value == "Component 2"
    assert ws.cell(2, 8).value == "Recovery"
    assert ws.cell(2, 9).value == "Rel. Sol. Volume"
    assert ws.cell(2, 10).value == "Rmax"
    assert ws.cell(2, 11).value == "Rel. Sol. Volume @ Rmax"

    assert ws.cell(3, 2).number_format == "0.00000%"
    assert ws.cell(3, 8).number_format == "0.00%"
    assert ws.cell(3, 9).number_format == "0.000"
    assert ws.cell(3, 10).number_format == "0.00%"

    assert any(str(rng) == "B1:C1" for rng in ws.merged_cells.ranges)
    assert ws.freeze_panes == "A3"


def test_excel_writer_merges_header_groups_by_component_count(tmp_path):
    output_path = tmp_path / "four_component.xlsx"
    write_excel(output_path, {
        "slice_records": [
            {
                "Mixture_id": "mix_1",
                "Xc_1": 0.8,
                "Xc_2": 0.1,
                "Xc_3": 0.05,
                "Xc_4": 0.05,
                "Xs_1": 0.7,
                "Xs_2": 0.1,
                "Xs_3": 0.1,
                "Xs_4": 0.1,
                "Xliq_1": 0.5,
                "Xliq_2": 0.2,
                "Xliq_3": 0.2,
                "Xliq_4": 0.1,
                "R": 0.75,
                "RelSolVol": 1.25,
                "Rmax": 0.6,
                "RelSolVol(Rmax)": 2.5,
            }
        ]
    })

    wb = load_workbook(output_path)
    ws = wb.active

    assert any(str(rng) == "B1:E1" for rng in ws.merged_cells.ranges)
    assert any(str(rng) == "F1:I1" for rng in ws.merged_cells.ranges)
    assert any(str(rng) == "J1:M1" for rng in ws.merged_cells.ranges)


def test_slice_count_comes_from_mixture_slicing_config():
    summary = {
        "mixture": {
            "mixture_id": "260819_001",
            "slicing": {"max_solvent_volumes": 2},
        }
    }
    assert resolve_slice_count(summary, fallback_num_slices=3) == 2

    metadata_summary = {
        "mixture": {
            "mixture_id": "260819_002",
            "metadata": {"slicing": {"max_solvent_volumes": 4}},
        }
    }
    assert resolve_slice_count(metadata_summary, fallback_num_slices=3) == 4
