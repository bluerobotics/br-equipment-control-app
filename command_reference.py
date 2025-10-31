import tkinter as tk
from tkinter import ttk
import re
import theme
from script_processor import SCRIPT_COMMANDS
from comms import devices_lock

class Tooltip:
    """
    Creates a tooltip for a given widget.
    """
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None
        self.id = None
        self.text = ""
        self.delay = 200  # ms
        self.wraplength = 400 # pixels

    def showtip(self, text):
        """Display text in tooltip window"""
        self.text = text
        if self.tip_window or not self.text:
            return

        if self.id:
            self.widget.after_cancel(self.id)
        
        self.id = self.widget.after(self.delay, self._show)
    
    def showtip_at_position(self, text, x, y):
        """Display text in tooltip window at specific position"""
        self.text = text
        if self.tip_window or not self.text:
            return

        if self.id:
            self.widget.after_cancel(self.id)
        
        # Store the position for the _show method
        self.tip_x = x
        self.tip_y = y
        self.id = self.widget.after(self.delay, self._show)

    def _show(self):
        """Display text in a tooltip window."""
        if self.tip_window or not self.text:
            return
            
        # Use stored position if available, otherwise use cursor position
        if hasattr(self, 'tip_x') and hasattr(self, 'tip_y'):
            x, y = self.tip_x, self.tip_y
        else:
            # Get the position of the cursor
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            tw, 
            text=self.text, 
            justify=tk.LEFT,
            background=theme.WIDGET_BG,
            foreground=theme.FG_COLOR,
            relief=tk.SOLID, 
            borderwidth=1,
            wraplength=self.wraplength,
            font=theme.FONT_NORMAL
        )
        label.pack(ipadx=5, ipady=3)

    def hidetip(self):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = None
        
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class CommandReference(ttk.Frame):
    def __init__(self, parent, script_editor_widget, device_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.script_editor_widget = script_editor_widget
        self.device_manager = device_manager
        self.command_lines = {}  # Map line numbers to command names
        self.variable_lines = {}  # Map line numbers to variable names
        self.event_lines = {}  # Map line numbers to event names
        self.device_lines = {}  # Map line numbers to device names
        
        self.configure(style='TFrame', padding=10)

        # --- Title Section ---
        title_frame = ttk.Frame(self, style='TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 8))
        
        title_label = ttk.Label(title_frame, 
                               text="Reference", 
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.PRIMARY_ACCENT,
                               style='TLabel')
        title_label.pack(side=tk.LEFT)
        
        help_label = ttk.Label(title_frame, 
                              text="double-click to add  |  right-click for options",
                              font=theme.FONT_NORMAL, 
                              foreground=theme.COMMENT_COLOR,
                              style='TLabel')
        help_label.pack(side=tk.RIGHT, anchor='e')

        # --- Notebook (Tabs) ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Commands Tab
        commands_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(commands_frame, text='Commands')
        
        self.commands_text = self._create_text_widget(commands_frame, 'commands')
        
        # Add command button
        commands_btn_frame = ttk.Frame(commands_frame, style='TFrame')
        commands_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        add_command_btn = tk.Button(commands_btn_frame,
                                    text="+ Add Command...",
                                    command=self.show_add_command_dialog,
                                    bg=theme.SUCCESS_GREEN,
                                    fg=theme.BG_COLOR,
                                    font=theme.FONT_BOLD,
                                    relief=tk.FLAT,
                                    padx=10,
                                    pady=5,
                                    cursor='hand2')
        add_command_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Variables Tab
        variables_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(variables_frame, text='Variables')
        
        self.variables_text = self._create_text_widget(variables_frame, 'variables')
        
        # Add variable button
        variables_btn_frame = ttk.Frame(variables_frame, style='TFrame')
        variables_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        add_variable_btn = tk.Button(variables_btn_frame,
                                     text="+ Add Variable...",
                                     command=self.show_add_variable_dialog,
                                     bg=theme.SUCCESS_GREEN,
                                     fg=theme.BG_COLOR,
                                     font=theme.FONT_BOLD,
                                     relief=tk.FLAT,
                                     padx=10,
                                     pady=5,
                                     cursor='hand2')
        add_variable_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Events Tab
        events_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(events_frame, text='Events')
        
        self.events_text = self._create_text_widget(events_frame, 'events')
        
        # Add event button
        events_btn_frame = ttk.Frame(events_frame, style='TFrame')
        events_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        add_event_btn = tk.Button(events_btn_frame,
                                  text="+ Add Event...",
                                  command=self.show_add_event_dialog,
                                  bg=theme.SUCCESS_GREEN,
                                  fg=theme.BG_COLOR,
                                  font=theme.FONT_BOLD,
                                  relief=tk.FLAT,
                                  padx=10,
                                  pady=5,
                                  cursor='hand2')
        add_event_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Devices Tab
        devices_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(devices_frame, text='Devices')
        
        self.devices_text = self._create_text_widget(devices_frame, 'devices')
        
        # Add device button
        devices_btn_frame = ttk.Frame(devices_frame, style='TFrame')
        devices_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        add_device_btn = tk.Button(devices_btn_frame,
                                   text="+ Add Device...",
                                   command=self.show_add_device_dialog,
                                   bg=theme.SUCCESS_GREEN,
                                   fg=theme.BG_COLOR,
                                   font=theme.FONT_BOLD,
                                   relief=tk.FLAT,
                                   padx=10,
                                   pady=5,
                                   cursor='hand2')
        add_device_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Set the active text widget reference
        self.text = self.commands_text
        
        # Track current tab
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self.refresh() # Initial population

        # Context menu for commands (dynamically built based on command type)
        self.commands_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        
        self.variables_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        self.variables_context_menu.add_command(label="Copy Variable", command=self.copy_variable)
        self.variables_context_menu.add_command(label="Add to Script", command=self.add_variable_to_script)
        self.variables_context_menu.add_separator()
        self.variables_context_menu.add_command(label="Edit Variable...", command=self.edit_variable)
        self.variables_context_menu.add_command(label="More Info...", command=self.show_variable_info)
        self.variables_context_menu.add_separator()
        self.variables_context_menu.add_command(label="Delete Variable", command=self.delete_variable,
                                               foreground=theme.ERROR_RED)
        
        self.events_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        self.events_context_menu.add_command(label="Copy Event", command=self.copy_event)
        self.events_context_menu.add_command(label="Add to Script", command=self.add_event_to_script)
        self.events_context_menu.add_separator()
        self.events_context_menu.add_command(label="Edit Event...", command=self.edit_event)
        self.events_context_menu.add_command(label="More Info...", command=self.show_event_info)
        self.events_context_menu.add_separator()
        self.events_context_menu.add_command(label="Delete Event", command=self.delete_event,
                                            foreground=theme.ERROR_RED)
        
        self.devices_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        self.devices_context_menu.add_command(label="Edit Device...", command=self.edit_device)
        self.devices_context_menu.add_command(label="More Info...", command=self.show_device_info)
        self.devices_context_menu.add_separator()
        self.devices_context_menu.add_command(label="Delete Device", command=self.delete_device,
                                             foreground=theme.ERROR_RED)

        self.commands_text.bind("<Button-3>", self.show_commands_context_menu)
        self.commands_text.bind("<Double-1>", lambda e: self.add_to_script())
        
        self.variables_text.bind("<Button-3>", self.show_variables_context_menu)
        self.variables_text.bind("<Double-1>", lambda e: self.add_variable_to_script())
        
        self.events_text.bind("<Button-3>", self.show_events_context_menu)
        self.events_text.bind("<Double-1>", lambda e: self.add_event_to_script())
        
        self.devices_text.bind("<Button-3>", self.show_devices_context_menu)

        # Initialize tooltips
        self.commands_tooltip = Tooltip(self.commands_text)
        self.variables_tooltip = Tooltip(self.variables_text)
        self.events_tooltip = Tooltip(self.events_text)
        self.devices_tooltip = Tooltip(self.devices_text)
    
    def _create_text_widget(self, parent, widget_type):
        """Create and configure a text widget for commands, variables, or events."""
        text_frame = ttk.Frame(parent, style='TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        text = tk.Text(text_frame,
            bg=theme.WIDGET_BG, 
            fg=theme.FG_COLOR,
            font=theme.FONT_NORMAL,
            selectbackground=theme.SELECTION_BG,
            selectforeground=theme.SELECTION_FG,
            borderwidth=0,
            highlightthickness=0,
            cursor="arrow",
            wrap=tk.NONE,
            spacing1=2,
            spacing3=2)
        
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=vsb.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for syntax highlighting
        text.tag_configure('device', foreground=theme.DEVICE_COLOR, font=theme.FONT_BOLD)  # Purple headers
        text.tag_configure('device_part', foreground=theme.DEVICE_COLOR)  # Purple device prefix (before dot)
        
        if widget_type == 'commands':
            # Commands: device.command = purple.blue, script commands = teal
            text.tag_configure('command', foreground=theme.COMMAND_COLOR)  # Blue for command names
            text.tag_configure('script_command', foreground=theme.SCRIPT_COMMAND_COLOR)  # Teal for script commands
            text.tag_configure('params', foreground=theme.PARAMETER_COLOR)  # Orange for parameters
        elif widget_type == 'variables':
            # Variables: device.variable = purple.burgundy
            text.tag_configure('variable', foreground='#C04848')  # Burgundy for variable names
            text.tag_configure('params', foreground='#E67373')  # Lighter burgundy/red for type/unit info
            text.tag_configure('enum_badge', foreground=theme.WARNING_YELLOW, font=theme.FONT_BOLD)  # Yellow badge for enums
        elif widget_type == 'events':
            # Events: device.event = purple.green (using SUCCESS_GREEN for events)
            text.tag_configure('event', foreground=theme.SUCCESS_GREEN)  # Green for event names
            text.tag_configure('params', foreground=theme.PARAMETER_COLOR)  # Orange for parameters
        elif widget_type == 'devices':
            # Devices: just device name in blue
            text.tag_configure('device_name', foreground=theme.COMMAND_COLOR, font=theme.FONT_BOLD)  # Blue for device names
            text.tag_configure('device_info', foreground=theme.COMMENT_COLOR)  # Gray for info
        
        text.tag_configure('unit', foreground=theme.COMMENT_COLOR)
        text.tag_configure('desc', foreground=theme.COMMENT_COLOR)
        text.tag_configure('disconnected', foreground=theme.COMMENT_COLOR)
        text.tag_configure('hover', background=theme.SECONDARY_ACCENT)
        
        # Track current hover line per widget
        text.current_hover_line = None
        
        # Make text read-only
        text.bind("<Key>", lambda e: "break")

        # Hover highlighting
        text.bind("<Motion>", lambda e: self._on_mouse_motion(e, text, widget_type))
        text.bind("<Leave>", lambda e: self._on_mouse_leave(e, text))
        
        return text
    
    def _on_tab_changed(self, event):
        """Update the active text widget when tab changes."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.text = self.commands_text
        elif current_tab == 1:
            self.text = self.variables_text
        elif current_tab == 2:
            self.text = self.events_text
        else:
            self.text = self.devices_text

    def _extract_param_and_unit(self, param_name):
        """Extract parameter name and unit from 'param(unit)' format."""
        try:
            if '(' in param_name and ')' in param_name:
                start = param_name.index('(')
                end = param_name.index(')', start + 1)
                name = param_name[:start]
                unit = param_name[start+1:end]
                return name, unit
            return param_name, ""
        except ValueError:
            return param_name, ""
    
    def refresh(self):
        """Clears and repopulates all text widgets with commands, variables, events, and devices."""
        self.refresh_commands()
        self.refresh_variables()
        self.refresh_events()
        self.refresh_devices()
    
    def refresh_commands(self):
        """Clears and repopulates the commands text widget."""
        self.scripting_commands = self.device_manager.get_all_scripting_commands()
        self.command_lines = {}
        
        # Clear text
        self.commands_text.config(state=tk.NORMAL)
        self.commands_text.delete('1.0', tk.END)
        
        line_num = 1
        
        # Group commands by device
        device_commands = {}
        for cmd, details in self.scripting_commands.items():
            device = details['device']
            if device not in device_commands:
                device_commands[device] = []
            device_commands[device].append((cmd, details))
        
        # Add script commands
        from script_processor import SCRIPT_COMMANDS
        if 'script' not in device_commands:
            device_commands['script'] = []
        for cmd, details in SCRIPT_COMMANDS.items():
            device_commands['script'].append((cmd, details))
        
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            
            for device_name in sorted(device_commands.keys()):
                is_connected = device_states.get(device_name, {}).get('connected', False)
                
                # Device header (bold purple or gray if disconnected)
                device_start = f"{line_num}.0"
                self.commands_text.insert(tk.END, f"{device_name.lower()}\n")
                device_end = f"{line_num}.end"
                
                if is_connected:
                    self.commands_text.tag_add('device', device_start, device_end)
                else:
                    self.commands_text.tag_add('disconnected', device_start, device_end)
                
                line_num += 1
                
                # Commands under this device
                for cmd, details in sorted(device_commands[device_name]):
                    cmd_start_line = line_num
                    
                    # Store command for this line
                    self.command_lines[line_num] = cmd
                    
                    # Check if this is a script command (device == 'script')
                    is_script_cmd = details.get('device') == 'script'
                    command_tag = 'script_command' if is_script_cmd else 'command'
                    
                    # Parse command for multi-color: device.command
                    if '.' in cmd:
                        device_part, cmd_part = cmd.split('.', 1)
                        
                        # Insert with proper spacing
                        line_start = f"{line_num}.0"
                        self.commands_text.insert(tk.END, f"  {device_part}")
                        device_part_end = f"{line_num}.{2 + len(device_part)}"
                        self.commands_text.tag_add('device_part', f"{line_num}.2", device_part_end)
                        
                        self.commands_text.insert(tk.END, ".")
                        dot_pos = f"{line_num}.{2 + len(device_part)}"
                        self.commands_text.tag_add('device_part', dot_pos, f"{line_num}.{3 + len(device_part)}")
                        
                        cmd_start_pos = f"{line_num}.{3 + len(device_part)}"
                        self.commands_text.insert(tk.END, cmd_part)
                        cmd_end_pos = f"{line_num}.{3 + len(device_part) + len(cmd_part)}"
                        self.commands_text.tag_add(command_tag, cmd_start_pos, cmd_end_pos)
                    else:
                        # Script commands without dot notation
                        self.commands_text.insert(tk.END, f"  {cmd}")
                        self.commands_text.tag_add(command_tag, f"{line_num}.2", f"{line_num}.{2 + len(cmd)}")
                    
                    # Add params with separate colors for parameter names and units
                    if details.get('params'):
                        for param in details['params']:
                            # Handle both old and new parameter structures
                            param_name = param.get('name') or param.get('parameter', '')
                            param_unit = param.get('unit', '')
                            
                            if param_name:
                                # Add space before parameter
                                self.commands_text.insert(tk.END, " ")
                                
                                # Add parameter name in orange
                                param_start_col = int(self.commands_text.index(f'{line_num}.end').split('.')[1])
                                self.commands_text.insert(tk.END, param_name)
                                param_end_col = int(self.commands_text.index(f'{line_num}.end').split('.')[1])
                                self.commands_text.tag_add('params', f"{line_num}.{param_start_col}", f"{line_num}.{param_end_col}")
                                
                                # Add unit in grey if present
                                if param_unit:
                                    self.commands_text.insert(tk.END, " ")
                                    unit_start_col = int(self.commands_text.index(f'{line_num}.end').split('.')[1])
                                    self.commands_text.insert(tk.END, param_unit)
                                    unit_end_col = int(self.commands_text.index(f'{line_num}.end').split('.')[1])
                                    self.commands_text.tag_add('unit', f"{line_num}.{unit_start_col}", f"{line_num}.{unit_end_col}")
                    
                    # Store description for tooltip (don't display inline)
                    description = details.get('help') or details.get('description')
                    if description:
                        # Create a tag for this command line to store the description
                        self.commands_text.tag_add(f"cmd_{cmd}", f"{line_num}.0", f"{line_num}.end")
                        # Store the description in the tag's data
                        self.commands_text.tag_bind(f"cmd_{cmd}", "<Enter>", 
                                         lambda e, desc=description: self._show_tooltip(e, desc, self.commands_tooltip))
                        self.commands_text.tag_bind(f"cmd_{cmd}", "<Leave>", lambda e: self._hide_tooltip(self.commands_tooltip))
                    
                    self.commands_text.insert(tk.END, "\n")
                    line_num += 1
                
                # Add blank line between devices
                self.commands_text.insert(tk.END, "\n")
                line_num += 1
        
        self.commands_text.config(state=tk.DISABLED)
    
    def refresh_variables(self):
        """Clears and repopulates the variables text widget with telemetry parameters."""
        self.variable_lines = {}
        
        # Clear text
        self.variables_text.config(state=tk.NORMAL)
        self.variables_text.delete('1.0', tk.END)
        
        line_num = 1
        
        # Get all devices and their messages
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            
            for device_name in sorted(self.device_manager.get_all_device_names()):
                device_data = self.device_manager.devices.get(device_name, {})
                telemetry_data = device_data.get('telemetry_data', {})
                
                # Skip if no telemetry data
                if not telemetry_data:
                    continue
                
                is_connected = device_states.get(device_name, {}).get('connected', False)
                
                # Device header (burgundy or gray if disconnected)
                device_start = f"{line_num}.0"
                self.variables_text.insert(tk.END, f"{device_name.lower()}\n")
                device_end = f"{line_num}.end"
                
                if is_connected:
                    self.variables_text.tag_add('device', device_start, device_end)
                else:
                    self.variables_text.tag_add('disconnected', device_start, device_end)
                
                line_num += 1
                
                # Variables under this device (telemetry_data is now a flat dict)
                for param_name, param_details in sorted(telemetry_data.items()):
                    # Store variable for this line with full qualified name
                    full_var_name = f"{device_name}.{param_name}"
                    self.variable_lines[line_num] = (device_name, param_name, param_details)
                    
                    # Insert with device.variable format (similar to commands)
                    # Device part in purple
                    self.variables_text.insert(tk.END, f"  {device_name}")
                    device_part_end = f"{line_num}.{2 + len(device_name)}"
                    self.variables_text.tag_add('device_part', f"{line_num}.2", device_part_end)
                    
                    # Dot in purple
                    self.variables_text.insert(tk.END, ".")
                    dot_pos = f"{line_num}.{2 + len(device_name)}"
                    self.variables_text.tag_add('device_part', dot_pos, f"{line_num}.{3 + len(device_name)}")
                    
                    # Variable name in burgundy
                    var_start_pos = f"{line_num}.{3 + len(device_name)}"
                    self.variables_text.insert(tk.END, param_name)
                    var_end_pos = f"{line_num}.{3 + len(device_name) + len(param_name)}"
                    self.variables_text.tag_add('variable', var_start_pos, var_end_pos)
                    
                    # Add type in brackets (lighter red)
                    param_type = param_details.get('type', '')
                    param_unit = param_details.get('unit', '')
                    
                    if param_type:
                        self.variables_text.insert(tk.END, " ")
                        type_start_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        type_text = f"({param_type})"
                        self.variables_text.insert(tk.END, type_text)
                        type_end_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        self.variables_text.tag_add('params', f"{line_num}.{type_start_col}", f"{line_num}.{type_end_col}")
                    
                    # Add unit in grey after the brackets
                    if param_unit:
                        self.variables_text.insert(tk.END, " ")
                        unit_start_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        self.variables_text.insert(tk.END, param_unit)
                        unit_end_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        self.variables_text.tag_add('unit', f"{line_num}.{unit_start_col}", f"{line_num}.{unit_end_col}")
                    
                    # Add [enum] badge if variable has a map
                    param_map = param_details.get('map', {})
                    if param_map:
                        self.variables_text.insert(tk.END, " ")
                        enum_start_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        self.variables_text.insert(tk.END, "[enum]")
                        enum_end_col = int(self.variables_text.index(f'{line_num}.end').split('.')[1])
                        self.variables_text.tag_add('enum_badge', f"{line_num}.{enum_start_col}", f"{line_num}.{enum_end_col}")
                    
                    # Store description for tooltip
                    description = param_details.get('help', '')
                    if description:
                        var_key = f"{device_name}.{param_name}"
                        self.variables_text.tag_add(f"var_{var_key}", f"{line_num}.0", f"{line_num}.end")
                        self.variables_text.tag_bind(f"var_{var_key}", "<Enter>", 
                                         lambda e, desc=description: self._show_tooltip(e, desc, self.variables_tooltip))
                        self.variables_text.tag_bind(f"var_{var_key}", "<Leave>", lambda e: self._hide_tooltip(self.variables_tooltip))
                    
                    self.variables_text.insert(tk.END, "\n")
                    line_num += 1
                
                # Add blank line between devices
                self.variables_text.insert(tk.END, "\n")
                line_num += 1
        
        self.variables_text.config(state=tk.DISABLED)
    
    def refresh_events(self):
        """Clears and repopulates the events text widget."""
        self.event_lines = {}
        
        # Clear text
        self.events_text.config(state=tk.NORMAL)
        self.events_text.delete('1.0', tk.END)
        
        line_num = 1
        
        # Get all events from all devices
        all_events = self.device_manager.get_all_events()
        
        if not all_events:
            self.events_text.insert(tk.END, "No events defined.")
            self.events_text.config(state=tk.DISABLED)
            return
        
        # Group events by device
        device_events = {}
        for event_name, event_details in all_events.items():
            device = event_details['device']
            if device not in device_events:
                device_events[device] = []
            device_events[device].append((event_name, event_details))
        
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            
            for device_name in sorted(device_events.keys()):
                is_connected = device_states.get(device_name, {}).get('connected', False)
                
                # Device header (green or gray if disconnected)
                device_start = f"{line_num}.0"
                self.events_text.insert(tk.END, f"{device_name.lower()}\n")
                device_end = f"{line_num}.end"
                
                if is_connected:
                    self.events_text.tag_add('device', device_start, device_end)
                else:
                    self.events_text.tag_add('disconnected', device_start, device_end)
                
                line_num += 1
                
                # Events under this device
                for event_name, event_details in sorted(device_events[device_name]):
                    # Store event for this line
                    self.event_lines[line_num] = event_name
                    
                    # Parse event name for multi-color: device.event
                    if '.' in event_name:
                        device_part, event_part = event_name.split('.', 1)
                        
                        # Device part in purple
                        self.events_text.insert(tk.END, f"  {device_part}")
                        device_part_end = f"{line_num}.{2 + len(device_part)}"
                        self.events_text.tag_add('device_part', f"{line_num}.2", device_part_end)
                        
                        # Dot
                        self.events_text.insert(tk.END, ".")
                        dot_pos = f"{line_num}.{2 + len(device_part)}"
                        self.events_text.tag_add('device_part', dot_pos, f"{line_num}.{3 + len(device_part)}")
                        
                        # Event name in green
                        event_start_pos = f"{line_num}.{3 + len(device_part)}"
                        self.events_text.insert(tk.END, event_part)
                        event_end_pos = f"{line_num}.{3 + len(device_part) + len(event_part)}"
                        self.events_text.tag_add('event', event_start_pos, event_end_pos)
                    
                    # Add params with colors
                    if event_details.get('params'):
                        for param in event_details['params']:
                            param_name = param.get('parameter', '')
                            param_type = param.get('type', '')
                            
                            if param_name:
                                # Add space before parameter
                                self.events_text.insert(tk.END, " ")
                                
                                # Add parameter name in orange
                                param_start_col = int(self.events_text.index(f'{line_num}.end').split('.')[1])
                                self.events_text.insert(tk.END, param_name)
                                param_end_col = int(self.events_text.index(f'{line_num}.end').split('.')[1])
                                self.events_text.tag_add('params', f"{line_num}.{param_start_col}", f"{line_num}.{param_end_col}")
                                
                                # Add type in grey if present
                                if param_type:
                                    self.events_text.insert(tk.END, " ")
                                    type_start_col = int(self.events_text.index(f'{line_num}.end').split('.')[1])
                                    type_text = f"({param_type})"
                                    self.events_text.insert(tk.END, type_text)
                                    type_end_col = int(self.events_text.index(f'{line_num}.end').split('.')[1])
                                    self.events_text.tag_add('unit', f"{line_num}.{type_start_col}", f"{line_num}.{type_end_col}")
                    
                    # Store description for tooltip
                    description = event_details.get('description', '')
                    if description:
                        self.events_text.tag_add(f"evt_{event_name}", f"{line_num}.0", f"{line_num}.end")
                        self.events_text.tag_bind(f"evt_{event_name}", "<Enter>", 
                                         lambda e, desc=description: self._show_tooltip(e, desc, self.events_tooltip))
                        self.events_text.tag_bind(f"evt_{event_name}", "<Leave>", lambda e: self._hide_tooltip(self.events_tooltip))
                    
                    self.events_text.insert(tk.END, "\n")
                    line_num += 1
                
                # Add blank line between devices
                self.events_text.insert(tk.END, "\n")
                line_num += 1
        
        self.events_text.config(state=tk.DISABLED)
    
    def refresh_devices(self):
        """Clears and repopulates the devices text widget."""
        self.device_lines = {}
        
        # Clear text
        self.devices_text.config(state=tk.NORMAL)
        self.devices_text.delete('1.0', tk.END)
        
        line_num = 1
        
        # Get all device names
        device_names = sorted(self.device_manager.get_all_device_names())
        
        if not device_names:
            self.devices_text.insert(tk.END, "No devices defined.")
            self.devices_text.config(state=tk.DISABLED)
            return
        
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            
            for device_name in device_names:
                # Store device for this line
                self.device_lines[line_num] = device_name
                
                # Get device info
                is_connected = device_states.get(device_name, {}).get('connected', False)
                device_data = self.device_manager.devices.get(device_name, {})
                
                # Count commands, variables, events (use correct keys)
                commands_count = len(device_data.get('scripting_commands', {}))
                telemetry_count = len(device_data.get('telemetry_data', {}))
                events_count = len(device_data.get('events_data', {}))
                
                print(f"[DEBUG] Device {device_name}: {commands_count} cmds, {telemetry_count} vars, {events_count} events")
                print(f"[DEBUG] Device data keys: {list(device_data.keys())}")
                
                # Device name in blue
                device_start = f"{line_num}.0"
                self.devices_text.insert(tk.END, device_name)
                device_end = f"{line_num}.{len(device_name)}"
                self.devices_text.tag_add('device_name', device_start, device_end)
                
                # Connection status
                status_text = " [connected]" if is_connected else " [disconnected]"
                status_start = device_end
                self.devices_text.insert(tk.END, status_text)
                status_end = f"{line_num}.end"
                if is_connected:
                    self.devices_text.tag_add('device_info', status_start, status_end)
                else:
                    self.devices_text.tag_add('disconnected', status_start, status_end)
                
                self.devices_text.insert(tk.END, "\n")
                line_num += 1
                
                # Stats line
                stats_text = f"  {commands_count} commands, {telemetry_count} variables, {events_count} events"
                self.devices_text.insert(tk.END, stats_text)
                self.devices_text.tag_add('device_info', f"{line_num}.0", f"{line_num}.end")
                
                self.devices_text.insert(tk.END, "\n\n")
                line_num += 2
        
        self.devices_text.config(state=tk.DISABLED)

    def get_selected_command(self):
        """Get command at current cursor position."""
        try:
            cursor_pos = self.text.index(tk.INSERT)
            line_num = int(cursor_pos.split('.')[0])
            return self.command_lines.get(line_num)
        except:
            return None

    def copy_command(self):
        command = self.get_selected_command()
        if command: 
            self.clipboard_clear()
            self.clipboard_append(command)

    def add_to_script(self):
        command = self.get_selected_command()
        if command: 
            self.script_editor_widget.insert(tk.INSERT, f"{command} ")

    def get_selected_variable(self):
        """Get variable at current cursor position in variables tab."""
        try:
            cursor_pos = self.variables_text.index(tk.INSERT)
            line_num = int(cursor_pos.split('.')[0])
            return self.variable_lines.get(line_num)
        except:
            return None
    
    def copy_variable(self):
        """Copy full device.variable name to clipboard."""
        variable_info = self.get_selected_variable()
        if variable_info:
            device_name, param_name, param = variable_info
            full_var_name = f"{device_name}.{param_name}"
            self.clipboard_clear()
            self.clipboard_append(full_var_name)
    
    def add_variable_to_script(self):
        """Insert full device.variable name into script at cursor position."""
        variable_info = self.get_selected_variable()
        if variable_info:
            device_name, param_name, param = variable_info
            full_var_name = f"{device_name}.{param_name}"
            self.script_editor_widget.insert(tk.INSERT, f"{full_var_name} ")
    
    def show_commands_context_menu(self, event):
        # Set cursor to click position
        self.commands_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        command = self.get_selected_command()
        if command:
            # Clear the menu and rebuild it
            self.commands_context_menu.delete(0, tk.END)
            
            # Check if it's a script command (case-insensitive)
            script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE', 
                             'wait', 'math', 'wait_for', 'comment', 'cycle']
            is_script_command = command in script_commands
            print(f"[DEBUG] Context menu for command: {command}, is_script_command: {is_script_command}")
            
            # Add common options
            self.commands_context_menu.add_command(label="Copy Command", command=self.copy_command)
            self.commands_context_menu.add_command(label="Add to Script", command=self.add_to_script)
            self.commands_context_menu.add_separator()
            
            # Only add edit/delete for non-script commands
            if not is_script_command:
                self.commands_context_menu.add_command(label="Edit Command...", command=self.edit_command)
            
            self.commands_context_menu.add_command(label="More Info...", command=self.show_more_info)
            
            if not is_script_command:
                self.commands_context_menu.add_separator()
                self.commands_context_menu.add_command(label="Delete Command", command=self.delete_command, 
                                                      foreground=theme.ERROR_RED)
            
            self.commands_context_menu.post(event.x_root, event.y_root)
    
    def show_variables_context_menu(self, event):
        # Set cursor to click position
        self.variables_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        variable_info = self.get_selected_variable()
        if variable_info:
            self.variables_context_menu.post(event.x_root, event.y_root)

    def show_more_info(self):
        """Opens a detailed information window for the selected command."""
        command = self.get_selected_command()
        if not command:
            return
        
        # Get full command details
        cmd_details = self.scripting_commands.get(command)
        if not cmd_details:
            return
        
        # Create the info window
        info_window = tk.Toplevel(self)
        info_window.title(f"Command Info: {command}")
        info_window.geometry("700x600")
        info_window.configure(bg=theme.BG_COLOR)
        
        # Make it modal
        info_window.transient(self.winfo_toplevel())
        info_window.grab_set()
        
        # Header frame with title and close button
        header_frame = ttk.Frame(info_window, style='TFrame', padding=(15, 15, 15, 0))
        header_frame.pack(fill='x')
        
        # Title
        title_label = ttk.Label(header_frame, text=command, 
                               font=("JetBrains Mono", 18, "bold"),
                               foreground=theme.PRIMARY_ACCENT,
                               style='TLabel')
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Close button in top right
        close_btn_top = ttk.Button(header_frame, text="✕", width=3, 
                                   command=info_window.destroy)
        close_btn_top.pack(side=tk.RIGHT)
        
        # Main frame with padding
        main_frame = ttk.Frame(info_window, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Device badge - extract device name from command
        device_name = 'script'
        if '.' in command:
            device_name = command.split('.')[0]
        
        device_frame = ttk.Frame(main_frame, style='TFrame')
        device_frame.pack(anchor='w', pady=(5, 15))
        device_label = ttk.Label(device_frame, 
                                text=f" {device_name.upper()} ",
                                font=("JetBrains Mono", 9, "bold"),
                                background=theme.SECONDARY_ACCENT,
                                foreground=theme.FG_COLOR,
                                padding=(8, 4))
        device_label.pack(side=tk.LEFT)
        
        # Create scrollable content area
        canvas = tk.Canvas(main_frame, bg=theme.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Description section
        desc_label = ttk.Label(scrollable_frame, text="Description",
                              font=("JetBrains Mono", 12, "bold"),
                              foreground=theme.PRIMARY_ACCENT,
                              style='TLabel')
        desc_label.pack(anchor='w', pady=(0, 5))
        
        desc_text = ttk.Label(scrollable_frame, 
                             text=cmd_details.get('help') or cmd_details.get('description', 'No description available.'),
                             font=("JetBrains Mono", 10),
                             wraplength=650,
                             justify='left',
                             style='TLabel')
        desc_text.pack(anchor='w', pady=(0, 15))
        
        # Parameters section
        if cmd_details.get('params'):
            params_label = ttk.Label(scrollable_frame, text="Parameters",
                                    font=("JetBrains Mono", 12, "bold"),
                                    foreground=theme.PRIMARY_ACCENT,
                                    style='TLabel')
            params_label.pack(anchor='w', pady=(0, 5))
            
            for param in cmd_details['params']:
                param_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=10)
                param_frame.pack(fill='x', pady=(0, 8))
                
                # Parameter name (handle both old and new structures)
                param_name_text = param.get('name') or param.get('parameter', 'Unknown')
                param_name = ttk.Label(param_frame,
                                      text=f"• {param_name_text}",
                                      font=("JetBrains Mono", 10, "bold"),
                                      foreground=theme.SUCCESS_GREEN,
                                      style='TLabel')
                param_name.pack(anchor='w')
                
                # Parameter type
                param_type = param.get('type', 'str')
                type_label = ttk.Label(param_frame,
                                      text=f"  Type: {param_type}",
                                      font=("JetBrains Mono", 9),
                                      foreground=theme.COMMENT_COLOR,
                                      style='TLabel')
                type_label.pack(anchor='w', padx=(10, 0))
                
                # Show unit if present
                param_unit = param.get('unit', '')
                if param_unit:
                    unit_label = ttk.Label(param_frame,
                                          text=f"  Unit: {param_unit}",
                                          font=("JetBrains Mono", 9),
                                          foreground=theme.COMMENT_COLOR,
                                          style='TLabel')
                    unit_label.pack(anchor='w', padx=(10, 0))
                
                # Show enum/choice options for string types
                choices = param.get('enum') or param.get('options')
                if param_type in ('str', 'string') and choices:
                    enum_label = ttk.Label(param_frame,
                                          text=f"  Choices: {', '.join(choices)}",
                                          font=("JetBrains Mono", 9),
                                          foreground=theme.SUCCESS_GREEN,
                                          style='TLabel')
                    enum_label.pack(anchor='w', padx=(10, 0))
                
                # Optional flag
                if param.get('optional'):
                    optional_label = ttk.Label(param_frame,
                                              text=f"  Optional (default: {param.get('default', 'N/A')})",
                                              font=("JetBrains Mono", 9),
                                              foreground=theme.WARNING_YELLOW,
                                              style='TLabel')
                    optional_label.pack(anchor='w', padx=(10, 0))
        
        # Returns section
        if cmd_details.get('returns'):
            returns_label = ttk.Label(scrollable_frame, text="Returns",
                                     font=("JetBrains Mono", 12, "bold"),
                                     foreground=theme.PRIMARY_ACCENT,
                                     style='TLabel')
            returns_label.pack(anchor='w', pady=(15, 5))
            
            returns_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=10)
            returns_frame.pack(fill='x', pady=(0, 8))
            
            returns_text = ', '.join([f'"{ret}"' for ret in cmd_details['returns']])
            returns_info = ttk.Label(returns_frame,
                                    text=f"Possible responses: {returns_text}",
                                    font=("JetBrains Mono", 10),
                                    foreground=theme.SUCCESS_GREEN,
                                    wraplength=630,
                                    justify='left',
                                    style='TLabel')
            returns_info.pack(anchor='w')
        
        # Examples section
        examples_label = ttk.Label(scrollable_frame, text="Examples",
                                  font=("JetBrains Mono", 12, "bold"),
                                  foreground=theme.PRIMARY_ACCENT,
                                  style='TLabel')
        examples_label.pack(anchor='w', pady=(15, 5))
        
        # Generate example code
        examples = self._generate_examples(command, cmd_details)
        
        for i, example in enumerate(examples):
            example_frame = ttk.Frame(scrollable_frame, style='TFrame')
            example_frame.pack(fill='x', pady=(0, 10))
            
            # Example text widget with copy button
            example_text_frame = tk.Frame(example_frame, bg=theme.WIDGET_BG, 
                                         highlightthickness=1, 
                                         highlightbackground=theme.COMMENT_COLOR)
            example_text_frame.pack(fill='x')
            
            example_text = tk.Text(example_text_frame, 
                                  height=example.count('\n') + 1,
                                  font=("JetBrains Mono", 10),
                                  bg=theme.WIDGET_BG,
                                  fg=theme.FG_COLOR,
                                  insertbackground=theme.FG_COLOR,
                                  selectbackground=theme.PRIMARY_ACCENT,
                                  relief=tk.FLAT,
                                  padx=10,
                                  pady=10,
                                  wrap=tk.NONE)
            example_text.insert('1.0', example)
            example_text.config(state=tk.DISABLED)
            example_text.pack(side=tk.LEFT, fill='both', expand=True)
            
            # Copy button
            copy_btn = ttk.Button(example_text_frame,
                                 text="📋",
                                 width=4,
                                 command=lambda ex=example: self._copy_example(ex))
            copy_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind escape to close
        info_window.bind('<Escape>', lambda e: info_window.destroy())
        
        # Auto-size window to content and center
        info_window.update_idletasks()
        
        # Calculate required height based on content
        scrollable_frame.update_idletasks()
        content_height = scrollable_frame.winfo_reqheight()
        header_height = header_frame.winfo_reqheight()
        
        # Add padding and constraints
        total_height = min(content_height + header_height + 60, info_window.winfo_screenheight() - 100)
        window_width = 700
        
        # Center the window
        x = (info_window.winfo_screenwidth() // 2) - (window_width // 2)
        y = (info_window.winfo_screenheight() // 2) - (total_height // 2)
        info_window.geometry(f"{window_width}x{total_height}+{x}+{y}")
    
    def show_variable_info(self):
        """Opens a detailed information window for the selected variable."""
        variable_info = self.get_selected_variable()
        if not variable_info:
            return
        
        device_name, param_name, param = variable_info
        
        # Create the info window
        info_window = tk.Toplevel(self)
        info_window.title(f"Variable Info: {param_name}")
        info_window.configure(bg=theme.BG_COLOR)
        
        # Make it modal
        info_window.transient(self.winfo_toplevel())
        info_window.grab_set()
        
        # Header frame
        header_frame = ttk.Frame(info_window, style='TFrame', padding=(15, 15, 15, 0))
        header_frame.pack(fill='x')
        
        # Title in burgundy
        title_label = ttk.Label(header_frame, text=param_name, 
                               font=("JetBrains Mono", 18, "bold"),
                               foreground='#C04848',
                               style='TLabel')
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Close button
        close_btn = ttk.Button(header_frame, text="✕", width=3, 
                              command=info_window.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        # Main content
        content_frame = ttk.Frame(info_window, style='TFrame', padding=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Device badge
        device_frame = ttk.Frame(content_frame, style='TFrame')
        device_frame.pack(anchor='w', pady=(5, 15))
        device_label = ttk.Label(device_frame, 
                                text=f" {device_name.upper()} ",
                                font=("JetBrains Mono", 9, "bold"),
                                background=theme.SECONDARY_ACCENT,
                                foreground=theme.FG_COLOR,
                                padding=(8, 4))
        device_label.pack(side=tk.LEFT)
        
        # Description
        if param.get('help'):
            desc_label = ttk.Label(content_frame, text="Description",
                                  font=("JetBrains Mono", 12, "bold"),
                                  foreground='#C04848',
                                  style='TLabel')
            desc_label.pack(anchor='w', pady=(0, 5))
            
            desc_text = ttk.Label(content_frame, 
                                 text=param['help'],
                                 font=("JetBrains Mono", 10),
                                 wraplength=550,
                                 justify='left',
                                 style='TLabel')
            desc_text.pack(anchor='w', pady=(0, 15))
        
        # Properties
        props_label = ttk.Label(content_frame, text="Properties",
                               font=("JetBrains Mono", 12, "bold"),
                               foreground='#C04848',
                               style='TLabel')
        props_label.pack(anchor='w', pady=(0, 5))
        
        props_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
        props_frame.pack(fill='x', pady=(0, 8))
        
        # Type
        param_type = param.get('type', 'unknown')
        type_label = ttk.Label(props_frame,
                              text=f"Type: {param_type}",
                              font=("JetBrains Mono", 10),
                              style='TLabel')
        type_label.pack(anchor='w', pady=2)
        
        # Unit
        param_unit = param.get('unit', '')
        if param_unit:
            unit_label = ttk.Label(props_frame,
                                  text=f"Unit: {param_unit}",
                                  font=("JetBrains Mono", 10),
                                  style='TLabel')
            unit_label.pack(anchor='w', pady=2)
        
        # Default
        param_default = param.get('default', 'N/A')
        default_label = ttk.Label(props_frame,
                                 text=f"Default: {param_default}",
                                 font=("JetBrains Mono", 10),
                                 style='TLabel')
        default_label.pack(anchor='w', pady=2)
        
        # Precision
        param_precision = param.get('precision', '')
        if param_precision:
            precision_label = ttk.Label(props_frame,
                                       text=f"Precision: {param_precision} decimal places",
                                       font=("JetBrains Mono", 10),
                                       style='TLabel')
            precision_label.pack(anchor='w', pady=2)
        
        # Map (enum values)
        param_map = param.get('map', {})
        if param_map:
            map_label = ttk.Label(content_frame, text="Value Mappings",
                                 font=("JetBrains Mono", 12, "bold"),
                                 foreground='#C04848',
                                 style='TLabel')
            map_label.pack(anchor='w', pady=(15, 5))
            
            map_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
            map_frame.pack(fill='x', pady=(0, 8))
            
            for key, value in param_map.items():
                mapping_label = ttk.Label(map_frame,
                                         text=f"{key} → {value}",
                                         font=("JetBrains Mono", 10),
                                         foreground=theme.SUCCESS_GREEN,
                                         style='TLabel')
                mapping_label.pack(anchor='w', pady=2)
        
        # Bind escape to close
        info_window.bind('<Escape>', lambda e: info_window.destroy())
        
        # Calculate required size and center the window
        info_window.update_idletasks()
        
        # Get required size based on content
        req_width = info_window.winfo_reqwidth()
        req_height = info_window.winfo_reqheight()
        
        # Add padding and apply min/max limits
        window_width = max(600, req_width + 20)
        window_height = min(max(req_height + 20, 300), int(info_window.winfo_screenheight() * 0.8))
        
        # Center the window
        x = (info_window.winfo_screenwidth() // 2) - (window_width // 2)
        y = (info_window.winfo_screenheight() // 2) - (window_height // 2)
        info_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # ===== EVENT METHODS =====
    
    def get_selected_event(self):
        """Get event at current cursor position in events tab."""
        try:
            cursor_pos = self.events_text.index(tk.INSERT)
            line_num = int(cursor_pos.split('.')[0])
            return self.event_lines.get(line_num)
        except Exception:
            return None

    def copy_event(self):
        """Copy selected event to clipboard."""
        event_name = self.get_selected_event()
        if event_name:
            self.clipboard_clear()
            self.clipboard_append(event_name)

    def add_event_to_script(self):
        """Add selected event to script editor."""
        event_name = self.get_selected_event()
        if event_name and self.script_editor_widget:
            # Insert at current cursor position in script editor
            self.script_editor_widget.text.insert(tk.INSERT, f"WAIT_FOR {event_name}")
            self.script_editor_widget.text.focus_set()

    def show_events_context_menu(self, event):
        """Show context menu for events."""
        # Set cursor to click position
        self.events_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        event_name = self.get_selected_event()
        if event_name:
            self.events_context_menu.post(event.x_root, event.y_root)

    def show_event_info(self):
        """Opens a detailed information window for the selected event."""
        event_name = self.get_selected_event()
        if not event_name:
            return
        
        # Get event details
        all_events = self.device_manager.get_all_events()
        event_details = all_events.get(event_name)
        if not event_details:
            return
        
        # Create the info window
        info_window = tk.Toplevel(self)
        info_window.title(f"Event Info: {event_name}")
        info_window.configure(bg=theme.BG_COLOR)
        
        # Make it modal
        info_window.transient(self.winfo_toplevel())
        info_window.grab_set()
        
        # Header frame
        header_frame = ttk.Frame(info_window, style='TFrame', padding=(15, 15, 15, 0))
        header_frame.pack(fill='x')
        
        # Title in green
        title_label = ttk.Label(header_frame, text=event_name.split('.')[-1], 
                               font=("JetBrains Mono", 18, "bold"),
                               foreground=theme.SUCCESS_GREEN,
                               style='TLabel')
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Close button
        close_btn = ttk.Button(header_frame, text="✕", width=3, 
                              command=info_window.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        # Main content
        content_frame = ttk.Frame(info_window, style='TFrame', padding=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Device badge
        device_name = event_details.get('device', 'unknown')
        device_frame = ttk.Frame(content_frame, style='TFrame')
        device_frame.pack(anchor='w', pady=(5, 15))
        device_label = ttk.Label(device_frame, 
                                text=f" {device_name.upper()} ",
                                font=("JetBrains Mono", 9, "bold"),
                                background=theme.SECONDARY_ACCENT,
                                foreground=theme.FG_COLOR,
                                padding=(8, 4))
        device_label.pack(side=tk.LEFT)
        
        # Type badge (script_control, safety, etc.)
        event_type = event_details.get('type', 'unknown')
        type_label = ttk.Label(device_frame, 
                              text=f" {event_type.upper()} ",
                              font=("JetBrains Mono", 9, "bold"),
                              background=theme.WARNING_YELLOW,
                              foreground=theme.BG_COLOR,
                              padding=(8, 4))
        type_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Description
        description = event_details.get('description', 'No description available.')
        desc_label = ttk.Label(content_frame, text="Description",
                              font=("JetBrains Mono", 12, "bold"),
                              foreground=theme.SUCCESS_GREEN,
                              style='TLabel')
        desc_label.pack(anchor='w', pady=(0, 5))
        
        desc_text = ttk.Label(content_frame, 
                             text=description,
                             font=("JetBrains Mono", 10),
                             wraplength=550,
                             justify='left',
                             style='TLabel')
        desc_text.pack(anchor='w', pady=(0, 15))
        
        # Parameters section (if any)
        if event_details.get('params'):
            params_label = ttk.Label(content_frame, text="Parameters",
                                    font=("JetBrains Mono", 12, "bold"),
                                    foreground=theme.SUCCESS_GREEN,
                                    style='TLabel')
            params_label.pack(anchor='w', pady=(0, 5))
            
            for param in event_details['params']:
                param_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
                param_frame.pack(fill='x', pady=(0, 8))
                
                # Parameter name
                param_name_text = param.get('parameter', 'Unknown')
                param_name_label = ttk.Label(param_frame,
                                      text=f"• {param_name_text}",
                                      font=("JetBrains Mono", 10, "bold"),
                                      foreground=theme.PARAMETER_COLOR,
                                      style='TLabel')
                param_name_label.pack(anchor='w')
                
                # Parameter type
                param_type = param.get('type', 'unknown')
                type_label = ttk.Label(param_frame,
                                      text=f"  Type: {param_type}",
                                      font=("JetBrains Mono", 9),
                                      foreground=theme.COMMENT_COLOR,
                                      style='TLabel')
                type_label.pack(anchor='w', padx=(10, 0))
                
                # Optional flag
                if param.get('optional'):
                    optional_label = ttk.Label(param_frame,
                                              text="  Optional",
                                              font=("JetBrains Mono", 9),
                                              foreground=theme.WARNING_YELLOW,
                                              style='TLabel')
                    optional_label.pack(anchor='w', padx=(10, 0))
                
                # Description
                param_desc = param.get('description', '')
                if param_desc:
                    param_desc_label = ttk.Label(param_frame,
                                                text=f"  {param_desc}",
                                                font=("JetBrains Mono", 9),
                                                foreground=theme.FG_COLOR,
                                                wraplength=500,
                                                justify='left',
                                                style='TLabel')
                    param_desc_label.pack(anchor='w', padx=(10, 0), pady=(5, 0))
        
        # Usage example
        usage_label = ttk.Label(content_frame, text="Script Usage",
                               font=("JetBrains Mono", 12, "bold"),
                               foreground=theme.SUCCESS_GREEN,
                               style='TLabel')
        usage_label.pack(anchor='w', pady=(15, 5))
        
        usage_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
        usage_frame.pack(fill='x')
        
        usage_text = ttk.Label(usage_frame,
                              text=f"WAIT_FOR {event_name}",
                              font=("JetBrains Mono", 10, "bold"),
                              foreground=theme.SCRIPT_COMMAND_COLOR,
                              style='TLabel')
        usage_text.pack(anchor='w')
        
        usage_desc = ttk.Label(usage_frame,
                              text="Pauses script execution until this event is received from the device.",
                              font=("JetBrains Mono", 9),
                              foreground=theme.COMMENT_COLOR,
                              wraplength=530,
                              justify='left',
                              style='TLabel')
        usage_desc.pack(anchor='w', pady=(5, 0))
        
        # Bind escape to close
        info_window.bind('<Escape>', lambda e: info_window.destroy())
        
        # Calculate required size and center the window
        info_window.update_idletasks()
        
        # Get required size based on content
        req_width = info_window.winfo_reqwidth()
        req_height = info_window.winfo_reqheight()
        
        # Add padding and apply min/max limits
        window_width = max(600, req_width + 20)
        window_height = min(max(req_height + 20, 300), int(info_window.winfo_screenheight() * 0.8))
        
        # Center the window
        x = (info_window.winfo_screenwidth() // 2) - (window_width // 2)
        y = (info_window.winfo_screenheight() // 2) - (window_height // 2)
        info_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _generate_examples(self, command, cmd_details):
        """Generate usage examples for a command."""
        examples = []
        params = cmd_details.get('params', [])
        
        def extract_unit(param_name):
            try:
                start = param_name.index('(')
                end = param_name.index(')', start + 1)
                return param_name[start+1:end]
            except ValueError:
                return ""

        def default_for_unit(param_type, unit, choices=None):
            """Return a reasonable default value (as string) based on unit and type."""
            if choices:
                return str(choices[0])
            normalized = unit.strip().lower()
            # Common unit defaults
            unit_defaults_float = {
                'mm': '10.5',
                'mm/s': '20',
                'kg': '120',
                '%': '40',
                'n': '1000',
                's': '2',
                'ms': '500',
                'ml': '5',
                'c': '70',            # Celsius abbreviated
                '°c': '70',
                'deg': '45',
                'psi': '30',
                'bar': '2',
                'pa': '100000',
                'v': '12',
                'a': '1',
            }
            unit_defaults_int = {
                'mm': '10',
                'mm/s': '20',
                'kg': '120',
                '%': '40',
                'n': '1000',
                's': '2',
                'ms': '500',
                'ml': '5',
                'psi': '30',
                'bar': '2',
                'pa': '100000',
                'v': '12',
                'a': '1',
            }
            if param_type == 'int':
                if normalized in unit_defaults_int:
                    return unit_defaults_int[normalized]
                return '100'
            # float and others default
            if normalized in unit_defaults_float:
                return unit_defaults_float[normalized]
            return '10.5' if param_type == 'float' else 'value'

        if not params:
            # No parameters - show simple usage
            examples.append(f"# Simple usage\n{command}")
        else:
            # Basic example with all required params
            param_values_with_units = []
            param_values_plain = []
            
            for param in params:
                param_type = param.get('type', 'str')
                choices = param.get('enum') or param.get('options')
                unit = extract_unit(param.get('name', ''))
                # Unit-aware default selection
                val = default_for_unit(param_type, unit, choices)

                param_values_plain.append(val)
                if unit:
                    param_values_with_units.append(f"{val} {unit}")
                else:
                    param_values_with_units.append(val)

            basic_example = f"# Basic usage\n{command} {' '.join(param_values_with_units)}"
            examples.append(basic_example)
            
            # If there are optional params, show example with and without
            if any(p.get('optional') for p in params):
                required_values_with_units = []
                
                for i, param in enumerate(params):
                    if not param.get('optional'):
                        val = param_values_plain[i]
                        unit = extract_unit(param.get('name', ''))
                        if unit:
                            required_values_with_units.append(f"{val} {unit}")
                        else:
                            required_values_with_units.append(val)
                
                if required_values_with_units:
                    optional_example = f"# With only required parameters\n{command} {' '.join(required_values_with_units)}"
                    examples.append(optional_example)
            
            # Multi-line script example
            if len(examples) == 1:
                multi_example = f"# In a script sequence\nWAIT 1000\n{command} {' '.join(param_values_with_units)}\nWAIT 500"
                examples.append(multi_example)
        
        return examples
    
    def _copy_example(self, text):
        """Copy example text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(text)
    
    def _on_mouse_motion(self, event, text_widget, widget_type):
        """Highlight the row under the mouse cursor."""
        try:
            # Get the line number at the mouse position
            index = text_widget.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            # Check if this is a command, variable, event, or device line
            is_item_line = False
            if widget_type == 'commands' and line_num in self.command_lines:
                is_item_line = True
            elif widget_type == 'variables' and line_num in self.variable_lines:
                is_item_line = True
            elif widget_type == 'events' and line_num in self.event_lines:
                is_item_line = True
            elif widget_type == 'devices' and line_num in self.device_lines:
                is_item_line = True
            
            if is_item_line:
                if text_widget.current_hover_line != line_num:
                    # Remove previous hover highlight
                    if text_widget.current_hover_line:
                        text_widget.tag_remove('hover', f"{text_widget.current_hover_line}.0", f"{text_widget.current_hover_line}.end")
                    
                    # Add new hover highlight
                    text_widget.tag_add('hover', f"{line_num}.0", f"{line_num}.end")
                    text_widget.current_hover_line = line_num
                    
                    # Change cursor to hand
                    text_widget.config(cursor="hand2")
            else:
                # Not on an item line, remove hover
                if text_widget.current_hover_line:
                    text_widget.tag_remove('hover', f"{text_widget.current_hover_line}.0", f"{text_widget.current_hover_line}.end")
                    text_widget.current_hover_line = None
                text_widget.config(cursor="arrow")
        except:
            pass
    
    def _on_mouse_leave(self, event, text_widget):
        """Remove hover highlight when mouse leaves the widget."""
        if text_widget.current_hover_line:
            text_widget.tag_remove('hover', f"{text_widget.current_hover_line}.0", f"{text_widget.current_hover_line}.end")
            text_widget.current_hover_line = None
        text_widget.config(cursor="arrow")
    
    def _show_tooltip(self, event, description, tooltip):
        """Show tooltip with description."""
        if tooltip:
            # Position tooltip at mouse cursor
            x, y = event.x_root, event.y_root
            tooltip.showtip_at_position(description, x, y)
    
    def _hide_tooltip(self, tooltip):
        """Hide tooltip."""
        if tooltip:
            tooltip.hidetip()
    
    # ===== JSON EDITING METHODS =====
    
    def show_add_command_dialog(self):
        """Show dialog to add a new command."""
        AddCommandDialog(self, self.device_manager, on_save=lambda: self.refresh_commands())
    
    def edit_command(self):
        """Show dialog to edit the selected command."""
        command = self.get_selected_command()
        if not command:
            return
        
        # Don't allow editing script commands
        script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE', 
                         'wait', 'math', 'wait_for', 'comment', 'cycle']
        if command in script_commands:
            from tkinter import messagebox
            messagebox.showerror("Cannot Edit", 
                               "Built-in script commands cannot be edited.")
            return
        
        # Get command details
        cmd_details = self.scripting_commands.get(command)
        if cmd_details:
            AddCommandDialog(self, self.device_manager, 
                           on_save=lambda: self.refresh_commands(),
                           edit_mode=True,
                           command_name=command,
                           command_data=cmd_details)
    
    def show_add_variable_dialog(self):
        """Show dialog to add a new variable."""
        AddVariableDialog(self, self.device_manager, on_save=lambda: self.refresh_variables())
    
    def show_add_event_dialog(self):
        """Show dialog to add a new event."""
        AddEventDialog(self, self.device_manager, on_save=lambda: self.refresh_events())
    
    # ===== DEVICE METHODS =====
    
    def get_selected_device(self):
        """Get device at current cursor position in devices tab."""
        try:
            cursor_pos = self.devices_text.index(tk.INSERT)
            line_num = int(cursor_pos.split('.')[0])
            return self.device_lines.get(line_num)
        except Exception:
            return None
    
    def show_devices_context_menu(self, event):
        # Set cursor to click position
        self.devices_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        device = self.get_selected_device()
        if device:
            self.devices_context_menu.post(event.x_root, event.y_root)
    
    def show_device_info(self):
        """Opens a detailed information window for the selected device."""
        device_name = self.get_selected_device()
        if not device_name:
            return
        
        device_data = self.device_manager.devices.get(device_name, {})
        
        # Create info window
        info_window = tk.Toplevel(self)
        info_window.title(f"Device Info: {device_name}")
        info_window.geometry("650x550")
        info_window.configure(bg=theme.BG_COLOR)
        info_window.transient(self.winfo_toplevel())
        info_window.grab_set()
        
        # Main content
        content_frame = ttk.Frame(info_window, style='TFrame', padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text=device_name,
                 font=theme.FONT_LARGE_BOLD,
                 foreground=theme.COMMAND_COLOR).pack(anchor='w', pady=(0, 20))
        
        # Stats
        ttk.Label(content_frame, text="Statistics",
                 font=theme.FONT_BOLD,
                 foreground=theme.PRIMARY_ACCENT).pack(anchor='w', pady=(0, 10))
        
        stats_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
        stats_frame.pack(fill='x', pady=(0, 20))
        
        commands_count = len(device_data.get('scripting_commands', {}))
        telemetry_count = len(device_data.get('telemetry_data', {}))
        events_count = len(device_data.get('events_data', {}))
        
        ttk.Label(stats_frame, text=f"Commands: {commands_count}",
                 font=theme.FONT_NORMAL).pack(anchor='w', pady=2)
        ttk.Label(stats_frame, text=f"Variables: {telemetry_count}",
                 font=theme.FONT_NORMAL).pack(anchor='w', pady=2)
        ttk.Label(stats_frame, text=f"Events: {events_count}",
                 font=theme.FONT_NORMAL).pack(anchor='w', pady=2)
        
        # Connection status
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            is_connected = device_states.get(device_name, {}).get('connected', False)
        
        ttk.Label(content_frame, text="Status",
                 font=theme.FONT_BOLD,
                 foreground=theme.PRIMARY_ACCENT).pack(anchor='w', pady=(0, 10))
        
        status_frame = ttk.Frame(content_frame, style='Card.TFrame', padding=10)
        status_frame.pack(fill='x')
        
        status_text = "Connected" if is_connected else "Disconnected"
        status_color = theme.SUCCESS_GREEN if is_connected else theme.ERROR_RED
        ttk.Label(status_frame, text=f"Connection: {status_text}",
                 font=theme.FONT_NORMAL,
                 foreground=status_color).pack(anchor='w', pady=2)
        
        info_window.bind('<Escape>', lambda e: info_window.destroy())
    
    def show_add_device_dialog(self):
        """Show dialog to add a new device."""
        AddDeviceDialog(self, self.device_manager, on_save=lambda: self.refresh())
    
    def edit_device(self):
        """Show dialog to edit the selected device."""
        device_name = self.get_selected_device()
        if not device_name:
            return
        
        AddDeviceDialog(self, self.device_manager,
                       on_save=lambda: self.refresh(),
                       edit_mode=True,
                       device_name=device_name)
    
    def delete_device(self):
        """Delete the selected device folder and all its files."""
        from tkinter import messagebox
        import shutil
        import os
        
        device_name = self.get_selected_device()
        if not device_name:
            return
        
        # Confirm deletion
        response = messagebox.askyesno("Confirm Deletion",
                                       f"Are you sure you want to delete device:\n\n{device_name}\n\n" +
                                       "This will DELETE the entire device folder and ALL its files.\n" +
                                       "This action CANNOT be undone!",
                                       icon='warning')
        if not response:
            return
        
        try:
            device_path = os.path.join('devices', device_name)
            
            if os.path.exists(device_path):
                shutil.rmtree(device_path)
                messagebox.showinfo("Success", f"Device '{device_name}' deleted successfully!")
                
                # Rediscover devices to pick up the deletion
                self.device_manager.discover_devices()
                self.refresh()
            else:
                messagebox.showerror("Error", f"Device folder not found: {device_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete device:\n{str(e)}")
    
    def delete_command(self):
        """Delete the selected command from its JSON file."""
        from tkinter import messagebox
        import json
        import os
        
        command = self.get_selected_command()
        if not command:
            return
        
        # Don't allow deleting script commands
        script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE', 
                         'wait', 'math', 'wait_for', 'comment', 'cycle']
        if command in script_commands:
            messagebox.showerror("Cannot Delete", 
                               "Built-in script commands cannot be deleted.")
            return
        
        # Confirm deletion
        response = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete command:\n\n{command}\n\n" +
                                       "This will modify the JSON file and cannot be undone.")
        if not response:
            return
        
        # Extract device and command name
        if '.' not in command:
            messagebox.showerror("Error", "Invalid command format.")
            return
        
        device_name = command.split('.')[0]
        cmd_name = command.split('.', 1)[1]
        
        # Find and update the JSON file
        try:
            json_path = os.path.join('devices', device_name, 'commands.json')
            
            if not os.path.exists(json_path):
                messagebox.showerror("Error", f"Commands file not found: {json_path}")
                return
            
            # Load JSON
            with open(json_path, 'r') as f:
                commands_data = json.load(f)
            
            # Remove the command
            if cmd_name in commands_data:
                del commands_data[cmd_name]
                
                # Save back to file
                with open(json_path, 'w') as f:
                    json.dump(commands_data, f, indent=4)
                
                messagebox.showinfo("Success", f"Command '{command}' deleted successfully.")
                
                # Reload device data and refresh
                self.device_manager.reload_device_modules()
                self.refresh_commands()
            else:
                messagebox.showerror("Error", f"Command '{cmd_name}' not found in JSON.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete command:\n{str(e)}")
    
    def edit_variable(self):
        """Show dialog to edit the selected variable."""
        variable_info = self.get_selected_variable()
        if not variable_info:
            return
        
        device_name, param_name, param_details = variable_info
        full_var_name = f"{device_name}.{param_name}"
        
        # Open edit dialog
        AddVariableDialog(self, self.device_manager, 
                         on_save=lambda: self.refresh_variables(),
                         edit_mode=True,
                         variable_name=full_var_name,
                         variable_data=param_details,
                         device_name=device_name)
    
    def delete_variable(self):
        """Delete the selected variable from its JSON file."""
        from tkinter import messagebox
        import json
        import os
        
        variable_info = self.get_selected_variable()
        if not variable_info:
            return
        
        device_name, param_name, param = variable_info
        full_var_name = f"{device_name}.{param_name}"
        
        # Confirm deletion
        response = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete variable:\n\n{full_var_name}\n\n" +
                                       "This will modify the JSON file and cannot be undone.")
        if not response:
            return
        
        # Find and update the JSON file
        try:
            json_path = os.path.join('devices', device_name, 'telemetry.json')
            
            if not os.path.exists(json_path):
                messagebox.showerror("Error", f"Telemetry file not found: {json_path}")
                return
            
            # Load JSON
            with open(json_path, 'r') as f:
                telemetry_data = json.load(f)
            
            # Remove the variable
            if param_name in telemetry_data:
                del telemetry_data[param_name]
                
                # Save back to file
                with open(json_path, 'w') as f:
                    json.dump(telemetry_data, f, indent=4)
                
                messagebox.showinfo("Success", f"Variable '{full_var_name}' deleted successfully.")
                
                # Reload device data and refresh
                self.device_manager.reload_device_modules()
                self.refresh_variables()
            else:
                messagebox.showerror("Error", f"Variable '{param_name}' not found in JSON.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete variable:\n{str(e)}")
    
    def edit_event(self):
        """Show dialog to edit the selected event."""
        event_name = self.get_selected_event()
        if not event_name:
            return
        
        # Get event details
        all_events = self.device_manager.get_all_events()
        event_details = all_events.get(event_name)
        if not event_details:
            return
        
        # Extract device name
        device_name = event_details.get('device', '')
        if not device_name and '.' in event_name:
            device_name = event_name.split('.')[0]
        
        # Open edit dialog
        AddEventDialog(self, self.device_manager, 
                      on_save=lambda: self.refresh_events(),
                      edit_mode=True,
                      event_name=event_name,
                      event_data=event_details,
                      device_name=device_name)
    
    def delete_event(self):
        """Delete the selected event from its JSON file."""
        from tkinter import messagebox
        import json
        import os
        
        event_name = self.get_selected_event()
        if not event_name:
            return
        
        # Extract device and event name
        if '.' not in event_name:
            messagebox.showerror("Error", "Invalid event format.")
            return
        
        device_name = event_name.split('.')[0]
        evt_name = event_name.split('.', 1)[1]
        
        # Confirm deletion
        response = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete event:\n\n{event_name}\n\n" +
                                       "This will modify the JSON file and cannot be undone.")
        if not response:
            return
        
        # Find and update the JSON file
        try:
            json_path = os.path.join('devices', device_name, 'events.json')
            
            if not os.path.exists(json_path):
                messagebox.showerror("Error", f"Events file not found: {json_path}")
                return
            
            # Load JSON
            with open(json_path, 'r') as f:
                events_data = json.load(f)
            
            # Remove the event
            if evt_name in events_data:
                del events_data[evt_name]
                
                # Save back to file
                with open(json_path, 'w') as f:
                    json.dump(events_data, f, indent=4)
                
                messagebox.showinfo("Success", f"Event '{event_name}' deleted successfully.")
                
                # Reload device data and refresh
                self.device_manager.reload_device_modules()
                self.refresh_events()
            else:
                messagebox.showerror("Error", f"Event '{evt_name}' not found in JSON.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete event:\n{str(e)}")

