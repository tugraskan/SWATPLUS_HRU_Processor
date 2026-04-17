# FileModifier.py
import os
import re

from core.object_counts import update_object_count_file


class FileModifier:
    """Processes specific SWAT+ model files in a directory."""

    def __init__(self, txtinout_dir):
        self.txtinout_dir = os.fspath(txtinout_dir)
        self.params = {}
        self.hru_id_map = {}
        self.hru_props_map = {}

    def _file_path(self, filename):
        direct = os.path.join(self.txtinout_dir, filename)
        if os.path.isfile(direct):
            return direct

        target = filename.lower()
        for existing in os.listdir(self.txtinout_dir):
            if existing.lower() == target:
                return os.path.join(self.txtinout_dir, existing)
        return direct

    def _read_hru_rows(self):
        path = self._file_path("hru.con")
        with open(path, "r") as file:
            lines = file.readlines()

        if len(lines) < 2:
            raise ValueError("hru.con must contain a title and column header.")

        headers = lines[1].split()
        rows = []
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            rows.append(dict(zip(headers, fields)))
        return headers, rows

    def _expand_element_tokens(self, tokens):
        """
        Expand SWAT+ element ranges.

        SWAT+ definition files use a negative second value for inclusive ranges,
        for example "302 -303" means elements 302 and 303.
        """
        values = []
        for token in tokens:
            try:
                values.append(int(token))
            except ValueError:
                continue

        expanded = []
        index = 0
        while index < len(values):
            if index + 1 < len(values) and values[index + 1] < 0:
                start = values[index]
                end = abs(values[index + 1])
                step = 1 if start <= end else -1
                expanded.extend(range(start, end + step, step))
                index += 2
            else:
                expanded.append(values[index])
                index += 1

        return expanded

    def _compress_element_ids(self, element_ids):
        """
        Compress consecutive element IDs back to SWAT+ range tokens.
        """
        values = [int(element_id) for element_id in element_ids]
        if not values:
            return []

        compressed = []
        index = 0
        while index < len(values):
            start = values[index]
            end = start
            while index + 1 < len(values) and values[index + 1] == end + 1:
                index += 1
                end = values[index]

            if end == start:
                compressed.append(str(start))
            else:
                compressed.extend([str(start), str(-end)])
            index += 1

        return compressed

    def _format_row(self, fields, width=12):
        return " ".join(str(value).rjust(width) for value in fields) + "\n"

    def _header_index(self, headers, names, default=None):
        names = {name.lower() for name in names}
        return next((i for i, header in enumerate(headers) if header.lower() in names), default)

    def get_hru_range(self):
        headers, rows = self._read_hru_rows()
        id_column = next((col for col in headers if col.lower() == "id"), None)
        if id_column is None:
            raise ValueError("No 'ID' column found in hru.con file.")

        hru_ids = []
        for row in rows:
            try:
                hru_ids.append(int(row[id_column]))
            except (KeyError, ValueError):
                continue
        if not hru_ids:
            raise ValueError("No HRU IDs found in hru.con file.")

        return min(hru_ids), max(hru_ids), len(hru_ids)

    def get_hru_line(self, filter_id):
        headers, rows = self._read_hru_rows()
        id_column = next((col for col in headers if col.lower() == "id"), None)
        if id_column is None:
            raise ValueError("No 'ID' column found in hru.con file.")
        for row in rows:
            try:
                if int(row[id_column]) == int(filter_id):
                    return row
            except (KeyError, ValueError):
                continue
        return None

    def modify_hru_con(self, filter_ids):
        """
        Keep only selected HRU connectivity rows, renumber IDs, and remove routing.

        The .con props column points into hru-data.hru, so it is remapped
        independently from the HRU object ID.
        """
        path = self._file_path("hru.con")
        with open(path, "r") as file:
            lines = file.readlines()

        if len(lines) < 2:
            raise ValueError("hru.con must contain a title and column header.")

        title = lines[0]
        column_header = lines[1]
        column_names = column_header.split()

        id_idx = next((i for i, col in enumerate(column_names) if col.lower() == "id"), None)
        out_idx = next(
            (
                i
                for i, col in enumerate(column_names)
                if col.lower() in {"out_tot", "src_tot"}
            ),
            None,
        )
        props_idx = 7 if len(column_names) > 7 else None

        if id_idx is None:
            raise ValueError("No 'id' column found in hru.con.")
        if out_idx is None:
            raise ValueError("No 'out_tot' or 'src_tot' column found in hru.con.")

        filter_set = {int(filter_id) for filter_id in filter_ids}
        selected = []
        found_ids = set()
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            try:
                hru_id = int(fields[id_idx])
            except (IndexError, ValueError):
                continue
            if hru_id in filter_set:
                selected.append(fields)
                found_ids.add(hru_id)

        missing_ids = sorted(filter_set - found_ids)
        if missing_ids:
            raise ValueError(f"HRU ID(s) not found in hru.con: {missing_ids}")

        original_props = []
        if props_idx is not None:
            for fields in selected:
                if props_idx < len(fields):
                    try:
                        original_props.append(int(fields[props_idx]))
                    except ValueError:
                        pass

        unique_props = sorted(set(original_props))
        props_map = {old: new for new, old in enumerate(unique_props, start=1)}
        self.hru_props_map = props_map

        base_col_count = out_idx + 1
        base_col_names = column_names[:base_col_count]
        renumbered = []
        self.hru_id_map = {}
        for new_id, fields in enumerate(selected, start=1):
            old_id = int(fields[id_idx])
            self.hru_id_map[old_id] = new_id
            row = fields[:base_col_count]
            row[id_idx] = str(new_id)
            if props_idx is not None and props_idx < len(row):
                try:
                    row[props_idx] = str(props_map[int(row[props_idx])])
                except (KeyError, ValueError):
                    pass
            row[out_idx] = "0"
            renumbered.append(row)

        column_widths = []
        for index, column in enumerate(base_col_names):
            max_data = max(len(row[index]) for row in renumbered)
            column_widths.append(max(len(column), max_data))

        with open(path, "w") as file:
            file.write(title)
            file.write(
                " ".join(
                    column.rjust(width)
                    for column, width in zip(base_col_names, column_widths)
                )
                + "\n"
            )
            for row in renumbered:
                file.write(
                    " ".join(
                        value.rjust(width)
                        for value, width in zip(row, column_widths)
                    )
                    + "\n"
                )

        print(f"hru.con updated: kept {len(renumbered)} HRU(s).")
        return unique_props

    def modify_object_cnt(self, hru_count):
        """Update object.cnt for isolated-HRU mode."""
        update_object_count_file(self._file_path("object.cnt"), {"hru": hru_count})
        print("object.cnt updated successfully.")

    def modify_file_cio(self, parameters_to_nullify=None):
        """
        Replace selected file.cio filename tokens with null.
        """
        if parameters_to_nullify is None:
            parameters_to_nullify = {
                "rout_unit.dr",
                "water_allocation.wro",
                "element.wro",
                "water_rights.wro",
                "object.prt",
                "rout_unit.con",
                "aquifer.con",
                "aquifer2d.con",
                "channel.con",
                "reservoir.con",
                "recall.con",
                "exco.con",
                "delratio.con",
                "outlet.con",
                "chandeg.con",
                "gwflow.con",
                "hru-lte.con",
            }

        path = self._file_path("file.cio")
        with open(path, "r") as file:
            content = file.read()

        for filename in parameters_to_nullify:
            pattern = re.compile(rf"\b{re.escape(filename)}\b", re.IGNORECASE)
            if pattern.search(content):
                content = pattern.sub("null", content)
                print(f"  {filename} -> null")

        with open(path, "w") as file:
            file.write(content)

        print("file.cio updated successfully.")

    def disable_print_objects(self, object_names):
        """
        Turn off print.prt rows for object outputs that are not valid anymore.
        """
        path = self._file_path("print.prt")
        if not os.path.isfile(path):
            return

        disabled = {name.lower() for name in object_names}
        changed = 0
        new_lines = []
        with open(path, "r") as file:
            for line in file:
                fields = line.split()
                if len(fields) >= 5 and fields[0].lower() in disabled:
                    fields[1:5] = ["n", "n", "n", "n"]
                    line = " ".join(fields) + "\n"
                    changed += 1
                new_lines.append(line)

        if changed:
            with open(path, "w") as file:
                file.writelines(new_lines)
            print(f"print.prt updated: disabled {changed} routing-unit output row(s).")

    def modify_secondary_references(self, hru_id_map=None):
        """
        Filter and remap files that reference HRUs by element position.

        These files are not primary HRU tables, but SWAT+ reads them into arrays
        that are later indexed by HRU number. Their HRU object pointers and
        definition element references must stay aligned with the renumbered HRUs.
        """
        hru_id_map = hru_id_map or self.hru_id_map
        if not hru_id_map:
            raise ValueError("HRU ID map is empty. Run modify_hru_con first.")

        lsu_elem_map = self.modify_ls_unit_ele(hru_id_map)
        self.modify_ls_unit_def(lsu_elem_map)
        ru_elem_map = self.modify_rout_unit_ele(hru_id_map)
        ru_id_map = self.modify_rout_unit_def(ru_elem_map)
        self.modify_rout_unit_rtu(ru_id_map)

        return {
            "ls_unit_elements": lsu_elem_map,
            "rout_unit_elements": ru_elem_map,
            "rout_units": ru_id_map,
        }

    def modify_ls_unit_ele(self, hru_id_map):
        """
        Keep landscape elements for selected HRUs and remap their HRU pointer.
        """
        path = self._file_path("ls_unit.ele")
        if not os.path.isfile(path):
            return {}

        with open(path, "r") as file:
            lines = file.readlines()
        if len(lines) < 2:
            return {}

        title = lines[0]
        column_header = lines[1]
        headers = column_header.split()
        id_idx = self._header_index(headers, {"id"}, 0)
        typ_idx = self._header_index(headers, {"obj_typ", "objtyp"}, 2)
        obj_idx = self._header_index(headers, {"obj_typ_no", "objtypno", "obj_id"}, 3)

        selected = []
        for line in lines[2:]:
            fields = line.split()
            if len(fields) <= max(id_idx, typ_idx, obj_idx):
                continue
            try:
                old_elem_id = int(fields[id_idx])
                old_hru_id = int(fields[obj_idx])
            except ValueError:
                continue
            if fields[typ_idx].lower() == "hru" and old_hru_id in hru_id_map:
                selected.append((hru_id_map[old_hru_id], old_elem_id, fields))

        selected.sort(key=lambda item: item[0])
        elem_map = {}
        renumbered = []
        for new_hru_id, old_elem_id, fields in selected:
            elem_map[old_elem_id] = new_hru_id
            fields[id_idx] = str(new_hru_id)
            fields[obj_idx] = str(new_hru_id)
            renumbered.append(fields)

        with open(path, "w") as file:
            file.write(title)
            file.write(column_header)
            for row in renumbered:
                file.write(self._format_row(row))

        print(f"ls_unit.ele updated: kept {len(renumbered)} element(s).")
        return elem_map

    def modify_ls_unit_def(self, elem_map):
        """
        Keep landscape-unit definitions that reference retained LSU elements.
        """
        path = self._file_path("ls_unit.def")
        if not os.path.isfile(path):
            return {}

        with open(path, "r") as file:
            lines = file.readlines()
        if len(lines) < 3:
            return {}

        title = lines[0]
        column_header = lines[2]
        def_map = {}
        renumbered = []

        for line in lines[3:]:
            fields = line.split()
            if len(fields) < 4:
                continue
            try:
                old_def_id = int(fields[0])
                elem_tot = int(fields[3])
            except ValueError:
                continue

            old_elements = self._expand_element_tokens(fields[4:4 + elem_tot])
            new_elements = [elem_map[elem] for elem in old_elements if elem in elem_map]
            if not new_elements:
                continue

            compressed_elements = self._compress_element_ids(new_elements)
            new_def_id = len(renumbered) + 1
            def_map[old_def_id] = new_def_id
            fields[0] = str(new_def_id)
            fields[3] = str(len(compressed_elements))
            renumbered.append(fields[:4] + compressed_elements)

        with open(path, "w") as file:
            file.write(title)
            file.write(f"{len(renumbered)}\n")
            file.write(column_header)
            for row in renumbered:
                file.write(self._format_row(row))

        print(f"ls_unit.def updated: kept {len(renumbered)} definition(s).")
        return def_map

    def modify_rout_unit_ele(self, hru_id_map):
        """
        Keep routing-unit elements for selected HRUs and remap their HRU pointer.
        """
        path = self._file_path("rout_unit.ele")
        if not os.path.isfile(path):
            return {}

        with open(path, "r") as file:
            lines = file.readlines()
        if len(lines) < 2:
            return {}

        title = lines[0]
        column_header = lines[1]
        headers = column_header.split()
        id_idx = self._header_index(headers, {"id"}, 0)
        typ_idx = self._header_index(headers, {"obj_typ", "objtyp"}, 2)
        obj_idx = self._header_index(headers, {"obj_id", "obj_typ_no", "objtypno"}, 3)

        selected = []
        for line in lines[2:]:
            fields = line.split()
            if len(fields) <= max(id_idx, typ_idx, obj_idx):
                continue
            try:
                old_elem_id = int(fields[id_idx])
                old_hru_id = int(fields[obj_idx])
            except ValueError:
                continue
            if fields[typ_idx].lower() == "hru" and old_hru_id in hru_id_map:
                selected.append((hru_id_map[old_hru_id], old_elem_id, fields))

        selected.sort(key=lambda item: item[0])
        elem_map = {}
        renumbered = []
        for new_elem_id, (new_hru_id, old_elem_id, fields) in enumerate(selected, start=1):
            elem_map[old_elem_id] = new_elem_id
            fields[id_idx] = str(new_elem_id)
            fields[obj_idx] = str(new_hru_id)
            renumbered.append(fields)

        with open(path, "w") as file:
            file.write(title)
            file.write(column_header)
            for row in renumbered:
                file.write(self._format_row(row))

        print(f"rout_unit.ele updated: kept {len(renumbered)} element(s).")
        return elem_map

    def modify_rout_unit_def(self, elem_map):
        """
        Keep routing-unit definitions that reference retained route elements.
        """
        path = self._file_path("rout_unit.def")
        if not os.path.isfile(path):
            return {}

        with open(path, "r") as file:
            lines = file.readlines()
        if len(lines) < 2:
            return {}

        title = lines[0]
        column_header = lines[1]
        ru_map = {}
        renumbered = []

        for line in lines[2:]:
            fields = line.split()
            if len(fields) < 3:
                continue
            try:
                old_ru_id = int(fields[0])
                elem_tot = int(fields[2])
            except ValueError:
                continue

            old_elements = self._expand_element_tokens(fields[3:3 + elem_tot])
            new_elements = [elem_map[elem] for elem in old_elements if elem in elem_map]
            if not new_elements:
                continue

            compressed_elements = self._compress_element_ids(new_elements)
            new_ru_id = len(renumbered) + 1
            ru_map[old_ru_id] = new_ru_id
            fields[0] = str(new_ru_id)
            fields[2] = str(len(compressed_elements))
            renumbered.append(fields[:3] + compressed_elements)

        with open(path, "w") as file:
            file.write(title)
            file.write(column_header)
            for row in renumbered:
                file.write(self._format_row(row))

        print(f"rout_unit.def updated: kept {len(renumbered)} definition(s).")
        return ru_map

    def modify_rout_unit_rtu(self, ru_id_map):
        """
        Keep rout_unit.rtu rows matching retained route-unit definitions.
        """
        path = self._file_path("rout_unit.rtu")
        if not os.path.isfile(path):
            return

        with open(path, "r") as file:
            lines = file.readlines()
        if len(lines) < 2:
            return

        title = lines[0]
        column_header = lines[1]
        headers = column_header.split()
        def_idx = self._header_index(headers, {"def", "define"}, 2)
        renumbered = []

        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            try:
                old_ru_id = int(fields[0])
            except ValueError:
                continue
            if old_ru_id not in ru_id_map:
                continue
            fields[0] = str(ru_id_map[old_ru_id])
            if def_idx is not None and def_idx < len(fields):
                try:
                    old_def_id = int(fields[def_idx])
                except ValueError:
                    old_def_id = None
                if old_def_id in ru_id_map:
                    fields[def_idx] = str(ru_id_map[old_def_id])
            renumbered.append(fields)

        with open(path, "w") as file:
            file.write(title)
            file.write(column_header)
            for row in renumbered:
                file.write(self._format_row(row))

        print(f"rout_unit.rtu updated: kept {len(renumbered)} row(s).")

    def modify_hru_data(self, filter_ids):
        """
        Keep only selected hru-data.hru rows and renumber their first-column IDs.
        """
        path = self._file_path("hru-data.hru")
        if not os.path.isfile(path):
            raise FileNotFoundError("hru-data.hru not found.")

        with open(path, "r") as file:
            lines = file.readlines()

        if len(lines) < 3:
            raise ValueError("hru-data.hru must contain a title, header, and data row.")

        title = lines[0]
        column_header = lines[1]
        filter_set = {int(filter_id) for filter_id in filter_ids}
        selected = []
        found_ids = set()

        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            try:
                data_id = int(fields[0])
            except ValueError:
                continue
            if data_id in filter_set:
                selected.append(line)
                found_ids.add(data_id)

        missing_ids = sorted(filter_set - found_ids)
        if missing_ids:
            raise ValueError(f"ID(s) not found in hru-data.hru: {missing_ids}")

        renumbered = []
        for new_id, line in enumerate(selected, start=1):
            fields = line.split(maxsplit=1)
            if len(fields) > 1:
                renumbered.append(f"{new_id:>8} {fields[1]}\n")
            else:
                renumbered.append(f"{new_id:>8}\n")

        with open(path, "w") as file:
            file.write(title)
            file.write(column_header)
            file.writelines(renumbered)

        print(f"hru-data.hru updated: kept {len(renumbered)} row(s).")
