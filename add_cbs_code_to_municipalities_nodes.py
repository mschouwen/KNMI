import csv
from pathlib import Path


GEMEENTE_FILE = Path(r"d:\temp\gemeente2012.csv")
NODES_FILE = Path(r"d:\temp\municipalities_nodes.csv")
OUTPUT_FILE = Path(r"d:\temp\municipalities_nodes_with_cbs_code.csv")
UNMATCHED_FILE = Path(r"d:\temp\municipalities_nodes_unmatched.txt")


def normalize_name(value: str) -> str:
    text = str(value or "")
    text = text.replace("0", " ")
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    text = text.replace("\"", "").replace("'", "")
    text = " ".join(text.split())
    return text.casefold()


def clean_field(value: str) -> str:
    return str(value or "").strip().strip('"')


def flatten_non_zero_values(values_text: str) -> str:
    parts = str(values_text or "").split(":")
    flattened: list[str] = []

    for index, raw_value in enumerate(parts):
        value = raw_value.strip()
        if not value:
            continue

        try:
            if float(value) == 0.0:
                continue
        except ValueError:
            # Keep non-numeric values to avoid losing unexpected data.
            pass

        flattened.append(f"{index}={value}")

    return ":".join(flattened)


def read_alias_lookup(path: Path) -> dict[str, tuple[str, str]]:
    lookup: dict[str, tuple[str, str]] = {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)

        for row in reader:
            if not row:
                continue

            cbs_code = clean_field(row[0])
            aliases = [clean_field(item) for item in row[1:] if clean_field(item)]
            if not cbs_code or not aliases:
                continue

            preferred_name = aliases[0]

            for alias in aliases:
                lookup[normalize_name(alias)] = (cbs_code, preferred_name)

    return lookup


def resolve_code_and_preferred_name(
    municipality_name: str,
    alias_lookup: dict[str, tuple[str, str]],
) -> tuple[str, str]:
    normalized = normalize_name(municipality_name)
    if normalized in alias_lookup:
        return alias_lookup[normalized]

    # Retry with a compact form for minor spacing differences.
    compact = normalized.replace(" ", "")
    for alias, (code, preferred_name) in alias_lookup.items():
        if alias.replace(" ", "") == compact:
            return code, preferred_name

    return "", ""


def insert_cbs_code_column(
    input_path: Path,
    output_path: Path,
    alias_lookup: dict[str, tuple[str, str]],
) -> list[str]:
    unmatched_names: list[str] = []

    with input_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"Input file is empty: {input_path}")

        try:
            municipality_index = header.index("municipality")
        except ValueError as exc:
            raise ValueError("Column 'municipality' not found in municipalities_nodes.csv") from exc

        values_index = header.index("values_per_day") if "values_per_day" in header else None

        updated_header = (
            header[: municipality_index + 1]
            + ["cbs_code"]
            + header[municipality_index + 1 :]
        )

        with output_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(updated_header)

            for row in reader:
                if not row:
                    continue

                while len(row) < len(header):
                    row.append("")

                municipality_name = clean_field(row[municipality_index])
                cbs_code, preferred_name = resolve_code_and_preferred_name(municipality_name, alias_lookup)
                if not cbs_code:
                    unmatched_names.append(municipality_name)
                elif preferred_name and municipality_name != preferred_name:
                    row[municipality_index] = preferred_name

                if values_index is not None and values_index < len(row):
                    row[values_index] = flatten_non_zero_values(row[values_index])

                updated_row = (
                    row[: municipality_index + 1]
                    + [cbs_code]
                    + row[municipality_index + 1 :]
                )
                writer.writerow(updated_row)

    return unmatched_names


def write_unmatched(path: Path, unmatched_names: list[str]) -> None:
    unique_names = sorted({name for name in unmatched_names if name})
    with path.open("w", encoding="utf-8", newline="") as handle:
        for name in unique_names:
            handle.write(f"{name}\n")


def main() -> None:
    alias_lookup = read_alias_lookup(GEMEENTE_FILE)
    unmatched_names = insert_cbs_code_column(NODES_FILE, OUTPUT_FILE, alias_lookup)
    write_unmatched(UNMATCHED_FILE, unmatched_names)

    print(f"Read aliases from: {GEMEENTE_FILE}")
    print(f"Read municipalities from: {NODES_FILE}")
    print(f"Wrote updated file to: {OUTPUT_FILE}")
    print(f"Unmatched municipality names: {len(unmatched_names)}")
    print(f"Unmatched report: {UNMATCHED_FILE}")


if __name__ == "__main__":
    main()