# ===== ADD/EDIT DIALOGS =====

class AddCommandDialog(tk.Toplevel):
    """Dialog for adding or editing a command to a device."""
    
    def __init__(self, parent, device_manager, on_save=None, edit_mode=False, command_name=None, command_data=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.on_save = on_save
        self.edit_mode = edit_mode
        self.original_command_name = command_name
        self.command_data = command_data
        
        self.title("Edit Command" if edit_mode else "Add Command")
        self.configure(bg=theme.BG_COLOR)
        self.transient(parent)
        self.grab_set()
        
        # Set reasonable window size with good canvas height for scrolling
        self.geometry("800x700")
        self.minsize(750, 600)
        
        self.create_widgets()
        
        # Load existing data if in edit mode
        if self.edit_mode and self.command_data:
            self.load_command_data()
        
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        # Configure combobox style
        style = ttk.Style()
        style.map('TCombobox', 
                 fieldbackground=[('readonly', theme.WIDGET_BG)],
                 selectbackground=[('readonly', theme.WIDGET_BG)],
                 selectforeground=[('readonly', theme.FG_COLOR)])
        style.map('TCombobox', 
                 background=[('readonly', theme.WIDGET_BG)])
        
        # Main frame
        main_frame = ttk.Frame(self, style='TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_text = "Edit Command" if self.edit_mode else "Add New Command"
        title_label = ttk.Label(main_frame, text=title_text,
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.PRIMARY_ACCENT)
        title_label.pack(pady=(0, 20))
        
        # Device selection
        device_frame = ttk.Frame(main_frame, style='TFrame')
        device_frame.pack(fill=tk.X, pady=5)
        ttk.Label(device_frame, text="Device:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        
        self.device_var = tk.StringVar()
        device_names = list(self.device_manager.get_all_device_names())
        if device_names:
            self.device_var.set(device_names[0])
        
        device_dropdown = ttk.Combobox(device_frame, textvariable=self.device_var,
                                      values=device_names, state='readonly', width=30)
        device_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Command name
        name_frame = ttk.Frame(main_frame, style='TFrame')
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Command Name:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_frame = ttk.Frame(main_frame, style='TFrame')
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="Description:", font=theme.FONT_BOLD).pack(anchor='w')
        self.desc_text = tk.Text(desc_frame, height=3, width=50,
                                bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                insertbackground=theme.FG_COLOR,
                                font=theme.FONT_NORMAL)
        self.desc_text.pack(fill=tk.X, pady=(5, 0))
        
        # Buttons frame (pack first so it stays at bottom)
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.destroy,
                               bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                               font=theme.FONT_NORMAL, relief=tk.FLAT,
                               padx=20, pady=8)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        save_btn = tk.Button(button_frame, text="Save", command=self.save_command,
                            bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                            font=theme.FONT_BOLD, relief=tk.FLAT,
                            padx=20, pady=8)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Parameters section
        params_label_frame = ttk.Frame(main_frame, style='TFrame')
        params_label_frame.pack(fill=tk.X, pady=(15, 5))
        ttk.Label(params_label_frame, text="Parameters:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        add_param_btn = tk.Button(params_label_frame, text="+ Add Parameter",
                                  command=self.add_parameter,
                                  bg=theme.PRIMARY_ACCENT, fg=theme.BG_COLOR,
                                  font=theme.FONT_NORMAL, relief=tk.FLAT,
                                  padx=10, pady=3)
        add_param_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Parameters list frame (scrollable)
        params_canvas_frame = ttk.Frame(main_frame, style='TFrame')
        params_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.params_canvas = tk.Canvas(params_canvas_frame, bg=theme.BG_COLOR,
                                       highlightthickness=0)
        params_scrollbar = ttk.Scrollbar(params_canvas_frame, orient="vertical",
                                        command=self.params_canvas.yview)
        self.params_frame = ttk.Frame(self.params_canvas, style='TFrame')
        
        self.params_frame.bind("<Configure>",
                              lambda e: self.params_canvas.configure(scrollregion=self.params_canvas.bbox("all")))
        
        self.params_canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        self.params_canvas.configure(yscrollcommand=params_scrollbar.set)
        
        self.params_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        params_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mousewheel scrolling (bind only when mouse is over canvas)
        def on_mousewheel(event):
            self.params_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.params_canvas.bind("<Enter>", lambda e: self.params_canvas.bind_all("<MouseWheel>", on_mousewheel))
        self.params_canvas.bind("<Leave>", lambda e: self.params_canvas.unbind_all("<MouseWheel>"))
        
        # Store parameters
        self.parameters = []
    
    def add_parameter(self):
        """Add a parameter entry row."""
        param_row = ttk.Frame(self.params_frame, style='Card.TFrame', padding=5)
        param_row.pack(fill=tk.X, pady=2)
        
        # Parameter name
        ttk.Label(param_row, text="Name:", font=theme.FONT_NORMAL).grid(row=0, column=0, sticky='w', padx=(0, 5))
        name_entry = ttk.Entry(param_row, width=15)
        name_entry.grid(row=0, column=1, padx=5)
        
        # Type
        ttk.Label(param_row, text="Type:", font=theme.FONT_NORMAL).grid(row=0, column=2, sticky='w', padx=(10, 5))
        type_var = tk.StringVar(value="float")
        type_combo = ttk.Combobox(param_row, textvariable=type_var,
                                  values=["float", "int", "string", "bool"],
                                  state='readonly', width=10)
        type_combo.grid(row=0, column=3, padx=5)
        
        # Unit
        ttk.Label(param_row, text="Unit:", font=theme.FONT_NORMAL).grid(row=0, column=4, sticky='w', padx=(10, 5))
        unit_entry = ttk.Entry(param_row, width=10)
        unit_entry.grid(row=0, column=5, padx=5)
        
        # Remove button - command set later
        remove_btn = tk.Button(param_row, text="✕",
                              bg=theme.ERROR_RED, fg='white',
                              font=theme.FONT_NORMAL, relief=tk.FLAT,
                              padx=5, pady=2)
        remove_btn.grid(row=0, column=6, padx=(10, 0))
        
        # Inline options editor (for string types)
        options_frame = ttk.Frame(param_row, style='TFrame')
        options_frame.grid(row=1, column=0, columnspan=7, sticky='ew', pady=(5, 0))
        options_frame.grid_remove()  # Hidden by default
        
        ttk.Label(options_frame, text="Options:", font=theme.FONT_SMALL, 
                 foreground=theme.COMMENT_COLOR).pack(side=tk.LEFT, padx=(5, 10))
        
        # Listbox for options
        options_listbox = tk.Listbox(options_frame, height=3, width=30,
                                    bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                    font=theme.FONT_SMALL, relief=tk.FLAT,
                                    selectbackground=theme.SELECTION_BG)
        options_listbox.pack(side=tk.LEFT, padx=5)
        
        # Right side: input and buttons
        options_control_frame = ttk.Frame(options_frame, style='TFrame')
        options_control_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # Input frame with label
        input_frame = ttk.Frame(options_control_frame, style='TFrame')
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(input_frame, text="Add new:", font=theme.FONT_SMALL,
                 foreground=theme.COMMENT_COLOR).pack(anchor='w')
        
        # Entry and buttons frame
        entry_buttons_frame = ttk.Frame(options_control_frame, style='TFrame')
        entry_buttons_frame.pack(fill=tk.X)
        
        new_option_entry = ttk.Entry(entry_buttons_frame, width=15)
        new_option_entry.pack(side=tk.LEFT, padx=(0, 3))
        
        # Add button
        add_option_btn = tk.Button(entry_buttons_frame, text="+",
                                  bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                                  font=theme.FONT_SMALL, relief=tk.FLAT,
                                  padx=8, pady=2)
        add_option_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Remove button
        remove_option_btn = tk.Button(entry_buttons_frame, text="−",
                                     bg=theme.ERROR_RED, fg='white',
                                     font=theme.FONT_SMALL, relief=tk.FLAT,
                                     padx=8, pady=2)
        remove_option_btn.pack(side=tk.LEFT)
        
        # Store parameter data
        param_data = {
            'frame': param_row,
            'name': name_entry,
            'type': type_var,
            'unit': unit_entry,
            'options': [],
            'options_frame': options_frame,
            'options_listbox': options_listbox,
            'new_option_entry': new_option_entry
        }
        
        # Set up option management functions
        def add_option():
            option = new_option_entry.get().strip()
            if option and option not in param_data['options']:
                param_data['options'].append(option)
                options_listbox.insert(tk.END, option)
                new_option_entry.delete(0, tk.END)
        
        def remove_option():
            selection = options_listbox.curselection()
            if selection:
                index = selection[0]
                option = options_listbox.get(index)
                options_listbox.delete(index)
                param_data['options'].remove(option)
        
        def edit_option(event):
            from tkinter import simpledialog
            selection = options_listbox.curselection()
            if selection:
                index = selection[0]
                old_value = options_listbox.get(index)
                new_value = simpledialog.askstring("Edit Option", "Edit option value:",
                                                   initialvalue=old_value, parent=self)
                if new_value and new_value.strip() and new_value != old_value:
                    new_value = new_value.strip()
                    if new_value not in param_data['options']:
                        param_data['options'][index] = new_value
                        options_listbox.delete(index)
                        options_listbox.insert(index, new_value)
                        options_listbox.selection_set(index)
        
        # Bind buttons and events
        add_option_btn.config(command=add_option)
        remove_option_btn.config(command=remove_option)
        options_listbox.bind('<Double-Button-1>', edit_option)
        options_listbox.bind('<Delete>', lambda e: remove_option())
        new_option_entry.bind('<Return>', lambda e: add_option())
        
        # Remove parameter button
        remove_btn.config(command=lambda f=param_row, pd=param_data: self.remove_parameter(f, pd))
        
        # Show/hide options frame based on type
        def on_type_change(*args, pd=param_data):
            if pd['type'].get() == "string":
                pd['options_frame'].grid()
            else:
                pd['options_frame'].grid_remove()
                pd['options'].clear()
                pd['options_listbox'].delete(0, tk.END)
        
        type_var.trace('w', on_type_change)
        
        self.parameters.append(param_data)
    
    def remove_parameter(self, frame, param_data):
        """Remove a parameter row."""
        frame.destroy()
        if param_data in self.parameters:
            self.parameters.remove(param_data)
    
    def load_command_data(self):
        """Load existing command data into the dialog."""
        if not self.command_data:
            return
        
        # Extract device name from full command name (e.g., "pressboi.move_abs" -> "pressboi")
        if self.original_command_name and '.' in self.original_command_name:
            device_name = self.original_command_name.split('.')[0]
            cmd_name = self.original_command_name.split('.', 1)[1]
        else:
            device_name = self.command_data.get('device', '')
            cmd_name = self.original_command_name or ''
        
        # Set device
        if device_name:
            self.device_var.set(device_name)
        
        # Set command name
        self.name_entry.insert(0, cmd_name)
        # Allow editing command name in edit mode
        
        # Set description
        description = self.command_data.get('description', '') or self.command_data.get('help', '')
        if description:
            self.desc_text.insert('1.0', description)
        
        # Load parameters
        params = self.command_data.get('params', [])
        for param in params:
            # Add parameter row
            param_row = ttk.Frame(self.params_frame, style='Card.TFrame', padding=5)
            param_row.pack(fill=tk.X, pady=2)
            
            # Parameter name
            ttk.Label(param_row, text="Name:", font=theme.FONT_NORMAL).grid(row=0, column=0, sticky='w', padx=(0, 5))
            name_entry = ttk.Entry(param_row, width=15)
            name_entry.insert(0, param.get('parameter', ''))
            name_entry.grid(row=0, column=1, padx=5)
            
            # Type
            ttk.Label(param_row, text="Type:", font=theme.FONT_NORMAL).grid(row=0, column=2, sticky='w', padx=(10, 5))
            type_var = tk.StringVar(value=param.get('type', 'float'))
            type_combo = ttk.Combobox(param_row, textvariable=type_var,
                                      values=["float", "int", "string", "bool"],
                                      state='readonly', width=10)
            type_combo.grid(row=0, column=3, padx=5)
            
            # Unit
            ttk.Label(param_row, text="Unit:", font=theme.FONT_NORMAL).grid(row=0, column=4, sticky='w', padx=(10, 5))
            unit_entry = ttk.Entry(param_row, width=10)
            unit_entry.insert(0, param.get('unit', ''))
            unit_entry.grid(row=0, column=5, padx=5)
            
            # Remove button
            remove_btn = tk.Button(param_row, text="✕",
                                  bg=theme.ERROR_RED, fg='white',
                                  font=theme.FONT_NORMAL, relief=tk.FLAT,
                                  padx=5, pady=2)
            remove_btn.grid(row=0, column=6, padx=(10, 0))
            
            # Inline options editor (for string types)
            options_frame = ttk.Frame(param_row, style='TFrame')
            options_frame.grid(row=1, column=0, columnspan=7, sticky='ew', pady=(5, 0))
            
            ttk.Label(options_frame, text="Options:", font=theme.FONT_SMALL, 
                     foreground=theme.COMMENT_COLOR).pack(side=tk.LEFT, padx=(5, 10))
            
            # Listbox for options
            options_listbox = tk.Listbox(options_frame, height=3, width=30,
                                        bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                        font=theme.FONT_SMALL, relief=tk.FLAT,
                                        selectbackground=theme.SELECTION_BG)
            options_listbox.pack(side=tk.LEFT, padx=5)
            
            # Right side: input and buttons
            options_control_frame = ttk.Frame(options_frame, style='TFrame')
            options_control_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)
            
            # Input frame with label
            input_frame = ttk.Frame(options_control_frame, style='TFrame')
            input_frame.pack(fill=tk.X, pady=(0, 5))
            
            ttk.Label(input_frame, text="Add new:", font=theme.FONT_SMALL,
                     foreground=theme.COMMENT_COLOR).pack(anchor='w')
            
            # Entry and buttons frame
            entry_buttons_frame = ttk.Frame(options_control_frame, style='TFrame')
            entry_buttons_frame.pack(fill=tk.X)
            
            new_option_entry = ttk.Entry(entry_buttons_frame, width=15)
            new_option_entry.pack(side=tk.LEFT, padx=(0, 3))
            
            # Add button
            add_option_btn = tk.Button(entry_buttons_frame, text="+",
                                      bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                                      font=theme.FONT_SMALL, relief=tk.FLAT,
                                      padx=8, pady=2)
            add_option_btn.pack(side=tk.LEFT, padx=(0, 2))
            
            # Remove button
            remove_option_btn = tk.Button(entry_buttons_frame, text="−",
                                         bg=theme.ERROR_RED, fg='white',
                                         font=theme.FONT_SMALL, relief=tk.FLAT,
                                         padx=8, pady=2)
            remove_option_btn.pack(side=tk.LEFT)
            
            # Load existing options
            options_list = param.get('enum', []) or param.get('options', [])
            
            # Store parameter data
            param_data = {
                'frame': param_row,
                'name': name_entry,
                'type': type_var,
                'unit': unit_entry,
                'options': list(options_list),
                'options_frame': options_frame,
                'options_listbox': options_listbox,
                'new_option_entry': new_option_entry
            }
            
            # Populate listbox with existing options
            for option in options_list:
                options_listbox.insert(tk.END, option)
            
            # Set up option management functions
            def add_option(pd=param_data):
                option = pd['new_option_entry'].get().strip()
                if option and option not in pd['options']:
                    pd['options'].append(option)
                    pd['options_listbox'].insert(tk.END, option)
                    pd['new_option_entry'].delete(0, tk.END)
            
            def remove_option(pd=param_data):
                selection = pd['options_listbox'].curselection()
                if selection:
                    index = selection[0]
                    option = pd['options_listbox'].get(index)
                    pd['options_listbox'].delete(index)
                    pd['options'].remove(option)
            
            def edit_option(event, pd=param_data):
                from tkinter import simpledialog
                selection = pd['options_listbox'].curselection()
                if selection:
                    index = selection[0]
                    old_value = pd['options_listbox'].get(index)
                    new_value = simpledialog.askstring("Edit Option", "Edit option value:",
                                                       initialvalue=old_value, parent=self)
                    if new_value and new_value.strip() and new_value != old_value:
                        new_value = new_value.strip()
                        if new_value not in pd['options']:
                            pd['options'][index] = new_value
                            pd['options_listbox'].delete(index)
                            pd['options_listbox'].insert(index, new_value)
                            pd['options_listbox'].selection_set(index)
            
            # Bind buttons and events
            add_option_btn.config(command=lambda pd=param_data: add_option(pd))
            remove_option_btn.config(command=lambda pd=param_data: remove_option(pd))
            options_listbox.bind('<Double-Button-1>', lambda e, pd=param_data: edit_option(e, pd))
            options_listbox.bind('<Delete>', lambda e, pd=param_data: remove_option(pd))
            new_option_entry.bind('<Return>', lambda e, pd=param_data: add_option(pd))
            
            # Configure remove parameter button
            remove_btn.config(command=lambda f=param_row, pd=param_data: self.remove_parameter(f, pd))
            
            # Show/hide options frame based on type
            def on_type_change(*args, pd=param_data):
                if pd['type'].get() == "string":
                    pd['options_frame'].grid()
                else:
                    pd['options_frame'].grid_remove()
                    pd['options'].clear()
                    pd['options_listbox'].delete(0, tk.END)
            
            type_var.trace('w', on_type_change)
            
            # Show options frame if type is string
            if type_var.get() == "string":
                options_frame.grid()
            else:
                options_frame.grid_remove()
            
            self.parameters.append(param_data)
    
    def save_command(self):
        """Save the new command to JSON."""
        from tkinter import messagebox
        import json
        import os
        
        device_name = self.device_var.get()
        cmd_name = self.name_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not cmd_name:
            messagebox.showerror("Error", "Command name is required.")
            return
        
        if not description:
            messagebox.showerror("Error", "Description is required.")
            return
        
        # Build parameters list
        params_list = []
        for param_data in self.parameters:
            param_name = param_data['name'].get().strip()
            param_type = param_data['type'].get()
            param_unit = param_data['unit'].get().strip()
            param_options = param_data.get('options', [])
            
            if param_name:  # Only add if name is provided
                param_obj = {
                    "parameter": param_name,
                    "type": param_type
                }
                if param_unit:
                    param_obj["unit"] = param_unit
                if param_options and param_type == "string":
                    param_obj["enum"] = param_options
                params_list.append(param_obj)
        
        # Load existing commands
        json_path = os.path.join('devices', device_name, 'commands.json')
        
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    commands_data = json.load(f)
            else:
                commands_data = {}
            
            # Handle edit mode vs add mode
            old_cmd_name = None
            if self.edit_mode:
                # In edit mode, check if name changed and remove old entry
                if self.original_command_name and '.' in self.original_command_name:
                    old_cmd_name = self.original_command_name.split('.', 1)[1]
                    if old_cmd_name != cmd_name and old_cmd_name in commands_data:
                        # Name changed, remove old entry
                        del commands_data[old_cmd_name]
                
                # Check if new name already exists (and it's not the same as old name)
                if cmd_name in commands_data and cmd_name != old_cmd_name:
                    messagebox.showerror("Error", f"Command '{cmd_name}' already exists.")
                    return
            else:
                # Add mode - check if command already exists
                if cmd_name in commands_data:
                    messagebox.showerror("Error", f"Command '{cmd_name}' already exists.")
                    return
            
            # Create/update command
            commands_data[cmd_name] = {
                "device": device_name,
                "target": "device",
                "description": description,
                "params": params_list,
                "returns": ["done", "error"]
            }
            
            # Save to file
            with open(json_path, 'w') as f:
                json.dump(commands_data, f, indent=4)
            
            action = "updated" if self.edit_mode else "added"
            messagebox.showinfo("Success", f"Command '{cmd_name}' {action} successfully!")
            
            # Reload and refresh
            self.device_manager.reload_device_modules()
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save command:\n{str(e)}")


