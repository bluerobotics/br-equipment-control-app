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

def make_homed_tracer(var, label_to_color):
    """Changes a label's color based on 'Homed' status."""
    def tracer(*args):
        state = var.get()
        if state == 'Homed':
            label_to_color.config(foreground=theme.SUCCESS_GREEN)
        else:
            label_to_color.config(foreground=theme.ERROR_RED)
    return tracer

def make_torque_tracer(double_var, string_var):
    """Updates a string variable with a percentage from a double variable."""
    def tracer(*args):
        try:
            # Get the value, which might be a float or a string like "50.0 %"
            val_raw = double_var.get()
            
            # Convert to float, stripping non-numeric parts if necessary
            val_float = float(str(val_raw).split()[0])
            
            string_var.set(f"{int(val_float)}%")
        except (tk.TclError, ValueError, IndexError):
            string_var.set("ERR")
    return tracer

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

def make_unit_stripper(source_var, dest_var, unit_to_strip):
    """Strips a unit suffix from a source variable and updates a destination variable."""
    def tracer(*args):
        value = source_var.get()
        # Remove the unit suffix if present
        if value.endswith(unit_to_strip):
            value = value[:-len(unit_to_strip)].strip()
        dest_var.set(value)
    return tracer

def create_torque_widget(parent, torque_dv, height):
    """Creates a vertical torque meter widget."""
    torque_frame = ttk.Frame(parent, height=height, width=30, style='TFrame')
    torque_frame.pack_propagate(False)
    torque_sv = tk.StringVar()
    torque_frame.tracer = make_torque_tracer(torque_dv, torque_sv)
    torque_dv.trace_add('write', torque_frame.tracer)
    pbar = ttk.Progressbar(torque_frame, variable=torque_dv, maximum=100, orient=tk.VERTICAL, style='Card.Vertical.TProgressbar')
    pbar.pack(fill=tk.BOTH, expand=True)
    label = ttk.Label(torque_frame, textvariable=torque_sv, font=theme.FONT_SMALL, anchor='center', style='Subtle.TLabel')
    label.place(relx=0.5, rely=0.5, anchor='center')
    torque_frame.tracer()
    return torque_frame

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
        # conn_icon_label.config(text="✅" if is_connected else "🔌", foreground=theme.SUCCESS_GREEN if is_connected else theme.ERROR_RED) # Removed as per edit hint
        ip_label.config(text=ip_address)
    header_frame.conn_tracer = conn_tracer
    conn_var.trace_add("write", header_frame.conn_tracer)
    header_frame.conn_tracer()
    outer_container.ip_label = ip_label
    content_frame = ttk.Frame(container, style='Card.TFrame')
    content_frame.pack(fill='x', expand=True, pady=(5,0))
    return outer_container, content_frame

def get_gui_variable_names():
    """Returns a list of tkinter variable names required by this GUI module."""
    return [
        'gantry_main_state_var', 'status_var_gantry',
        'gantry_x_pos_var', 'gantry_x_torque_var', 'gantry_x_enabled_var', 'gantry_x_homed_var', 'gantry_x_state_var',
        'gantry_y_pos_var', 'gantry_y_torque_var', 'gantry_y_enabled_var', 'gantry_y_homed_var', 'gantry_y_state_var',
        'gantry_z_pos_var', 'gantry_z_torque_var', 'gantry_z_enabled_var', 'gantry_z_homed_var', 'gantry_z_state_var'
    ]

# --- Main GUI Creation Function ---

