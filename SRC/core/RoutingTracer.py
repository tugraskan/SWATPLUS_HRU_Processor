# RoutingTracer.py
"""
Traces the SWAT+ routing chain downstream from selected HRUs and filters
all connectivity (.con), data, and element files to keep only the reachable
objects.  Renumbers IDs so SWAT+ array slots line up correctly.

Workflow:
  1. Parse rout_unit.ele → find which routing units contain selected HRUs
  2. Parse every .con file → build a routing graph
  3. BFS downstream from those routing units → collect all reachable objects
  4. Filter + renumber every .con, data, element, and definition file
  5. Update object.cnt with new counts
"""

import os
import re
from collections import deque

from core.object_counts import update_object_count_file


# Maps obj_typ code → (.con filename, data filename or None)
OBJ_TYPE_FILES = {
    "hru": ("hru.con",        "hru-data.hru"),
    "ru":  ("rout_unit.con",  "rout_unit.rtu"),
    "sdc": ("chandeg.con",    "channel-lte.cha"),
    "cha": ("channel.con",    "channel.cha"),
    "aqu": ("aquifer.con",    "aquifer.aqu"),
    "res": ("reservoir.con",  "reservoir.res"),
    "rec": ("recall.con",     "recall.rec"),
    "exc": ("exco.con",       None),
    "dr":  ("delratio.con",   None),
    "out": ("outlet.con",     None),
}

