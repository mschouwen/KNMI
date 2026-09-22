import csv
import re
from pathlib import Path


LINKS_FILE = Path(r"d:\temp\LinksOpenLuchtRecreatie2012.csv")
GEMEENTE_FILE = Path(r"d:\temp\gemeente2012.csv")
OUTPUT_FILE = Path(r"d:\temp\LinksOpenLuchtRecreatie2012_ext.csv")
SKIPPED_FILE = Path(r"d:\temp\skipped2012.txt")

# Input rows are expected as: NameA,NameB,1234 (quotes optional)
LINK_ROW_PATTERN = re.compile(r'^\s*"?([^",]+)"?\s*,\s*"?([^",]+)"?\s*,\s*(\d+)\s*$')


def normalize_name(name: str) -> str:
    # In source links file, 0 represents a space in municipality names.
    # Some municipality names may begin with a quote-like character, which should
    # not affect the lookup key. Keep real apostrophes in the middle of names.
    text = str(name or "")
    text = text.replace("0", " ")
    text = text.strip()
    text = re.sub(r"^[\'\"`’]+", "", text)
    compact = " ".join(text.split())
    return compact.casefold()


def clean_value(value: str) -> str:
    return value.strip().strip("'").strip('"')


def is_cbs_code(value: str) -> bool:
    compact = clean_value(value)
    return len(compact) == 4 and compact.isdigit()


def is_name_like(value: str) -> bool:
    compact = clean_value(value)
    return any(char.isalpha() for char in compact)


def extract_cbs_and_name(row: list[str]) -> tuple[str, str] | None:
    # Known shifted layouts to try first.
    candidate_pairs = [(1, 2), (2, 1), (3, 2), (2, 3)]

    for cbs_idx, name_idx in candidate_pairs:
        if len(row) <= max(cbs_idx, name_idx):
            continue

        cbs_code = clean_value(row[cbs_idx])
        municipality_name = clean_value(row[name_idx])

        if is_cbs_code(cbs_code) and is_name_like(municipality_name):
            return cbs_code, municipality_name

    return None


def read_gemeente_lookup(file_path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}

    with file_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            if not row:
                continue

            #extracted = extract_cbs_and_name(row)
            #if extracted is None:
            #    continue

            cbs_code, municipality_name = int(clean_value(row[0])), clean_value(row[1])

            lookup[normalize_name(municipality_name)] = cbs_code

    return lookup


def read_links_rows(file_path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    text = file_path.read_text(encoding="ascii")

    for line in text.splitlines():
        if not line.strip():
            continue

        match = LINK_ROW_PATTERN.match(line)
        if match is None:
            continue

        municipality_a, municipality_b, value = match.groups()
        rows.append((municipality_a, municipality_b, value))

    return rows


def extend_rows(
    links_rows: list[tuple[str, str, str]], gemeente_lookup: dict[str, str]
) -> tuple[list[tuple[str, str, str, str, str]], set[str]]:
    extended: list[tuple[str, str, str, str, str]] = []
    skipped_names: set[str] = set()

    for municipality_a_raw, municipality_b_raw, value in links_rows:
        municipality_a_clean = normalize_name(municipality_a_raw)
        municipality_b_clean = normalize_name(municipality_b_raw)

        cbs_code_a = gemeente_lookup.get(municipality_a_clean)
        cbs_code_b = gemeente_lookup.get(municipality_b_clean)

        if cbs_code_a is None:
            skipped_names.add(municipality_a_raw.replace("0", " ").strip())

        if cbs_code_b is None:
            skipped_names.add(municipality_b_raw.replace("0", " ").strip())

        if cbs_code_a is None or cbs_code_b is None:
            continue

        extended.append((
            " ".join(municipality_a_raw.replace("0", " ").split()),
            " ".join(municipality_b_raw.replace("0", " ").split()),
            value,
            cbs_code_a,
            cbs_code_b,
        ))

    return extended, skipped_names


def write_output(file_path: Path, rows: list[tuple[str, str, str, str, str]]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "municipality_name_1",
            "municipality_name_2",
            "value",
            "cbs_code_1",
            "cbs_code_2",
        ])
        writer.writerows(rows)


def write_skipped_names(file_path: Path, skipped_names: set[str]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as f:
        for municipality_name in sorted(skipped_names):
            f.write(f"{municipality_name}\n")


def main() -> None:
    gemeente_lookup = read_gemeente_lookup(GEMEENTE_FILE)
    links_rows = read_links_rows(LINKS_FILE)
    extended_rows, skipped_names = extend_rows(links_rows, gemeente_lookup)
    write_output(OUTPUT_FILE, extended_rows)
    write_skipped_names(SKIPPED_FILE, skipped_names)

    print(f"Read {len(links_rows)} rows from {LINKS_FILE}")
    print(f"Wrote {len(extended_rows)} rows to {OUTPUT_FILE}")
    print(f"Wrote {len(skipped_names)} skipped municipality names to {SKIPPED_FILE}")


if __name__ == "__main__":
    main()