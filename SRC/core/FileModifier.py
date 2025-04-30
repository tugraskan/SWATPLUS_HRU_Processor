# FileModifier.py
import os
import pandas as pd

import re
from SRC.core.TxtinoutReader import TxtinoutReader


class FileModifier:
    """Processes specific SWAT+ model files in a directory for customized modifications."""

    def __init__(self, txtinout_dir):
        self.txtinout_dir = txtinout_dir
        self.txtinout = TxtinoutReader(txtinout_dir)
        self.params = {}

    def get_hru_range(self):
        hru_file = self.txtinout.register_file("HRU.con", has_units=False)
        id_column = next((col for col in hru_file.df.columns if col.lower() == 'id'), None)
        if id_column is None:
            raise ValueError("No 'ID' column found in HRU.con file.")
        min_hru = hru_file.df[id_column].min()
        max_hru = hru_file.df[id_column].max()
        total_hrus = hru_file.df[id_column].count()
        return min_hru, max_hru, total_hrus

    def get_hru_line(self, filter_id):
        hru_file = self.txtinout.register_file("HRU.con", has_units=False)
        id_column = next((col for col in hru_file.df.columns if col.lower() == 'id'), None)
        if id_column is None:
            raise ValueError("Error: No 'ID' column found in HRU.con file.")
        id_row = hru_file.df[hru_file.df[id_column] == filter_id]
        if id_row.empty:
            return None
        return id_row.iloc[0].to_dict()

    def modify_hru_con(self, filter_ids):
        """
        Modifies HRU.con by setting specific ID rows to 1 and moving them to the top,
        while preserving the exact format of all values.
        """

        path = os.path.join(self.txtinout_dir, "HRU.con")

        # 1) Read with the first line as header
        df = pd.read_csv(path, delim_whitespace=True, dtype=str, header=1)

        # 2) Find the ID column (case‐insensitive)
        id_col = next((c for c in df.columns if c.lower() == 'id'), None)
        if not id_col:
            print("Error: No 'ID' column found in HRU.con.")

            return

        # 3) Extract & modify the matching rows
        modified_rows = []

        for fid in filter_ids:
            row = df[df[id_col] == str(fid)].copy()
            if row.empty:
                print(f"No row with ID={fid}")

                continue
            row[id_col] = '1'
            modified_rows.append(row)

        # 4) Re‐assemble: modified rows at top, then the rest
        remaining = df[~df[id_col].isin(map(str, filter_ids))]
        out = pd.concat(modified_rows + [remaining], ignore_index=True)


        # 5) Compute column widths (cast all cells to str to avoid float‐len issues)
        column_widths = [
            max(len(col), out[col].astype(str).map(len).max())
            for col in out.columns
        ]

        # 6) Write back, preserving formatting
        with open(path, 'w') as f:
            f.write(' '.join(out.columns) + '\n')
            for _, row in out.iterrows():
                parts = row.astype(str).tolist()
                line = ' '.join(val.rjust(w) for val, w in zip(parts, column_widths))
                f.write(line + '\n')

        print("HRU.con updated successfully.")

    def modify_object_cnt(self, hru_count):
        """
        Modify object.cnt by setting specific columns to reflect the number of HRUs,
        while preserving the exact format of all values.
        """
        path = os.path.join(self.txtinout_dir, "object.cnt")

        # 1) Read with the first line as header
        df = pd.read_csv(path, delim_whitespace=True, dtype=str, header=1)

        # 2) Find the NAME column
        name_col = next((c for c in df.columns if c.lower() == 'name'), None)
        if not name_col:
            print("Error: No 'NAME' column found in object.cnt.")
            return
        obj_name = df[name_col].iloc[0]

        # 3) Prepare updates
        zero_fields = [
            'LHRU','RTU','GWFL','AQU','CHA','RES','REC',
            'EXCO','DEL','CAN','PMP','OUT','LCHA','AQU2D','HRD','WRO'
        ]
        updates = {'OBJ': str(hru_count), 'HRU': str(hru_count)}
        updates.update({k: '0' for k in zero_fields})

        # 4) Apply updates row‐wise
        for key, val in updates.items():
            col = next((c for c in df.columns if c.lower() == key.lower()), None)
            if col:
                df.loc[df[name_col] == obj_name, col] = val

        # 5) Compute column widths
        column_widths = [
            max(len(col), df[col].astype(str).map(len).max())
            for col in df.columns
        ]

        # 6) Write back
        with open(path, 'w') as f:
            f.write(' '.join(df.columns) + '\n')
            for _, row in df.iterrows():
                parts = row.astype(str).tolist()
                line = ' '.join(val.rjust(w) for val, w in zip(parts, column_widths))
                f.write(line + '\n')

        print("object.cnt updated successfully.")

    def modify_file_cio(self, parameters_to_nullify=None):
        """
        Modifies file.cio by setting specified parameters to "null" in a case-insensitive manner,

        while preserving the exact format of the file.
        """
        if parameters_to_nullify is None:
            parameters_to_nullify = {
                "object.prt", "rout_unit.def", "rout_unit.ele", "rout_unit.rtu",
                "rout_unit.dr", "water_allocation.wro", "element.wro",
                "water_rights.wro", "ls_unit.def"
            }


        path = os.path.join(self.txtinout_dir, "file.cio")
        with open(path, 'r') as f:
            lines = f.readlines()

        # 1) Split off the header row (first line)
        header = lines[0]
        body = lines[1:]

        # 2) Compile regex patterns
        patterns = [
            (re.compile(rf'(?i)\b{re.escape(p)}\b'), p)
            for p in parameters_to_nullify
        ]

        # 3) Process body, replacing each match with "null" padded to original width
        out = [header]
        for line in body:
            new = line
            for pat, name in patterns:
                if pat.search(new):
                    new = pat.sub(lambda m: '"null"'.ljust(len(m.group(0))), new)
                    print(f"Changed {name} to 'null'")
            out.append(new)

        # 4) Write all lines back
        with open(path, 'w') as f:
            f.writelines(out)

        print("file.cio updated successfully.")

