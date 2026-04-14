import subprocess
import os
from core.FileReader import FileReader
import shutil
import fnmatch
import multiprocessing
try:
    import tqdm
except ImportError:
    tqdm = None
from pathlib import Path
import datetime
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor


class TxtinoutReader:

    def __init__(self, path: str) -> None:

        """
        Initialize a TxtinoutReader instance for working with SWAT model data.

        Parameters:
        path (str, os.PathLike): The path to the SWAT model folder.

        Raises:
        TypeError: If the provided path is not a string or a Path object, or if the folder does not exist,
                    or if there is more than one .exe file in the folder, or if no .exe file is found.

        Attributes:
        root_folder (Path): The path to the root folder of the SWAT model.
        swat_exe_path (Path): The path to the main SWAT executable file.
        """

        # check if path is a string or a path
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError("path must be a string or os.PathLike object")

        path = Path(path).resolve()

        # Collect executables without requiring one for read/modify workflows.
        self.swat_exe_paths = [
            path / file for file in os.listdir(path) if file.lower().endswith(".exe")
        ]
        self.swat_exe_path = (
            self.swat_exe_paths[0] if len(self.swat_exe_paths) == 1 else None
        )

  
        # find parent directory
        # self.swat_exe_path = path / swat_exe
        # find parent directory
        self.root_folder = path
        # self.swat_exe_path = path / swat_exe

    def update_context(self, new_path: str) -> None:
        """
        Update the root folder and executable paths for a new context.

        Parameters:
        new_path (str): The path to the new directory.

        Raises:
        ValueError: If the new path is not a valid directory.
        """
        # Resolve the new path
        new_path = Path(new_path).resolve()

        # Check if it's a valid directory
        if not new_path.is_dir():
            raise ValueError(f"Invalid directory: {new_path}")

        # Update root folder
        self.root_folder = new_path

        self.swat_exe_paths = [
            new_path / exe
            for exe in os.listdir(new_path)
            if exe.lower().endswith(".exe")
        ]
        self.swat_exe_path = (
            self.swat_exe_paths[0] if len(self.swat_exe_paths) == 1 else None
        )

    def _build_line_to_add(self, obj: str, daily: bool, monthly: bool, yearly: bool, avann: bool) -> str:
        """
        Build a line to add to the 'print.prt' file based on the provided parameters.

        Parameters:
        obj (str): The object name or identifier.
        daily (bool): Flag for daily print frequency.
        monthly (bool): Flag for monthly print frequency.
        yearly (bool): Flag for yearly print frequency.
        avann (bool): Flag for average annual print frequency.

        Returns:
        str: A formatted string representing the line to add to the 'print.prt' file.
        """
        print_periodicity = {
            'daily': daily,
            'monthly': monthly,
            'yearly': yearly,
            'avann': avann,
        }

        arg_to_add = obj.ljust(29)
        for value in print_periodicity.values():
            if value:
                periodicity = 'y'
            else:
                periodicity = 'n'

            arg_to_add += periodicity.ljust(14)

        arg_to_add = arg_to_add.rstrip()
        arg_to_add += '\n'
        return arg_to_add

    def enable_object_in_print_prt(self, obj: str, daily: bool, monthly: bool, yearly: bool, avann: bool) -> None:
        """
        Enable or update an object in the 'print.prt' file. If obj is not a default identifier, it will be added at the end of the file.

        Parameters:
        obj (str): The object name or identifier.
        daily (bool): Flag for daily print frequency.
        monthly (bool): Flag for monthly print frequency.
        yearly (bool): Flag for yearly print frequency.
        avann (bool): Flag for average annual print frequency.

        Returns:
        None
        """

        # check if obj is object itself or file
        if os.path.splitext(obj)[1] != '':
            arg_to_add = obj.rsplit('_', maxsplit=1)[0]
        else:
            arg_to_add = obj

        # read all print_prt file, line by line
        print_prt_path = self.root_folder / 'print.prt'
        new_print_prt = ""
        found = False
        with open(print_prt_path) as file:
            for line in file:
                if not line.startswith(arg_to_add + ' '):  # Line must start exactly with arg_to_add, not a word that starts with arg_to_add
                    new_print_prt += line
                else:
                    # obj already exist, replace it in same position
                    new_print_prt += self._build_line_to_add(arg_to_add, daily, monthly, yearly, avann)
                    found = True

        if not found:
            new_print_prt += self._build_line_to_add(arg_to_add, daily, monthly, yearly, avann)

        # store new print_prt
        with open(print_prt_path, 'w') as file:
            file.write(new_print_prt)

    # modify yrc_start and yrc_end
    def set_beginning_and_end_year(self, beginning: int, end: int) -> None:
        """
        Modify the beginning and end year in the 'time.sim' file.

        Parameters:
        beginning (int): The new beginning year.
        end (int): The new end year.

        Returns:
        None
        """

        nth_line = 3

        # time_sim_path = f"{self.root_folder}\\{'time.sim'}"
        time_sim_path = self.root_folder / 'time.sim'

        # Open the file in read mode and read its contents
        with open(time_sim_path, 'r') as file:
            lines = file.readlines()

        year_line = lines[nth_line - 1]

        # Split the input string by spaces
        elements = year_line.split()

        elements[1] = beginning
        elements[3] = end

        # Reconstruct the result string while maintaining spaces
        result_string = '{: >8} {: >10} {: >10} {: >10} {: >10} \n'.format(*elements)

        lines[nth_line - 1] = result_string

        with open(time_sim_path, 'w') as file:
            file.writelines(lines)

    # modify warmup
    def set_warmup(self, warmup: int) -> None:
        """
        Modify the warmup period in the 'time.sim' file.

        Parameters:
        warmup (int): The new warmup period value.

        Returns:
        None
        """
        time_sim_path = self.root_folder / 'print.prt'

        # Open the file in read mode and read its contents
        with open(time_sim_path, 'r') as file:
            lines = file.readlines()

        nth_line = 3
        year_line = lines[nth_line - 1]

        # Split the input string by spaces
        elements = year_line.split()

        elements[0] = warmup

        # Reconstruct the result string while maintaining spaces
        result_string = '{: <12} {: <11} {: <11} {: <10} {: <10} {: <10} \n'.format(*elements)

        lines[nth_line - 1] = result_string

        with open(time_sim_path, 'w') as file:
            file.writelines(lines)

    def _enable_disable_csv_print(self, enable: bool = True) -> None:
        """
        Enable or disable CSV print in the 'print.prt' file.

        Parameters:
        enable (bool, optional): True to enable CSV print, False to disable (default is True).

        Returns:
        None
        """

        # read
        nth_line = 7

        # time_sim_path = f"{self.root_folder}\\{'time.sim'}"
        print_prt_path = self.root_folder / 'print.prt'

        # Open the file in read mode and read its contents
        with open(print_prt_path, 'r') as file:
            lines = file.readlines()

        if enable:
            lines[nth_line - 1] = 'y' + lines[nth_line - 1][1:]
        else:
            lines[nth_line - 1] = 'n' + lines[nth_line - 1][1:]

        with open(print_prt_path, 'w') as file:
            file.writelines(lines)

    def enable_csv_print(self) -> None:
        """
        Enable CSV print in the 'print.prt' file.

        Returns:
        None
        """
        self._enable_disable_csv_print(enable=True)

    def disable_csv_print(self) -> None:
        """
        Disable CSV print in the 'print.prt' file.

        Returns:
        None
        """
        self._enable_disable_csv_print(enable=False)

    def register_file(self, filename: str, has_units: bool = False, index: Optional[str] = None, usecols: Optional[List[str]] = None, filter_by: Dict[str, List[str]] = {}) -> FileReader:

        """
        Register a file to work with in the SWAT model.

        Parameters:
        filename (str): The name of the file to register.
        has_units (bool): Indicates if the file has units information (default is False).
        index (str, optional): The name of the index column (default is None).
        usecols (List[str], optional): A list of column names to read (default is None).
        filter_by (Dict[str, List[str]], optional): A dictionary of column names and values (list of str) to filter by (default is an empty dictionary).

        Returns:
        FileReader: A FileReader instance for the registered file.
        """

        file_path = os.path.join(self.root_folder, filename)
        return FileReader(file_path, has_units, index, usecols, filter_by)

    """
    if overwrite = True, content of dir folder will be deleted and txtinout folder will be copied there
    if overwrite = False, txtinout folder will be copied to a new folder inside dir
    """

    def copy_swat(src_dir, dest_dir, exclude_suffixes=None, keep_routing=False):
        """
        Creates a lightweight working copy of a TxtInOut directory.

        Copies top-level input files and excludes common SWAT+ generated output.
        Hard links are intentionally avoided because SWAT+ can overwrite output
        files in place, and hard-linked output would mutate the source run too.
        """
        if not os.path.exists(src_dir):
            raise FileNotFoundError(f"Source directory {src_dir} does not exist.")

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        if exclude_suffixes is None:
            exclude_suffixes = [
                '*.txt',
                '*.csv',
                '*.out',
                '*.fin',
                '*.sqlite',
                '*.db',
                '*.log',
                '*.pid',
                'fort.*',
            ]

        os.makedirs(dest_dir, exist_ok=True)

        # Only process top-level files (no subdirectories)
        for file_name in os.listdir(src_dir):
            src_file = os.path.join(src_dir, file_name)
            if not os.path.isfile(src_file):
                continue
            lower_name = file_name.lower()
            if any(fnmatch.fnmatch(lower_name, pattern.lower()) for pattern in exclude_suffixes):
                continue

            dest_file = os.path.join(dest_dir, file_name)

            shutil.copy2(src_file, dest_file)

        print("Working copy created.")

    def _run_swat(self, show_output: bool = True) -> None:
        """
        Run the SWAT simulation.

        Parameters:
        show_output (bool, optional): If True, print the simulation output; if False, suppress output (default is True).

        Returns:
        None
        """

        # Run simulation
        swat_exe_path = self.swat_exe_path

        with subprocess.Popen(
            [str(swat_exe_path)],
            cwd=str(self.root_folder),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process:
            # Read and print the output while it's being produced
            while True:
                # Read a line of output
                raw_output = process.stdout.readline()

                # Check if the output is empty and the subprocess has finished
                if raw_output == b'' and process.poll() is not None:
                    break

                # Decode the output using 'latin-1' encoding
                try:
                    output = raw_output.decode('latin-1', errors='replace').strip()
                except UnicodeDecodeError:
                    # Handle decoding errors here (e.g., skip or replace invalid characters)
                    continue

                # Print the decoded output if needed
                if output and show_output:
                    print(output)

            if process.returncode != 0:
                raise RuntimeError(f"SWAT+ exited with code {process.returncode}.")

    """
    params --> {filename: (id_col, [(id, col, value)])}
    """

    def run_swat(self, params: Dict[str, Tuple[str, List[Tuple[str, str, int]]]] = {}, show_output: bool = True) -> str:
        """
        Run the SWAT simulation with modified input parameters.

        Parameters:
        params (Dict[str, Tuple[str, List[Tuple[str, str, int]]], optional): A dictionary containing modifications to input files. Format: {filename: (id_col, [(id, col, value)])}.
        show_output (bool, optional): If True, print the simulation output; if False, suppress output (default is True).

        Returns:
        str: The path to the directory where the SWAT simulation was executed.
        """

        aux_txtinout = TxtinoutReader(self.root_folder)

        # Modify files for simulation
        for filename, file_params in params.items():

            id_col, file_mods = file_params

            # get file
            file = aux_txtinout.register_file(filename, has_units=False, index=id_col)

            # for each col_name in file_params
            for id, col_name, value in file_mods:  # if id is not given, value will be applied to all rows
                if id is None:
                    file.df[col_name] = value
                else:
                    file.df.loc[id, col_name] = value

            # store file
            file.overwrite_file()

        beginning = datetime.datetime.now()

        # run simulation
        # print(f'Simulation started at {beginning.strftime("%H:%M:%S")}. Stored at {str(self.root_folder)}.')
        aux_txtinout._run_swat(show_output=show_output)
        end = datetime.datetime.now()
        td = end - beginning

        return self.root_folder

    def run_swat2(self, show_output: bool = True) -> None:
        """
        Run the SWAT+ simulation using the current state of the TxtinoutReader instance.
        """
        if not self.swat_exe_path:
            raise ValueError("Executable path is not set. Cannot run SWAT+ simulation.")

        if not self.root_folder:
            raise ValueError("Root folder is not set. Cannot run SWAT+ simulation.")

        print(f"Running SWAT+ simulation with executable: {self.swat_exe_path}")
        print(f"Simulation directory: {self.root_folder}")

        try:
            # Run the executable
            with subprocess.Popen(
                [str(self.swat_exe_path)],
                cwd=str(self.root_folder),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            ) as process:
                while True:
                    raw_output = process.stdout.readline()
                    if raw_output == b'' and process.poll() is not None:
                        break

                    output = raw_output.decode('latin-1', errors='replace').strip()
                    if output and show_output:
                        print(output)

                if process.returncode != 0:
                    raise RuntimeError(f"SWAT+ exited with code {process.returncode}.")

            print("SWAT+ simulation completed successfully.")
        except Exception as e:
            raise RuntimeError(f"Error running SWAT+ simulation: {str(e)}")

    def run_swat_star(self, args: Tuple[Dict[str, Tuple[str, List[Tuple[str, str, int]]]], bool]) -> str:
        """
        Run the SWAT simulation with modified input parameters using arguments provided as a tuple.

        Parameters:
        args (Tuple[Dict[str, Tuple[str, List[Tuple[str, str, int]]], bool]): A tuple containing simulation parameters.
        The first element is a dictionary with input parameter modifications, the second element is a boolean to show output.

        Returns:
        str: The path to the directory where the SWAT simulation was executed.
        """
        return self.run_swat(*args)

    def copy_and_run(self, dir: str, overwrite: bool = False, params: Dict[str, Tuple[str, List[Tuple[str, str, int]]]] = {}, show_output: bool = True) -> str:

        """
        Copy the SWAT model files to a specified directory, modify input parameters, and run the simulation.

        Parameters:
        dir (str): The target directory where the SWAT model files will be copied.
        overwrite (bool, optional): If True, overwrite the content of 'dir'; if False, create a new folder inside 'dir' (default is False).
        params (Dict[str, Tuple[str, List[Tuple[str, str, int]]], optional): A dictionary containing modifications to input files.
        Format: {filename: (id_col, [(id, col, value)])}.
        show_output (bool, optional): If True, print the simulation output; if False, suppress output (default is True).

        Returns:
        str: The path to the directory where the SWAT simulation was executed.
        """

        tmp_path = self.copy_swat(dir=dir, overwrite=overwrite)
        reader = TxtinoutReader(tmp_path)
        return reader.run_swat(params, show_output=show_output)

    def copy_and_run_star(self, args: Tuple[str, bool, Dict[str, Tuple[str, List[Tuple[str, str, int]]]], bool]) -> str:
        """
        Copy the SWAT model files to a specified directory, modify input parameters, and run the simulation using arguments provided as a tuple.

        Parameters:
        args (Tuple[str, bool, Dict[str, Tuple[str, List[Tuple[str, str, int]]]], bool]): A tuple containing simulation parameters.
        The first element is the target directory, the second element is a boolean to overwrite content, and the third element is a dictionary with input parameter modifications and a boolean to show output.

        Returns:
        str: The path to the directory where the SWAT simulation was executed.
        """
        return self.copy_and_run(*args)

    """
    params --> [{filename: (id_col, [(id, col, value)])}]
    """

    def run_parallel_swat(self,
                          params: List[Dict[str, Tuple[str, List[Tuple[str, str, int]]]]],
                          n_workers: int = 1,
                          dir: str = None,
                          parallelization: str = 'threads') -> List[str]:

        """
        Run SWAT simulations in parallel with modified input parameters.

        Parameters:
        params (List[Dict[str, Tuple[str, List[Tuple[str, str, int]]]]): A list of dictionaries containing modifications to input files.
        Format: [{filename: (id_col, [(id, col, value)])}].
        n_workers (int, optional): The number of parallel workers to use (default is 1).
        dir (str, optional): The target directory where the SWAT model files will be copied (default is None).
        parallelization (str, optional): The parallelization method to use ('threads' or 'processes') (default is 'threads').

        Returns:
        List[str]: A list of paths to the directories where the SWAT simulations were executed.
        """

        max_treads = multiprocessing.cpu_count()
        threads = max(min(n_workers, max_treads), 1)

        if n_workers == 1:

            results_ret = []

            iterator = range(len(params))
            if tqdm is not None:
                iterator = tqdm.tqdm(iterator)
            for i in iterator:
                results_ret.append(self.copy_and_run(dir=dir,
                                                     overwrite=False,
                                                     params=params[i],
                                                     show_output=False))

            return results_ret

        else:

            items = [[dir, False, params[i], False] for i in range(len(params))]

            if parallelization == 'threads':
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    results = list(executor.map(self.copy_and_run_star, items))
            elif parallelization == 'processes':
                with multiprocessing.Pool(threads) as pool:
                    results = list(pool.map(self.copy_and_run_star, items))
            else:
                raise ValueError("parallelization must be 'threads' or 'processes'")

            return results
