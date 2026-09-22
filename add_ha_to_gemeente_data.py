import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MUNICIPALITY_FILE = Path(r"d:\temp\gemeente_data1.csv")
RECREATION_FILE = Path(r"d:\temp\near_50_zonder_buren_fix_ha.csv")
OUTPUT_FILE = Path(r"d:\temp\gemeente_data2.csv")


def normalize_cbs_code(value):
    text = str(value or "").strip().strip('"').strip("'").upper()
    text = text.replace(" ", "").replace("-", "")
    text = text.replace("GM", "")
    if not text:
        return ""
    if text.isdigit():
        return str(int(text))
    return text


def read_ha_lookup(csv_path: Path):
    lookup = {}

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=';')
        if reader.fieldnames is None:
            return lookup

        required = {"near_GM_new", "ha"}
        missing = required - set(field.strip() for field in reader.fieldnames if field is not None)
        if missing:
            raise ValueError(
                f"Missing required columns in {csv_path.name}: {sorted(missing)}"
            )

        for row in reader:
            if row is None:
                continue

            code = normalize_cbs_code(row.get("near_GM_new", ""))
            ha_value = (row.get("ha", "") or "").strip()
            if not code or not ha_value:
                continue

            lookup.setdefault(code, ha_value)

    return lookup


def merge_rows(municipality_path: Path, ha_lookup):
    with municipality_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = list(reader.fieldnames or [])

        if not fieldnames:
            raise ValueError(f"No header found in {municipality_path.name}")

        if "ha" not in fieldnames:
            fieldnames.append("ha")

        rows = []
        for row in reader:
            if row is None:
                continue

            code = normalize_cbs_code(row.get("cbs_code", ""))
            row["ha"] = ha_lookup.get(code, "")
            rows.append(row)

    return fieldnames, rows


def main():
    if not MUNICIPALITY_FILE.exists():
        raise FileNotFoundError(f"Missing municipality file: {MUNICIPALITY_FILE}")
    if not RECREATION_FILE.exists():
        raise FileNotFoundError(f"Missing hectare file: {RECREATION_FILE}")

    ha_lookup = read_ha_lookup(RECREATION_FILE)
    fieldnames, rows = merge_rows(MUNICIPALITY_FILE, ha_lookup)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Merged {len(rows)} municipality rows into {OUTPUT_FILE.name}")
    print(f"Matched {len(ha_lookup)} unique hectare entries by cbs_code")


if __name__ == "__main__":
    main()
