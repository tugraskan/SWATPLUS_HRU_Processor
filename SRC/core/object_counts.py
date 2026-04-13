import re
from pathlib import Path


COUNT_COLUMN_ALIASES = {
    "obj": ("obj", "objs"),
    "hru": ("hru",),
    "hru_lte": ("lhru", "hru_lte", "hrulte", "hlt"),
    "ru": ("rtu", "ru"),
    "gwflow": ("gwfl", "gwflow"),
    "aqu": ("aqu",),
    "cha": ("cha", "chan"),
    "res": ("res",),
    "recall": ("rec", "recall"),
    "exco": ("exco",),
    "dr": ("dlr", "dr", "del"),
    "canal": ("can", "canal"),
    "pump": ("pmp", "pump"),
    "outlet": ("out", "outlet"),
    "chandeg": ("lcha", "chandeg", "sdc"),
    "aqu2d": ("aqu2d",),
    "herd": ("hrd", "herd"),
    "wro": ("wro",),
}

OBJECT_TYPE_TO_COUNT_KEY = {
    "hru": "hru",
    "hlt": "hru_lte",
    "hru_lte": "hru_lte",
    "ru": "ru",
    "gwflow": "gwflow",
    "aqu": "aqu",
    "cha": "cha",
    "res": "res",
    "rec": "recall",
    "recall": "recall",
    "exc": "exco",
    "exco": "exco",
    "dr": "dr",
    "out": "outlet",
    "outlet": "outlet",
    "sdc": "chandeg",
    "chandeg": "chandeg",
}

COUNT_KEYS = tuple(key for key in COUNT_COLUMN_ALIASES if key != "obj")


def _normalize(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _column_index(headers, key):
    aliases = {_normalize(alias) for alias in COUNT_COLUMN_ALIASES[key]}
    for index, header in enumerate(headers):
        if _normalize(header) in aliases:
            return index
    return None


def _canonical_counts(counts):
    canonical = {}
    for key, value in counts.items():
        count_key = OBJECT_TYPE_TO_COUNT_KEY.get(key, key)
        if count_key not in COUNT_COLUMN_ALIASES:
            continue
        canonical[count_key] = canonical.get(count_key, 0) + int(value)
    return canonical


def _format_fields(headers, fields):
    width_count = max(len(headers), len(fields))
    widths = []
    for index in range(width_count):
        header = headers[index] if index < len(headers) else ""
        field = fields[index] if index < len(fields) else ""
        widths.append(max(len(header), len(field)))
    return " ".join(
        fields[index].rjust(widths[index]) for index in range(len(fields))
    ) + "\n"


def update_object_count_file(path, counts):
    """
    Update object.cnt count columns while preserving basin metadata columns.

    SWAT+ editor versions differ in the visible headers around object.cnt. For
    example, current files include name/ls_area/tot_area before obj/hru counts,
    while older helper code assumed name/obj/hru. This updater uses header names
    and aliases, so area columns are not overwritten.
    """
    path = Path(path)
    with path.open("r") as file:
        lines = file.readlines()

    if len(lines) < 3:
        raise ValueError(f"{path.name} must contain a title, header, and data row.")

    title = lines[0]
    header_line = lines[1]
    headers = header_line.split()
    obj_index = _column_index(headers, "obj")
    if obj_index is None:
        raise ValueError("object.cnt does not contain an object total column.")

    canonical_counts = _canonical_counts(counts)
    total = sum(canonical_counts.get(key, 0) for key in COUNT_KEYS)
    new_lines = [title, header_line]

    for line in lines[2:]:
        fields = line.split()
        if not fields:
            new_lines.append(line)
            continue

        if obj_index >= len(fields):
            raise ValueError("object.cnt data row has fewer columns than its header.")

        for key in COUNT_KEYS:
            index = _column_index(headers, key)
            if index is not None and index < len(fields):
                fields[index] = "0"

        fields[obj_index] = str(total)
        for key, value in canonical_counts.items():
            if key == "obj":
                continue
            index = _column_index(headers, key)
            if index is None:
                if value:
                    raise ValueError(f"object.cnt is missing a column for {key}.")
                continue
            if index >= len(fields):
                raise ValueError("object.cnt data row has fewer columns than its header.")
            fields[index] = str(value)

        new_lines.append(_format_fields(headers, fields))

    with path.open("w") as file:
        file.writelines(new_lines)
