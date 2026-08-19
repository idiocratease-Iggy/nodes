import json

from PyQt6.QtWidgets import QApplication

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
