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


from dataclasses import dataclass, field


@dataclass
class MultXeuModel:
    """
    Data model shared across PagePhysChem and PageGenerateMatrix.
    Stores all user selections and generated PhysChem data.
    """

    # ---------------------------------------------------------
    # Page 1 — PhysChem Generator (Explore: Single + Multi)
    # ---------------------------------------------------------

    # Single-system parameters
    n_components: int = 4
    main_component_level: int = 80

    # Multi-system PhysChem parameters
    use_auto: bool = True
    allow_addition: int = 0
    max_addition: int = 0
    max_slices: int = 3
    modulation_percent: int = 20
    num_unique_mixtures: int = 10
    num_systems: int = 10

    # PhysChem data (to be filled later)
    single_system: dict = field(default_factory=dict)
    physchem_matrix: dict = field(default_factory=dict)

    # ---------------------------------------------------------
    # Page 2 — Plate Picker + MultXeu metadata
    # ---------------------------------------------------------

    # Plate layout
    plate_rows: int = 4
    plate_cols: int = 6
    free_format: bool = False

    # Plate metadata
    fill_to_full_plates: bool = False

    # Replicates
    replicate_percent: int = 0

    # Analytical error
    analytical_error_percent: int = 0

    # ---------------------------------------------------------
    # Internal solver data (filled after test_run.py)
    # ---------------------------------------------------------

    # Raw solver output (eutectic path, gradients, etc.)
    solver_output: dict = field(default_factory=dict)

    # Sliced experimental matrix (after recovery slicing)
    sliced_matrix: list = field(default_factory=list)

    # Final Excel-ready experiments
    excel_experiments: list = field(default_factory=list)

    # Output directory for generated Excel files
    export_dir: str = "data"
