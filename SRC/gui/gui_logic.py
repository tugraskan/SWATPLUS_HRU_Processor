import tkinter as tk
from tkinter import messagebox, filedialog
import sys
import os

from pathlib import Path

# Add the root project directory to sys.path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.tooltip import Tooltip

from core.TxtinoutReader import TxtinoutReader
from core.utils import parse_filter_ids
from core.swat_main import main
from gui.gui_layout import create_executable_popup  # Function to create the executable selection popup
from core.FileModifier import FileModifier  # Importing FileModifier to resolve undefined name error


class SWATController:
    """
    The controller class for handling GUI events and logic for the SWAT+ TxtInOut Processor.
    """

    def __init__(self, root):
        """
        Initialize the controller with the main Tkinter root.

        Args:
            root (Tk): The main Tkinter root window.
        """
        self.root = root
        self.file_modifier = None  # Object to handle file modifications
        self.selected_exe = None  # Store the selected `.exe` file
        self.exe_files = []

    def browse_directory(self):
        """
        Open a directory selection dialog and update the source directory entry field.
        """
        directory = filedialog.askdirectory()
        if directory:
            self.src_dir_entry.delete(0, tk.END)  # Clear the existing entry
            self.src_dir_entry.insert(0, directory)  # Set the selected directory
            self.setup_file_modifier(directory)

    def setup_file_modifier(self, directory):
        """
        Set up the file modifier for the selected directory and retrieve `.exe` files.

        Args:
            directory (str): Path to the selected directory.
        """
        self.file_modifier = FileModifier(directory)
        self.selected_exe = None
        try:
            # Initialize TxtinoutReader and retrieve `.exe` files
            txtinout_reader = TxtinoutReader(directory)
            self.exe_files = txtinout_reader.swat_exe_paths  # Store `.exe` file paths
            print(f"Executable files detected: {self.exe_files}")  # Debugging

            # Update HRU range and total HRUs in the GUI
            min_hru, max_hru, total_hrus = self.file_modifier.get_hru_range()
            self.label_hru_range.config(text=f"HRU Range: {min_hru} - {max_hru}")
            self.label_total_hrus.config(text=f"Total HRUs: {total_hrus}")
        except Exception as e:
            messagebox.showerror("File Error", str(e))
            self.exe_files = []  # Reset `.exe` files on error

    def toggle_hru_mode(self):
        """
        Toggle between single and multiple HRU modes and update the tooltip accordingly.
        """
        if self.allow_multiple_hru_var.get():  # Multi-HRU mode
            self.filter_id_entry.delete(0, tk.END)  # Clear the input field
            Tooltip(self.filter_id_entry, "Enter multiple HRU IDs (e.g., '1,4-6,10')")
        else:  # Single-HRU mode
            self.filter_id_entry.delete(0, tk.END)  # Clear the input field
            Tooltip(self.filter_id_entry, "Enter a single HRU ID.")

    def validate_single_hru(self, new_value):
        """
        Validate input for single HRU mode to allow only integers.

        Args:
            new_value (str): The new value entered by the user.

        Returns:
            bool: True if valid, False otherwise.
        """
        if self.allow_multiple_hru_var.get():  # Allow any input in multi-HRU mode
            return True
        return new_value.isdigit() or new_value == ""  # Allow digits or an empty string

    def view_selected_line(self):
        """
        Display information about the selected HRU(s) in the GUI.
        """
        if not self.view_hru_var.get():  # Check if the view toggle is enabled
            self.label_selected_line.config(text="Selected HRU(s): Not Loaded")
            return

        filter_ids_input = self.filter_id_entry.get()

        # Validate the input for single or multiple HRU mode
        if not self.allow_multiple_hru_var.get():  # Single-HRU mode
            if not filter_ids_input.isdigit():
                messagebox.showerror("Invalid HRU ID", "Please enter a valid integer HRU ID.")
                return
            filter_ids = [int(filter_ids_input)]
        else:  # Multi-HRU mode
            try:
                filter_ids = parse_filter_ids(filter_ids_input)
            except ValueError as e:
                messagebox.showerror("Invalid Filter ID(s)", str(e))
                return

        if not self.file_modifier:  # Ensure file modifier is set up
            messagebox.showerror("Input Error", "Please select a source directory first.")
            return

        # Retrieve and display selected HRU(s)
        selected_lines = []
        for filter_id in filter_ids:
            selected_line = self.file_modifier.get_hru_line(filter_id)
            line_info = (
                f"HRU {filter_id}: {', '.join(f'{k}: {v}' for k, v in selected_line.items())}"
                if selected_line
                else f"No row found with ID = {filter_id}."
            )
            selected_lines.append(line_info)
        self.label_selected_line.config(text="\n".join(selected_lines))

    def prompt_executable_selection(self):
        """
        Display a popup for selecting an executable file and proceed with the simulation.
        """
        if not self.exe_files:  # Ensure there are `.exe` files to select
            messagebox.showerror("No Executables Found", "No executable files found in the directory.")
            return

        # Callback to handle the selected executable
        def handle_selection(selected_exe):
            self.selected_exe = selected_exe
            print(f"Selected Executable: {self.selected_exe}")  # Debugging
            self.run_script()  # Automatically proceed with the simulation

        # Create the executable selection popup
        create_executable_popup(self.root, self.exe_files, handle_selection)

    def run_script(self):
        """
        Run the SWAT+ processing and optionally the simulation.
        """
        src_dir = self.src_dir_entry.get()
        filter_ids_input = self.filter_id_entry.get()
        run_simulation = self.run_simulation_var.get()
        keep_routing = self.keep_routing_var.get()

        if not os.path.isdir(src_dir):  # Validate source directory
            messagebox.showerror("Invalid Directory", "Please select a valid source directory.")
            return

        try:
            filter_ids = parse_filter_ids(filter_ids_input)  # Parse filter IDs
        except ValueError as e:
            messagebox.showerror("Invalid Filter ID(s)", str(e))
            return

        # Ensure an executable is selected if simulation is enabled
        if run_simulation and not self.selected_exe:
            if isinstance(self.exe_files, Path):  # Single `.exe` file
                if self.exe_files.suffix == '.exe':  # Ensure it's a valid executable
                    self.selected_exe = self.exe_files  # Auto-select the file
                else:
                    messagebox.showerror("Error", "The provided file is not an executable.")
                    return
            elif isinstance(self.exe_files, list):  # Multiple `.exe` files
                if len(self.exe_files) > 1:  # Prompt for selection
                    self.prompt_executable_selection()
                    return
                elif len(self.exe_files) == 1:  # Auto-select the only file
                    self.selected_exe = self.exe_files[0]
                else:
                    messagebox.showerror("Error", "No executable files found.")
                    return
            else:
                messagebox.showerror("Error", "Invalid type for `exe_files`.")
                return

        print(f"Running with Executable: {self.selected_exe}")  # Debugging

        # Call the main processing logic
        try:
            main(
                src_dir=src_dir,
                filter_ids=filter_ids,
                run_simulation=run_simulation,
                exe_path=self.selected_exe,
                keep_routing=keep_routing,
            )
            messagebox.showinfo("Success", "SWAT+ files processed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
