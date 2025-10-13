import tkinter as tk
from tkinter import ttk
import theme

def create_terminal_panel(parent, shared_gui_refs):
    """
    Creates the terminal display panel at the bottom of the window.
    Returns a dictionary of references to the created widgets.
    """
    # Use a themed frame for consistent styling
    bottom_frame = ttk.Frame(parent, style='Card.TFrame')

    terminal_container = ttk.Frame(bottom_frame, style='Card.TFrame')
    terminal_container.pack(fill=tk.X, expand=True, pady=(5, 0), padx=10)
    terminal_container.grid_rowconfigure(0, weight=1)
    terminal_container.grid_columnconfigure(0, weight=1)

    terminal = tk.Text(terminal_container, height=8, bg=theme.WIDGET_BG, fg=theme.TERMINAL_FG_COLOR, 
                       insertbackground=theme.FG_COLOR, wrap="word",
                       highlightbackground=theme.SECONDARY_ACCENT, highlightthickness=1, bd=0, 
                       font=("Consolas", 9))
    terminal.grid(row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(terminal_container, command=terminal.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    terminal['yscrollcommand'] = scrollbar.set

    options_frame = ttk.Frame(bottom_frame, style='Card.TFrame')
    options_frame.pack(fill=tk.X, pady=(2, 0), padx=10)

    show_telemetry_var = tk.BooleanVar(value=False)
    show_discovery_var = tk.BooleanVar(value=False)

    # Use a style that inherits the correct background from the theme
    style = ttk.Style()
    style.configure("Terminal.TCheckbutton", background=theme.CARD_BG, foreground=theme.FG_COLOR, font=("Segoe UI", 8))
    style.map("Terminal.TCheckbutton", background=[('active', theme.CARD_BG)])

    telemetry_check = ttk.Checkbutton(options_frame, text="Show Raw Telemetry", variable=show_telemetry_var,
                                      style="Terminal.TCheckbutton")
    telemetry_check.pack(side=tk.LEFT, padx=5)

    discovery_check = ttk.Checkbutton(options_frame, text="Show Raw Discovery", variable=show_discovery_var,
                                      style="Terminal.TCheckbutton")
    discovery_check.pack(side=tk.LEFT, padx=5)

    # Return a dictionary of the created widgets and their references
    return {
        'terminal': terminal,
        'terminal_cb': lambda msg: terminal.insert(tk.END, msg) and terminal.see(tk.END),
        'terminal_frame': bottom_frame,
        'show_telemetry_var': show_telemetry_var,
        'show_discovery_var': show_discovery_var
    }
