# **SWAT+ TxtInOut Processor**

## **Project Description**
This repository contains a GUI-based tool designed to streamline the processing and modification of SWAT+ TxtInOut files. It includes features for filtering Hydrologic Response Units (HRUs), modifying key SWAT+ files, and optionally running simulations using user-selected SWAT+ executables. The tool aims to make SWAT+ workflows more accessible and efficient for users.

## **Key Components**
### **GUI Modules**
- **`gui_main.py`**: Handles the main application logic and user interactions.
- **`gui_layout.py`**: Defines the layout and structure of the graphical user interface (GUI).
- **`gui_logic.py`**: Implements the backend logic tied to user actions in the GUI.
- **`toggle_switch.py`**: Custom toggle switch widget for enabling/disabling features.
- **`tooltip.py`**: Provides hover-based tooltips for better user guidance.

### **Core Processing Modules**
- **`swat_main.py`**: Central processing logic for SWAT+ TxtInOut files, including simulation execution.
- **`FileModifier.py`**: Handles modifications to SWAT+ input files like `hru.con`, `object.cnt`, and `file.cio`.
- **`TxtinoutReader.py`**: A wrapper from the pySWATPlus project for managing SWAT+ TxtInOut files and handling simulations.
- **`FileReader.py`**: A utility from pySWATPlus for reading and processing SWAT+ files.
- **`utils.py`**: General utility functions to support file operations and input validation.

## **PySWATPlus Integration**
- **`TxtinoutReader`** and **`FileReader`** modules are adapted from the pySWATPlus project, providing robust file-reading capabilities tailored for SWAT+.

## **Features**
- **HRU Filtering**: Modify SWAT+ input files for a single HRU or a range of HRUs.
- **Simulation Execution**: Run SWAT+ simulations directly from the GUI with support for selecting multiple executable files.
- **File Modifications**: Update core SWAT+ files (e.g., `hru.con`, `object.cnt`, `file.cio`) based on user inputs.
- **User-Friendly Interface**: A GUI with tooltips and toggles to simplify SWAT+ workflows.

## **How to Use**
1. Launch the GUI application.
2. Select a source directory containing SWAT+ TxtInOut files.
3. Configure HRU filters and file modification settings.
4. Optionally, run simulations by selecting a SWAT+ executable.

## **Requirements**
- SWAT+ TxtInOut files in the source directory.
- Python 3.x and required dependencies (if running from source).

## **Acknowledgments**
This project integrates key modules from the pySWATPlus project, a comprehensive library for managing and processing SWAT+ files.

## **Download and Run the Executable**
1. **Download the Executable:**
   - Go to the [Releases](https://github.com/tugraskan/swat-huc/releases) page of this repository.
   - Download the latest release of the executable for your operating system.

2. **Run the Executable:**
   - Locate the downloaded executable file on your computer.
   - Double-click the executable to launch the application.
   - Follow the on-screen instructions to use the SWAT+ TxtInOut Processor.
