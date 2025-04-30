# gui/toggle_switch.py

import tkinter as tk

class ToggleSwitch(tk.Frame):
    """
    A custom Toggle Switch widget for Tkinter, acting as a labeled switch
    that toggles between ON and OFF states.
    """

    def __init__(self, master, text, var, on_text="ON", off_text="OFF", command=None):
        """
        Initialize the ToggleSwitch widget.

        Parameters:
        - master: The parent widget for this ToggleSwitch.
        - text (str): The label text displayed next to the toggle switch.
        - var (tk.BooleanVar): A Tkinter BooleanVar to hold the state of the toggle switch.
        - on_text (str): Text displayed when the switch is ON (default: "ON").
        - off_text (str): Text displayed when the switch is OFF (default: "OFF").
        - command (callable): An optional callback function executed when the switch is toggled.
        """
        super().__init__(master)  # Initialize as a Frame widget
        self.var = var  # State variable to track ON/OFF
        self.command = command  # Optional callback function
        self.on_text = on_text  # Text displayed when ON
        self.off_text = off_text  # Text displayed when OFF

        # Button for toggling between ON/OFF states
        self.switch_button = tk.Button(
            self,
            text=self.off_text,
            width=6,
            bg="grey",  # Default OFF background color
            fg="white",  # Text color
            relief="sunken",  # Button appearance for OFF state
            command=self.toggle  # Command to execute when clicked
        )
        self.switch_button.pack(side="left")  # Place the button on the left side of the frame

        # Label to display the toggle switch's description text
        self.label = tk.Label(self, text=text, width=20, anchor="w")  # Left-aligned text
        self.label.pack(side="left", padx=(10, 0))  # Add spacing between button and label

    def toggle(self):
        """
        Toggle the switch's state and update its appearance.

        This method flips the state of the BooleanVar, changes the button's
        appearance (text, background color, and relief), and executes the
        optional callback function if provided.
        """
        # Flip the state of the BooleanVar
        self.var.set(not self.var.get())

        # Update the button's appearance based on the new state
        self.switch_button.config(
            text=self.on_text if self.var.get() else self.off_text,  # Text updates to ON/OFF
            bg="green" if self.var.get() else "grey",  # Green for ON, Grey for OFF
            relief="raised" if self.var.get() else "sunken"  # Raised for ON, Sunken for OFF
        )

        # Execute the callback function, if provided
        if self.command:
            self.command()
