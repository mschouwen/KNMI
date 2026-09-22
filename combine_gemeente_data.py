import csv
from pathlib import Path


MUNICIPALITY_FILE = Path(r"d:\temp\gemeente2012.csv")
POPULATION_FILE = Path(r"d:\temp\StartPopulationHighestR90TrMr.txt")
NEIGHBOUR_FILE = Path(r"d:\temp\LinksTravelNeigh.txt")
SPATIAL_FILE = Path(r"d:\temp\gemeente_spatial.txt")
OUTPUT_FILES = [
    Path(r"d:\temp\gemeente_data1.csv"),
    Path(r"d:\projects\KNMI\gemeente_data1.csv"),
]
SKIPPED_FILE = Path(r"d:\projects\KNMI\skipped_names.txt")
RADIUS_METERS = 50_000


def normalize_name(value: str) -> str:
    text = str(value or "")
    text = text.replace("0", " ")
    text = text.replace("\"", "").replace("'", "")
    text = " ".join(text.split())
    text = text.strip()
    return text.casefold()


def clean_field(value: str) -> str:
    return str(value or "").strip().strip('"').strip("'")


def read_municipality_rows(path: Path) -> list[tuple[str, str, list[str]]]:
    rows: list[tuple[str, str, list[str]]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return rows

        for row in reader:
            if not row:
                continue
            cbs_code = clean_field(row[0])
            names = [clean_field(column) for column in row[1:] if clean_field(column)]
            if not cbs_code or not names:
                continue
            rows.append((cbs_code, names[0], names))
    return rows


def read_population_lookup(path: Path) -> dict[str, int]:
    lookup: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return lookup

        required_columns = {"Name", "TotPop"}
        missing = required_columns - {clean_field(name) for name in reader.fieldnames if name is not None}
        if missing:
            raise ValueError(f"Missing required columns in StartPopulationHighestR90TrMr.txt: {sorted(missing)}")

        for row in reader:
            if row is None:
                continue
            name_value = clean_field(row.get("Name", ""))
            totpop_value = clean_field(row.get("TotPop", ""))
            if not name_value or not totpop_value:
                continue
            try:
                lookup[normalize_name(name_value)] = int(float(totpop_value))
            except ValueError:
                continue
    return lookup


def read_alias_to_code_lookup(path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for cbs_code, _, aliases in read_municipality_rows(path):
        for alias in aliases:
            lookup[normalize_name(alias)] = cbs_code
    return lookup


def read_neighbour_lookup(path: Path, alias_to_code: dict[str, str]) -> dict[str, set[str]]:
    neighbours: dict[str, set[str]] = {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter='\t')
        for row in reader:
            if not row or len(row) < 2:
                continue
            left_name = clean_field(row[0])
            right_name = clean_field(row[1])
            left_code = alias_to_code.get(normalize_name(left_name))
            right_code = alias_to_code.get(normalize_name(right_name))
            if left_code is None or right_code is None:
                continue
            neighbours.setdefault(left_code, set()).add(right_code)
            neighbours.setdefault(right_code, set()).add(left_code)

    return neighbours


def read_spatial_lookup(path: Path) -> dict[str, tuple[int, int]]:
    lookup: dict[str, tuple[int, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cbs_code = clean_field(row.get("cbs_code", ""))
            x = clean_field(row.get("x", ""))
            y = clean_field(row.get("y", ""))
            if not cbs_code or not x or not y:
                continue
            try:
                lookup[cbs_code] = (int(float(x)), int(float(y)))
            except ValueError:
                continue
    return lookup


def validate_within_50km(cbs_code: str, direct_neighbours: set[str], within_50km_codes: list[str]) -> None:
    overlap = sorted(set(within_50km_codes) & set(direct_neighbours))
    if overlap:
        raise ValueError(
            f"Municipality {cbs_code} has overlapping direct neighbours in within_50km: {overlap}"
        )


def build_output_rows() -> tuple[list[tuple[str, str, int, str, str]], list[str]]:
    municipality_rows = read_municipality_rows(MUNICIPALITY_FILE)
    population_lookup = read_population_lookup(POPULATION_FILE)
    alias_to_code = read_alias_to_code_lookup(MUNICIPALITY_FILE)
    neighbour_lookup = read_neighbour_lookup(NEIGHBOUR_FILE, alias_to_code)
    spatial_lookup = read_spatial_lookup(SPATIAL_FILE)

    output_rows: list[tuple[str, str, int, str, str]] = []
    unmatched: list[str] = []

    for cbs_code, preferred_name, aliases in municipality_rows:
        matched_totpop = None
        for alias in aliases:
            lookup_key = normalize_name(alias)
            if lookup_key in population_lookup:
                matched_totpop = population_lookup[lookup_key]
                break
        if matched_totpop is None:
            unmatched.append(f"{cbs_code}::{preferred_name}")
            continue

        direct_neighbours = neighbour_lookup.get(cbs_code, set())
        neighbor_codes = sorted(direct_neighbours)
        neighbour_value = ":".join(neighbor_codes) if neighbor_codes else ""

        within_50km_codes = []
        source_x, source_y = spatial_lookup.get(cbs_code, (None, None))
        if source_x is not None and source_y is not None:
            for other_code, (other_x, other_y) in spatial_lookup.items():
                if other_code == cbs_code:
                    continue
                if other_code in direct_neighbours:
                    continue
                if other_x is None or other_y is None:
                    continue
                distance = ((source_x - other_x) ** 2 + (source_y - other_y) ** 2) ** 0.5
                if distance <= RADIUS_METERS:
                    within_50km_codes.append(other_code)

        validate_within_50km(cbs_code, direct_neighbours, within_50km_codes)

        within_50km_value = ":".join(sorted(within_50km_codes)) if within_50km_codes else ""
        output_rows.append((cbs_code, preferred_name, matched_totpop, neighbour_value, within_50km_value))

    if unmatched:
        print(f"Skipped {len(unmatched)} municipality rows without a matching TotPop name.")
        for item in unmatched[:10]:
            print(item)

    return output_rows, unmatched


def write_output(rows: list[tuple[str, str, int, str, str]], unmatched: list[str]) -> None:
    for output_file in OUTPUT_FILES:
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["cbs_code", "preferred_name", "TotPop", "neighbours", "within_50km"])
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {output_file}")

    with SKIPPED_FILE.open("w", encoding="utf-8", newline="") as handle:
        for name in unmatched:
            handle.write(f"{name}\n")
    print(f"Wrote {len(unmatched)} unmatched names to {SKIPPED_FILE}")


def main() -> None:
    rows, unmatched = build_output_rows()
    write_output(rows, unmatched)


if __name__ == "__main__":
    main()
