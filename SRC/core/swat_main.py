import os
from datetime import datetime
from pathlib import Path
from core.TxtinoutReader import TxtinoutReader
from core.FileModifier import FileModifier
from core.RoutingTracer import RoutingTracer


def main(src_dir=None, filter_ids=None, run_simulation=False, exe_path=None, keep_routing=False):
    """
    Main function for SWAT+ TxtInOut processing and simulation.

    Parameters:
    - src_dir (str): Source directory containing SWAT+ TxtInOut files.
    - filter_ids (list[int]): List of HRU IDs to filter.
    - run_simulation (bool): Whether to run the SWAT+ simulation.
    - exe_path (str): Path to the SWAT+ executable file (required if run_simulation=True).
    - keep_routing (bool): If True, preserve the downstream routing chain.
    """
    if filter_ids is None:
        filter_ids = [6]

    # Validate the input source directory and HRU IDs
    if src_dir is None or not os.path.isdir(src_dir):
        raise ValueError("Please provide a valid source directory.")  # Ensure a valid directory is provided
    if not all(isinstance(i, int) for i in filter_ids):
        raise ValueError("Filter IDs must be integers.")  # Ensure all filter IDs are integers
    if not filter_ids:
        raise ValueError("Please provide at least one HRU ID.")
    if any(i <= 0 for i in filter_ids):
        raise ValueError("Filter IDs must be positive integers.")

    # Prepare destination folder name based on the HRU IDs or current timestamp
    dest_folder_name = (
        f"solo_{filter_ids[0]}" if len(filter_ids) == 1  # Single HRU: "solo_<id>"
        else f"multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # Multiple HRUs: "multi_<timestamp>"
    )
    dest_dir = Path(src_dir) / dest_folder_name  # Destination directory path

    # Copy source directory contents to the destination directory
    TxtinoutReader.copy_swat(src_dir, dest_dir, keep_routing=keep_routing)

    if keep_routing:
        # Routing-aware mode: trace downstream chain, filter all object types
        tracer = RoutingTracer(dest_dir)
        tracer.trace_and_filter(filter_ids)
    else:
        # Simple isolation mode: keep only HRUs, nullify everything else
        fm = FileModifier(dest_dir)
        props_ids = fm.modify_hru_con(filter_ids)
        fm.modify_hru_data(props_ids if props_ids else filter_ids)
        fm.modify_secondary_references()
        fm.modify_object_cnt(len(filter_ids))
        fm.modify_file_cio()
        fm.disable_print_objects({
            "lsunit_wb",
            "lsunit_nb",
            "lsunit_ls",
            "lsunit_pw",
            "ru",
            "ru_salt",
            "ru_cs",
        })

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
