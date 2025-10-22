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
        
        # Variables Tab
        variables_frame = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(variables_frame, text='Variables')
        
        self.variables_text = self._create_text_widget(variables_frame, 'variables')
        
        # Set the active text widget reference
        self.text = self.commands_text
        
        # Track current tab
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self.refresh() # Initial population

        # Context menus
        self.commands_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        self.commands_context_menu.add_command(label="Copy Command", command=self.copy_command)
        self.commands_context_menu.add_command(label="Add to Script", command=self.add_to_script)
        self.commands_context_menu.add_separator()
        self.commands_context_menu.add_command(label="More Info...", command=self.show_more_info)
        
        self.variables_context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        self.variables_context_menu.add_command(label="Copy Variable", command=self.copy_variable)
        self.variables_context_menu.add_command(label="Add to Script", command=self.add_variable_to_script)
        self.variables_context_menu.add_separator()
        self.variables_context_menu.add_command(label="More Info...", command=self.show_variable_info)

        self.commands_text.bind("<Button-3>", self.show_commands_context_menu)
        self.commands_text.bind("<Double-1>", lambda e: self.add_to_script())
        
        self.variables_text.bind("<Button-3>", self.show_variables_context_menu)
        self.variables_text.bind("<Double-1>", lambda e: self.add_variable_to_script())

        # Initialize tooltips
        self.commands_tooltip = Tooltip(self.commands_text)
        self.variables_tooltip = Tooltip(self.variables_text)
    
    def _create_text_widget(self, parent, widget_type):
        """Create and configure a text widget for commands or variables."""
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
        else:
            # Variables: device.variable = purple.burgundy
            text.tag_configure('variable', foreground='#C04848')  # Burgundy for variable names
            text.tag_configure('params', foreground='#E67373')  # Lighter burgundy/red for type/unit info
        
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
        else:
            self.text = self.variables_text

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
        """Clears and repopulates both text widgets with commands and variables."""
        self.refresh_commands()
        self.refresh_variables()
    
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
        info_window.geometry("600x400")
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
        
        # Center the window
        info_window.update_idletasks()
        window_width = 600
        window_height = 400
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
            
            # Check if this is a command or variable line
            is_item_line = False
            if widget_type == 'commands' and line_num in self.command_lines:
                is_item_line = True
            elif widget_type == 'variables' and line_num in self.variable_lines:
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
        self.geometry("500x350")
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
