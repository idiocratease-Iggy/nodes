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
    randomize_design: bool = False
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
