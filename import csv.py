import csv
from pathlib import Path

input_file = Path(r"d:\temp\OutputBasemodel_9.csv")
output_file = Path(r"d:\temp\OutputBasemodel_9_reduced.csv")
temp_file = output_file.with_suffix(".tmp.csv")

def round_if_numeric(value: str) -> str:
    text = value.strip()
    if text == "":
        return value

    # Try plain numeric (supports scientific notation too, e.g. 1e-3)
    try:
        number = float(text)
        return f"{number:.2f}"
    except ValueError:
        return value

with input_file.open("r", newline="", encoding="utf-8-sig") as fin, \
     temp_file.open("w", newline="", encoding="utf-8-sig") as fout:

    reader = csv.reader(fin, delimiter=";")
    writer = csv.writer(fout, delimiter=";")

    for row in reader:
        writer.writerow([round_if_numeric(cell) for cell in row])

# Write output file only after successful processing
temp_file.replace(output_file)