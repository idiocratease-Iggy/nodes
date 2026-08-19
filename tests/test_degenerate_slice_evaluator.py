from pathlib import Path
from types import SimpleNamespace

import pytest

from multx_slicing_engine.canonical_eutectic import _normalize_summary_rows
from multx_slicing_engine.canonical_gradients import compute_segment_gradients
from multx_slicing_engine.canonical_types import EutecticPathState, Node, Segment
from multx_slicing_engine.evaluate_recovery import evaluate_at_recovery
from multx_slicing_engine.multi_mixture_harness import run_multi_mixture_harness_from_json


def _make_state(segments):
    initial = SimpleNamespace(X=[0.5, 0.5, 0.0])
    nodes = [
        Node(index=0, Tk=0.0, Xeu=[0.0, 0.0, 1.0], Xliq_after=[0.0, 0.0, 1.0], recovery=0.0, removed_components=[], multi_removal=False, solvent=0.0),
        Node(index=1, Tk=0.0, Xeu=[0.4, 0.6, 0.0], Xliq_after=[0.3, 0.7, 0.0], recovery=0.75, removed_components=[], multi_removal=False, solvent=0.0),
        Node(index=2, Tk=0.0, Xeu=[0.2, 0.8, 0.0], Xliq_after=[0.1, 0.9, 0.0], recovery=0.5, removed_components=[], multi_removal=False, solvent=0.0),
        Node(index=3, Tk=0.0, Xeu=[0.0, 1.0, 0.0], Xliq_after=[0.0, 1.0, 0.0], recovery=0.0, removed_components=[], multi_removal=False, solvent=0.0),
    ]
    return EutecticPathState(
        solver="vba",
        initial_mixture=initial,
        nodes=nodes,
        segments=segments,
        Rmax=1.0,
        final_purity=0.0,
        tk_nodes=[],
        degenerate_cascade=True,
    )


def test_normalize_summary_rows_removes_duplicate_recovery_nodes():
    rows = [
        [1.0, 0.90, 0.10, 0.00],
        [0.95, 0.50, 0.50, 0.00],
        [0.95, 0.50, 0.50, 0.00],
        [0.90, 0.10, 0.90, 0.00],
    ]

    normalized = _normalize_summary_rows(rows)

    assert [row[0] for row in normalized] == [1.0, 0.95, 0.90]


def test_evaluate_recovery_prefers_later_segment_after_collapsed_boundaries():
    state = _make_state([
        Segment(index=0, start_R=1.0, end_R=0.75, Xliq_start=[0.9, 0.1, 0.0], Xliq_end=[0.2, 0.8, 0.0], solvent_start=0.0, solvent_end=0.5, metadata={}),
        Segment(index=1, start_R=0.75, end_R=0.75, Xliq_start=[0.1, 0.9, 0.0], Xliq_end=[0.1, 0.9, 0.0], solvent_start=0.5, solvent_end=0.5, metadata={}),
        Segment(index=2, start_R=0.75, end_R=0.50, Xliq_start=[0.1, 0.9, 0.0], Xliq_end=[0.0, 1.0, 0.0], solvent_start=0.5, solvent_end=1.0, metadata={}),
    ])

    result = evaluate_at_recovery(state, compute_segment_gradients(state), 0.75)

    assert result.Xliq == pytest.approx([0.1, 0.9, 0.0])


def test_zeroed_component_stays_zero_during_interpolation():
    state = _make_state([
        Segment(index=0, start_R=1.0, end_R=0.5, Xliq_start=[0.5, 0.0, 0.5], Xliq_end=[0.1, 0.2, 0.7], solvent_start=0.0, solvent_end=1.0, metadata={}),
    ])

    result = evaluate_at_recovery(state, compute_segment_gradients(state), 0.75)

    assert result.Xliq[1] == pytest.approx(0.0)


def test_json_route_prints_slice_section(capsys):
    json_path = Path(__file__).resolve().parents[1] / "data" / "physchem_matrix.json"

    run_multi_mixture_harness_from_json(str(json_path), max_mixtures=1)

    captured = capsys.readouterr().out
    assert "SLICES FOR MIXTURE" in captured
    assert "SLICES FOR ALL MIXTURES" in captured
