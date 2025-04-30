# gui/tooltip.py

import tkinter as tk


class Tooltip:
    """
    A class to create tooltips for Tkinter widgets. The tooltip
    appears when the user hovers over the widget and disappears
    when the user moves the cursor away.
    """

    def __init__(self, widget, text):
        """
        Initialize the Tooltip.

        Parameters:
        - widget: The Tkinter widget to which the tooltip is attached.
        - text: The text to display in the tooltip.
        """
        self.widget = widget  # The widget this tooltip is attached to
        self.text = text  # The text to display in the tooltip
        self.tip_window = None  # The window showing the tooltip (None if not visible)

        # Bind events to show and hide the tooltip on mouse hover
        widget.bind("<Enter>", self.show_tooltip)  # Show tooltip on mouse enter
        widget.bind("<Leave>", self.hide_tooltip)  # Hide tooltip on mouse leave

    def show_tooltip(self, _):
        """
        Display the tooltip window when the user hovers over the widget.

        Parameters:
        - _: The event object (not used).
        """
        if self.tip_window or not self.text:
            # If the tooltip is already displayed or no text to show, do nothing
            return

        # Calculate the position for the tooltip window relative to the widget
        x, y, _, _ = self.widget.bbox("insert")  # Get widget's bounding box
        x += self.widget.winfo_rootx() + 25  # Add offset to x position
        y += self.widget.winfo_rooty() + 25  # Add offset to y position

        # Create a new top-level window for the tooltip
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove the window decorations (border, title bar)
        tw.wm_geometry(f"+{x}+{y}")  # Position the tooltip window

        # Add a label to display the tooltip text
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",  # Align text to the left
            background="#ffffe0",  # Light yellow background
            relief="solid",  # Add a solid border around the tooltip
            borderwidth=1,  # Border width of 1 pixel
            font=("tahoma", "8", "normal")  # Font styling
        )
        label.pack(ipadx=1)  # Add internal padding around the label

    def hide_tooltip(self, _):
        """
        Destroy the tooltip window when the user moves the cursor away from the widget.

        Parameters:
        - _: The event object (not used).
        """
        if self.tip_window:
            # Destroy the tooltip window and reset the reference
            self.tip_window.destroy()
            self.tip_window = None
