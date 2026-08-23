# layout_reference_table.py

import math
from dataclasses import dataclass, asdict
from typing import List
import openpyxl
from openpyxl import Workbook



# ---------------------------------------------------------
# Layout entry structure (CRYSS DOE lineage)
# ---------------------------------------------------------
@dataclass
class LayoutEntry:
    id: str
    origin_id: str
    origin_plate_ref: str
    replicate_status: str

    mixture_id: str
    slice_number: int

    plate_number: int
    well_address: str
    block_number: int

    replicate_index: int
    experiment_code: str

    # meta flags
    free_format: bool
    fill_plates: bool
    replicate_percent: int
    include_error: bool
    error_percent: int


# ---------------------------------------------------------
# Well address generator (fixed format only)
# ---------------------------------------------------------
def generate_well_addresses(rows: int, cols: int) -> List[str]:
    addresses = []
    for r in range(rows):
        row_letter = chr(ord('A') + r)
        for c in range(1, cols + 1):
            addresses.append(f"{row_letter}{c}")
    return addresses


# ---------------------------------------------------------
# Experiment code generator
# ---------------------------------------------------------
def make_experiment_code(mixture_id: str, slice_number: int, well: str) -> str:
    return f"EXP_{mixture_id}_S{slice_number}_{well}"


