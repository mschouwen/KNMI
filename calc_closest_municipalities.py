import csv
import math
from pathlib import Path


DATA_FILE = Path(r"d:\temp\gemeente_spatial.txt")
DISTANCE_KM = 50


def _is_code_like(value: str) -> bool:
    compact = value.strip().strip('"')
    return len(compact) == 4 and compact.isdigit()


def read_municipalities(file_path: Path) -> list[tuple[str, float, float]]:
    municipalities: list[tuple[str, float, float]] = []

    with file_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header row.

        for row in reader:
            if not row:
                continue

            cbs_candidate_1 = row[1].strip().strip('"') if len(row) > 1 else ""
            cbs_candidate_2 = row[2].strip().strip('"') if len(row) > 2 else ""
            cbs_candidate_3 = row[3].strip().strip('"') if len(row) > 3 else ""

            if _is_code_like(cbs_candidate_1):
                cbs_code = cbs_candidate_1
            elif _is_code_like(cbs_candidate_2):
                cbs_code = cbs_candidate_2
            else:
                cbs_code = cbs_candidate_3

            if not cbs_code:
                continue

            x = float(row[6])
            y = float(row[7])
            municipalities.append((cbs_code, x, y))

    return municipalities


def build_nearest_map(
    municipalities: list[tuple[str, float, float]], max_distance_km: float
) -> dict[str, list[str]]:
    max_distance_m = max_distance_km * 1000.0
    nearest_map: dict[str, list[tuple[str, float]]] = {cbs: [] for cbs, _, _ in municipalities}

    for i, (cbs_a, x_a, y_a) in enumerate(municipalities):
        for j in range(i + 1, len(municipalities)):
            cbs_b, x_b, y_b = municipalities[j]
            distance_m = math.hypot(x_a - x_b, y_a - y_b)

            if distance_m <= max_distance_m:
                nearest_map[cbs_a].append((cbs_b, distance_m))
                nearest_map[cbs_b].append((cbs_a, distance_m))

    ordered_map: dict[str, list[str]] = {}
    for cbs_code, neighbours in nearest_map.items():
        neighbours.sort(key=lambda item: item[1])
        ordered_map[cbs_code] = [neighbour_code for neighbour_code, _ in neighbours]

    return ordered_map


def write_output(output_path: Path, nearest_map: dict[str, list[str]]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cbs_code", "closest_municipalities"])

        for cbs_code in sorted(nearest_map):
            nearest_codes = ":".join(nearest_map[cbs_code])
            writer.writerow([cbs_code, nearest_codes])


def main() -> None:
    municipalities = read_municipalities(DATA_FILE)
    nearest_map = build_nearest_map(municipalities, DISTANCE_KM)

    output_file = DATA_FILE.parent / f"closest_municipalities_{DISTANCE_KM}.txt"
    write_output(output_file, nearest_map)

    print(f"Wrote {len(nearest_map)} municipalities to {output_file}")


if __name__ == "__main__":
    main()