import tkinter as tk
from tkinter import ttk
import theme

def create_status_bar(parent, shared_gui_refs):
    """
    Creates the main container for all status widgets and returns a dictionary
    of the created widgets and variables.
    """
    # --- Main Container ---
    # This frame will hold all the individual status panels.
    status_bar_container = ttk.Frame(parent, style='TFrame')
    status_bar_container.pack(side=tk.TOP, fill='x', expand=False)

    # The main application will now be responsible for populating this container
    # with device-specific panels.

    return {
        'status_bar_container': status_bar_container
    }

