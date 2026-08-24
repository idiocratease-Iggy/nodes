# layout_reference_table.py

import math
import random
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


def status_rank(row):
    status = row.get("replicate_status", "")
    if status == "Base":
        return 0
    if status == "Replicate":
        return 1
    if status == "Extra replicate (plate filling)":
        return 2
    return 3


def sort_layout_rows(rows: List[dict]) -> List[dict]:
    return sorted(
        rows,
        key=lambda r: (
            status_rank(r),
            str(r.get("mixture_id", "")),
            int(r.get("slice_number", 0) or 0),
            str(r.get("origin_id", r.get("id", ""))),
            str(r.get("id", "")),
            str(r.get("well_address", "")),
        ),
    )


def apply_experimental_error(rows: List[dict], error_percent: int) -> List[dict]:
    mutated_rows = [dict(row) for row in rows]
    if error_percent <= 0:
        return mutated_rows

    for row in mutated_rows:
        for key, value in list(row.items()):
            if key.startswith(("Xc_", "Xs_", "Xliq_")) and value not in (None, ""):
                try:
                    numeric_value = float(value)
                    multiplier = 1.0 + (error_percent / 100.0) * (1 if random.random() >= 0.5 else -1)
                    row[key] = numeric_value * multiplier
                except (TypeError, ValueError):
                    continue

            if key in {"R", "RelSolVol", "Rmax", "RelSolVol(Rmax)"} and value not in (None, ""):
                try:
                    numeric_value = float(value)
                    multiplier = 1.0 + (error_percent / 100.0) * (1 if random.random() >= 0.5 else -1)
                    row[key] = numeric_value * multiplier
                except (TypeError, ValueError):
                    continue

    return mutated_rows


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

    if free_format:
        wells_per_plate = 999999  # effectively infinite
        fixed_wells = None
    else:
        fixed_wells = generate_well_addresses(rows, cols)
        wells_per_plate = len(fixed_wells)

    n_mixtures = len(ordered_mixture_ids)
    base_experiments = n_mixtures * slice_count
    extra_replicates = math.ceil(base_experiments * (replicate_percent / 100.0)) if include_replicates else 0
    total_experiments = base_experiments + extra_replicates

    fill_plate_extras = 0
    if not free_format and fill_plates:
        leftover = total_experiments % wells_per_plate
        if leftover > 0:
            fill_plate_extras = wells_per_plate - leftover
            total_experiments += fill_plate_extras

    base_rows: List[dict] = []
    for base_index in range(base_experiments):
        mixture_idx = base_index // slice_count
        slice_number = (base_index % slice_count) + 1
        mixture_id = ordered_mixture_ids[mixture_idx]
        base_exp_id = f"EXP{base_index+1:03d}"

        entry = LayoutEntry(
            id=base_exp_id,
            origin_id=base_exp_id,
            origin_plate_ref="",
            replicate_status="Base",
            mixture_id=mixture_id,
            slice_number=slice_number,
            plate_number=0,
            well_address="",
            block_number=1,
            replicate_index=1,
            experiment_code="",
            free_format=free_format,
            fill_plates=fill_plates,
            replicate_percent=replicate_percent,
            include_error=include_error,
            error_percent=error_percent,
        )
        base_rows.append(asdict(entry))

    replicate_rows: List[dict] = []
    if extra_replicates:
        replicate_candidates = random.sample(base_rows, k=extra_replicates) if base_rows else []
        for replicate_index, source_row in enumerate(replicate_candidates, start=1):
            source_origin_id = source_row["origin_id"]
            entry = LayoutEntry(
                id=f"{source_origin_id}R{replicate_index}",
                origin_id=source_origin_id,
                origin_plate_ref="",
                replicate_status="Replicate",
                mixture_id=source_row["mixture_id"],
                slice_number=source_row["slice_number"],
                plate_number=0,
                well_address="",
                block_number=1,
                replicate_index=replicate_index,
                experiment_code="",
                free_format=free_format,
                fill_plates=fill_plates,
                replicate_percent=replicate_percent,
                include_error=include_error,
                error_percent=error_percent,
            )
            replicate_rows.append(asdict(entry))
        replicate_rows.sort(key=lambda r: r["mixture_id"])

    fill_rows: List[dict] = []
    if base_rows and fill_plate_extras:
        fill_candidates = random.sample(base_rows, k=min(fill_plate_extras, len(base_rows)))
        for fill_index, source_row in enumerate(fill_candidates, start=1):
            source_origin_id = source_row.get("origin_id", f"EXP{fill_index + 1:03d}")
            entry = LayoutEntry(
                id=f"{source_origin_id}F{fill_index}",
                origin_id=source_origin_id,
                origin_plate_ref="",
                replicate_status="Extra replicate (plate filling)",
                mixture_id=source_row.get("mixture_id", ordered_mixture_ids[0] if ordered_mixture_ids else ""),
                slice_number=source_row.get("slice_number", 1),
                plate_number=0,
                well_address="",
                block_number=1,
                replicate_index=fill_index,
                experiment_code="",
                free_format=free_format,
                fill_plates=fill_plates,
                replicate_percent=replicate_percent,
                include_error=include_error,
                error_percent=error_percent,
            )
            fill_rows.append(asdict(entry))
    fill_rows.sort(key=lambda r: r["mixture_id"])

    final_rows: List[dict] = []
    final_rows.extend(base_rows)
    final_rows.extend(replicate_rows)
    final_rows.extend(fill_rows)
    final_rows = sort_layout_rows(final_rows)

    if free_format:
        for row_index, row in enumerate(final_rows):
            row["plate_number"] = 1
            row["well_address"] = f"{row_index + 1:03d}"
            row["block_number"] = 1
            row["experiment_code"] = make_experiment_code(row["mixture_id"], row["slice_number"], row["well_address"])
    else:
        for row_index, row in enumerate(final_rows):
            row["plate_number"] = (row_index // wells_per_plate) + 1
            row["well_address"] = fixed_wells[row_index % wells_per_plate]
            row["block_number"] = 1
            row["experiment_code"] = make_experiment_code(row["mixture_id"], row["slice_number"], row["well_address"])

        base_plate_refs = {
            row["origin_id"]: f"Plate{row['plate_number']}.{row['well_address']}"
            for row in final_rows
            if row["replicate_status"] == "Base"
        }

        for row in final_rows:
            if row["replicate_status"] == "Base":
                row["origin_plate_ref"] = base_plate_refs.get(row["origin_id"], "")
            elif row["origin_id"] in base_plate_refs:
                row["origin_plate_ref"] = base_plate_refs[row["origin_id"]]
            else:
                row["origin_plate_ref"] = ""
            row["experiment_code"] = make_experiment_code(row["mixture_id"], row["slice_number"], row["well_address"])

    return final_rows


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
            "Replicate Index",
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
                row["replicate_index"],
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