class RoutingTracer:
    """Traces and filters the SWAT+ routing chain for a set of selected HRUs."""

    def __init__(self, txtinout_dir):
        self.dir = txtinout_dir

    # ------------------------------------------------------------------
    #  Public entry point
    # ------------------------------------------------------------------

    def trace_and_filter(self, selected_hru_ids):
        """
        Main method.  Given a list of original HRU IDs:
          - traces the routing chain downstream,
          - filters every .con / data / element file,
          - writes updated object.cnt.
        """
        # 1. Find routing units that contain selected HRUs
        ru_ids = self._find_routing_units_for_hrus(selected_hru_ids)
        print(f"Routing units containing selected HRUs: {ru_ids}")

        # 2. Parse all .con files → build graph  {(typ, id): [(target_typ, target_id, hyd, frac), ...]}
        graph = {}
        con_rows = {}  # {typ: {id: raw_fields_list}}
        for typ, (con_file, _) in OBJ_TYPE_FILES.items():
            path = os.path.join(self.dir, con_file)
            if not os.path.isfile(path):
                continue
            rows = self._parse_con_file(path)
            con_rows[typ] = rows
            for obj_id, fields in rows.items():
                targets = self._extract_routing_targets(fields)
                graph[(typ, obj_id)] = targets

        # 3. BFS downstream from selected HRUs and their routing units
        keep = {}  # {typ: set(ids)}
        keep.setdefault("hru", set()).update(selected_hru_ids)
        keep.setdefault("ru", set()).update(ru_ids)

        queue = deque()
        for hid in selected_hru_ids:
            queue.append(("hru", hid))
        for rid in ru_ids:
            queue.append(("ru", rid))

        visited = set(queue)
        while queue:
            node = queue.popleft()
            for target_typ, target_id, _, _ in graph.get(node, []):
                key = (target_typ, target_id)
                if key not in visited:
                    visited.add(key)
                    keep.setdefault(target_typ, set()).add(target_id)
                    queue.append(key)

        print("Objects to keep:")
        for typ in sorted(keep):
            print(f"  {typ}: {sorted(keep[typ])}")

        # 4. Filter and renumber everything
        # Build old→new ID mappings  {typ: {old_id: new_id}}
        id_maps = {}
        for typ, ids in keep.items():
            sorted_ids = sorted(ids)
            id_maps[typ] = {old: new for new, old in enumerate(sorted_ids, start=1)}

        # 4a. Filter .con files + data files
        for typ, (con_file, data_file) in OBJ_TYPE_FILES.items():
            if typ not in keep:
                # Nullify this .con file in file.cio later
                continue
            kept_ids = keep[typ]
            my_map = id_maps[typ]

            con_path = os.path.join(self.dir, con_file)
            original_props = set()
            if os.path.isfile(con_path):
                original_props = self._filter_con_file(con_path, kept_ids, my_map, id_maps)

            if data_file:
                data_path = os.path.join(self.dir, data_file)
                if os.path.isfile(data_path):
                    # Filter data file by original props values (cross-references),
                    # NOT by object IDs — props may differ from IDs.
                    filter_ids_for_data = original_props if original_props else kept_ids
                    data_map = {old: new for new, old in enumerate(sorted(filter_ids_for_data), start=1)}
                    self._filter_data_file(data_path, filter_ids_for_data, data_map)

        # 4b. Filter rout_unit.ele and rout_unit.def
        if "ru" in keep:
            self._filter_rout_unit_ele(keep, id_maps)
            self._filter_rout_unit_def(keep["ru"], id_maps)

        # 4c. Filter ls_unit.ele/def. SWAT+ allocates lsu_elem from these
        # files and later indexes it by HRU number, so they must stay aligned.
        if "hru" in id_maps:
            from core.FileModifier import FileModifier

            modifier = FileModifier(self.dir)
            lsu_elem_map = modifier.modify_ls_unit_ele(id_maps["hru"])
            modifier.modify_ls_unit_def(lsu_elem_map)

        # 5. Update object.cnt
        self._update_object_cnt(keep)

        # 6. Update file.cio — nullify only the types we don't keep
        self._update_file_cio(keep)

        return keep, id_maps

    # ------------------------------------------------------------------
    #  Parsing helpers
    # ------------------------------------------------------------------

    def _parse_con_file(self, path):
        """Parse a .con file → {id: [field_strings]}. Preserves raw fields."""
        rows = {}
        with open(path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 3:
            return rows
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            try:
                obj_id = int(fields[0])
            except ValueError:
                continue
            rows[obj_id] = fields
        return rows

    def _expand_element_tokens(self, tokens):
        """
        Expand rout_unit.def element tokens.

        SWAT+ uses a negative second token to represent an inclusive range,
        e.g. "302 -303" means elements 302 and 303.
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
                if start <= end:
                    expanded.extend(range(start, end + 1))
                else:
                    expanded.extend(range(start, end - 1, -1))
                index += 2
            else:
                expanded.append(values[index])
                index += 1

        return expanded

    def _extract_routing_targets(self, fields):
        """
        Given the field list of a .con row, extract the routing targets.
        Base columns: 0-12 (id..src_tot), then groups of 4: obj_typ, obj_id, hyd_typ, frac
        """
        targets = []
        try:
            src_tot = int(fields[12])  # src_tot is column index 12
        except (IndexError, ValueError):
            return targets
        for i in range(src_tot):
            base = 13 + i * 4
            if base + 3 >= len(fields):
                break
            obj_typ = fields[base]
            try:
                obj_id = int(fields[base + 1])
            except ValueError:
                continue
            hyd_typ = fields[base + 2]
            try:
                frac = float(fields[base + 3])
            except ValueError:
                frac = 1.0
            targets.append((obj_typ, obj_id, hyd_typ, frac))
        return targets

    def _find_routing_units_for_hrus(self, hru_ids):
        """
        Parse rout_unit.def and rout_unit.ele to find which routing units
        contain any of the selected HRU IDs.
        
        rout_unit.ele columns: id, name, obj_typ, obj_typ_no, frac, dr_name
        rout_unit.def columns: id, name, num_elem, elem_id_1, elem_id_2, ...
        """
        hru_set = set(hru_ids)
        
        # Parse rout_unit.ele: find element IDs that reference our HRUs
        ele_path = os.path.join(self.dir, "rout_unit.ele")
        hru_elem_ids = set()  # element IDs in rout_unit.ele that are our HRUs
        if os.path.isfile(ele_path):
            with open(ele_path, 'r') as f:
                lines = f.readlines()
            for line in lines[2:]:
                fields = line.split()
                if len(fields) < 4:
                    continue
                try:
                    elem_id = int(fields[0])
                    obj_typ = fields[2]
                    obj_typ_no = int(fields[3])
                except (ValueError, IndexError):
                    continue
                if obj_typ == "hru" and obj_typ_no in hru_set:
                    hru_elem_ids.add(elem_id)

        # Parse rout_unit.def: find routing units that contain those elements
        def_path = os.path.join(self.dir, "rout_unit.def")
        ru_ids = set()
        if os.path.isfile(def_path):
            with open(def_path, 'r') as f:
                lines = f.readlines()
            for line in lines[2:]:
                fields = line.split()
                if len(fields) < 3:
                    continue
                try:
                    ru_id = int(fields[0])
                    num_elem = int(fields[2])
                except (ValueError, IndexError):
                    continue
                elem_ids = set(self._expand_element_tokens(fields[3:3 + num_elem]))
                if elem_ids & hru_elem_ids:
                    ru_ids.add(ru_id)

        return ru_ids

    # ------------------------------------------------------------------
    #  Filtering / rewriting
    # ------------------------------------------------------------------

    def _filter_con_file(self, path, kept_ids, my_map, all_maps):
        """
        Rewrite a .con file keeping only rows whose original ID is in kept_ids.
        Renumber the ID column (col 0) using my_map.
        Remap the props column (col 7) as an independent cross-reference pointer.
        Update routing targets (obj_typ, obj_id) using all_maps.
        Returns the set of original props values for data file filtering.
        """
        with open(path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 2:
            return set()

        header = lines[0]
        col_header = lines[1]
        col_names = col_header.split()

        # Find key column indices — props is always position 7 in .con format,
        # header name varies by type ('hru', 'sdc', 'cha', etc.)
        id_idx = 0
        props_idx = 7 if len(col_names) > 7 else None
        src_idx = next((i for i, c in enumerate(col_names) if c.lower() == 'src_tot'), 12)

        kept_strs = {str(i) for i in kept_ids}
        selected = []
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            if fields[id_idx] in kept_strs:
                selected.append(fields)

        # Collect original props values and build cross-reference mapping
        original_props = set()
        if props_idx is not None:
            for fields in selected:
                if props_idx < len(fields):
                    try:
                        original_props.add(int(fields[props_idx]))
                    except ValueError:
                        pass
        props_map = {old: new for new, old in enumerate(sorted(original_props), start=1)}

        # Renumber and update routing targets
        renumbered = []
        for fields in selected:
            old_id = int(fields[id_idx])
            new_id = my_map[old_id]
            fields[id_idx] = str(new_id)

            # Remap props using cross-reference mapping (NOT object ID mapping)
            if props_idx is not None and props_idx < len(fields):
                try:
                    old_props = int(fields[props_idx])
                    fields[props_idx] = str(props_map[old_props])
                except (ValueError, KeyError):
                    pass

            # Rebuild routing targets — keep only those pointing to kept objects
            try:
                src_tot = int(fields[src_idx])
            except (IndexError, ValueError):
                src_tot = 0

            new_targets = []
            for i in range(src_tot):
                typ_col = (src_idx + 1) + i * 4
                id_col = typ_col + 1
                hyd_col = typ_col + 2
                frac_col = typ_col + 3
                if frac_col >= len(fields):
                    break
                target_typ = fields[typ_col]
                try:
                    target_old_id = int(fields[id_col])
                except ValueError:
                    continue
                target_map = all_maps.get(target_typ, {})
                if target_old_id in target_map:
                    # Target exists — update the ID
                    new_targets.append([
                        target_typ,
                        str(target_map[target_old_id]),
                        fields[hyd_col],
                        fields[frac_col],
                    ])
                # else: target was removed — omit it

            # Rebuild fields: base columns + surviving targets
            base = fields[:src_idx]
            base.append(str(len(new_targets)))  # updated src_tot
            for t in new_targets:
                base.extend(t)
            fields = base

            renumbered.append(fields)

        # Compute column widths
        base_count = src_idx + 1
        # Include routing target columns too
        max_cols = max((len(r) for r in renumbered), default=base_count)
        all_labels = col_names[:max_cols] if len(col_names) >= max_cols else col_names

        with open(path, 'w') as f:
            f.write(header)
            f.write(col_header)
            for row in renumbered:
                f.write('  '.join(v.rjust(8) for v in row) + '\n')

        print(f"  {os.path.basename(path)}: kept {len(renumbered)} rows")
        return original_props

    def _filter_data_file(self, path, kept_ids, id_map):
        """
        Filter a data file (e.g., hru-data.hru, aquifer.aqu) keeping only rows
        whose first-column ID is in kept_ids, and renumber using id_map.
        """
        with open(path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 3:
            return

        header = lines[0]
        col_header = lines[1]

        kept_strs = {str(i) for i in kept_ids}
        renumbered = []
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            if fields[0] in kept_strs:
                old_id = int(fields[0])
                new_id = id_map[old_id]
                # Replace the first field with new ID, keep rest of line
                rest = line.split(maxsplit=1)
                if len(rest) > 1:
                    renumbered.append(f"{new_id:>8} {rest[1]}")
                else:
                    renumbered.append(f"{new_id:>8}\n")

        with open(path, 'w') as f:
            f.write(header)
            f.write(col_header)
            for line in renumbered:
                if not line.endswith('\n'):
                    line += '\n'
                f.write(line)

        print(f"  {os.path.basename(path)}: kept {len(renumbered)} rows")

    def _filter_rout_unit_ele(self, keep, id_maps):
        """
        Filter rout_unit.ele to keep only elements that reference kept objects.
        Renumber element IDs sequentially, update obj_typ_no using id_maps.
        
        Columns: id, name, obj_typ, obj_typ_no, frac, dr_name
        """
        path = os.path.join(self.dir, "rout_unit.ele")
        if not os.path.isfile(path):
            return

        with open(path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 3:
            return

        header = lines[0]
        col_header = lines[1]

        selected = []
        for line in lines[2:]:
            fields = line.split()
            if len(fields) < 4:
                continue
            obj_typ = fields[2]
            try:
                obj_typ_no = int(fields[3])
            except ValueError:
                continue
            if obj_typ in keep and obj_typ_no in keep[obj_typ]:
                selected.append(fields)

        # Renumber element IDs 1..N, update obj_typ_no
        # Also build elem_id_map for rout_unit.def
        self._elem_id_map = {}  # old_elem_id → new_elem_id
        renumbered = []
        for new_elem_id, fields in enumerate(selected, start=1):
            old_elem_id = int(fields[0])
            self._elem_id_map[old_elem_id] = new_elem_id
            fields[0] = str(new_elem_id)
            obj_typ = fields[2]
            old_obj_no = int(fields[3])
            type_map = id_maps.get(obj_typ, {})
            if old_obj_no in type_map:
                fields[3] = str(type_map[old_obj_no])
            renumbered.append(fields)

        with open(path, 'w') as f:
            f.write(header)
            f.write(col_header)
            for row in renumbered:
                f.write('  '.join(v.rjust(12) for v in row) + '\n')

        print(f"  rout_unit.ele: kept {len(renumbered)} elements")

    def _filter_rout_unit_def(self, kept_ru_ids, id_maps):
        """
        Filter rout_unit.def to keep only routing units in kept_ru_ids.
        Renumber RU IDs and update element references using _elem_id_map.
        
        Columns: id, name, num_elem, elem_1, elem_2, ...
        """
        path = os.path.join(self.dir, "rout_unit.def")
        if not os.path.isfile(path):
            return

        with open(path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 3:
            return

        header = lines[0]
        col_header = lines[1]

        ru_map = id_maps.get("ru", {})
        elem_map = getattr(self, '_elem_id_map', {})
        kept_strs = {str(i) for i in kept_ru_ids}

        renumbered = []
        for line in lines[2:]:
            fields = line.split()
            if not fields:
                continue
            if fields[0] in kept_strs:
                old_ru_id = int(fields[0])
                new_ru_id = ru_map.get(old_ru_id, old_ru_id)
                fields[0] = str(new_ru_id)

                # Update element references, expanding compressed SWAT+ ranges.
                new_elem_refs = []
                try:
                    num_elem = int(fields[2])
                except ValueError:
                    num_elem = 0
                old_elements = self._expand_element_tokens(fields[3:3 + num_elem])
                for old_elem in old_elements:
                    if old_elem in elem_map:
                        new_elem_refs.append(str(elem_map[old_elem]))
                    # else: element was removed, skip it

                # Reconstruct with updated elem count + refs
                fields[2] = str(len(new_elem_refs))
                fields = fields[:3] + new_elem_refs
                renumbered.append(fields)

        with open(path, 'w') as f:
            f.write(header)
            f.write(col_header)
            for row in renumbered:
                f.write('  '.join(v.rjust(12) for v in row) + '\n')

        print(f"  rout_unit.def: kept {len(renumbered)} routing units")

    # ------------------------------------------------------------------
    #  object.cnt / file.cio
    # ------------------------------------------------------------------

    def _update_object_cnt(self, keep):
        """Update object.cnt with correct counts for each kept object type."""
        path = os.path.join(self.dir, "object.cnt")
        update_object_count_file(path, {typ: len(ids) for typ, ids in keep.items()})
        print("  object.cnt updated")

    def _update_file_cio(self, keep):
        """
        Update file.cio to nullify .con and data files for types we did not
        keep. Always nullify water allocation files.
        """
        # Always nullify these allocation / print files for subsets.
        always_null = {
            "water_allocation.wro", "element.wro", "water_rights.wro",
            "object.prt",
        }

        # Nullify .con and data files for types NOT in keep
        for typ, (con_file, data_file) in OBJ_TYPE_FILES.items():
            if typ not in keep:
                always_null.add(con_file)
                if data_file:
                    always_null.add(data_file)

        path = os.path.join(self.dir, "file.cio")
        with open(path, 'r') as f:
            content = f.read()

        for param in always_null:
            pattern = re.compile(rf'\b{re.escape(param)}\b', re.IGNORECASE)
            if pattern.search(content):
                content = pattern.sub('null', content)
                print(f"    {param} -> null")

        with open(path, 'w') as f:
            f.write(content)
        print("  file.cio updated")