# ---------------------------------------------------------
# Main builder
# ---------------------------------------------------------
def build_layout_reference_table(
    mixture_ids,
    slice_count,
    free_format,
    plate_format,
    rows,
    cols,
    include_replicates,
    replicate_percent,
    fill_plates,
    include_error,
    error_percent,
    randomize_order,
) -> List[dict]:

    if not mixture_ids:
        return []

    ordered_mixture_ids = list(dict.fromkeys(str(mixture_id) for mixture_id in mixture_ids))
    slice_count = int(slice_count) if slice_count is not None else 1
    slice_count = max(1, slice_count)
    free_format = bool(free_format)
    rows = int(rows)
    cols = int(cols)
    include_replicates = bool(include_replicates)
    replicate_percent = int(replicate_percent)
    fill_plates = bool(fill_plates)
    include_error = bool(include_error)
    error_percent = int(error_percent)
    randomize_order = bool(randomize_order)

    if free_format:
        wells_per_plate = 999999  # effectively infinite
        fixed_wells = None
    else:
        fixed_wells = generate_well_addresses(rows, cols)
        wells_per_plate = len(fixed_wells)

    # 1) Base experiments
    n_mixtures = len(ordered_mixture_ids)
    base_experiments = n_mixtures * slice_count

    # 2) Replicate percentage
    extra_replicates = math.ceil(base_experiments * (replicate_percent / 100.0)) if include_replicates else 0
    total_experiments = base_experiments + extra_replicates

    # 3) Fill-plate logic (only in fixed format)
    fill_plate_extras = 0
    if not free_format and fill_plates:
        leftover = total_experiments % wells_per_plate
        if leftover > 0:
            fill_plate_extras = wells_per_plate - leftover
            total_experiments += fill_plate_extras

    print("DEBUG: FREE_FORMAT =", free_format)
    print("DEBUG: plate_format =", plate_format)
    print("DEBUG: rows =", rows)
    print("DEBUG: cols =", cols)
    print("DEBUG: base_experiments =", base_experiments)
    print("DEBUG: extra_replicates =", extra_replicates)
    print("DEBUG: fill_plate_extras =", fill_plate_extras)
    print("DEBUG: total_experiments =", total_experiments)

    table: List[dict] = []

    # 4) Build rows for a single slice scenario.
    # Each call to this function represents one independent plate layout, so the
    # numbering and well addressing must restart from 1 / A1 for that scenario.
    for exp_index in range(total_experiments):
        if free_format:
            plate_number = 1
            well_address = f"{exp_index+1:03d}"
            origin_plate_ref = ""
            block_number = 1
        else:
            plate_number = (exp_index // wells_per_plate) + 1
            well_index = exp_index % wells_per_plate
            well_address = fixed_wells[well_index]
            block_number = 1
            origin_plate_ref = (
                f"Plate{plate_number}.{well_address}"
                if exp_index < base_experiments
                else ""
            )

        base_index = exp_index % base_experiments
        mixture_idx = base_index // slice_count
        slice_number = (base_index % slice_count) + 1
        mixture_id = ordered_mixture_ids[mixture_idx]

        if exp_index < base_experiments:
            replicate_status = "Base"
            replicate_index = 1
            id_suffix = ""
        elif exp_index < base_experiments + extra_replicates:
            replicate_status = "Replicate"
            replicate_index = (exp_index - base_experiments) + 1
            id_suffix = f"R{replicate_index}"
        else:
            replicate_status = "Extra replicate (plate filling)"
            replicate_index = (exp_index - base_experiments - extra_replicates) + 1
            id_suffix = f"F{replicate_index}"

        base_exp_id = f"EXP{base_index+1:03d}"
        id_full = base_exp_id + id_suffix
        experiment_code = make_experiment_code(mixture_id, slice_number, well_address)

        entry = LayoutEntry(
            id=id_full,
            origin_id=base_exp_id,
            origin_plate_ref=origin_plate_ref,
            replicate_status=replicate_status,
            mixture_id=mixture_id,
            slice_number=slice_number,
            plate_number=plate_number,
            well_address=well_address,
            block_number=block_number,
            replicate_index=replicate_index,
            experiment_code=experiment_code,
            free_format=free_format,
            fill_plates=fill_plates,
            replicate_percent=replicate_percent,
            include_error=include_error,
            error_percent=error_percent,
        )

        table.append(asdict(entry))

    if randomize_order:
        import random
        random.shuffle(table)

    return table


# ---------------------------------------------------------
# Excel writer
# ---------------------------------------------------------
def write_excel(filename="layout_test.xlsx"):
    layout = build_layout_reference_table(
        mixture_ids=["260823_001", "260823_002", "260823_003", "260823_004"],
        slice_count=3,
        free_format=False,
        plate_format="6x4",
        rows=6,
        cols=4,
        include_replicates=True,
        replicate_percent=25,
        fill_plates=True,
        include_error=True,
        error_percent=5,
        randomize_order=False,
    )

    wb = Workbook()

    tracking_headers = [
        "ID",
        "Origin ID",
        "Replicate Status",
        "Mixture ID",
        "Slice Number",
        "Experiment Code",
    ]
    if not False:
        tracking_headers = [
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

    ws1 = wb.active
    ws1.title = "LayoutTracking"
    ws1.append(tracking_headers)

    for row in layout:
        if False:
            ws1.append([
                row["id"],
                row["origin_id"],
                row["replicate_status"],
                row["mixture_id"],
                row["slice_number"],
                row["experiment_code"],
            ])
        else:
            ws1.append([
                row["id"],
                row["origin_id"],
                row["origin_plate_ref"],
                row["replicate_status"],
                f"Plate{row['plate_number']}",
                row["well_address"],
                row["mixture_id"],
                row["slice_number"],
                row["experiment_code"],
            ])

    ws2 = wb.create_sheet("ExperimentDesign")

    if False:
        design_headers = [
            "Experiment Code",
            "Mixture ID",
            "Slice Number",
            "Notes",
        ]
        ws2.append(design_headers)

        for row in layout:
            ws2.append([
                row["experiment_code"],
                row["mixture_id"],
                row["slice_number"],
                "",
            ])
    else:
        ws2.append([
            "Experiment Code", "Mixture ID", "Slice Number",
            "Plate", "Well", "Notes"
        ])

        for row in layout:
            ws2.append([
                row["experiment_code"],
                row["mixture_id"],
                row["slice_number"],
                f"Plate{row['plate_number']}",
                row["well_address"],
                "",
            ])

    wb.save(filename)
    print(f"Excel file written: {filename}")


# ---------------------------------------------------------
# Run prototype
# ---------------------------------------------------------
if __name__ == "__main__":
    write_excel()