def create_gui_components(parent, shared_gui_refs):
    """Creates the Gantry status panel."""

    # Initialize all required tkinter variables
    for var_name in get_gui_variable_names():
        if var_name.endswith('_var'):
            if 'torque' in var_name:
                shared_gui_refs.setdefault(var_name, tk.DoubleVar(value=0.0))
            else:
                shared_gui_refs.setdefault(var_name, tk.StringVar(value='---'))
    
    font_large_readout = ("JetBrains Mono", 28, "bold")
    bar_height = 55

    device_frame, content_frame = create_device_frame(parent, "Gantry", shared_gui_refs['gantry_main_state_var'], shared_gui_refs['status_var_gantry'])
    shared_gui_refs['gantry_panel'] = device_frame
    
    # Override the IP label tracer for gantry to show "@ IP" or "@ COM"
    ip_label = getattr(device_frame, 'ip_label', None)
    if ip_label is not None:
        # Remove all existing tracers on this variable to avoid conflicts
        trace_info = shared_gui_refs['status_var_gantry'].trace_info()
        for trace in trace_info:
            if 'write' in trace[0]:
                try:
                    shared_gui_refs['status_var_gantry'].trace_remove('write', trace[1])
                except Exception as e:
                    pass
        
        def gantry_conn_tracer(*args):
            full_status = shared_gui_refs['status_var_gantry'].get()
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
        
        shared_gui_refs['status_var_gantry'].trace_add('write', gantry_conn_tracer)
        gantry_conn_tracer()
        
        # Also schedule a delayed update to catch any timing issues
        def delayed_update():
            gantry_conn_tracer()
        parent.after(100, delayed_update)

    gantry_axes_data = [
        {'label': 'X', 'pos_var': 'gantry_x_pos_var', 'homed_var': 'gantry_x_homed_var', 'torque_var': 'gantry_x_torque_var', 'state_var': 'gantry_x_state_var'},
        {'label': 'Y', 'pos_var': 'gantry_y_pos_var', 'homed_var': 'gantry_y_homed_var', 'torque_var': 'gantry_y_torque_var', 'state_var': 'gantry_y_state_var'},
        {'label': 'Z', 'pos_var': 'gantry_z_pos_var', 'homed_var': 'gantry_z_homed_var', 'torque_var': 'gantry_z_torque_var', 'state_var': 'gantry_z_state_var'},
    ]
    for axis_info in gantry_axes_data:
        axis_frame = ttk.Frame(content_frame, style='Card.TFrame')
        axis_frame.pack(anchor='w', pady=4, fill='x')
        axis_frame.grid_columnconfigure(2, weight=1)
        axis_label = ttk.Label(axis_frame, text=f"{axis_info['label']}:", width=3, anchor='w', font=font_large_readout, style='Subtle.TLabel')
        axis_label.grid(row=0, column=0, sticky='ns', padx=(0, 5))
        
        # Create and trace the state label
        state_label = ttk.Label(axis_frame, textvariable=shared_gui_refs[axis_info['state_var']], font=theme.FONT_NORMAL, style='Subtle.TLabel')
        state_label.grid(row=0, column=1, sticky='w', padx=(0, 10))
        state_label.tracer = make_state_tracer(shared_gui_refs[axis_info['state_var']], state_label)
        shared_gui_refs[axis_info['state_var']].trace_add('write', state_label.tracer)
        state_label.tracer()

        # Create a display variable that strips " mm" from the position
        pos_display_var = tk.StringVar(value='0.00')
        pos_source_var = shared_gui_refs[axis_info['pos_var']]
        stripper = make_unit_stripper(pos_source_var, pos_display_var, ' mm')
        pos_source_var.trace_add('write', stripper)
        stripper()  # Initialize
        
        ttk.Label(axis_frame, textvariable=pos_display_var, font=font_large_readout, anchor='e', style='Subtle.TLabel').grid(row=0, column=2, sticky='ew', padx=(0, 10))
        torque_widget = create_torque_widget(axis_frame, shared_gui_refs[axis_info['torque_var']], bar_height)
        torque_widget.grid(row=0, column=3, rowspan=1, sticky='ns', padx=(10, 0))
        homed_var = shared_gui_refs[axis_info['homed_var']]
        axis_label.tracer = make_homed_tracer(homed_var, axis_label)
        homed_var.trace_add('write', axis_label.tracer)
        axis_label.tracer()

    return device_frame
