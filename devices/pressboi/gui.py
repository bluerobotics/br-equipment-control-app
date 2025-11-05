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

import theme

# --- GUI Helper Functions ---

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
            val_raw = double_var.get()
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
        if "STANDBY" in state or "IDLE" in state: 
            color = theme.SUCCESS_GREEN
        elif "BUSY" in state or "ACTIVE" in state or "HOMING" in state or "MOVING" in state or "PRESSING" in state: 
            color = theme.BUSY_BLUE
        elif "ERROR" in state: 
            color = theme.ERROR_RED
        elif "DISABLED" in state: 
            color = theme.ERROR_RED
        elif "ENABLED" in state: 
            color = theme.SUCCESS_GREEN
        label_to_color.config(foreground=color)
    return tracer

def make_force_tracer(var, label_to_color):
    """Changes color based on force magnitude (in kg)."""
    def tracer(*args):
        try:
            value_str = var.get().split()[0]
            force = float(value_str)
            if force < 100:
                color = theme.FG_COLOR
            elif force < 500:
                color = theme.SUCCESS_GREEN
            elif force < 800:
                color = theme.WARNING_YELLOW
            else:
                color = theme.ERROR_RED
            label_to_color.config(foreground=color)
        except (ValueError, IndexError):
            label_to_color.config(foreground=theme.FG_COLOR)
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
    torque_frame = ttk.Frame(parent, height=height, width=40, style='TFrame')
    torque_frame.pack_propagate(False)
    torque_sv = tk.StringVar()
    torque_frame.tracer = make_torque_tracer(torque_dv, torque_sv)
    torque_dv.trace_add('write', torque_frame.tracer)
    pbar = ttk.Progressbar(torque_frame, variable=torque_dv, maximum=100, orient=tk.VERTICAL, style='Card.Vertical.TProgressbar')
    pbar.pack(fill=tk.BOTH, expand=True)
    label = ttk.Label(torque_frame, textvariable=torque_sv, font=("JetBrains Mono", 8, "bold"), anchor='center', style='Subtle.TLabel')
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
    title_label = ttk.Label(header_frame, text=title.lower(), font=("JetBrains Mono", 14, "bold"), foreground=theme.DEVICE_COLOR, style='Subtle.TLabel')
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
        'pressboi_force_var', 'pressboi_force_limit_var',
        'pressboi_current_pos_var', 'pressboi_retract_pos_var',
        'pressboi_target_pos_var', 'pressboi_homed_var',
        'pressboi_enabled0_var', 'pressboi_enabled1_var',
        'pressboi_torque_m1_var', 'pressboi_torque_m2_var',
        'pressboi_torque_avg_var', 'pressboi_enabled_combined_var'
    ]

# --- Main GUI Creation Function ---

