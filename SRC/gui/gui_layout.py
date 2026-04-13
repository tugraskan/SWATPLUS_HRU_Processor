import tkinter as tk
from gui.toggle_switch import ToggleSwitch
from gui.tooltip import Tooltip
from tkinter import ttk, messagebox
from pathlib import Path


def setup_gui(root, controller):
    """
    Set up the main graphical user interface (GUI) for the SWAT+ tool.

    Parameters:
    - root: The main Tkinter root window.
    - controller: The controller instance responsible for handling logic.
    """
    # Source Directory
    tk.Label(root, text="Source Directory:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    src_dir_entry = tk.Entry(root, width=50)
    src_dir_entry.grid(row=0, column=1, padx=10, pady=10)
    browse_button = tk.Button(root, text="Browse", command=controller.browse_directory)
    browse_button.grid(row=0, column=2, padx=10, pady=10)
    Tooltip(src_dir_entry, "Select the directory containing SWAT+ TxtInOut files.")
    Tooltip(browse_button, "Browse to select the source directory.")  # Tooltip for the browse button

    # Assign to controller
    controller.src_dir_entry = src_dir_entry

    # HRU Range and Total HRUs Labels
    label_hru_range = tk.Label(root, text="HRU Range: Not Loaded")
    label_hru_range.grid(row=1, column=1, padx=5, pady=5)
    controller.label_hru_range = label_hru_range

    label_total_hrus = tk.Label(root, text="Total HRUs: Not Loaded")
    label_total_hrus.grid(row=2, column=1, padx=5, pady=5)
    controller.label_total_hrus = label_total_hrus

    # Filter ID(s) Entry with Validation
    tk.Label(root, text="Filter ID(s):").grid(row=3, column=0, padx=10, pady=10, sticky="w")

    # Validation Command
    vcmd = (root.register(controller.validate_single_hru), '%P')
    filter_id_entry = tk.Entry(root, width=20, validate="key", validatecommand=vcmd)
    filter_id_entry.grid(row=3, column=1, padx=10, pady=10, sticky="w")
    Tooltip(filter_id_entry, "Enter a single HRU ID or multiple HRU IDs (e.g., '1,4-6,10').")
    controller.filter_id_entry = filter_id_entry

    # Toggle for Multiple HRUs
    allow_multiple_hru_var = tk.BooleanVar(value=False)
    hru_toggle = ToggleSwitch(root, "Multiple HRUs", allow_multiple_hru_var, command=controller.toggle_hru_mode)
    hru_toggle.grid(row=3, column=2, padx=10, pady=10)
    Tooltip(hru_toggle, "Enable or disable multiple HRU selection.")  # Tooltip for multiple HRU toggle
    controller.allow_multiple_hru_var = allow_multiple_hru_var

    # View HRU(s) Toggle
    view_hru_var = tk.BooleanVar(value=False)
    view_toggle = ToggleSwitch(root, "View HRU(s)", view_hru_var, command=controller.view_selected_line)
    view_toggle.grid(row=4, column=2, padx=10, pady=10)
    Tooltip(view_toggle, "Toggle to view selected HRU information.")  # Tooltip for view HRU toggle
    controller.view_hru_var = view_hru_var

    # Selected HRU Line Display
    label_selected_line = tk.Label(root, text="Selected HRU(s): Not Loaded", wraplength=400, justify="left")
    label_selected_line.grid(row=5, column=1, padx=5, pady=5)
    controller.label_selected_line = label_selected_line

    # Run SWAT+ Simulation Toggle
    run_simulation_var = tk.BooleanVar(value=False)
    run_toggle = ToggleSwitch(root, "Run SWAT+ Simulation", run_simulation_var)
    run_toggle.grid(row=6, column=1, padx=10, pady=10)
    Tooltip(run_toggle, "Enable or disable SWAT+ simulation after modification.")  # Tooltip for run simulation toggle
    controller.run_simulation_var = run_simulation_var

    # Keep Routing Toggle
    keep_routing_var = tk.BooleanVar(value=False)
    routing_toggle = ToggleSwitch(root, "Keep Routing", keep_routing_var)
    routing_toggle.grid(row=7, column=1, padx=10, pady=10)
    Tooltip(routing_toggle, "When ON, preserves the downstream routing chain (channels, aquifers, reservoirs, etc.) instead of isolating HRUs only.")
    controller.keep_routing_var = keep_routing_var

    # Modify HRU Button
    run_button = tk.Button(root, text="Modify HRU", command=controller.run_script)
    run_button.grid(row=9, column=1, padx=10, pady=20)
    Tooltip(run_button, "Click to modify HRUs and optionally run the simulation.")  # Tooltip for the modify HRU button

def create_executable_popup(root, exe_files, on_selection):
    """
    Create a popup dialog for selecting an executable file.

    Parameters:
    - root: The main Tkinter root window.
    - exe_files (list): List of executable file paths to display.
    - on_selection (callable): Callback function to execute when a selection is made.
    """
    if not exe_files:
        messagebox.showerror("No Executables Found", "No executable files found in the directory.")
        return

    selected_exe = tk.StringVar(value="")  # Variable to store the selected executable

    def on_ok():
        """
        Callback for the OK button in the popup.
        """
        if not selected_exe.get():
            messagebox.showerror("No Selection", "Please select one executable.")
        else:
            on_selection(Path(selected_exe.get()))  # Pass the selected path to the callback
            popup.destroy()  # Close the popup

    # Create and configure the popup window
    popup = tk.Toplevel(root)
    popup.title("Select Executable")
    popup.geometry("400x300")

    ttk.Label(popup, text="Select an executable file to run the simulation:").pack(pady=10)
    for exe in exe_files:
        ttk.Radiobutton(
            popup,
            text=str(exe.name),
            variable=selected_exe,
            value=str(exe)
        ).pack(anchor="w")

    ttk.Button(popup, text="OK", command=on_ok).pack(pady=10)
    popup.transient(root)  # Keep popup on top of the root window
    popup.grab_set()  # Make popup modal
    popup.mainloop()
