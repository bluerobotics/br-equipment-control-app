import tkinter as tk
from tkinter import ttk
import sys
import os

# Adjust path for standalone execution
if __name__ == "__main__":
    # This allows the script to find modules in the parent directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, parent_dir)

from src import theme

# --- GUI Helper Functions (self-contained in each module) ---

def make_state_tracer(var, label_to_color):
    """Changes a label's color based on general device state."""
    def tracer(*args):
        state = var.get().upper()
        color = theme.FG_COLOR
        if "STANDBY" in state: color = theme.SUCCESS_GREEN
        elif "BUSY" in state or "ACTIVE" in state or "HOMING" in state or "MOVING" in state: color = theme.BUSY_BLUE
        elif "ERROR" in state: color = theme.ERROR_RED
        label_to_color.config(foreground=color)
    return tracer

def create_device_frame(parent, title, state_var, conn_var):
    """Creates the main bordered frame for a device panel."""
    outer_container = ttk.Frame(parent, style='CardBorder.TFrame', padding=1)
    container = ttk.Frame(outer_container, style='Card.TFrame', padding=10)
    container.pack(fill='x', expand=True)
    header_frame = ttk.Frame(container, style='Card.TFrame')
    header_frame.pack(fill='x', expand=True, anchor='n')
    title_label = ttk.Label(header_frame, text=title.lower(), font=theme.FONT_LARGE_BOLD, foreground=theme.DEVICE_COLOR, style='Subtle.TLabel')
    title_label.pack(side=tk.LEFT, padx=(0, 5))
    ip_label = ttk.Label(header_frame, text="", font=theme.FONT_SMALL, style='Subtle.TLabel')
    ip_label.pack(side=tk.LEFT, anchor='sw', pady=(0, 2))
    state_label = ttk.Label(header_frame, textvariable=state_var, font=theme.FONT_BOLD, style='Subtle.TLabel')
    state_label.pack(side=tk.RIGHT)
    state_label.tracer = make_state_tracer(state_var, state_label)
    state_var.trace_add('write', state_label.tracer)
    state_label.tracer()
    def conn_tracer(*args):
        full_status = conn_var.get()
        is_connected = "Connected" in full_status
        ip_address = ""
        if is_connected:
            try:
                ip_address = full_status.split('(')[1].split(')')[0]
            except IndexError: ip_address = "?.?.?.?"
        # The conn_icon_label is removed, so this tracer is no longer needed.
        # The ip_label will handle the text update.
        ip_label.config(text=ip_address)
    header_frame.conn_tracer = conn_tracer
    conn_var.trace_add("write", header_frame.conn_tracer)
    header_frame.conn_tracer()
    outer_container.ip_label = ip_label
    content_frame = ttk.Frame(container, style='Card.TFrame')
    content_frame.pack(fill='x', expand=True, pady=(5,0))
    return outer_container, content_frame

# --- Main GUI Creation Function ---

def get_required_variables():
    """Returns a list of all required tkinter variables for the Pressurizer GUI."""
    return [
        'pressurizer_main_state_var',
        'pressurizer_pressure_var',
        'pressurizer_cycles_programmed_var',
        'pressurizer_cycles_complete_var',
        'pressurizer_tank1_temp_var',
        'pressurizer_tank2_temp_var',
        'status_var_pressurizer'
    ]

def create_stat(parent, label_text, var, row, col, unit=""):
    """Helper to create a formatted stat label in the grid."""
    frame = ttk.Frame(parent, style='Card.TFrame')
    frame.grid(row=row, column=col, sticky='ew', padx=5, pady=2)
    ttk.Label(frame, text=label_text, style='Subtle.TLabel', anchor='w').pack(side=tk.LEFT)
    val_label = ttk.Label(frame, textvariable=var, style='Subtle.TLabel', font=theme.FONT_BOLD, anchor='e')
    val_label.pack(side=tk.RIGHT)
    if unit:
        ttk.Label(frame, text=unit, style='Subtle.TLabel', anchor='e').pack(side=tk.RIGHT)

def create_gui_components(parent, shared_gui_refs):
    """Creates the Pressurizer status panel."""
    
    # Initialize all required tkinter variables
    for var_name in get_required_variables():
        if var_name.endswith('_var'):
            shared_gui_refs.setdefault(var_name, tk.StringVar(value='---'))

    device_frame, content_frame = create_device_frame(
        parent, 
        "Pressurizer",
        shared_gui_refs['pressurizer_main_state_var'],
        shared_gui_refs['status_var_pressurizer']
    )
    shared_gui_refs['pressurizer_panel'] = device_frame
    
    # Override the IP label tracer for pressurizer to show "@ IP" or "@ COM"
    ip_label = getattr(device_frame, 'ip_label', None)
    if ip_label is not None:
        # Remove all existing tracers on this variable to avoid conflicts
        trace_info = shared_gui_refs['status_var_pressurizer'].trace_info()
        for trace in trace_info:
            if 'write' in trace[0]:
                try:
                    shared_gui_refs['status_var_pressurizer'].trace_remove('write', trace[1])
                except Exception as e:
                    pass
        
        def pressurizer_conn_tracer(*args):
            full_status = shared_gui_refs['status_var_pressurizer'].get()
            if '(' in full_status and ')' in full_status:
                try:
                    address = full_status.split('(')[1].split(')')[0]
                    if 'SIM' in full_status.upper() or 'SIMULATOR' in full_status.upper():
                        ip_label.config(text="[Simulator]", foreground=theme.WARNING_YELLOW)
                    else:
                        # Show @ for both IP addresses and COM ports
                        ip_label.config(text=f"@ {address}", foreground=theme.SUCCESS_GREEN)
                except (IndexError, AttributeError):
                    ip_label.config(text="", foreground=theme.COMMENT_COLOR)
            else:
                ip_label.config(text="", foreground=theme.COMMENT_COLOR)
        
        shared_gui_refs['status_var_pressurizer'].trace_add('write', pressurizer_conn_tracer)
        pressurizer_conn_tracer()
        
        # Also schedule a delayed update to catch any timing issues
        def delayed_update():
            pressurizer_conn_tracer()
        parent.after(100, delayed_update)
    
    # --- Main Content ---
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_columnconfigure(1, weight=1)

    # Pressure display
    pressure_frame = ttk.Frame(content_frame, style='Card.TFrame')
    pressure_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(5, 10))
    pressure_frame.grid_columnconfigure(1, weight=1)
    ttk.Label(pressure_frame, text="Pressure (msw):", style='Subtle.TLabel', font=theme.FONT_NORMAL).grid(row=0, column=0, sticky='w')
    pressure_val_label = ttk.Label(pressure_frame, textvariable=shared_gui_refs['pressurizer_pressure_var'], style='Subtle.TLabel', font=theme.FONT_LARGE_BOLD, anchor='e')
    pressure_val_label.grid(row=0, column=1, sticky='e')

    # Stats
    create_stat(content_frame, "Cycles Programmed:", shared_gui_refs['pressurizer_cycles_programmed_var'], 1, 0)
    create_stat(content_frame, "Cycles Complete:", shared_gui_refs['pressurizer_cycles_complete_var'], 1, 1)
    create_stat(content_frame, "Tank 1 Temp:", shared_gui_refs['pressurizer_tank1_temp_var'], 2, 0, "°C")
    create_stat(content_frame, "Tank 2 Temp:", shared_gui_refs['pressurizer_tank2_temp_var'], 2, 1, "°C")

    return device_frame