def create_gui_components(parent, shared_gui_refs):
    """Creates the PressBoi status panel with improved layout."""
    
    # Initialize all required tkinter variables
    for var_name in get_required_variables():
        if var_name.endswith('_var'):
            if 'torque' in var_name:
                shared_gui_refs.setdefault(var_name, tk.DoubleVar(value=0.0))
            else:
                shared_gui_refs.setdefault(var_name, tk.StringVar(value='---'))
    
    # Setup tracer to average the two motor torques
    def update_torque_average(*args):
        try:
            t1 = shared_gui_refs['pressboi_torque_m1_var'].get()
            t2 = shared_gui_refs['pressboi_torque_m2_var'].get()
            avg = (t1 + t2) / 2.0
            shared_gui_refs['pressboi_torque_avg_var'].set(avg)
        except:
            shared_gui_refs['pressboi_torque_avg_var'].set(0.0)
    
    shared_gui_refs['pressboi_torque_m1_var'].trace_add('write', update_torque_average)
    shared_gui_refs['pressboi_torque_m2_var'].trace_add('write', update_torque_average)
    
    # Setup tracer to combine enabled states
    def update_enabled_combined(*args):
        try:
            e0 = shared_gui_refs['pressboi_enabled0_var'].get()
            e1 = shared_gui_refs['pressboi_enabled1_var'].get()
            # Both should be enabled for combined to show enabled
            if e0 == "Enabled" and e1 == "Enabled":
                shared_gui_refs['pressboi_enabled_combined_var'].set("Enabled")
            else:
                shared_gui_refs['pressboi_enabled_combined_var'].set("Disabled")
        except:
            shared_gui_refs['pressboi_enabled_combined_var'].set("---")
    
    shared_gui_refs['pressboi_enabled0_var'].trace_add('write', update_enabled_combined)
    shared_gui_refs['pressboi_enabled1_var'].trace_add('write', update_enabled_combined)

    font_large = ("JetBrains Mono", 16, "bold")
    font_medium = ("JetBrains Mono", 12, "bold")
    font_small = ("JetBrains Mono", 10)

    outer_container, content_frame = create_device_frame(
        parent, 
        "PressBoi",
        shared_gui_refs['pressboi_main_state_var'],
        shared_gui_refs['status_var_pressboi']
    )
    
    # === Single Container for ALL data ===
    data_container = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
    data_container.pack(fill='both', expand=True, pady=(10, 5))
    
    # Torque bar on right side - height will match content
    torque_widget = create_torque_widget(data_container, shared_gui_refs['pressboi_torque_avg_var'], 120)
    torque_widget.pack(side=tk.RIGHT, padx=(20, 0))
    
    # Left side - all text data (no extra frame needed)
    left_side = ttk.Frame(data_container, style='Card.TFrame')
    left_side.pack(side=tk.LEFT, fill='both', expand=True)
    
    # Force row at top
    force_row = ttk.Frame(left_side, style='Card.TFrame')
    force_row.pack(fill='x', pady=(0, 10))
    
    ttk.Label(force_row, text="Force:", font=font_medium, style='Subtle.TLabel').pack(side=tk.LEFT, padx=(0, 10))
    force_value_label = ttk.Label(force_row, textvariable=shared_gui_refs['pressboi_force_var'], 
                                   font=font_large, foreground=theme.PRIMARY_ACCENT, style='Subtle.TLabel', anchor='e')
    force_value_label.pack(side=tk.LEFT)
    
    ttk.Label(force_row, text=" / ", font=font_medium, foreground=theme.COMMENT_COLOR, style='Subtle.TLabel').pack(side=tk.LEFT)
    ttk.Label(force_row, textvariable=shared_gui_refs['pressboi_force_limit_var'], 
              font=font_medium, foreground=theme.COMMENT_COLOR, style='Subtle.TLabel', anchor='e').pack(side=tk.LEFT)
    
    # Add force color tracer
    force_tracer = make_force_tracer(shared_gui_refs['pressboi_force_var'], force_value_label)
    shared_gui_refs['pressboi_force_var'].trace_add('write', force_tracer)
    force_tracer()
    
    # Position info below force
    pos_grid = ttk.Frame(left_side, style='Card.TFrame')
    pos_grid.pack(fill='x')
    pos_grid.grid_columnconfigure(1, weight=1)
    
    # Current and Target Position (inline, same size as force)
    pos_row = ttk.Frame(pos_grid, style='Card.TFrame')
    pos_row.grid(row=0, column=0, columnspan=4, sticky='w', pady=2)
    
    pos_label = ttk.Label(pos_row, text="Position:", font=font_medium, style='Subtle.TLabel')
    pos_label.pack(side=tk.LEFT, padx=(0, 10))
    
    # Create display variables that strip " mm" from positions
    current_pos_display = tk.StringVar(value='0.00')
    current_stripper = make_unit_stripper(shared_gui_refs['pressboi_current_pos_var'], current_pos_display, ' mm')
    shared_gui_refs['pressboi_current_pos_var'].trace_add('write', current_stripper)
    current_stripper()
    
    current_pos_label = ttk.Label(pos_row, textvariable=current_pos_display, 
                                   font=font_large, foreground=theme.SUCCESS_GREEN, style='Subtle.TLabel', anchor='e')
    current_pos_label.pack(side=tk.LEFT)
    
    arrow_label = ttk.Label(pos_row, text=" → ", font=font_medium, foreground=theme.COMMENT_COLOR, style='Subtle.TLabel')
    arrow_label.pack(side=tk.LEFT)
    
    target_pos_display = tk.StringVar(value='0.00')
    target_stripper = make_unit_stripper(shared_gui_refs['pressboi_target_pos_var'], target_pos_display, ' mm')
    shared_gui_refs['pressboi_target_pos_var'].trace_add('write', target_stripper)
    target_stripper()
    
    target_pos_label = ttk.Label(pos_row, textvariable=target_pos_display, 
                                  font=font_large, foreground=theme.WARNING_YELLOW, style='Subtle.TLabel', anchor='e')
    target_pos_label.pack(side=tk.LEFT)
    
    # Tracer to turn position red when not homed
    def position_homed_tracer(*args):
        homed_state = shared_gui_refs['pressboi_homed_var'].get()
        if homed_state == 'Homed':
            pos_label.config(foreground=theme.FG_COLOR)
            current_pos_label.config(foreground=theme.SUCCESS_GREEN)
            target_pos_label.config(foreground=theme.WARNING_YELLOW)
        else:
            pos_label.config(foreground=theme.ERROR_RED)
            current_pos_label.config(foreground=theme.ERROR_RED)
            target_pos_label.config(foreground=theme.ERROR_RED)
    
    shared_gui_refs['pressboi_homed_var'].trace_add('write', position_homed_tracer)
    position_homed_tracer()
    
    # Retract Position
    retract_row = ttk.Frame(pos_grid, style='Card.TFrame')
    retract_row.grid(row=1, column=0, columnspan=4, sticky='w', pady=(10, 2))
    
    ttk.Label(retract_row, text="Retract Position:", font=font_small, style='Subtle.TLabel').pack(side=tk.LEFT, padx=(0, 10))
    
    # Create display variable that strips " mm" from retract position
    retract_pos_display = tk.StringVar(value='0.00')
    retract_stripper = make_unit_stripper(shared_gui_refs['pressboi_retract_pos_var'], retract_pos_display, ' mm')
    shared_gui_refs['pressboi_retract_pos_var'].trace_add('write', retract_stripper)
    retract_stripper()
    
    ttk.Label(retract_row, textvariable=retract_pos_display, 
              font=font_small, style='Subtle.TLabel', anchor='e').pack(side=tk.LEFT)
    
    # Homed and Enabled Status (inline, no "Homed:" label)
    status_row = ttk.Frame(pos_grid, style='Card.TFrame')
    status_row.grid(row=2, column=0, columnspan=4, sticky='w', pady=(5, 2))
    
    homed_value_label = ttk.Label(status_row, textvariable=shared_gui_refs['pressboi_homed_var'], 
                                   font=font_small, style='Subtle.TLabel')
    homed_value_label.pack(side=tk.LEFT, padx=(0, 20))
    homed_tracer = make_homed_tracer(shared_gui_refs['pressboi_homed_var'], homed_value_label)
    shared_gui_refs['pressboi_homed_var'].trace_add('write', homed_tracer)
    homed_tracer()
    
    ttk.Label(status_row, text="Motors:", font=font_small, style='Subtle.TLabel').pack(side=tk.LEFT, padx=(0, 5))
    enabled_value_label = ttk.Label(status_row, textvariable=shared_gui_refs['pressboi_enabled_combined_var'], 
                                     font=font_small, style='Subtle.TLabel')
    enabled_value_label.pack(side=tk.LEFT)
    enabled_tracer = make_state_tracer(shared_gui_refs['pressboi_enabled_combined_var'], enabled_value_label)
    shared_gui_refs['pressboi_enabled_combined_var'].trace_add('write', enabled_tracer)
    enabled_tracer()
    
    # === Force vs Position Graph ===
    graph_container = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
    graph_container.pack(fill='both', expand=True, pady=(10, 0))
    
    # Graph title
    ttk.Label(graph_container, text="Force vs Position", 
              font=font_medium, foreground=theme.PRIMARY_ACCENT, 
              style='Subtle.TLabel').pack(anchor='w', pady=(0, 5))
    
    # Create canvas for graph
    graph_canvas = tk.Canvas(graph_container, 
                            width=400, height=200,
                            bg=theme.WIDGET_BG,
                            highlightthickness=1,
                            highlightbackground=theme.COMMENT_COLOR)
    graph_canvas.pack(fill='both', expand=True)
    
    # Store graph data (position, force) tuples
    graph_data = []
    max_points = 500  # Keep last 500 points
    
    def update_graph(*args):
        """Updates the force vs position graph when position or force changes."""
        try:
            # Get current values
            pos_str = shared_gui_refs['pressboi_current_pos_var'].get()
            force_str = shared_gui_refs['pressboi_force_var'].get()
            
            # Parse values
            pos = float(pos_str.split()[0]) if pos_str != '---' else None
            force = float(force_str.split()[0]) if force_str != '---' else None
            
            if pos is not None and force is not None:
                # Add new data point
                graph_data.append((pos, force))
                
                # Keep only last N points
                if len(graph_data) > max_points:
                    graph_data.pop(0)
                
                # Redraw graph
                draw_graph()
        except (ValueError, IndexError, AttributeError):
            pass  # Invalid data, skip update
    
    def draw_graph():
        """Draws the force vs position graph on the canvas."""
        graph_canvas.delete("all")
        
        if len(graph_data) < 2:
            # Not enough data to draw
            graph_canvas.create_text(200, 100, 
                                    text="Waiting for data...",
                                    fill=theme.COMMENT_COLOR,
                                    font=font_small)
            return
        
        # Get canvas dimensions
        width = graph_canvas.winfo_width()
        height = graph_canvas.winfo_height()
        
        # Use actual dimensions if available, otherwise use requested
        if width <= 1:
            width = 400
        if height <= 1:
            height = 200
        
        # Margins
        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 40
        
        plot_width = width - margin_left - margin_right
        plot_height = height - margin_top - margin_bottom
        
        # Find data ranges
        positions = [p for p, f in graph_data]
        forces = [f for p, f in graph_data]
        
        min_pos = min(positions)
        max_pos = max(positions)
        min_force = min(forces)
        max_force = max(forces)
        
        # Add some padding to ranges
        pos_range = max_pos - min_pos if max_pos != min_pos else 1
        force_range = max_force - min_force if max_force != min_force else 1
        
        min_pos -= pos_range * 0.1
        max_pos += pos_range * 0.1
        min_force -= force_range * 0.1
        max_force += force_range * 0.1
        
        # Draw axes
        # Y-axis
        graph_canvas.create_line(margin_left, margin_top,
                                margin_left, height - margin_bottom,
                                fill=theme.COMMENT_COLOR, width=2)
        # X-axis
        graph_canvas.create_line(margin_left, height - margin_bottom,
                                width - margin_right, height - margin_bottom,
                                fill=theme.COMMENT_COLOR, width=2)
        
        # Draw axis labels
        graph_canvas.create_text(width // 2, height - 10,
                                text="Position (mm)",
                                fill=theme.FG_COLOR,
                                font=("Menlo", 8))
        graph_canvas.create_text(15, height // 2,
                                text="Force (kg)",
                                fill=theme.FG_COLOR,
                                font=("Menlo", 8),
                                angle=90)
        
        # Draw scale labels
        # Y-axis ticks
        for i in range(5):
            y = margin_top + (plot_height * i / 4)
            force_val = max_force - (force_range * i / 4)
            graph_canvas.create_text(margin_left - 5, y,
                                    text=f"{force_val:.0f}",
                                    fill=theme.COMMENT_COLOR,
                                    font=("Menlo", 7),
                                    anchor='e')
        
        # X-axis ticks
        for i in range(5):
            x = margin_left + (plot_width * i / 4)
            pos_val = min_pos + (pos_range * i / 4)
            graph_canvas.create_text(x, height - margin_bottom + 5,
                                    text=f"{pos_val:.0f}",
                                    fill=theme.COMMENT_COLOR,
                                    font=("Menlo", 7),
                                    anchor='n')
        
        # Plot the data points as a line
        points = []
        for pos, force in graph_data:
            # Scale to canvas coordinates
            x = margin_left + ((pos - min_pos) / pos_range) * plot_width
            y = height - margin_bottom - ((force - min_force) / force_range) * plot_height
            points.append((x, y))
        
        # Draw lines connecting points
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            graph_canvas.create_line(x1, y1, x2, y2,
                                    fill=theme.PRIMARY_ACCENT,
                                    width=2)
        
        # Draw points
        for x, y in points:
            graph_canvas.create_oval(x-2, y-2, x+2, y+2,
                                    fill=theme.SUCCESS_GREEN,
                                    outline=theme.SUCCESS_GREEN)
    
    # Add button to clear graph data
    button_frame = ttk.Frame(graph_container, style='Card.TFrame')
    button_frame.pack(fill='x', pady=(5, 0))
    
    def clear_graph():
        graph_data.clear()
        draw_graph()
    
    ttk.Button(button_frame, text="Clear Graph", 
              command=clear_graph).pack(side=tk.RIGHT)
    
    # Attach tracers to update graph when position or force changes
    shared_gui_refs['pressboi_current_pos_var'].trace_add('write', update_graph)
    shared_gui_refs['pressboi_force_var'].trace_add('write', update_graph)
    
    # Initial draw
    graph_canvas.bind('<Configure>', lambda e: draw_graph())
    
    return outer_container
