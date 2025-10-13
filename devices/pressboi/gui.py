import tkinter as tk
from tkinter import ttk
import theme

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
            val = double_var.get()
            string_var.set(f"{int(val)}%")
        except (tk.TclError, ValueError):
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
        elif "DISABLED" in state: color = theme.ERROR_RED
        elif "ENABLED" in state: color = theme.SUCCESS_GREEN
        label_to_color.config(foreground=color)
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
    label = ttk.Label(torque_frame, textvariable=torque_sv, font=("JetBrains Mono", 7, "bold"), anchor='center', style='Subtle.TLabel')
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
    conn_icon_label = ttk.Label(header_frame, text="🔌", font=("JetBrains Mono", 12), style='Subtle.TLabel')
    conn_icon_label.pack(side=tk.LEFT, padx=(0, 2))
    title_label = ttk.Label(header_frame, text=title, font=("JetBrains Mono", 14, "bold"), foreground=theme.PRIMARY_ACCENT, style='Subtle.TLabel')
    title_label.pack(side=tk.LEFT, padx=(0, 5))
    ip_label = ttk.Label(header_frame, text="", font=("JetBrains Mono", 9), style='Subtle.TLabel')
    ip_label.pack(side=tk.LEFT, anchor='sw', pady=(0, 2))
    state_label = ttk.Label(header_frame, textvariable=state_var, font=("JetBrains Mono", 14, "bold"), style='Subtle.TLabel')
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
        conn_icon_label.config(text="✅" if is_connected else "🔌", foreground=theme.SUCCESS_GREEN if is_connected else theme.ERROR_RED)
        ip_label.config(text=ip_address)
    header_frame.conn_tracer = conn_tracer
    conn_var.trace_add("write", header_frame.conn_tracer)
    header_frame.conn_tracer()
    content_frame = ttk.Frame(container, style='Card.TFrame')
    content_frame.pack(fill='x', expand=True, pady=(5,0))
    return outer_container, content_frame

def get_required_variables():
    """Returns a list of tkinter variable names required by this GUI module."""
    return [
        'pressboi_main_state_var', 'status_var_pressboi',
        'pressboi_pos_m0_var', 'pressboi_homed_m0_var', 'pressboi_enabled_m0_var', 'pressboi_torque_m0_var',
        'pressboi_pos_m1_var', 'pressboi_homed_m1_var', 'pressboi_enabled_m1_var', 'pressboi_torque_m1_var',
        'pressboi_pressure_var', 'pressboi_temperature_var', 'pressboi_enabled_var'
    ]

# --- Main GUI Creation Function ---

def create_gui_components(parent, shared_gui_refs):
    """Creates the PressBoi status panel."""
    
    # Initialize all required tkinter variables
    for var_name in get_required_variables():
        if var_name.endswith('_var'):
            if 'torque' in var_name:
                shared_gui_refs.setdefault(var_name, tk.DoubleVar(value=0.0))
            else:
                shared_gui_refs.setdefault(var_name, tk.StringVar(value='---'))

    outer_container, content_frame = create_device_frame(
        parent, 
        "PressBoi",
        shared_gui_refs['pressboi_main_state_var'],
        shared_gui_refs['status_var_pressboi']
    )
    
    # --- Motor 0 ---
    m0_frame = ttk.Frame(content_frame, style='Card.TFrame')
    m0_frame.pack(fill=tk.X, expand=True, pady=(5, 2))
    
    m0_label = ttk.Label(m0_frame, text="M0 Pos:", style='Subtle.TLabel')
    m0_label.pack(side=tk.LEFT)
    
    m0_pos_label = ttk.Label(m0_frame, textvariable=shared_gui_refs['pressboi_pos_m0_var'], style='Subtle.TLabel', width=8)
    m0_pos_label.pack(side=tk.LEFT, padx=5)

    m0_homed_label = ttk.Label(m0_frame, text="Not Homed", style='Subtle.TLabel', foreground=theme.ERROR_RED)
    m0_homed_label.pack(side=tk.RIGHT)
    m0_homed_label.tracer = make_homed_tracer(shared_gui_refs['pressboi_homed_m0_var'], m0_homed_label)
    shared_gui_refs['pressboi_homed_m0_var'].trace_add('write', m0_homed_label.tracer)
    m0_homed_label.tracer()

    m0_enabled_label = ttk.Label(m0_frame, text="Disabled", foreground=theme.ERROR_RED, style='Subtle.TLabel')
    m0_enabled_label.pack(side=tk.RIGHT, padx=10)
    m0_enabled_label.tracer = make_state_tracer(shared_gui_refs['pressboi_enabled_m0_var'], m0_enabled_label)
    shared_gui_refs['pressboi_enabled_m0_var'].trace_add('write', m0_enabled_label.tracer)
    m0_enabled_label.tracer()

    create_torque_widget(m0_frame, shared_gui_refs['pressboi_torque_m0_var'], 20).pack(side=tk.RIGHT)

    # --- Motor 1 ---
    m1_frame = ttk.Frame(content_frame, style='Card.TFrame')
    m1_frame.pack(fill=tk.X, expand=True, pady=(5, 2))
    
    m1_label = ttk.Label(m1_frame, text="M1 Pos:", style='Subtle.TLabel')
    m1_label.pack(side=tk.LEFT)
    
    m1_pos_label = ttk.Label(m1_frame, textvariable=shared_gui_refs['pressboi_pos_m1_var'], style='Subtle.TLabel', width=8)
    m1_pos_label.pack(side=tk.LEFT, padx=5)

    m1_homed_label = ttk.Label(m1_frame, text="Not Homed", style='Subtle.TLabel', foreground=theme.ERROR_RED)
    m1_homed_label.pack(side=tk.RIGHT)
    m1_homed_label.tracer = make_homed_tracer(shared_gui_refs['pressboi_homed_m1_var'], m1_homed_label)
    shared_gui_refs['pressboi_homed_m1_var'].trace_add('write', m1_homed_label.tracer)
    m1_homed_label.tracer()

    m1_enabled_label = ttk.Label(m1_frame, text="Disabled", foreground=theme.ERROR_RED, style='Subtle.TLabel')
    m1_enabled_label.pack(side=tk.RIGHT, padx=10)
    m1_enabled_label.tracer = make_state_tracer(shared_gui_refs['pressboi_enabled_m1_var'], m1_enabled_label)
    shared_gui_refs['pressboi_enabled_m1_var'].trace_add('write', m1_enabled_label.tracer)
    m1_enabled_label.tracer()
    
    create_torque_widget(m1_frame, shared_gui_refs['pressboi_torque_m1_var'], 20).pack(side=tk.RIGHT)

    return outer_container
