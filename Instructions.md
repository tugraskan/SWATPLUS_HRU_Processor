# **SWAT+ TxtInOut Processor**

## **Getting Started**
This application provides a simple interface for processing and modifying SWAT+ TxtInOut files with options for running simulations.

### **How to Run**
1. **Launch the Application:**
   - Double-click the packaged executable or run it from the command line.
   - The GUI window titled **"SWAT+ TxtInOut Processor"** will open.

2. **Select the Source Directory:**
   - Click **"Browse"** to open a directory selection dialog.
   - Navigate to the folder containing SWAT+ TxtInOut files and confirm.

3. **Set HRU Filtering Options:**
   - For single HRU modifications:
     - Leave the **"Multiple HRUs"** toggle OFF.
     - Enter a single HRU ID in the input field.
   - For multiple HRUs:
     - Turn ON the **"Multiple HRUs"** toggle.
     - Enter HRU IDs in list or range format (e.g., `1,4-6,10`).

4. **View HRU(s):**
   - Toggle **"View HRU(s)"** to display the selected HRU details.
   - Information will appear in the display area.

5. **Modify HRUs:**
   - After entering HRU details, click **"Modify HRU"** to apply changes to SWAT+ files.

6. **Run SWAT+ Simulation (Optional):**
   - Turn ON the **"Run SWAT+ Simulation"** toggle.
   - If multiple executables are found, a popup will prompt you to select one.
   - The selected executable will run automatically after modifications.

7. **Success Notification:**
   - Once the process completes, a notification will confirm success.
   - For simulations, check the terminal for additional output details.

---

## **Tooltips**
Tooltips are available throughout the application to guide users:
- Hover over buttons and input fields to see relevant instructions.

---

## **Requirements**
- Ensure the source directory contains valid SWAT+ TxtInOut files.
- For multiple HRUs, input validation ensures only correctly formatted ranges or lists are processed.

---

## **Support**
For questions or troubleshooting, refer to the terminal or logs generated during the application's execution.

## **Download and Run the Executable**
1. **Download the Executable:**
   - Go to the [Releases](https://github.com/tugraskan/swat-huc/releases) page of this repository.
   - Download the latest release of the executable for your operating system.

2. **Run the Executable:**
   - Locate the downloaded executable file on your computer.
   - Double-click the executable to launch the application.
   - Follow the on-screen instructions to use the SWAT+ TxtInOut Processor.
