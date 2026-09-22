import csv
from pathlib import Path


INPUT_PATH = Path(r"d:\temp\gemeente_data2.csv")
OUTPUT_PATH = Path(r"d:\temp\gemeente_data3.csv")


def parse_code_list(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(":") if item.strip()]


def parse_float(value):
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def main():
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {INPUT_PATH}")

    lookup = {}
    for row in rows:
        code = str(row.get("cbs_code", "")).strip()
        if code:
            lookup[code] = row

    neighbour_totals = {}
    within_50_totals = {}

    for row in rows:
        code = str(row.get("cbs_code", "")).strip()
        if not code:
            continue

        neighbour_codes = parse_code_list(row.get("neighbours", ""))
        within_codes = parse_code_list(row.get("within_50km", ""))

        neighbour_totals[code] = sum(
            parse_float(lookup.get(other_code, {}).get("ha", 0))
            for other_code in neighbour_codes
            if other_code in lookup
        )
        within_50_totals[code] = sum(
            parse_float(lookup.get(other_code, {}).get("ha", 0))
            for other_code in within_codes
            if other_code in lookup
        )

    for row in rows:
        code = str(row.get("cbs_code", "")).strip()
        if not code:
            continue

        ha = parse_float(row.get("ha", 0))
        totpop = parse_float(row.get("TotPop", 0))

        near_total = neighbour_totals.get(code, 0.0)
        near_50_total = within_50_totals.get(code, 0.0)

        fraction_near = ha / near_total if near_total > 0 else 0.0
        fraction_50 = ha / near_50_total if near_50_total > 0 else 0.0
        #fraction_self = ha / totpop if totpop > 0 else 0.0

        row["rnear"] = int(fraction_near * totpop * 0.26)
        row["r50"] = int(fraction_50 * totpop * 0.3596)
        row["rself"] = int( totpop * 0.2)

    fieldnames = list(rows[0].keys()) + ["rnear", "r50"] if "rnear" not in rows[0] and "r50" not in rows[0] else list(rows[0].keys())
    if "rnear" not in fieldnames:
        fieldnames.append("rnear")
    if "r50" not in fieldnames:
        fieldnames.append("r50")
    if "rself" not in fieldnames:
        fieldnames.append("rself")
      

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Calculated commuter values for {len(rows)} municipalities and wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
