from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from config import data_path


STATION_HEADER_LINE = "# STN         LON(east)   LAT(north)  ALT(m)      NAME"
STATION_INFO_PATTERN = re.compile(
	r"\s*(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(.+?)\s*$"
)


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
) -> tuple[dict[str, tuple[str, str, str, str]], list[str], str | None, list[str]]:
	station_metadata: dict[str, tuple[str, str, str, str]] = {}
	comment_lines: list[str] = []
	data_rows: list[str] = []
	data_header: str | None = None
	in_station_table = False

	for line in response.decode("utf-8", errors="replace").splitlines():
		if line == STATION_HEADER_LINE:
			in_station_table = True
			continue

		if in_station_table:
			if line.startswith("#"):
				match = STATION_INFO_PATTERN.fullmatch(line[1:])
				if match is not None:
					station_id, lon, lat, alt, name = match.groups()
					station_metadata[station_id] = (lon, lat, alt, name)
					continue
			in_station_table = False

		if line.startswith("# STN,"):
			data_header = line[1:].strip()
		elif line.startswith("#"):
			comment_lines.append(line)
		elif line.strip():
			data_rows.append(line)

	return station_metadata, comment_lines, data_header, data_rows


def augment_data_row(
	row: str, station_metadata: dict[str, tuple[str, str, str, str]]
) -> str:
	columns = [column.strip() for column in row.split(",")]
	return ",".join(columns)
	#return ",".join([*columns, *metadata])


def merge_knmi_responses(responses: list[bytes]) -> bytes:
	if not responses:
		return b""

	comment_lines: list[str] = []
	all_station_metadata: dict[str, tuple[str, str, str, str]] = {}
	raw_rows: list[str] = []
	data_header: str | None = None

	for index, response in enumerate(responses):
		station_metadata, response_comments, response_header, response_rows = parse_knmi_response(response)
		if index == 0:
			comment_lines = response_comments

		if data_header is None and response_header is not None:
			data_header = response_header

#		all_station_metadata.update(station_metadata)
		raw_rows.extend(response_rows)

	if data_header is None:
		return b""

	merged_rows = [
		augment_data_row(row, all_station_metadata) for row in raw_rows
	]

	merged_lines = comment_lines[:]
	if merged_lines and merged_lines[-1] != "#":
		merged_lines.append("#")

	#merged_lines.append(STATION_HEADER_LINE)
	for station_id in sorted(all_station_metadata, key=int):
		lon, lat, alt, name = all_station_metadata[station_id]
		merged_lines.append(
			f"# {int(station_id):<11}{lon:<12}{lat:<12}{alt:<12}{name}"
		)

	header_columns = [column.strip() for column in data_header.split(",")]
	merged_lines.append(
		"# " + ",".join([*header_columns, "LON(east)", "LAT(north)", "ALT(m)", "NAME"])
	)
	merged_lines.extend(merged_rows)

	return "\n".join(merged_lines).encode("utf-8") + b"\n"


if __name__ == "__main__":
	# Example values; replace with the variables/values you need.
	station_ids = ["209:210:215:225", "229:235:240:242", "248:249:251:257", "258:260:265:267", "269:270:273:275", "277:278:279:280","283:285:286:290", "308:310:311:312", "313:315:316:319", "323:324:330:331", "340:343:344:348", "350:356:370:375", "377:380:391:392"]  # Add more station IDs as needed
	output_path = data_path("station_data.txt")
	responses: list[bytes] = []

	for station_group in station_ids:
		post_fields = {
			"stns": station_group,
			"vars": "TX:SQ:RH:NG:UG",
			"start": "19700101",
			"end": "20090818",
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
