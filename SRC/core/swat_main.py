import os
from datetime import datetime
from pathlib import Path
from core.TxtinoutReader import TxtinoutReader
from core.FileModifier import FileModifier


def main(src_dir=None, filter_ids=[6], run_simulation=False, exe_path=None):
    """
    Main function for SWAT+ TxtInOut processing and simulation.

    Parameters:
    - src_dir (str): Source directory containing SWAT+ TxtInOut files.
    - filter_ids (list[int]): List of HRU IDs to filter.
    - run_simulation (bool): Whether to run the SWAT+ simulation.
    - exe_path (str): Path to the SWAT+ executable file (required if run_simulation=True).
    """
    # Validate the input source directory and HRU IDs
    if src_dir is None or not os.path.isdir(src_dir):
        raise ValueError("Please provide a valid source directory.")  # Ensure a valid directory is provided
    if not all(isinstance(i, int) for i in filter_ids):
        raise ValueError("Filter IDs must be integers.")  # Ensure all filter IDs are integers

    # Prepare destination folder name based on the HRU IDs or current timestamp
    dest_folder_name = (
        f"solo_{filter_ids[0]}" if len(filter_ids) == 1  # Single HRU: "solo_<id>"
        else f"multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # Multiple HRUs: "multi_<timestamp>"
    )
    dest_dir = Path(src_dir) / dest_folder_name  # Destination directory path

    # Copy source directory contents to the destination directory
    TxtinoutReader.copy_swat(src_dir, dest_dir)

    # Initialize FileModifier for the destination directory and modify SWAT+ input files
    fm = FileModifier(dest_dir)
    fm.modify_hru_con(filter_ids)  # Modify HRU.con file with specified HRU IDs
    fm.modify_object_cnt(len(filter_ids))  # Update object.cnt file based on the number of HRUs
    fm.modify_file_cio()  # Update file.cio for the simulation setup

    # If simulation is enabled, set up and run the simulation
    if run_simulation:
        # Ensure executable path is provided
        if not exe_path:
            raise ValueError("Executable path must be provided when running the simulation.")
        
        exe_path = Path(exe_path)  # Convert to Path object for consistency
        if not exe_path.is_file():
            raise ValueError(f"Invalid executable path: {exe_path}")  # Ensure the file exists

        # Initialize TxtinoutReader for the destination directory
        txt_reader = TxtinoutReader(dest_dir)
        txt_reader.swat_exe_path = exe_path  # Set the executable path for the simulation

        # Run the SWAT+ simulation
        try:
            txt_reader.run_swat2()  # Execute the simulation using the provided executable
            print(f"SWAT+ simulation completed successfully with {exe_path}.")
        except Exception as e:
            raise RuntimeError(f"Failed to run SWAT+ simulation: {str(e)}")
