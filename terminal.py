import tkinter as tk
from tkinter import ttk

def create_terminal_panel(parent, shared_gui_refs):
    """
    Creates the terminal display panel at the bottom of the window.
    Returns a dictionary of references to the created widgets.
    """
    # --- Bottom Frame (Terminal) ---
    # This frame will be packed at the bottom of the root window.
    bottom_frame = tk.Frame(parent, bg="#21232b")

    terminal_container = tk.Frame(bottom_frame)
    terminal_container.pack(fill=tk.X, expand=True, pady=(5, 0), padx=10)
    terminal_container.grid_rowconfigure(0, weight=1)
    terminal_container.grid_columnconfigure(0, weight=1)

    terminal = tk.Text(terminal_container, height=8, bg="#1b1e2b", fg="#0f8", insertbackground="white", wrap="word",
                       highlightbackground="#34374b", highlightthickness=1, bd=0, font=("Consolas", 9))
    terminal.grid(row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(terminal_container, command=terminal.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    terminal['yscrollcommand'] = scrollbar.set

    options_frame = tk.Frame(bottom_frame, bg="#21232b")
    options_frame.pack(fill=tk.X, pady=(2, 0), padx=10)

    show_telemetry_var = tk.BooleanVar(value=False)
    show_discovery_var = tk.BooleanVar(value=False)

    style = ttk.Style()
    style.configure("TCheckbutton", background="#21232b", foreground="white", font=("Segoe UI", 8))
    style.map("TCheckbutton", background=[('active', '#21232b')])

    telemetry_check = ttk.Checkbutton(options_frame, text="Show Raw Telemetry", variable=show_telemetry_var,
                                      style="TCheckbutton")
    telemetry_check.pack(side=tk.LEFT, padx=5)

    discovery_check = ttk.Checkbutton(options_frame, text="Show Raw Discovery", variable=show_discovery_var,
                                      style="TCheckbutton")
    discovery_check.pack(side=tk.LEFT, padx=5)

    # Return a dictionary of the created widgets and their references
    return {
        'terminal': terminal,
        'terminal_cb': lambda msg: terminal.insert(tk.END, msg) and terminal.see(tk.END),
        'terminal_frame': bottom_frame,
        'show_telemetry_var': show_telemetry_var,
        'show_discovery_var': show_discovery_var
    }