class AddVariableDialog(tk.Toplevel):
    """Dialog for adding or editing a variable/telemetry field to a device."""
    
    def __init__(self, parent, device_manager, on_save=None, edit_mode=False, variable_name=None, variable_data=None, device_name=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.on_save = on_save
        self.edit_mode = edit_mode
        self.original_variable_name = variable_name
        self.variable_data = variable_data
        self.original_device_name = device_name
        
        self.title("Edit Variable" if edit_mode else "Add Variable")
        self.configure(bg=theme.BG_COLOR)
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Load existing data if in edit mode
        if self.edit_mode and self.variable_data:
            self.load_variable_data()
        
        # Update and dynamically size
        self.update_idletasks()
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        
        # Get required size based on content
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()
        
        # Add padding and apply min/max limits
        width = max(600, req_width + 40)
        height = min(max(req_height + 40, 400), int(self.winfo_screenheight() * 0.85))
        
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        # Configure combobox style
        style = ttk.Style()
        style.map('TCombobox', 
                 fieldbackground=[('readonly', theme.WIDGET_BG)],
                 selectbackground=[('readonly', theme.WIDGET_BG)],
                 selectforeground=[('readonly', theme.FG_COLOR)])
        style.map('TCombobox', 
                 background=[('readonly', theme.WIDGET_BG)])
        
        # Main frame
        main_frame = ttk.Frame(self, style='TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_text = "Edit Variable" if self.edit_mode else "Add New Variable"
        title_label = ttk.Label(main_frame, text=title_text,
                               font=theme.FONT_LARGE_BOLD,
                               foreground='#C04848')
        title_label.pack(pady=(0, 20))
        
        # Device selection
        device_frame = ttk.Frame(main_frame, style='TFrame')
        device_frame.pack(fill=tk.X, pady=5)
        ttk.Label(device_frame, text="Device:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        
        self.device_var = tk.StringVar()
        device_names = list(self.device_manager.get_all_device_names())
        if device_names:
            self.device_var.set(device_names[0])
        
        device_dropdown = ttk.Combobox(device_frame, textvariable=self.device_var,
                                      values=device_names, state='readonly', width=30)
        device_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Variable name
        name_frame = ttk.Frame(main_frame, style='TFrame')
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Variable Name:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Type
        type_frame = ttk.Frame(main_frame, style='TFrame')
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="Type:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="float")
        type_combo = ttk.Combobox(type_frame, textvariable=self.type_var,
                                 values=["int", "float", "bool", "string"],
                                 state='readonly', width=15)
        type_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Unit
        unit_frame = ttk.Frame(main_frame, style='TFrame')
        unit_frame.pack(fill=tk.X, pady=5)
        ttk.Label(unit_frame, text="Unit (optional):", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.unit_entry = ttk.Entry(unit_frame, width=20)
        self.unit_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Default value
        default_frame = ttk.Frame(main_frame, style='TFrame')
        default_frame.pack(fill=tk.X, pady=5)
        ttk.Label(default_frame, text="Default Value:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.default_entry = ttk.Entry(default_frame, width=20)
        self.default_entry.insert(0, "0")
        self.default_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_frame = ttk.Frame(main_frame, style='TFrame')
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="Description:", font=theme.FONT_BOLD).pack(anchor='w')
        self.desc_text = tk.Text(desc_frame, height=3, width=50,
                                bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                insertbackground=theme.FG_COLOR,
                                font=theme.FONT_NORMAL)
        self.desc_text.pack(fill=tk.X, pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.destroy,
                               bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                               font=theme.FONT_NORMAL, relief=tk.FLAT,
                               padx=20, pady=8)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        save_btn = tk.Button(button_frame, text="Save", command=self.save_variable,
                            bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                            font=theme.FONT_BOLD, relief=tk.FLAT,
                            padx=20, pady=8)
        save_btn.pack(side=tk.RIGHT, padx=5)
    
    def load_variable_data(self):
        """Load existing variable data into the dialog."""
        if not self.variable_data:
            return
        
        # Extract variable name
        if self.original_variable_name and '.' in self.original_variable_name:
            var_name = self.original_variable_name.split('.', 1)[1]
        else:
            var_name = self.original_variable_name or ''
        
        # Set device
        if self.original_device_name:
            self.device_var.set(self.original_device_name)
        
        # Set variable name
        self.name_entry.insert(0, var_name)
        
        # Set type
        var_type = self.variable_data.get('type', 'float')
        self.type_var.set(var_type)
        
        # Set unit
        unit = self.variable_data.get('unit', '')
        if unit:
            self.unit_entry.insert(0, unit)
        
        # Set default
        default = self.variable_data.get('default', '')
        if default is not None:
            self.default_entry.insert(0, str(default))
        
        # Set description
        description = self.variable_data.get('help', '')
        if description:
            self.desc_text.insert('1.0', description)
    
    def save_variable(self):
        """Save the new variable to JSON."""
        from tkinter import messagebox
        import json
        import os
        
        device_name = self.device_var.get()
        var_name = self.name_entry.get().strip()
        var_type = self.type_var.get()
        unit = self.unit_entry.get().strip()
        default = self.default_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not var_name:
            messagebox.showerror("Error", "Variable name is required.")
            return
        
        # Load existing telemetry
        json_path = os.path.join('devices', device_name, 'telemetry.json')
        
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    telemetry_data = json.load(f)
            else:
                telemetry_data = {}
            
            # Handle edit mode vs add mode
            old_var_name = None
            if self.edit_mode:
                # In edit mode, check if name changed and remove old entry
                if self.original_variable_name and '.' in self.original_variable_name:
                    old_var_name = self.original_variable_name.split('.', 1)[1]
                    if old_var_name != var_name and old_var_name in telemetry_data:
                        # Name changed, remove old entry
                        del telemetry_data[old_var_name]
                
                # Check if new name already exists (and it's not the same as old name)
                if var_name in telemetry_data and var_name != old_var_name:
                    messagebox.showerror("Error", f"Variable '{var_name}' already exists.")
                    return
            else:
                # Add mode - check if variable already exists
                if var_name in telemetry_data:
                    messagebox.showerror("Error", f"Variable '{var_name}' already exists.")
                    return
            
            # Parse default value
            try:
                if var_type == "int":
                    default_val = int(default)
                elif var_type == "float":
                    default_val = float(default)
                elif var_type == "bool":
                    default_val = default.lower() in ['true', '1', 'yes']
                else:
                    default_val = default
            except ValueError:
                messagebox.showerror("Error", f"Invalid default value for type '{var_type}'.")
                return
            
            # Create new variable
            telemetry_data[var_name] = {
                "type": var_type,
                "default": default_val,
                "help": description
            }
            
            if unit:
                telemetry_data[var_name]["unit"] = unit
            
            if var_type == "float":
                telemetry_data[var_name]["precision"] = 2
            
            # Save to file
            with open(json_path, 'w') as f:
                json.dump(telemetry_data, f, indent=4)
            
            action = "updated" if self.edit_mode else "added"
            messagebox.showinfo("Success", f"Variable '{var_name}' {action} successfully!")
            
            # Reload and refresh
            self.device_manager.reload_device_modules()
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save variable:\n{str(e)}")


class AddEventDialog(tk.Toplevel):
    """Dialog for adding or editing an event to a device."""
    
    def __init__(self, parent, device_manager, on_save=None, edit_mode=False, event_name=None, event_data=None, device_name=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.on_save = on_save
        self.edit_mode = edit_mode
        self.original_event_name = event_name
        self.event_data = event_data
        self.original_device_name = device_name
        
        self.title("Edit Event" if edit_mode else "Add Event")
        self.geometry("900x700")
        self.minsize(850, 600)
        self.configure(bg=theme.BG_COLOR)
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Load existing data if in edit mode
        if self.edit_mode and self.event_data:
            self.load_event_data()
        
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        # Configure combobox style
        style = ttk.Style()
        style.map('TCombobox', 
                 fieldbackground=[('readonly', theme.WIDGET_BG)],
                 selectbackground=[('readonly', theme.WIDGET_BG)],
                 selectforeground=[('readonly', theme.FG_COLOR)])
        style.map('TCombobox', 
                 background=[('readonly', theme.WIDGET_BG)])
        
        # Main frame
        main_frame = ttk.Frame(self, style='TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_text = "Edit Event" if self.edit_mode else "Add New Event"
        title_label = ttk.Label(main_frame, text=title_text,
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.SUCCESS_GREEN)
        title_label.pack(pady=(0, 20))
        
        # Device selection
        device_frame = ttk.Frame(main_frame, style='TFrame')
        device_frame.pack(fill=tk.X, pady=5)
        ttk.Label(device_frame, text="Device:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        
        self.device_var = tk.StringVar()
        device_names = list(self.device_manager.get_all_device_names())
        if device_names:
            self.device_var.set(device_names[0])
        
        device_dropdown = ttk.Combobox(device_frame, textvariable=self.device_var,
                                      values=device_names, state='readonly', width=30)
        device_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Event name
        name_frame = ttk.Frame(main_frame, style='TFrame')
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Event Name:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Type
        type_frame = ttk.Frame(main_frame, style='TFrame')
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="Type:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="script_control")
        type_combo = ttk.Combobox(type_frame, textvariable=self.type_var,
                                 values=["script_control", "safety", "status", "error"],
                                 state='readonly', width=20)
        type_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_frame = ttk.Frame(main_frame, style='TFrame')
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="Description:", font=theme.FONT_BOLD).pack(anchor='w')
        self.desc_text = tk.Text(desc_frame, height=3, width=50,
                                bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                insertbackground=theme.FG_COLOR,
                                font=theme.FONT_NORMAL)
        self.desc_text.pack(fill=tk.X, pady=(5, 0))
        
        # Buttons frame (pack first so it stays at bottom)
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.destroy,
                               bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                               font=theme.FONT_NORMAL, relief=tk.FLAT,
                               padx=20, pady=8)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        save_btn = tk.Button(button_frame, text="Save", command=self.save_event,
                            bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                            font=theme.FONT_BOLD, relief=tk.FLAT,
                            padx=20, pady=8)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Parameters section
        params_label_frame = ttk.Frame(main_frame, style='TFrame')
        params_label_frame.pack(fill=tk.X, pady=(15, 5))
        ttk.Label(params_label_frame, text="Parameters:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        add_param_btn = tk.Button(params_label_frame, text="+ Add Parameter",
                                  command=self.add_parameter,
                                  bg=theme.PRIMARY_ACCENT, fg=theme.BG_COLOR,
                                  font=theme.FONT_NORMAL, relief=tk.FLAT,
                                  padx=10, pady=3)
        add_param_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Parameters list frame (scrollable)
        params_canvas_frame = ttk.Frame(main_frame, style='TFrame')
        params_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.params_canvas = tk.Canvas(params_canvas_frame, bg=theme.BG_COLOR,
                                       highlightthickness=0)
        params_scrollbar = ttk.Scrollbar(params_canvas_frame, orient="vertical",
                                        command=self.params_canvas.yview)
        self.params_frame = ttk.Frame(self.params_canvas, style='TFrame')
        
        self.params_frame.bind("<Configure>",
                              lambda e: self.params_canvas.configure(scrollregion=self.params_canvas.bbox("all")))
        
        self.params_canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        self.params_canvas.configure(yscrollcommand=params_scrollbar.set)
        
        self.params_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        params_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mousewheel scrolling (bind only when mouse is over canvas)
        def on_mousewheel(event):
            self.params_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.params_canvas.bind("<Enter>", lambda e: self.params_canvas.bind_all("<MouseWheel>", on_mousewheel))
        self.params_canvas.bind("<Leave>", lambda e: self.params_canvas.unbind_all("<MouseWheel>"))
        
        # Store parameters
        self.parameters = []
    
    def load_event_data(self):
        """Load existing event data into the dialog."""
        if not self.event_data:
            return
        
        # Extract event name
        if self.original_event_name and '.' in self.original_event_name:
            event_name = self.original_event_name.split('.', 1)[1]
        else:
            event_name = self.original_event_name or ''
        
        # Set device
        if self.original_device_name:
            self.device_var.set(self.original_device_name)
        
        # Set event name
        self.name_entry.insert(0, event_name)
        
        # Set type
        event_type = self.event_data.get('type', 'device_event')
        self.type_var.set(event_type)
        
        # Set description
        description = self.event_data.get('description', '')
        if description:
            self.desc_text.insert('1.0', description)
        
        # Load parameters
        params = self.event_data.get('params', [])
        for param in params:
            self.add_parameter(
                param_name=param.get('parameter', ''),
                param_type=param.get('type', 'string'),
                param_desc=param.get('description', '')
            )
    
    def add_parameter(self, param_name='', param_type='string', param_desc=''):
        """Add a parameter entry row."""
        param_row = ttk.Frame(self.params_frame, style='Card.TFrame', padding=5)
        param_row.pack(fill=tk.X, pady=2)
        
        # Parameter name
        ttk.Label(param_row, text="Name:", font=theme.FONT_NORMAL).grid(row=0, column=0, sticky='w', padx=(0, 5))
        name_entry = ttk.Entry(param_row, width=20)
        name_entry.insert(0, param_name)
        name_entry.grid(row=0, column=1, padx=5)
        
        # Type
        ttk.Label(param_row, text="Type:", font=theme.FONT_NORMAL).grid(row=0, column=2, sticky='w', padx=(10, 5))
        type_var = tk.StringVar(value=param_type)
        type_combo = ttk.Combobox(param_row, textvariable=type_var,
                                  values=["string", "int", "float", "bool"],
                                  state='readonly', width=10)
        type_combo.grid(row=0, column=3, padx=5)
        
        # Description
        ttk.Label(param_row, text="Desc:", font=theme.FONT_NORMAL).grid(row=0, column=4, sticky='w', padx=(10, 5))
        desc_entry = ttk.Entry(param_row, width=25)
        desc_entry.insert(0, param_desc)
        desc_entry.grid(row=0, column=5, padx=5)
        
        # Remove button
        remove_btn = tk.Button(param_row, text="✕",
                              bg=theme.ERROR_RED, fg='white',
                              font=theme.FONT_NORMAL, relief=tk.FLAT,
                              padx=5, pady=2)
        remove_btn.grid(row=0, column=6, padx=(10, 0))
        
        # Store parameter data
        param_data = {
            'frame': param_row,
            'name': name_entry,
            'type': type_var,
            'desc': desc_entry
        }
        
        # Remove parameter button
        remove_btn.config(command=lambda f=param_row, pd=param_data: self.remove_parameter(f, pd))
        
        self.parameters.append(param_data)
    
    def remove_parameter(self, frame, param_data):
        """Remove a parameter row."""
        frame.destroy()
        if param_data in self.parameters:
            self.parameters.remove(param_data)
    
    def save_event(self):
        """Save the new event to JSON."""
        from tkinter import messagebox
        import json
        import os
        
        device_name = self.device_var.get()
        event_name = self.name_entry.get().strip()
        event_type = self.type_var.get()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not event_name:
            messagebox.showerror("Error", "Event name is required.")
            return
        
        if not description:
            messagebox.showerror("Error", "Description is required.")
            return
        
        # Build parameters list
        params_list = []
        for param_data in self.parameters:
            param_name = param_data['name'].get().strip()
            param_type = param_data['type'].get()
            param_desc = param_data['desc'].get().strip()
            
            if param_name:  # Only add if name is provided
                param_obj = {
                    "parameter": param_name,
                    "type": param_type
                }
                if param_desc:
                    param_obj["description"] = param_desc
                params_list.append(param_obj)
        
        # Load existing events
        json_path = os.path.join('devices', device_name, 'events.json')
        
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    events_data = json.load(f)
            else:
                events_data = {}
            
            # Handle edit mode vs add mode
            old_event_name = None
            if self.edit_mode:
                # In edit mode, check if name changed and remove old entry
                if self.original_event_name and '.' in self.original_event_name:
                    old_event_name = self.original_event_name.split('.', 1)[1]
                    if old_event_name != event_name and old_event_name in events_data:
                        # Name changed, remove old entry
                        del events_data[old_event_name]
                
                # Check if new name already exists (and it's not the same as old name)
                if event_name in events_data and event_name != old_event_name:
                    messagebox.showerror("Error", f"Event '{event_name}' already exists.")
                    return
            else:
                # Add mode - check if event already exists
                if event_name in events_data:
                    messagebox.showerror("Error", f"Event '{event_name}' already exists.")
                    return
            
            # Create/update event
            events_data[event_name] = {
                "device": device_name,
                "type": event_type,
                "description": description,
                "params": params_list
            }
            
            # Save to file
            with open(json_path, 'w') as f:
                json.dump(events_data, f, indent=4)
            
            action = "updated" if self.edit_mode else "added"
            messagebox.showinfo("Success", f"Event '{event_name}' {action} successfully!")
            
            # Reload and refresh
            self.device_manager.reload_device_modules()
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save event:\n{str(e)}")


class AddDeviceDialog(tk.Toplevel):
    """Dialog for adding or editing a device."""
    
    def __init__(self, parent, device_manager, on_save=None, edit_mode=False, device_name=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.on_save = on_save
        self.edit_mode = edit_mode
        self.original_device_name = device_name
        
        self.title("Edit Device" if edit_mode else "Add New Device")
        self.geometry("650x550")
        self.minsize(600, 500)
        self.configure(bg=theme.BG_COLOR)
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Load existing data if in edit mode
        if self.edit_mode and self.original_device_name:
            self.load_device_data()
        
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self, style='TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_text = "Edit Device" if self.edit_mode else "Add New Device"
        title_label = ttk.Label(main_frame, text=title_text,
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.COMMAND_COLOR)
        title_label.pack(pady=(0, 20))
        
        # Device name
        name_frame = ttk.Frame(main_frame, style='TFrame')
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Device Name:", font=theme.FONT_BOLD).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Copy from existing device (only in add mode)
        if not self.edit_mode:
            copy_frame = ttk.Frame(main_frame, style='TFrame')
            copy_frame.pack(fill=tk.X, pady=10)
            
            self.copy_var = tk.BooleanVar(value=False)
            copy_check = tk.Checkbutton(copy_frame, text="Copy from existing device:",
                                       variable=self.copy_var,
                                       bg=theme.BG_COLOR, fg=theme.FG_COLOR,
                                       font=theme.FONT_NORMAL,
                                       selectcolor=theme.WIDGET_BG,
                                       activebackground=theme.BG_COLOR,
                                       activeforeground=theme.FG_COLOR,
                                       command=self.toggle_copy_device)
            copy_check.pack(side=tk.LEFT)
            
            self.copy_device_var = tk.StringVar()
            device_names = list(self.device_manager.get_all_device_names())
            if device_names:
                self.copy_device_var.set(device_names[0])
            
            self.copy_device_dropdown = ttk.Combobox(copy_frame, textvariable=self.copy_device_var,
                                                     values=device_names, state='disabled', width=20)
            self.copy_device_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_frame = ttk.Frame(main_frame, style='TFrame')
        desc_frame.pack(fill=tk.X, pady=15)
        ttk.Label(desc_frame, text="Description (optional):", font=theme.FONT_BOLD).pack(anchor='w')
        self.desc_text = tk.Text(desc_frame, height=3, width=50,
                                bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                                insertbackground=theme.FG_COLOR,
                                font=theme.FONT_NORMAL)
        self.desc_text.pack(fill=tk.X, pady=(5, 0))
        
        # Info text
        info_label = ttk.Label(main_frame,
                              text="This will create a new device folder with:\n" +
                                   "• commands.json, telemetry.json, events.json\n" +
                                   "• gui.py (template)\n" +
                                   "• generated/ folder (for auto-generated C++ code)",
                              font=theme.FONT_SMALL,
                              foreground=theme.COMMENT_COLOR,
                              justify=tk.LEFT)
        info_label.pack(pady=(20, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.destroy,
                               bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                               font=theme.FONT_NORMAL, relief=tk.FLAT,
                               padx=20, pady=8)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        save_btn = tk.Button(button_frame, text="Save", command=self.save_device,
                            bg=theme.SUCCESS_GREEN, fg=theme.BG_COLOR,
                            font=theme.FONT_BOLD, relief=tk.FLAT,
                            padx=20, pady=8)
        save_btn.pack(side=tk.RIGHT, padx=5)
    
    def load_device_data(self):
        """Load existing device data into the dialog."""
        if not self.original_device_name:
            return
        
        # Set device name
        self.name_entry.insert(0, self.original_device_name)
    
    def toggle_copy_device(self):
        """Enable/disable the copy device dropdown."""
        if hasattr(self, 'copy_device_dropdown'):
            if self.copy_var.get():
                self.copy_device_dropdown.config(state='readonly')
            else:
                self.copy_device_dropdown.config(state='disabled')
    
    def save_device(self):
        """Save the device (create folder and JSON files)."""
        from tkinter import messagebox
        import json
        import os
        
        device_name = self.name_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not device_name:
            messagebox.showerror("Error", "Device name is required.")
            return
        
        # Validate device name (only alphanumeric and underscores)
        if not device_name.replace('_', '').isalnum():
            messagebox.showerror("Error", "Device name can only contain letters, numbers, and underscores.")
            return
        
        try:
            old_device_name = self.original_device_name if self.edit_mode else None
            
            # Handle rename
            if self.edit_mode and old_device_name and old_device_name != device_name:
                old_path = os.path.join('devices', old_device_name)
                new_path = os.path.join('devices', device_name)
                
                if os.path.exists(new_path):
                    messagebox.showerror("Error", f"Device '{device_name}' already exists.")
                    return
                
                # Rename folder
                os.rename(old_path, new_path)
                
                # Update device field in all JSON files
                for json_file in ['commands.json', 'telemetry.json', 'events.json']:
                    json_path = os.path.join(new_path, json_file)
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                        
                        # Update device field in all entries
                        for key in data:
                            if isinstance(data[key], dict) and 'device' in data[key]:
                                data[key]['device'] = device_name
                        
                        with open(json_path, 'w') as f:
                            json.dump(data, f, indent=4)
                
                # After rename, rediscover to pick up the new name
                self.device_manager.discover_devices()
            
            elif not self.edit_mode:
                # Create new device
                device_path = os.path.join('devices', device_name)
                
                if os.path.exists(device_path):
                    messagebox.showerror("Error", f"Device '{device_name}' already exists.")
                    return
                
                # Create device folder
                os.makedirs(device_path, exist_ok=True)
                
                # Create generated/ subfolder for auto-generated code
                gen_path = os.path.join(device_path, 'generated')
                os.makedirs(gen_path, exist_ok=True)
                
                # Check if we should copy from existing device
                should_copy = hasattr(self, 'copy_var') and self.copy_var.get()
                copy_from_device = self.copy_device_var.get() if should_copy else None
                
                if should_copy and copy_from_device:
                    # Copy JSON files from existing device
                    import shutil
                    source_path = os.path.join('devices', copy_from_device)
                    
                    for json_file in ['commands.json', 'telemetry.json', 'events.json']:
                        source_file = os.path.join(source_path, json_file)
                        dest_file = os.path.join(device_path, json_file)
                        
                        if os.path.exists(source_file):
                            # Copy and update device field
                            with open(source_file, 'r') as f:
                                data = json.load(f)
                            
                            # Update device field in all entries
                            for key in data:
                                if isinstance(data[key], dict) and 'device' in data[key]:
                                    data[key]['device'] = device_name
                            
                            with open(dest_file, 'w') as f:
                                json.dump(data, f, indent=4)
                        else:
                            # Create empty file if source doesn't exist
                            with open(dest_file, 'w') as f:
                                json.dump({}, f, indent=4)
                else:
                    # Create empty JSON files
                    for json_file in ['commands.json', 'telemetry.json', 'events.json']:
                        json_path = os.path.join(device_path, json_file)
                        with open(json_path, 'w') as f:
                            json.dump({}, f, indent=4)
                
                # Create __init__.py
                init_path = os.path.join(device_path, '__init__.py')
                with open(init_path, 'w') as f:
                    f.write(f'"""Device module for {device_name}"""\n')
                
                # Create gui.py template with variable display
                gui_path = os.path.join(device_path, 'gui.py')
                
                # Build template with proper formatting
                gui_template = f'''"""
GUI module for {device_name} device.

This module contains device-specific GUI components and panels.
"""

import tkinter as tk
from tkinter import ttk
import theme

def create_device_panel(parent, device_manager):
    """
    Create and return the device-specific control panel.
    
    Args:
        parent: Parent tkinter widget
        device_manager: Reference to the DeviceManager instance
    
    Returns:
        ttk.Frame: The device control panel
    """
    frame = ttk.Frame(parent, style='TFrame', padding=10)
    
    # Title
    title_label = ttk.Label(frame, 
                           text="{device_name.upper()}",
                           font=theme.FONT_LARGE_BOLD,
                           foreground=theme.PRIMARY_ACCENT)
    title_label.pack(pady=(0, 20))
    
    # Variables display
    vars_frame = ttk.Frame(frame, style='Card.TFrame', padding=15)
    vars_frame.pack(fill=tk.BOTH, expand=True)
    
    ttk.Label(vars_frame, text="Variables",
             font=theme.FONT_BOLD,
             foreground=theme.PRIMARY_ACCENT).pack(anchor='w', pady=(0, 10))
    
    # Get device data
    device_data = device_manager.devices.get('{device_name}', {{}})
    telemetry_data = device_data.get('telemetry_data', {{}})
    
    # Display each variable
    for var_name, var_details in sorted(telemetry_data.items()):
        var_frame = ttk.Frame(vars_frame, style='TFrame')
        var_frame.pack(fill='x', pady=2)
        
        # Variable name
        name_label = ttk.Label(var_frame,
                              text=f"{{var_name}}:",
                              font=theme.FONT_SMALL,
                              foreground=theme.COMMENT_COLOR,
                              width=20)
        name_label.pack(side=tk.LEFT)
        
        # Variable value
        var_type = var_details.get('type', 'string')
        unit = var_details.get('unit', '')
        unit_text = f" {{unit}}" if unit else ""
        
        value_label = ttk.Label(var_frame,
                               text=f"--- {{unit_text}}",
                               font=theme.FONT_SMALL,
                               foreground=theme.FG_COLOR)
        value_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # TODO: Connect to actual telemetry updates
    
    # TODO: Add device-specific controls below
    
    return frame
'''
                with open(gui_path, 'w') as f:
                    f.write(gui_template)
            
            action = "updated" if self.edit_mode else "created"
            messagebox.showinfo("Success", f"Device '{device_name}' {action} successfully!")
            
            # Always rediscover devices to pick up new/renamed devices
            self.device_manager.discover_devices()
            
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save device:\n{str(e)}")


def create_command_reference(parent, script_editor_widget, device_manager):
    # This is now a wrapper for the class
    return CommandReference(parent, script_editor_widget, device_manager)

# --- Themed Right-click Menu for Command Reference ---
class ThemedContextMenu(tk.Menu):
    def __init__(self, parent_widget, command_ref_instance, **kwargs):
        super().__init__(parent_widget, tearoff=0, **kwargs)
        self.parent_widget = parent_widget
        self.command_ref = command_ref_instance

        # --- Theming ---
        self.configure(
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            activebackground=theme.PRIMARY_ACCENT,
            activeforeground=theme.SELECTION_FG,
            relief='flat',
            bd=1
        )

        # --- Menu Items ---
        self.add_command(label="Copy", command=self._copy_command)
        self.add_command(label="Add to Script", command=self._add_to_script)
        self.add_separator(background=theme.SECONDARY_ACCENT)
        self.add_command(label="More Info...", command=self._show_more_info)

    def _get_command(self):
        """Gets the command key at the current mouse position."""
        return self.command_ref.get_command_at_cursor()

    def _copy_command(self):
        command = self._get_command()
        if command:
            self.parent_widget.clipboard_clear()
            self.parent_widget.clipboard_append(command)

    def _add_to_script(self):
        command = self._get_command()
        if command:
            self.command_ref.add_to_script_callback(command)
            
    def _show_more_info(self):
        full_command_key = self._get_command()
        if not full_command_key:
            return

        device_name, command_key = full_command_key.split('.', 1)

        # Get command info
        command_info = None
        if device_name == 'script':
            command_info = SCRIPT_COMMANDS.get(command_key)
        else:
            all_commands = self.command_ref.device_manager.get_device_scripting_commands(device_name)
            if all_commands:
                command_info = all_commands.get(command_key)

        if command_info:
            MoreInfoWindow(self.parent_widget, full_command_key, command_info)

    def show(self, event):
        """Updates menu state and displays it."""
        # We need to manually set the CURRENT index for the context menu
        self.parent_widget.mark_set(tk.CURRENT, f"@{event.x},{event.y}")
        
        command = self._get_command()
        if command:
            self.entryconfig("Copy", state=tk.NORMAL)
            self.entryconfig("Add to Script", state=tk.NORMAL)
            self.entryconfig("More Info...", state=tk.NORMAL)
        else:
            self.entryconfig("Copy", state=tk.DISABLED)
            self.entryconfig("Add to Script", state=tk.DISABLED)
            self.entryconfig("More Info...", state=tk.DISABLED)
            
        self.tk_popup(event.x_root, event.y_root)

# --- "More Info" Window ---
class MoreInfoWindow(tk.Toplevel):
    def __init__(self, parent, command_name, command_info):
        super().__init__(parent)
        self.title(f"Info: {command_name}")
        self.configure(bg=theme.WIDGET_BG)
        self.transient(parent)
        self.grab_set()

        # --- UI Elements ---
        text_area = tk.Text(self, wrap=tk.WORD, 
                                bg=theme.WIDGET_BG, 
                                fg=theme.FG_COLOR, 
                                font=theme.FONT_NORMAL,
                                borderwidth=1,
                                highlightthickness=0,
                                padx=15, pady=15,
                                spacing1=3, spacing3=3)
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Configure tags
        text_area.tag_configure("h1", font=theme.FONT_LARGE_BOLD, foreground=theme.PRIMARY_ACCENT)
        text_area.tag_configure("p", font=theme.FONT_NORMAL)
        text_area.tag_configure("param_name", font=theme.FONT_BOLD, foreground=theme.PARAMETER_COLOR)
        text_area.tag_configure("param_details", font=theme.FONT_NORMAL, lmargin1=20, lmargin2=20)
        text_area.tag_configure("code", font=theme.FONT_NORMAL, background=theme.CARD_BG)

        # --- Populate Content ---
        # Description
        text_area.insert(tk.END, "Description\n", "h1")
        description = command_info.get("description", "No description available.")
        text_area.insert(tk.END, f"{description}\n\n", "p")

        # Parameters
        params = command_info.get("params", [])
        if params:
            text_area.insert(tk.END, "Parameters\n", "h1")
            for param in params:
                p_name = param.get("parameter", "N/A")
                p_unit = f" ({param.get('unit')})" if param.get('unit') else ""
                p_desc = param.get("description", "No details provided.")
                p_options = param.get("enum") or param.get("options")
                
                text_area.insert(tk.END, f"{p_name}{p_unit}\n", "param_name")
                text_area.insert(tk.END, f"  {p_desc}\n", "param_details")
                if p_options:
                    options_str = ", ".join([f"'{opt}'" for opt in p_options])
                    text_area.insert(tk.END, f"  Options: {options_str}\n", ("param_details", "code"))
                text_area.insert(tk.END, "\n")

        text_area.config(state=tk.DISABLED)
        
        close_button = ttk.Button(self, text="Close", command=self.destroy, style="Blue.TButton")
        close_button.pack(pady=10)
        
        # Calculate required size based on content
        self.update_idletasks()
        
        # Get number of lines in the text
        num_lines = int(text_area.index('end-1c').split('.')[0])
        
        # Calculate height: line height * num_lines + padding + button
        line_height = 20  # Approximate pixels per line
        height = min(max(num_lines * line_height + 100, 350), int(self.winfo_screenheight() * 0.8))
        width = 650
        
        # Center the window
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
