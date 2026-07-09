from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from config import data_path


def fetch_knmi_data(post_fields: dict[str, str]) -> bytes | None:
	try:
		url = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"
		encoded_fields = urlencode(post_fields).encode("utf-8")
		request = Request(
			url,
			data=encoded_fields,
			headers={"Content-Type": "application/x-www-form-urlencoded"},
			method="POST",
		)

		with urlopen(request, timeout=60) as response:
			response_bytes = response.read()
	except Exception as exc:
		print(f"Failed to fetch KNMI data: {exc}")
		return None

	return response_bytes


def parse_knmi_response(
	response: bytes,
) -> tuple[str | None, list[str]]:
	data_rows: list[str] = []
	data_header: str | None = None

	for line in response.decode("utf-8", errors="replace").splitlines():
		if line.startswith("# STN,"):
			data_header = line[1:].strip()
		elif line.startswith("#"):
			continue
		elif line.strip():
			data_rows.append(line)

	return data_header, data_rows


def normalize_csv_line(line: str) -> str:
	return ",".join(field.strip() for field in line.split(","))


def row_has_measurements(row: str) -> bool:
	columns = row.split(",")
	return any(value != "" for value in columns[2:])


def merge_knmi_responses(responses: list[bytes]) -> bytes:
	if not responses:
		return b""

	raw_rows: list[str] = []
	data_header: str | None = None

	for response in responses:
		response_header, response_rows = parse_knmi_response(response)
		if data_header is None and response_header is not None:
			data_header = response_header

		raw_rows.extend(response_rows)

	if data_header is None:
		return b""

	normalized_rows = [normalize_csv_line(row) for row in raw_rows]
	filtered_rows = [row for row in normalized_rows if row_has_measurements(row)]

	merged_lines = [normalize_csv_line(data_header)]
	merged_lines.extend(filtered_rows)

	return "\n".join(merged_lines).encode("utf-8") + b"\n"


if __name__ == "__main__":
	# Example values; replace with the variables/values you need.
	station_ids = ["209:210:215:225", "229:235:240:242", "248:249:251:257", "258:260:265:267", "269:270:273:275", "277:278:279:280","283:285:286:290", "308:310:311:312", "313:315:316:319", "323:324:330:331", "340:343:344:348", "350:356:370:375", "377:380:391:392"]  # Add more station IDs as needed
	output_path = data_path("station_data.txt")
	responses: list[bytes] = []

	for station_group in station_ids:
		post_fields = {
			"stns": station_group,
			"vars": "TX:TG:SQ:RH:UG:FG",
			"start": "19900101",
			"end": "20260703",
		}
		response_bytes = fetch_knmi_data(post_fields=post_fields)
		if response_bytes is not None:
			responses.append(response_bytes)

	if not responses:
		print("No KNMI data was downloaded.")
	else:
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_bytes(merge_knmi_responses(responses))
		print(f"Saved merged KNMI response to: {output_path}")
