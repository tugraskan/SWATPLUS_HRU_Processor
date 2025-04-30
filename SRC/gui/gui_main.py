import sys
import os

# Add the root project directory to sys.path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import tkinter for GUI elements
import tkinter as tk

# Import the GUI layout and logic components
from gui.gui_layout import setup_gui  # Function to set up the GUI layout
from gui.gui_logic import SWATController  # Class to handle logic for the application

# Entry point of the application
if __name__ == "__main__":
    print("Starting application...")  # Debugging message to indicate the start of the app

    # Create the main tkinter window
    root = tk.Tk()
    root.title("SWAT+ TxtInOut Processor")  # Set the title of the main window

    # Initialize the SWATController, which handles the application's logic
    controller = SWATController(root)

    # Set up the GUI layout, linking it to the controller
    # This creates the visual elements and associates them with the logic
    setup_gui(root, controller)

    # Start the tkinter main event loop to handle user interactions
    root.mainloop()
