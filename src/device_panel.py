import tkinter as tk
from tkinter import ttk
import re
from . import theme
from .script_processor import SCRIPT_COMMANDS
from .comms import devices_lock
from .terminal import log_to_terminal

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

class DevicePanel(ttk.Frame):
    """
    Right-side panel for managing devices, browsing commands/variables/events,
    and controlling device connections and simulators.
    """
    def __init__(self, parent, script_editor_widget, device_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.script_editor_widget = script_editor_widget
        self.device_manager = device_manager
        
        # Map line numbers to their data (legacy name kept for compatibility)
        self.tree_items = {}  # Deprecated: use line_items instead
        
        self.configure(style='TFrame', padding=10)

        # --- Title Section ---
        title_frame = ttk.Frame(self, style='TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 8))
        
        title_label = ttk.Label(title_frame, 
                               text="devices", 
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.PRIMARY_ACCENT,
                               style='TLabel')
        title_label.pack(side=tk.LEFT)
        
        help_label = ttk.Label(title_frame, 
                              text="right-click for options",
                              font=theme.FONT_NORMAL, 
                              foreground=theme.COMMENT_COLOR,
                              style='TLabel')
        help_label.pack(side=tk.RIGHT, anchor='e')
        
        # --- Text Widget (replaces Tree View for syntax highlighting) ---
        tree_frame = ttk.Frame(self, style='TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Scrollbar - will be shown/hidden dynamically based on content
        self.scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        
        # Text widget with syntax highlighting support
        self.text = tk.Text(tree_frame,
                           bg=theme.WIDGET_BG,
                           fg=theme.FG_COLOR,
                           font=theme.FONT_NORMAL,
                           selectbackground=theme.WIDGET_BG,  # Same as background to hide selection
                           selectforeground=theme.FG_COLOR,  # Same as foreground to hide selection
                           borderwidth=0,
                           highlightthickness=0,
                           cursor="arrow",
                           wrap=tk.NONE,
                           yscrollcommand=self._on_text_scroll,
                           insertwidth=0,  # Hide the blinking cursor
                           insertbackground=theme.WIDGET_BG)  # Hide cursor color
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text.yview)
        
        # Make text read-only and prevent text selection
        self.text.bind("<Key>", lambda e: "break")
        self.text.bind("<Control-a>", lambda e: "break")  # Prevent select all
        self.text.bind("<Button1-Motion>", lambda e: "break")  # Prevent drag selection
        
        # Configure syntax highlighting tags
        self.text.tag_configure('device', foreground=theme.DEVICE_COLOR, font=theme.FONT_BOLD)  # Purple for device name
        self.text.tag_configure('device_part', foreground=theme.DEVICE_COLOR)
        self.text.tag_configure('command_part', foreground=theme.COMMAND_COLOR)
        self.text.tag_configure('variable_part', foreground=theme.VARIABLE_COLOR)
        self.text.tag_configure('event_part', foreground=theme.SUCCESS_GREEN)
        self.text.tag_configure('script_command', foreground=theme.SCRIPT_COMMAND_COLOR)
        self.text.tag_configure('script_header', foreground=theme.SCRIPT_COMMAND_COLOR, font=theme.FONT_BOLD)
        self.text.tag_configure('commands_header', foreground=theme.PRIMARY_ACCENT, font=theme.FONT_BOLD)
        self.text.tag_configure('variables_header', foreground=theme.VARIABLE_COLOR, font=theme.FONT_BOLD)
        self.text.tag_configure('events_header', foreground=theme.SUCCESS_GREEN, font=theme.FONT_BOLD)
        self.text.tag_configure('warnings_header', foreground=theme.ERROR_RED, font=theme.FONT_BOLD)
        self.text.tag_configure('warning_part', foreground=theme.ERROR_RED)
        self.text.tag_configure('folder_icon', foreground=theme.COMMENT_COLOR)
        self.text.tag_configure('variable_info', foreground=theme.COMMENT_COLOR)
        self.text.tag_configure('parameter_name', foreground=theme.PARAMETER_COLOR)  # Orange/yellow for parameter names
        self.text.tag_configure('enum_badge', foreground=theme.WARNING_YELLOW)
        self.text.tag_configure('queued_badge', foreground='#61AFEF')  # Blue for queued variables
        self.text.tag_configure('status_icon', foreground=theme.SUCCESS_GREEN)
        self.text.tag_configure('connected_status', foreground=theme.SUCCESS_GREEN)  # Green for connected
        self.text.tag_configure('simulated_status', foreground=theme.WARNING_YELLOW)  # Yellow for [simulated]
        self.text.tag_configure('disconnected_status', foreground=theme.COMMENT_COLOR)  # Grey for disconnected
        self.text.tag_configure('usb_indicator', foreground='#61AFEF')  # Blue for USB connection
        self.text.tag_configure('hover', background=theme.SECONDARY_ACCENT)
        
        # Track which lines map to which items (line_num -> item_data)
        self.line_items = {}  # line_num -> {'type': ..., 'data': ...}
        
        # Track collapsed folders - start with all folders collapsed by default
        self.collapsed_folders = self._get_default_collapsed_folders()
        
        # Track hover line for highlighting
        self.current_hover_line = None
        
        # Add device button at bottom
        add_device_btn = ttk.Button(self,
                                    text="+ Add Device...",
                                    command=self.show_add_device_dialog,
                                    style='Green.TButton',
                                    cursor='hand2')
        add_device_btn.pack(fill=tk.X, pady=(5, 0), padx=10)

        self.refresh() # Initial population

        # Context menus (dynamically built)
        self.context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)

        # Bind text events
        self.text.bind("<Double-1>", self.on_text_double_click)
        self.text.bind("<Button-3>", self.on_text_right_click)
        self.text.bind("<Button-1>", self.on_text_single_click)
        self.text.bind("<Motion>", self.on_text_motion)
        self.text.bind("<Leave>", self.on_text_leave)
    
        # Start auto-refresh for connection status
        # First refresh after 1 second to catch devices connecting during startup
        self.after(1000, self._update_connection_status)
        # Then start periodic refresh every 2 seconds
        self.after(2000, self._schedule_status_refresh)
    
    def _on_text_scroll(self, first, last):
        """Handle scrollbar visibility based on content overflow."""
        first_float = float(first)
        last_float = float(last)
        
        # Show scrollbar only if content exceeds visible area
        if first_float <= 0.0 and last_float >= 1.0:
            # All content is visible, hide scrollbar
            self.scrollbar.pack_forget()
        else:
            # Content overflows, show scrollbar
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update scrollbar position
        self.scrollbar.set(first, last)
    
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
    
    def _schedule_status_refresh(self):
        """Schedule periodic refresh of connection status without full panel refresh."""
        self._update_connection_status()
        # Schedule next refresh in 2 seconds
        self.after(2000, self._schedule_status_refresh)
    
    def _update_connection_status(self):
        """Update only the connection status indicators without refreshing entire panel."""
        try:
            with devices_lock:
                device_states = self.device_manager.get_all_device_states()
                
                # Update each device's status in line_items
                for line_num, item_data in self.line_items.items():
                    if item_data.get('type') == 'device':
                        device_name = item_data.get('name', '')
                        device_state = device_states.get(device_name, {})
                        is_connected = device_state.get('connected', False)
                        is_simulated = device_name in self.device_manager.simulator_threads
                        device_ip = device_state.get('ip', '')
                        
                        # Get current line content
                        line_content = self.text.get(f"{line_num}.0", f"{line_num}.end")
                        
                        # Determine what the status text should be
                        if is_simulated:
                            # [simulated] always comes after connected
                            expected_has_connected = " connected" in line_content
                            expected_has_simulated = " [simulated]" in line_content
                            
                            if not expected_has_connected or not expected_has_simulated:
                                # Need to update: add/update connected and simulated
                                self._replace_status_badge(line_num, line_content, " connected", "connected_status")
                                # Add simulated after connected if not present
                                if " [simulated]" not in line_content:
                                    connected_idx = line_content.find(" connected")
                                    if connected_idx != -1:
                                        # Find end of connected text (might have @ IP)
                                        end_idx = line_content.find(" [simulated]", connected_idx)
                                        if end_idx == -1:
                                            end_idx = line_content.find("\n", connected_idx)
                                            if end_idx == -1:
                                                end_idx = len(line_content)
                                        self.text.insert(f"{line_num}.{end_idx}", " [simulated]", "simulated_status")
                        elif is_connected:
                            # Should have " connected" or " connected @ IP", no [simulated]
                            expected_has_connected = " connected" in line_content
                            expected_has_disconnected = " disconnected" in line_content
                            expected_has_simulated = " [simulated]" in line_content
                            
                            # Build new status text
                            if device_ip:
                                new_status_text = f" connected @ {device_ip}"
                            else:
                                new_status_text = " connected"
                            
                            if expected_has_disconnected or expected_has_simulated or not expected_has_connected:
                                # Need to update
                                # Remove simulated if present
                                if " [simulated]" in line_content:
                                    sim_start = line_content.find(" [simulated]")
                                    self.text.delete(f"{line_num}.{sim_start}", f"{line_num}.{sim_start + 12}")
                                    line_content = self.text.get(f"{line_num}.0", f"{line_num}.end")
                                
                                # Replace disconnected or update connected
                                self._replace_status_badge(line_num, line_content, new_status_text, "connected_status")
                        else:
                            # Should have " disconnected", no connected, no simulated
                            expected_has_disconnected = " disconnected" in line_content
                            expected_has_connected = " connected" in line_content
                            expected_has_simulated = " [simulated]" in line_content
                            
                            if expected_has_connected or expected_has_simulated or not expected_has_disconnected:
                                # Need to update
                                # Remove simulated if present
                                if " [simulated]" in line_content:
                                    sim_start = line_content.find(" [simulated]")
                                    self.text.delete(f"{line_num}.{sim_start}", f"{line_num}.{sim_start + 12}")
                                    line_content = self.text.get(f"{line_num}.0", f"{line_num}.end")
                                
                                # Replace connected or update disconnected
                                self._replace_status_badge(line_num, line_content, " disconnected", "disconnected_status")
        except Exception as e:
            # Silently ignore errors during status update to prevent GUI crashes
            print(f"[CommandReference] Status update error: {e}")
    
    def _replace_status_badge(self, line_num, line_content, new_status_text, new_tag):
        """Helper to replace status badge text on a line."""
        # Find and replace connected/disconnected status
        # Try " connected @" first (longer match), then " connected", then " disconnected"
        for old_text in [" connected @", " connected", " disconnected"]:
            if old_text in line_content:
                start_idx = line_content.find(old_text)
                # Find end - either [simulated], newline, or end of line
                # For " connected @", we need to include the IP address (everything after @ until space/newline/[simulated])
                if old_text == " connected @":
                    # Find @ position
                    at_idx = line_content.find("@", start_idx)
                    if at_idx != -1:
                        # Find first space, newline, or [simulated] after @
                        end_idx = line_content.find(" [simulated]", at_idx)
                        if end_idx == -1:
                            end_idx = line_content.find("\n", at_idx)
                            if end_idx == -1:
                                end_idx = len(line_content)
                    else:
                        # Fallback if @ not found
                        end_idx = line_content.find("\n", start_idx)
                        if end_idx == -1:
                            end_idx = len(line_content)
                else:
                    # For " connected" or " disconnected", end at [simulated], newline, or end
                    end_idx = line_content.find(" [simulated]", start_idx)
                    if end_idx == -1:
                        end_idx = line_content.find("\n", start_idx)
                        if end_idx == -1:
                            end_idx = len(line_content)
                
                # Delete old and insert new
                self.text.delete(f"{line_num}.{start_idx}", f"{line_num}.{end_idx}")
                self.text.insert(f"{line_num}.{start_idx}", new_status_text, new_tag)
                return
    
    def refresh(self):
        """Clears and repopulates the text widget with all devices and their items."""
        # Clear text
        self.text.delete(1.0, tk.END)
        self.tree_items.clear()
        self.line_items.clear()
        
        line_num = 1
        
        # Add script commands section
        script_cmds = self.device_manager.get_all_scripting_commands()
        script_only = {name: details for name, details in script_cmds.items() 
                      if '.' not in name}  # Only non-device commands
        
        if script_only:
            folder_key = ('', 'script_folder')
            is_collapsed = folder_key in self.collapsed_folders
            icon = "► " if is_collapsed else "▼ "
            
            self.text.insert(f"{line_num}.0", icon, "folder_icon")
            self.text.insert(f"{line_num}.end", f"script functions ({len(script_only)})\n", "script_header")
            self.line_items[line_num] = {'type': 'script_folder', 'line_start': line_num, 'device': '', 'name': ''}
            line_num += 1
            
            if not is_collapsed:
                for cmd_name, cmd_details in sorted(script_only.items()):
                    # Command name
                    self.text.insert(f"{line_num}.0", "    ", "folder_icon")
                    self.text.insert(f"{line_num}.end", f"{cmd_name}", "script_command")
                    
                    # Add parameter info with syntax highlighting
                    params = cmd_details.get('params', [])
                    if params:
                        for i, param in enumerate(params):
                            param_name = param.get('parameter', '')
                            unit = param.get('unit', '')
                            optional = param.get('optional', False)
                            variadic = param.get('variadic', False)
                            
                            # Add space before parameter
                            self.text.insert(f"{line_num}.end", " ", "folder_icon")
                            
                            # Determine if we should suppress optional brackets for specific params
                            suppress_optional_brackets = (
                                (cmd_name == 'start_logging' and param_name == 'frequency') or
                                (cmd_name == 'wait_for' and param_name == 'timeout')
                            )

                            # Add brackets for optional parameters (unless suppressed)
                            if optional and not suppress_optional_brackets:
                                self.text.insert(f"{line_num}.end", "[", "variable_info")

                            # Add parameter name in orange/yellow (with special formatting for certain commands)
                            param_display = param_name
                            if param_name == 'filename' and cmd_name in ('start_logging', 'stop_logging'):
                                param_display = f'"{param_name}"'
                            self.text.insert(f"{line_num}.end", param_display, "parameter_name")
                            
                            # Add ... for variadic parameters
                            if variadic:
                                self.text.insert(f"{line_num}.end", "...", "parameter_name")
                            
                            # Add unit in grey if present
                            if unit:
                                self.text.insert(f"{line_num}.end", f"({unit})", "variable_info")
                            
                            # Close brackets for optional parameters
                            if optional and not suppress_optional_brackets:
                                self.text.insert(f"{line_num}.end", "]", "variable_info")
                    
                    self.text.insert(f"{line_num}.end", "\n")
                    self.line_items[line_num] = {
                        'type': 'script_command',
                        'name': cmd_name,
                        'data': cmd_details
                    }
                    line_num += 1
            
            # Add blank line after script commands section
            self.text.insert(f"{line_num}.0", "\n")
            line_num += 1
        
        # Get all devices
        device_names = sorted(self.device_manager.get_all_device_names())
        
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            
            for device_name in device_names:
                device_data = self.device_manager.devices.get(device_name, {})
                device_state = device_states.get(device_name, {})
                is_connected = device_state.get('connected', False)
                # Check if device is simulated
                is_simulated = device_state.get('simulated', False)
                
                # Create device node with collapse icon
                device_folder_key = (device_name, 'device')
                device_collapsed = device_folder_key in self.collapsed_folders
                device_icon = "► " if device_collapsed else "▼ "
                
                # Build device line with connection status
                self.text.insert(f"{line_num}.0", device_icon, "folder_icon")
                self.text.insert(f"{line_num}.end", f"{device_name}", "device")
                
                # Get connection method
                connection_method = device_state.get('connection_method', 'network')
                
                # Add connection status with IP address or COM port
                if is_connected or is_simulated:
                    if connection_method == 'usb':
                        serial_port = device_state.get('serial_port', 'USB')
                        self.text.insert(f"{line_num}.end", f" connected @ {serial_port}", "connected_status")
                    elif connection_method == 'network':
                        device_ip = device_state.get('ip', '')
                        if device_ip:
                            self.text.insert(f"{line_num}.end", f" connected @ {device_ip}", "connected_status")
                        else:
                            self.text.insert(f"{line_num}.end", " connected", "connected_status")
                    else:
                        self.text.insert(f"{line_num}.end", " connected", "connected_status")
                    if is_simulated:
                        self.text.insert(f"{line_num}.end", " [simulated]", "simulated_status")
                else:
                    self.text.insert(f"{line_num}.end", " disconnected", "disconnected_status")
                
                self.text.insert(f"{line_num}.end", "\n")
                self.line_items[line_num] = {'type': 'device', 'name': device_name, 'device': device_name}
                line_num += 1
                
                # Skip children if device is collapsed
                if device_collapsed:
                    continue
                
                # Commands folder
                commands = device_data.get('scripting_commands', {})
                cmds_folder_key = (device_name, 'commands_folder')
                cmds_collapsed = cmds_folder_key in self.collapsed_folders
                cmds_icon = "  ► " if cmds_collapsed else "  ▼ "
                
                self.text.insert(f"{line_num}.0", cmds_icon, "folder_icon")
                self.text.insert(f"{line_num}.end", f"commands ({len(commands)})\n", "commands_header")
                self.line_items[line_num] = {'type': 'commands_folder', 'device': device_name, 'line_start': line_num}
                line_num += 1
                
                # Add individual commands if not collapsed
                if not cmds_collapsed:
                    for cmd_name, cmd_details in sorted(commands.items()):
                        self.text.insert(f"{line_num}.0", "      ", "folder_icon")
                        self.text.insert(f"{line_num}.end", f"{device_name}", "device_part")
                        self.text.insert(f"{line_num}.end", ".", "folder_icon")
                        self.text.insert(f"{line_num}.end", f"{cmd_name}", "command_part")
                        
                        # Add parameter info with syntax highlighting
                        params = cmd_details.get('params', [])
                        if params:
                            for i, param in enumerate(params):
                                param_name = param.get('parameter', '')
                                unit = param.get('unit', '')
                                
                                # Add space before parameter
                                self.text.insert(f"{line_num}.end", " ", "folder_icon")
                                
                                # Add parameter name in orange/yellow
                                self.text.insert(f"{line_num}.end", param_name, "parameter_name")
                                
                                # Add unit in grey if present
                                if unit:
                                    self.text.insert(f"{line_num}.end", f"({unit})", "variable_info")
                        
                        self.text.insert(f"{line_num}.end", "\n")
                        full_name = f"{device_name}.{cmd_name}"
                        self.line_items[line_num] = {
                            'type': 'command',
                            'name': full_name,
                            'data': cmd_details
                        }
                        line_num += 1
                
                # Variables folder
                variables = device_data.get('telemetry_data', {})
                vars_folder_key = (device_name, 'variables_folder')
                vars_collapsed = vars_folder_key in self.collapsed_folders
                vars_icon = "  ► " if vars_collapsed else "  ▼ "
                
                self.text.insert(f"{line_num}.0", vars_icon, "folder_icon")
                self.text.insert(f"{line_num}.end", f"variables ({len(variables)})\n", "variables_header")
                self.line_items[line_num] = {'type': 'variables_folder', 'device': device_name, 'line_start': line_num}
                line_num += 1
                
                # Add individual variables if not collapsed
                if not vars_collapsed:
                    # Get data logger to check if variables are being logged
                    data_logger = self.device_manager.shared_gui_refs.get('data_logger')
                    
                    for var_name, var_details in sorted(variables.items()):
                        self.text.insert(f"{line_num}.0", "      ", "folder_icon")
                        self.text.insert(f"{line_num}.end", f"{device_name}", "device_part")
                        self.text.insert(f"{line_num}.end", ".", "folder_icon")
                        
                        var_type = var_details.get('type', '')
                        unit = var_details.get('unit', '')
                        type_text = f" ({var_type})" if var_type else ""
                        unit_text = f" {unit}" if unit else ""
                        enum_badge = " [enum]" if var_details.get('map') else ""
                        
                        self.text.insert(f"{line_num}.end", f"{var_name}", "variable_part")
                        if type_text or unit_text:
                            self.text.insert(f"{line_num}.end", type_text + unit_text, "variable_info")
                        if enum_badge:
                            self.text.insert(f"{line_num}.end", enum_badge, "enum_badge")
                        
                        # Add [queued] indicator if this variable is queued for logging
                        if data_logger and data_logger.is_variable_queued(device_name, var_name):
                            self.text.insert(f"{line_num}.end", " [queued]", "queued_badge")
                        
                        # Add [logging] indicator if this variable is being logged
                        if data_logger and data_logger.is_variable_being_logged(device_name, var_name):
                            self.text.insert(f"{line_num}.end", " [logging]", "enum_badge")
                        
                        self.text.insert(f"{line_num}.end", "\n")
                        
                        full_var_name = f"{device_name}.{var_name}"
                        self.line_items[line_num] = {
                            'type': 'variable',
                            'device': device_name,
                            'name': var_name,
                            'data': var_details
                        }
                        line_num += 1
                
                # Events folder
                events = device_data.get('events_data', {})
                events_folder_key = (device_name, 'events_folder')
                events_collapsed = events_folder_key in self.collapsed_folders
                events_icon = "  ► " if events_collapsed else "  ▼ "
                
                self.text.insert(f"{line_num}.0", events_icon, "folder_icon")
                self.text.insert(f"{line_num}.end", f"events ({len(events)})\n", "events_header")
                self.line_items[line_num] = {'type': 'events_folder', 'device': device_name, 'line_start': line_num}
                line_num += 1
                
                # Add individual events if not collapsed
                if not events_collapsed:
                    for event_name, event_details in sorted(events.items()):
                        # Ensure event has device prefix
                        if '.' not in event_name:
                            full_event_name = f"{device_name}.{event_name}"
                        else:
                            full_event_name = event_name
                        
                        self.text.insert(f"{line_num}.0", "      ", "folder_icon")
                        if '.' in full_event_name:
                            parts = full_event_name.split('.', 1)
                            self.text.insert(f"{line_num}.end", parts[0], "device_part")
                            self.text.insert(f"{line_num}.end", ".", "folder_icon")
                            self.text.insert(f"{line_num}.end", f"{parts[1]}", "event_part")
                        else:
                            self.text.insert(f"{line_num}.end", f"{full_event_name}", "event_part")
                        
                        # Add parameter info with syntax highlighting
                        params = event_details.get('params', [])
                        if params:
                            for i, param in enumerate(params):
                                param_name = param.get('parameter', '')
                                unit = param.get('unit', '')
                                
                                # Add space before parameter
                                self.text.insert(f"{line_num}.end", " ", "folder_icon")
                                
                                # Add parameter name in orange/yellow
                                self.text.insert(f"{line_num}.end", param_name, "parameter_name")
                                
                                # Add unit in grey if present
                                if unit:
                                    self.text.insert(f"{line_num}.end", f"({unit})", "variable_info")
                        
                        self.text.insert(f"{line_num}.end", "\n")
                        
                        self.line_items[line_num] = {
                            'type': 'event',
                            'name': full_event_name,
                            'data': event_details
                        }
                        line_num += 1
                
                # Warnings folder
                warnings = device_data.get('warnings', {})
                warnings_folder_key = (device_name, 'warnings_folder')
                warnings_collapsed = warnings_folder_key in self.collapsed_folders
                warnings_icon = "  ► " if warnings_collapsed else "  ▼ "
                
                self.text.insert(f"{line_num}.0", warnings_icon, "folder_icon")
                self.text.insert(f"{line_num}.end", f"warnings ({len(warnings)})\n", "warnings_header")
                self.line_items[line_num] = {'type': 'warnings_folder', 'device': device_name, 'line_start': line_num}
                line_num += 1
                
                # Add individual warnings if not collapsed
                if not warnings_collapsed:
                    for warning_name, warning_details in sorted(warnings.items()):
                        # Ensure warning has device prefix
                        if '.' not in warning_name:
                            full_warning_name = f"{device_name}.{warning_name}"
                        else:
                            full_warning_name = warning_name
                        
                        self.text.insert(f"{line_num}.0", "      ", "folder_icon")
                        if '.' in full_warning_name:
                            parts = full_warning_name.split('.', 1)
                            self.text.insert(f"{line_num}.end", parts[0], "device_part")
                            self.text.insert(f"{line_num}.end", ".", "folder_icon")
                            self.text.insert(f"{line_num}.end", f"{parts[1]}", "warning_part")
                        else:
                            self.text.insert(f"{line_num}.end", f"{full_warning_name}", "warning_part")
                        
                        # Add description info
                        description = warning_details.get('description', '')
                        if description:
                            self.text.insert(f"{line_num}.end", f" - {description}", "variable_info")
                        
                        self.text.insert(f"{line_num}.end", "\n")
                        
                        self.line_items[line_num] = {
                            'type': 'warning',
                            'name': full_warning_name,
                            'data': warning_details
                        }
                        line_num += 1
    
    def _get_default_collapsed_folders(self):
        """Get the default set of collapsed folders (all folders except Script Commands)."""
        collapsed = set()
        device_names = self.device_manager.get_all_device_names()
        
        # Collapse all device folders
        for device_name in device_names:
            collapsed.add((device_name, 'device'))
            collapsed.add((device_name, 'commands_folder'))
            collapsed.add((device_name, 'variables_folder'))
            collapsed.add((device_name, 'events_folder'))
            collapsed.add((device_name, 'warnings_folder'))
        
        # Keep script commands expanded by default
        # collapsed.add(('', 'script_folder'))
        
        return collapsed
    
    def _get_line_at_position(self, event):
        """Get the line number at the click position."""
        index = self.text.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        return line_num
    
    def on_text_motion(self, event):
        """Handle mouse motion over text for hover highlighting."""
        line_num = self._get_line_at_position(event)
        item_data = self.line_items.get(line_num, {})
        
        # Only highlight if it's an actual item (not empty or folder header in some cases)
        is_item = item_data.get('type') in ['command', 'variable', 'event', 'warning', 'device', 
                                             'commands_folder', 'variables_folder', 
                                             'events_folder', 'warnings_folder', 'script_folder', 'script_command']
        
        if is_item and line_num != self.current_hover_line:
            # Remove previous hover
            if self.current_hover_line:
                self.text.tag_remove('hover', f"{self.current_hover_line}.0", f"{self.current_hover_line}.end")
            
            # Add new hover
            self.text.tag_add('hover', f"{line_num}.0", f"{line_num}.end")
            self.current_hover_line = line_num
        elif not is_item and self.current_hover_line:
            # Clear hover if over non-item
            self.text.tag_remove('hover', f"{self.current_hover_line}.0", f"{self.current_hover_line}.end")
            self.current_hover_line = None
    
    def on_text_leave(self, event):
        """Handle mouse leaving the text widget."""
        if self.current_hover_line:
            self.text.tag_remove('hover', f"{self.current_hover_line}.0", f"{self.current_hover_line}.end")
            self.current_hover_line = None
    
    def on_text_single_click(self, event):
        """Handle single click on text (for folder toggle)."""
        line_num = self._get_line_at_position(event)
        item_data = self.line_items.get(line_num, {})
        item_type = item_data.get('type')
        
        # Clear any text selection
        self.text.tag_remove(tk.SEL, "1.0", tk.END)
        
        # Toggle folder collapse/expand
        if item_type in ['commands_folder', 'variables_folder', 'events_folder', 'warnings_folder', 'script_folder', 'device']:
            # Use device name + type as stable key (not line number which changes)
            folder_key = (item_data.get('device', item_data.get('name', '')), item_type)
            if folder_key in self.collapsed_folders:
                self.collapsed_folders.remove(folder_key)
            else:
                self.collapsed_folders.add(folder_key)
            self.refresh()
        
        return "break"  # Prevent text selection and cursor placement
    
    def on_text_double_click(self, event):
        """Handle double-click on text items."""
        line_num = self._get_line_at_position(event)
        item_data = self.line_items.get(line_num, {})
        item_type = item_data.get('type')
        
        # Clear any text selection
        self.text.tag_remove(tk.SEL, "1.0", tk.END)
        
        # Commands: add to script
        if item_type == 'command':
            command_name = item_data.get('name')
            if command_name:
                self.script_editor_widget.insert(tk.INSERT, f"{command_name} ")
        
        # Script commands: add to script
        elif item_type == 'script_command':
            command_name = item_data.get('name')
            if command_name:
                self.script_editor_widget.insert(tk.INSERT, f"{command_name} ")
        
        # Variables: add to script
        elif item_type == 'variable':
            device_name = item_data.get('device')
            var_name = item_data.get('name')
            if device_name and var_name:
                self.script_editor_widget.insert(tk.INSERT, f"{device_name}.{var_name} ")
        
        # Events: add to script
        elif item_type == 'event':
            event_name = item_data.get('name')
            if event_name:
                self.script_editor_widget.insert(tk.INSERT, f"WAIT_FOR {event_name}\n")
        
        # Folders: toggle open/close
        elif item_type in ['commands_folder', 'variables_folder', 'events_folder', 'warnings_folder', 'script_folder', 'device']:
            # Use device name + type as stable key (not line number which changes)
            folder_key = (item_data.get('device', item_data.get('name', '')), item_type)
            if folder_key in self.collapsed_folders:
                self.collapsed_folders.remove(folder_key)
            else:
                self.collapsed_folders.add(folder_key)
            self.refresh()
        
        return "break"  # Prevent text selection
    
    def on_text_right_click(self, event):
        """Handle right-click on text items."""
        # Get line at click position
        line_num = self._get_line_at_position(event)
        item_data = self.line_items.get(line_num, {})
        item_type = item_data.get('type')
        
        # Set cursor to clicked line for selection methods to work
        self.text.mark_set(tk.INSERT, f"{line_num}.0")
        
        # Don't show visible selection highlight
        self.text.tag_remove(tk.SEL, 1.0, tk.END)
        
        # Build context menu dynamically based on item type
        self.context_menu.delete(0, tk.END)
        
        if item_type == 'device':
            # Get device simulation state
            device_name = item_data.get('name', '')
            is_simulated = device_name in self.device_manager.simulator_threads
            
            # Get connection method
            connection_method = self.device_manager.get_connection_method(device_name)
            
            # Get logging info
            data_logger = self.device_manager.shared_gui_refs.get('data_logger')
            queued_vars = data_logger.get_queued_variables(device_name) if data_logger else []
            has_active_logs = False
            if data_logger:
                for filepath, log_info in data_logger.get_active_logs().items():
                    if device_name in log_info['devices']:
                        has_active_logs = True
                        break
            
            # Add connection method submenu
            connection_submenu = tk.Menu(self.context_menu, tearoff=0,
                                        bg=theme.WIDGET_BG,
                                        fg=theme.FG_COLOR,
                                        activebackground=theme.PRIMARY_ACCENT,
                                        activeforeground=theme.FG_COLOR)
            
            # Network connection option
            connection_submenu.add_radiobutton(
                label="Network (UDP)",
                command=lambda: self.set_connection_network(device_name),
                variable=tk.StringVar(value=connection_method),
                value='network'
            )
            
            # USB connection option with port selection
            usb_submenu = tk.Menu(connection_submenu, tearoff=0,
                                 bg=theme.WIDGET_BG,
                                 fg=theme.FG_COLOR,
                                 activebackground=theme.PRIMARY_ACCENT,
                                 activeforeground=theme.FG_COLOR)
            
            # List available serial ports
            from . import serial_comms
            ports = serial_comms.list_serial_ports()
            if ports:
                for port, description in ports:
                    usb_submenu.add_command(
                        label=f"{port} - {description}",
                        command=lambda p=port, d=device_name: self.set_connection_usb(d, p)
                    )
            else:
                usb_submenu.add_command(label="No serial ports found", state='disabled')
            
            connection_submenu.add_cascade(label="USB Serial", menu=usb_submenu)
            
            # Add the connection submenu
            self.context_menu.add_cascade(label=f"Connection [{connection_method.upper()}]", menu=connection_submenu)
            
            self.context_menu.add_separator()
            
            # Add simulate/stop simulate option
            if is_simulated:
                self.context_menu.add_command(label="Stop Simulate", command=lambda: self.stop_simulate_device(device_name))
            else:
                # Create simulate submenu
                simulate_submenu = tk.Menu(self.context_menu, tearoff=0,
                                          bg=theme.WIDGET_BG,
                                          fg=theme.FG_COLOR,
                                          activebackground=theme.PRIMARY_ACCENT,
                                          activeforeground=theme.FG_COLOR)
                
                simulate_submenu.add_command(
                    label="Local Network (127.0.0.1)",
                    command=lambda: self.start_simulate_device(device_name, connection_type='network')
                )
                
                simulate_submenu.add_command(
                    label="USB Serial (Virtual)",
                    command=lambda: self.start_simulate_device(device_name, connection_type='usb')
                )
                
                self.context_menu.add_cascade(label="Start Simulate", menu=simulate_submenu)
            
            self.context_menu.add_separator()
            
            # Add logging options
            if queued_vars:
                self.context_menu.add_command(
                    label=f"Start Logging ({len(queued_vars)} queued vars)...",
                    command=lambda: self.start_logging_queued_device(device_name)
                )
            
            if has_active_logs:
                self.context_menu.add_command(
                    label="Stop All Logging for Device",
                    command=lambda: self.stop_logging_device(device_name)
                )
            
            if queued_vars or has_active_logs:
                self.context_menu.add_separator()
            
            self.context_menu.add_command(label="Refresh Device", command=lambda: self.refresh_device(device_name))
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Edit Device...", command=self.edit_device)
            self.context_menu.add_command(label="More Info...", command=self.show_device_info)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Remove Device", command=self.remove_device,
                                         foreground=theme.ERROR_RED)
        
        elif item_type == 'command' or item_type == 'script_command':
            command_name = item_data.get('name', '')
            script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE',
                             'wait', 'math', 'wait_for', 'comment', 'cycle',
                             'queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
            is_script_command = command_name in script_commands or command_name.startswith('script.') or item_type == 'script_command'
            
            self.context_menu.add_command(label="Copy Command", command=self.copy_command)
            self.context_menu.add_command(label="Add to Script", command=self.add_to_script)
            self.context_menu.add_separator()
            
            if not is_script_command:
                self.context_menu.add_command(label="Edit Command...", command=self.edit_command)
            
            self.context_menu.add_command(label="More Info...", command=self.show_more_info)
            
            if not is_script_command:
                self.context_menu.add_separator()
                self.context_menu.add_command(label="Delete Command", command=self.delete_command,
                                             foreground=theme.ERROR_RED)
        
        elif item_type == 'variable':
            device_name = item_data.get('device', '')
            var_name = item_data.get('name', '')
            
            # Check if variable is currently being logged or queued
            data_logger = self.device_manager.shared_gui_refs.get('data_logger')
            is_logging = data_logger.is_variable_being_logged(device_name, var_name) if data_logger else False
            is_queued = data_logger.is_variable_queued(device_name, var_name) if data_logger else False
            
            self.context_menu.add_command(label="Copy Variable", command=self.copy_variable)
            self.context_menu.add_command(label="Add to Script", command=self.add_variable_to_script)
            self.context_menu.add_separator()
            
            # Add queue/unqueue option
            if is_queued:
                self.context_menu.add_command(
                    label="Unqueue from Logging",
                    command=lambda: self.unqueue_variable(device_name, var_name)
                )
            else:
                self.context_menu.add_command(
                    label="Queue for Logging",
                    command=lambda: self.queue_variable(device_name, var_name)
                )
            
            # Add logging status if actively logging
            if is_logging:
                log_files = data_logger.get_logs_for_variable(device_name, var_name) if data_logger else []
                log_files_str = ", ".join(log_files) if log_files else "multiple files"
                self.context_menu.add_command(
                    label=f"Currently Logging ({log_files_str})",
                    state='disabled'
                )
            
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Edit Variable...", command=self.edit_variable)
            self.context_menu.add_command(label="More Info...", command=self.show_variable_info)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Delete Variable", command=self.delete_variable,
                                         foreground=theme.ERROR_RED)
        
        elif item_type == 'event':
            self.context_menu.add_command(label="Copy Event", command=self.copy_event)
            self.context_menu.add_command(label="Add to Script", command=self.add_event_to_script)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Edit Event...", command=self.edit_event)
            self.context_menu.add_command(label="More Info...", command=self.show_event_info)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Delete Event", command=self.delete_event,
                                         foreground=theme.ERROR_RED)
        
        elif item_type == 'commands_folder':
            device_name = item_data.get('device')
            self.context_menu.add_command(label="Add Command...", 
                                         command=lambda: self.show_add_command_dialog_for_device(device_name))
        
        elif item_type == 'variables_folder':
            device_name = item_data.get('device')
            self.context_menu.add_command(label="Add Variable...", 
                                         command=lambda: self.show_add_variable_dialog_for_device(device_name))
        
        elif item_type == 'events_folder':
            device_name = item_data.get('device')
            self.context_menu.add_command(label="Add Event...", 
                                         command=lambda: self.show_add_event_dialog_for_device(device_name))
        
        elif item_type == 'warnings_folder':
            device_name = item_data.get('device')
            self.context_menu.add_command(label="Add Warning...", 
                                         command=lambda: self.show_add_warning_dialog_for_device(device_name))
        
        elif item_type == 'warning':
            self.context_menu.add_command(label="Copy Warning", command=self.copy_warning)
            self.context_menu.add_command(label="Add to Script (throw)", command=self.add_warning_to_script)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Edit Warning...", command=self.edit_warning)
            self.context_menu.add_command(label="More Info...", command=self.show_warning_info)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Delete Warning", command=self.delete_warning,
                                         foreground=theme.ERROR_RED)
        
        # Show menu
        if self.context_menu.index('end') is not None:  # If menu has items
            self.context_menu.post(event.x_root, event.y_root)
    
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
        from .script_processor import SCRIPT_COMMANDS
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
                                # For start_logging and stop_logging, add quotes around filename parameter
                                param_display = param_name
                                if cmd in ['start_logging', 'stop_logging'] and param_name == 'filename':
                                    param_display = f'"{param_name}"'
                                
                                param_start_col = int(self.commands_text.index(f'{line_num}.end').split('.')[1])
                                self.commands_text.insert(tk.END, param_display)
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

    def _get_selected_line_num(self):
        """Get the currently selected line number from text widget."""
        try:
            # Try to get the selection first
            try:
                sel_start = self.text.index(tk.SEL_FIRST)
                line_num = int(sel_start.split('.')[0])
                return line_num
            except tk.TclError:
                # If no selection, try cursor position
                try:
                    sel_start = self.text.index(tk.INSERT)
                    line_num = int(sel_start.split('.')[0])
                    return line_num
                except:
                    return None
        except (ValueError, AttributeError):
            return None
    
    def get_selected_command(self):
        """Get command from selected text line."""
        line_num = self._get_selected_line_num()
        if not line_num:
            return None
        
        item_data = self.line_items.get(line_num, {})
        
        if item_data.get('type') in ['command', 'script_command']:
            return item_data.get('name')
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
        """Get variable from selected text line."""
        line_num = self._get_selected_line_num()
        if not line_num:
            return None
        
        item_data = self.line_items.get(line_num, {})
        
        if item_data.get('type') == 'variable':
            device_name = item_data.get('device')
            var_name = item_data.get('name')
            var_data = item_data.get('data')
            return (device_name, var_name, var_data)
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
    
    def queue_variable(self, device_name, var_name):
        """Queue a variable for logging."""
        data_logger = self.device_manager.shared_gui_refs.get('data_logger')
        if data_logger:
            data_logger.queue_variable(device_name, var_name)
            self.refresh()  # Refresh to show queued indicator
    
    def unqueue_variable(self, device_name, var_name):
        """Remove a variable from the logging queue."""
        data_logger = self.device_manager.shared_gui_refs.get('data_logger')
        if data_logger:
            data_logger.unqueue_variable(device_name, var_name)
            self.refresh()  # Refresh to remove queued indicator
    
    def start_logging_queued_device(self, device_name):
        """Start logging all queued variables for a device."""
        from tkinter import simpledialog, messagebox
        
        print(f"[TRACE] start_logging_queued_device called for {device_name}")
        
        # Check if device is connected
        device_state = self.device_manager.get_device_state(device_name)
        print(f"[TRACE] Device state: {device_state}")
        if not device_state or not device_state.get('connected'):
            print(f"[TRACE] Device not connected, showing error")
            messagebox.showerror(
                "Device Not Connected",
                f"Cannot start logging for {device_name}.\n\nThe device is not connected.\n\nPlease connect the device or start its simulator first."
            )
            return
        
        print(f"[TRACE] Getting data logger")
        # Get data logger
        data_logger = self.device_manager.shared_gui_refs.get('data_logger')
        if not data_logger:
            messagebox.showerror("Error", "Data logger not available")
            return
        
        print(f"[TRACE] Getting queued variables")
        # Check if there are queued variables
        queued = data_logger.get_queued_variables(device_name)
        print(f"[TRACE] Queued: {queued}")
        if not queued:
            messagebox.showinfo("Info", f"No variables queued for {device_name}")
            return
        
        print(f"[TRACE] Prompting for filename")
        # Prompt for filename
        filename = simpledialog.askstring(
            "Start Logging",
            f"Enter filename for logging {len(queued)} variable(s) from {device_name}:\n(Leave empty for auto-generated name)",
            initialvalue=""
        )
        print(f"[TRACE] User entered filename: {filename}")
        
        if filename is None:  # User cancelled
            print(f"[TRACE] User cancelled")
            return
        
        # If empty, set to None for auto-generation
        if not filename.strip():
            filename = None
        
        print(f"[TRACE] Calling start_logging_queued")
        # Start logging
        try:
            success, message, actual_filename = data_logger.start_logging_queued(device_name, filename)
            print(f"[TRACE] start_logging_queued returned: success={success}, message={message}")
            
            if success:
                messagebox.showinfo("Logging Started", message)
                print(f"[TRACE] Scheduling refresh")
                # Schedule refresh on main thread after dialog closes
                self.text.after(100, self.refresh)
                print(f"[TRACE] Refresh scheduled")
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            print(f"[TRACE] Exception caught: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to start logging: {e}")
    
    def stop_logging_device(self, device_name):
        """Stop all logging for a device."""
        from tkinter import messagebox
        
        # Get data logger
        data_logger = self.device_manager.shared_gui_refs.get('data_logger')
        if not data_logger:
            messagebox.showerror("Error", "Data logger not available")
            return
        
        # Stop logging
        success, message = data_logger.stop_logging_device(device_name)
        
        if success:
            messagebox.showinfo("Logging Stopped", message)
            self.refresh()  # Refresh to remove logging indicator
        else:
            messagebox.showerror("Error", message)
    
    def show_commands_context_menu(self, event):
        # Set cursor to click position
        self.commands_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        command = self.get_selected_command()
        if command:
            # Clear the menu and rebuild it
            self.commands_context_menu.delete(0, tk.END)
            
            # Check if it's a script command (case-insensitive)
            script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE', 
                             'wait', 'math', 'wait_for', 'comment', 'cycle',
                             'queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
            is_script_command = command in script_commands or command.startswith('script.')
            
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
        all_commands = self.device_manager.get_all_scripting_commands()
        cmd_details = all_commands.get(command)
        
        # If not found, check SCRIPT_COMMANDS directly (for script-only commands)
        if not cmd_details:
            from .script_processor import SCRIPT_COMMANDS
            cmd_details = SCRIPT_COMMANDS.get(command)
        
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
        """Get event from selected text line."""
        line_num = self._get_selected_line_num()
        if not line_num:
            return None
        
        item_data = self.line_items.get(line_num, {})
        
        if item_data.get('type') == 'event':
            return item_data.get('name')
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
        
        # Special examples for logging commands
        if command == 'queue_for_logging' or command == 'script.queue_for_logging':
            examples.append("# Queue variables inline\nqueue_for_logging device.force device.position device.torque")
            examples.append("# Queue variables with indented block\nqueue_for_logging\n    device.force\n    device.position\n    device.torque")
            return examples
        
        if command == 'start_logging' or command == 'script.start_logging':
            examples.append('# Start logging with timestamp in filename\nstart_logging "<date>-<time> data.csv" device')
            examples.append('# Complete workflow\nqueue_for_logging device.force device.position\nstart_logging "test_data.csv" device\n# Your test commands here\nstop_logging')
            return examples
        
        if command == 'stop_logging' or command == 'script.stop_logging':
            examples.append("# Stop all logging\nstop_logging")
            return examples
        
        if command == 'unqueue_for_logging' or command == 'script.unqueue_for_logging':
            examples.append("# Remove specific variables from queue\nunqueue_for_logging device.force device.torque")
            return examples
        
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
        AddCommandDialog(self, self.device_manager, on_save=lambda: self.refresh())
    
    def edit_command(self):
        """Show dialog to edit the selected command."""
        command = self.get_selected_command()
        if not command:
            return
        
        # Don't allow editing script commands
        script_commands = ['WAIT', 'MATH', 'WAIT_FOR', 'COMMENT', 'CYCLE', 
                         'wait', 'math', 'wait_for', 'comment', 'cycle',
                         'queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
        if command in script_commands or command.startswith('script.'):
            from tkinter import messagebox
            messagebox.showerror("Cannot Edit", 
                               "Built-in script commands cannot be edited.")
            return
        
        # Get command details
        all_commands = self.device_manager.get_all_scripting_commands()
        cmd_details = all_commands.get(command)
        if cmd_details:
            AddCommandDialog(self, self.device_manager, 
                           on_save=lambda: self.refresh(),
                           edit_mode=True,
                           command_name=command,
                           command_data=cmd_details)
    
    def show_add_variable_dialog(self):
        """Show dialog to add a new variable."""
        AddVariableDialog(self, self.device_manager, on_save=lambda: self.refresh())
    
    def show_add_event_dialog(self):
        """Show dialog to add a new event."""
        AddEventDialog(self, self.device_manager, on_save=lambda: self.refresh())
    
    # ===== DEVICE METHODS =====
    
    def get_selected_device(self):
        """Get device from selected text line."""
        line_num = self._get_selected_line_num()
        if not line_num:
            return None
        
        item_data = self.line_items.get(line_num, {})
        
        if item_data.get('type') == 'device':
            return item_data.get('name')
        return None
    
    def set_connection_network(self, device_name):
        """Switch device to network (UDP) connection."""
        from . import serial_comms
        from . import comms
        
        # Keep USB connection open to prevent firmware TX buffer from filling up
        # The serial listener will continue to read and discard USB data
        # Only the connection_method change will make the app ignore USB messages
        
        # Set connection method to network (this will save to config)
        self.device_manager.set_connection_method(device_name, 'network')
        
        # Mark as disconnected so the next network message will be treated as a new connection
        self.device_manager.update_device_state(device_name, {
            'connected': False
        })
        
        # Hide the status panel since device is now disconnected
        gui_refs = self.device_manager.shared_gui_refs
        reset_and_hide_fn = gui_refs.get('reset_and_hide_panel')
        if reset_and_hide_fn:
            reset_and_hide_fn(device_name)
        
        # Update searching panel visibility
        from . import comms
        comms.update_searching_panel_visibility(gui_refs)
        
        # Log the change
        log_to_terminal(f"{device_name}: Switched to network connection", gui_refs)
        
        # Update status variable to reflect network mode
        device_state = self.device_manager.get_device_state(device_name)
        status_var = gui_refs.get(f'status_var_{device_name}')
        if status_var and device_state:
            ip = device_state.get('ip')
            if device_state.get('connected') and ip:
                status_text = f"{device_name.capitalize()} (@{ip})"
            else:
                # Not yet connected on network; show generic device name
                status_text = f"{device_name.capitalize()}"
            status_var.set(status_text)
        
        # Refresh display
        self.refresh()
    
    def set_connection_usb(self, device_name, port):
        """Switch device to USB serial connection."""
        from . import serial_comms
        from . import comms
        
        gui_refs = self.device_manager.shared_gui_refs
        
        # Disconnect from any previous USB port
        device_state = self.device_manager.get_device_state(device_name)
        if device_state and device_state.get('serial_port'):
            serial_comms.disconnect_serial_device(device_state['serial_port'])
        
        # Set connection method to USB
        self.device_manager.set_connection_method(device_name, 'usb', port)
        
        # Update the status variable for GUI
        status_text = f"{device_name.capitalize()} ({port})"
        status_var = gui_refs.get(f'status_var_{device_name}')
        if status_var:
            status_var.set(status_text)
        
        # Start USB listener
        success = serial_comms.connect_serial_device(
            port, 
            device_name, 
            comms.handle_serial_message, 
            gui_refs, 
            self.device_manager
        )
        
        if success:
            log_to_terminal(f"{device_name}: Connected via USB on {port}", gui_refs)
            
            # Mark as disconnected so first USB message triggers connection UI update
            self.device_manager.update_device_state(device_name, {
                "connection_method": "usb",
                "serial_port": port,
                "connected": False,  # Reset so first message triggers is_new_connection
                "last_rx": 0  # Will be updated when first message arrives
            })
            
            # Send a discovery command to wake up USB communication
            # This helps if the firmware's USB buffers got into a bad state
            import time
            time.sleep(0.3)  # Give serial port time to be ready
            serial_comms.send_serial_command(port, "DISCOVER_DEVICE")
            
            # Don't refresh immediately - the device needs time to send first message
            # The USB message handler will trigger a refresh when data arrives
            # But schedule one anyway as a fallback
            self.after(1000, self.refresh)
        else:
            log_to_terminal(f"{device_name}: Failed to connect to {port}", gui_refs)
            # Refresh immediately on failure
            self.refresh()
    
    def start_simulate_device(self, device_name, connection_type='network'):
        """Start the simulator for a specific device.
        
        Args:
            device_name (str): Name of the device to simulate
            connection_type (str): 'network' for local network (127.0.0.1) or 'usb' for virtual USB
        """
        self.device_manager.start_simulator(device_name, connection_type=connection_type)
        # Refresh after a delay to let discovery complete
        self.after(1000, self.refresh)
    
    def stop_simulate_device(self, device_name):
        """Stop the simulator for a specific device."""
        self.device_manager.stop_simulator(device_name)
        # Refresh after a delay to let disconnection be detected
        self.after(3500, self.refresh)
    
    def show_add_command_dialog_for_device(self, device_name):
        """Show add command dialog pre-selected to a specific device."""
        # TODO: Update AddCommandDialog to accept a default device parameter
        self.show_add_command_dialog()
    
    def show_add_variable_dialog_for_device(self, device_name):
        """Show add variable dialog pre-selected to a specific device."""
        self.show_add_variable_dialog()
    
    def show_add_event_dialog_for_device(self, device_name):
        """Show add event dialog pre-selected to a specific device."""
        self.show_add_event_dialog()
    
    def show_devices_context_menu(self, event):
        # Set cursor to click position
        self.devices_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
        device = self.get_selected_device()
        if device:
            self.devices_context_menu.post(event.x_root, event.y_root)
    
    def refresh_device(self, device_name):
        """Refreshes/reloads the JSON files for a single device."""
        from tkinter import messagebox
        
        try:
            success = self.device_manager.reload_single_device(device_name)
            if success:
                # Refresh the display
                self.refresh()
                messagebox.showinfo(
                    "Device Refreshed",
                    f"Successfully reloaded configuration for '{device_name}'.\n\n"
                    f"Commands, telemetry, and events have been updated."
                )
            else:
                messagebox.showerror(
                    "Refresh Failed",
                    f"Failed to reload device '{device_name}'."
                )
        except Exception as e:
            messagebox.showerror(
                "Refresh Error",
                f"Error refreshing device '{device_name}':\n{str(e)}"
            )
    
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
        """Prompt user to select device folder and add it."""
        from tkinter import filedialog, messagebox
        import os
        import json
        
        # Prompt for folder selection
        device_root_path = filedialog.askdirectory(
            title="Select Device Folder",
            parent=self
        )
        
        if not device_root_path:
            return  # User cancelled
        
        # Check if user selected definition/ folder - if so, use parent as root
        if os.path.basename(device_root_path) == 'definition':
            device_root_path = os.path.dirname(device_root_path)
        
        # Add device path to config
        try:
            from main import add_device_path, get_device_paths
            success = add_device_path(device_root_path)
            
            if not success:
                messagebox.showerror("Error", f"Failed to add device path to config.\n\nPath: {device_root_path}")
                return
            
            # Reload device paths from config and rediscover devices
            # Update both device_manager and registry paths
            updated_paths = get_device_paths()
            self.device_manager.device_paths = updated_paths
            self.device_manager.registry.device_paths = updated_paths
            self.device_manager.discover_devices()
            
            # Refresh the UI
            self.refresh()
            
            # Refresh status panels and trigger auto-connect
            self._refresh_after_device_added()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add device:\n{str(e)}")
    
    def _refresh_after_device_added(self):
        """Helper to refresh UI and auto-connect after device is added."""
        shared_gui_refs = getattr(self.device_manager, 'shared_gui_refs', None)
        if not shared_gui_refs:
            return
        
        status_bar_container = shared_gui_refs.get('status_bar_container')
        if status_bar_container:
            # Preserve current variable values
            import tkinter as tk
            preserved_values = {}
            device_modules = self.device_manager.get_device_modules()
            for device_name, device_data in device_modules.items():
                device_vars_map = self.device_manager.get_all_device_variable_names().get(device_name, {})
                for var_name, schema_key in device_vars_map.items():
                    var = shared_gui_refs.get(var_name)
                    if var:
                        try:
                            preserved_values[var_name] = var.get()
                        except tk.TclError:
                            pass
                
                telemetry_data = device_data.get('telemetry_data', {})
                for schema_key, details in telemetry_data.items():
                    gui_var_name = details.get('gui_var', f"{device_name}_{schema_key}_var")
                    if gui_var_name not in preserved_values:
                        var = shared_gui_refs.get(gui_var_name)
                        if var:
                            try:
                                preserved_values[gui_var_name] = var.get()
                            except tk.TclError:
                                pass
            
            # Clear panel references and recreate
            panel_keys_to_remove = [key for key in shared_gui_refs.keys() if key.endswith('_panel')]
            for panel_key in panel_keys_to_remove:
                del shared_gui_refs[panel_key]
            
            for widget in list(status_bar_container.winfo_children()):
                widget.destroy()
            self.device_manager.create_all_gui_components(status_bar_container)
            
            # Restore preserved values
            for var_name, value in preserved_values.items():
                var = shared_gui_refs.get(var_name)
                if var:
                    try:
                        if isinstance(var, tk.StringVar):
                            var.set(str(value))
                        elif isinstance(var, tk.DoubleVar):
                            var.set(float(value))
                    except (tk.TclError, ValueError, TypeError):
                        pass
            
            # Update searching panel visibility
            from src.comms import update_searching_panel_visibility
            update_searching_panel_visibility(shared_gui_refs)
            
            root = shared_gui_refs.get('root')
            if root:
                root.update_idletasks()
        
        # Trigger auto-connect for USB devices
        root = shared_gui_refs.get('root')
        if hasattr(self.device_manager, 'auto_connect_usb_devices') and root:
            root.after(500, self.device_manager.auto_connect_usb_devices)
            # After auto-connect, show panels for connected devices
            root.after(2000, self._show_connected_panels_after_reconnect)
        
        from src.comms import update_searching_panel_visibility
        if root:
            root.after(100, lambda: update_searching_panel_visibility(shared_gui_refs))
    
    def _show_connected_panels_after_reconnect(self):
        """Show status panels for devices that are already connected after re-add."""
        print("[DEBUG] Checking for connected devices to show panels...")
        
        device_modules = self.device_manager.get_device_modules()
        all_states = self.device_manager.get_all_device_states()
        print(f"[DEBUG _show_connected] device_modules: {list(device_modules.keys())}")
        print(f"[DEBUG _show_connected] all_states: {all_states}")
        
        # Get the panel directly and show it
        gui_refs = self.device_manager.shared_gui_refs
        for device_name in device_modules.keys():
            device_state = all_states.get(device_name, {})
            if device_state.get('connected'):
                print(f"[DEBUG _show_connected] {device_name} is connected, showing panel")
                panel = gui_refs.get(f'{device_name}_panel')
                if panel:
                    try:
                        panel.pack(side="top", fill="x", padx=5, pady=2)
                        print(f"[DEBUG _show_connected] Packed panel for {device_name}")
                    except Exception as e:
                        print(f"[DEBUG _show_connected] Error packing panel for {device_name}: {e}")
                else:
                    print(f"[DEBUG _show_connected] Panel widget not found for {device_name}")
    
    def edit_device(self):
        """Show dialog to edit the selected device."""
        device_name = self.get_selected_device()
        if not device_name:
            return
        
        AddDeviceDialog(self, self.device_manager,
                       on_save=lambda: self.refresh(),
                       edit_mode=True,
                       device_name=device_name)
    
    def remove_device(self):
        """Remove the device from the app and persistence (does not delete files)."""
        from tkinter import messagebox
        import os
        import json
        
        device_name = self.get_selected_device()
        if not device_name:
            return
        
        # Find the device path from device_manager
        device_path_to_remove = None
        for path in self.device_manager.device_paths:
            # Check if this path contains the device
            definition_path = os.path.join(path, 'definition')
            if not os.path.isdir(definition_path):
                definition_path = path
            
            config_path = os.path.join(definition_path, 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        path_device_name = config.get('device_name') or config.get('name')
                        if path_device_name == device_name:
                            device_path_to_remove = path
                            break
                except Exception:
                    pass
            
            # Fallback: check folder name
            if os.path.basename(path) == device_name:
                device_path_to_remove = path
                break
        
        if not device_path_to_remove:
            messagebox.showerror("Error", f"Could not find device path for '{device_name}'\n\nAvailable paths:\n" + 
                               "\n".join(self.device_manager.device_paths))
            return
        
        # Confirm removal
        response = messagebox.askyesno("Remove Device",
                                       f"Remove device from app:\n\n{device_name}\n\n" +
                                       f"Path: {device_path_to_remove}\n\n" +
                                       "This will remove the device from the app and clear it from persistence.\n" +
                                       "The device files will NOT be deleted.",
                                       icon='question')
        if not response:
            return
        
        try:
            # Disconnect the device before removing it
            device_state = self.device_manager.get_device_state(device_name)
            if device_state:
                connection_method = device_state.get('connection_method', 'network')
                if connection_method == 'usb':
                    # Disconnect USB
                    serial_port = device_state.get('serial_port')
                    if serial_port:
                        from src import serial_comms
                        serial_comms.disconnect_serial_device(serial_port)
                        print(f"[DEBUG] Disconnected {device_name} from {serial_port}")
                # For network, the connection will be cleaned up by the monitor thread when it times out
            
            # Remove device path from config
            from main import remove_device_path, get_device_paths
            success = remove_device_path(device_path_to_remove)
            
            if not success:
                messagebox.showerror("Error", f"Failed to remove device path from config.\n\nPath: {device_path_to_remove}")
                return
            
            # Update device_manager's paths list (both manager and registry)
            updated_paths = get_device_paths()
            self.device_manager.device_paths = updated_paths
            self.device_manager.registry.device_paths = updated_paths
            
            # Remove device from internal structures (without re-discovering)
            # This prevents the device from being auto-reconnected
            if device_name in self.device_manager.registry.devices:
                del self.device_manager.registry.devices[device_name]
            
            # Remove device state
            self.device_manager.state.remove_device(device_name)
            
            # Remove device's GUI panel reference
            panel_key = f'{device_name}_panel'
            if panel_key in self.device_manager.shared_gui_refs:
                # Destroy the panel widget if it exists
                panel = self.device_manager.shared_gui_refs[panel_key]
                if panel and hasattr(panel, 'destroy'):
                    try:
                        panel.destroy()
                    except tk.TclError:
                        pass  # Already destroyed
                del self.device_manager.shared_gui_refs[panel_key]
            
            # Remove device's status variable
            status_var_key = f'status_var_{device_name}'
            if status_var_key in self.device_manager.shared_gui_refs:
                del self.device_manager.shared_gui_refs[status_var_key]
            
            # Refresh UI after a short delay to ensure device_manager has updated
            self.after(200, self.refresh)
            
            # Refresh status panels on the left sidebar after a delay
            def refresh_status_panels():
                shared_gui_refs = getattr(self.device_manager, 'shared_gui_refs', None)
                if shared_gui_refs:
                    status_bar_container = shared_gui_refs.get('status_bar_container')
                    if status_bar_container:
                        # Preserve current variable values before destroying panels
                        # This prevents values from being reset to "---" when panels are recreated
                        import tkinter as tk
                        preserved_values = {}
                        device_modules = self.device_manager.get_device_modules()
                        for device_name, device_data in device_modules.items():
                            # Get variables from the mapping (explicit gui_var)
                            device_vars_map = self.device_manager.get_all_device_variable_names().get(device_name, {})
                            for var_name, schema_key in device_vars_map.items():
                                var = shared_gui_refs.get(var_name)
                                if var:
                                    try:
                                        preserved_values[var_name] = var.get()
                                    except tk.TclError:
                                        pass  # Variable might not exist yet
                            
                            # Also preserve auto-generated variables (device_name_key_var pattern)
                            # Check telemetry schema for all keys and generate var names
                            telemetry_data = device_data.get('telemetry_data', {})
                            for schema_key, details in telemetry_data.items():
                                # Get gui_var if explicit, otherwise auto-generate
                                gui_var_name = details.get('gui_var', f"{device_name}_{schema_key}_var")
                                if gui_var_name not in preserved_values:
                                    var = shared_gui_refs.get(gui_var_name)
                                    if var:
                                        try:
                                            preserved_values[gui_var_name] = var.get()
                                        except tk.TclError:
                                            pass
                        
                        # Clear all panel references from shared_gui_refs before destroying
                        # (clear all *_panel keys, not just current devices)
                        panel_keys_to_remove = [key for key in shared_gui_refs.keys() if key.endswith('_panel')]
                        for panel_key in panel_keys_to_remove:
                            del shared_gui_refs[panel_key]
                        
                        # Clear all existing device panels (but keep the container itself)
                        for widget in list(status_bar_container.winfo_children()):
                            widget.destroy()
                        # Rebuild device panels with updated device list
                        self.device_manager.create_all_gui_components(status_bar_container)
                        
                        # Restore preserved variable values after panels are recreated
                        for var_name, value in preserved_values.items():
                            var = shared_gui_refs.get(var_name)
                            if var:
                                try:
                                    if isinstance(var, tk.StringVar):
                                        var.set(str(value))
                                    elif isinstance(var, tk.DoubleVar):
                                        var.set(float(value))
                                except (tk.TclError, ValueError, TypeError):
                                    pass  # Skip if variable type doesn't match or doesn't exist
                        
                        # Show panels for connected devices
                        device_modules = self.device_manager.get_device_modules()
                        all_states = self.device_manager.get_all_device_states()
                        for device_name in device_modules.keys():
                            device_state = all_states.get(device_name)
                            if device_state and device_state.get('connected'):
                                show_panel_fn = shared_gui_refs.get('show_panel')
                                if show_panel_fn:
                                    show_panel_fn(device_name)
                        
                        # Update "searching for devices" panel visibility
                        from src.comms import update_searching_panel_visibility
                        update_searching_panel_visibility(shared_gui_refs)
            
            self.after(300, refresh_status_panels)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove device:\n{str(e)}")
    
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
                         'wait', 'math', 'wait_for', 'comment', 'cycle',
                         'queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
        if command in script_commands or command.startswith('script.'):
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
                self.refresh()
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
                         on_save=lambda: self.refresh(),
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
                self.refresh()
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
                      on_save=lambda: self.refresh(),
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
                self.refresh()
            else:
                messagebox.showerror("Error", f"Event '{evt_name}' not found in JSON.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete event:\n{str(e)}")
    
    # ===== WARNING METHODS =====
    
    def get_selected_warning(self):
        """Get warning from selected text line."""
        line_num = self._get_selected_line_num()
        if not line_num:
            return None
        item_data = self.line_items.get(line_num, {})
        if item_data.get('type') == 'warning':
            return item_data.get('name')
        return None
    
    def copy_warning(self):
        """Copy selected warning to clipboard."""
        warning_name = self.get_selected_warning()
        if warning_name:
            self.clipboard_clear()
            self.clipboard_append(warning_name)
    
    def add_warning_to_script(self):
        """Add selected warning to script editor as throw command."""
        warning_name = self.get_selected_warning()
        if warning_name and self.script_editor_widget:
            self.script_editor_widget.text.insert(tk.INSERT, f"throw {warning_name}")
            self.script_editor_widget.text.focus_set()
    
    def show_add_warning_dialog_for_device(self, device_name):
        """Show add warning dialog for a specific device."""
        # Simple implementation - warnings are just {"description": "..."} in warnings.json
        from tkinter import simpledialog, messagebox
        import json
        import os
        
        warning_name = simpledialog.askstring("Add Warning", f"Warning name for {device_name}:")
        if not warning_name:
            return
        
        description = simpledialog.askstring("Add Warning", "Warning description:")
        if not description:
            return
        
        try:
            json_path = os.path.join('devices', device_name, 'warnings.json')
            warnings_data = {}
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    warnings_data = json.load(f)
            
            warnings_data[warning_name] = {"description": description}
            
            with open(json_path, 'w') as f:
                json.dump(warnings_data, f, indent=4)
            
            messagebox.showinfo("Success", f"Warning '{warning_name}' added successfully!")
            self.device_manager.reload_device_modules()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add warning:\n{str(e)}")
    
    def edit_warning(self):
        """Edit selected warning."""
        from tkinter import simpledialog, messagebox
        import json
        import os
        
        warning_name = self.get_selected_warning()
        if not warning_name:
            return
        
        device_name, warn_key = warning_name.split('.', 1)
        device_data = self.device_manager.devices.get(device_name, {})
        warnings_data = device_data.get('warnings', {})
        warning_info = warnings_data.get(warn_key, {})
        
        old_description = warning_info.get('description', '')
        new_description = simpledialog.askstring("Edit Warning", "Warning description:", initialvalue=old_description)
        if not new_description:
            return
        
        try:
            json_path = os.path.join('devices', device_name, 'warnings.json')
            with open(json_path, 'r') as f:
                file_warnings = json.load(f)
            
            file_warnings[warn_key] = {"description": new_description}
            
            with open(json_path, 'w') as f:
                json.dump(file_warnings, f, indent=4)
            
            messagebox.showinfo("Success", f"Warning '{warning_name}' updated successfully!")
            self.device_manager.reload_device_modules()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit warning:\n{str(e)}")
    
    def show_warning_info(self):
        """Show info for selected warning."""
        from tkinter import messagebox
        warning_name = self.get_selected_warning()
        if not warning_name:
            return
        
        device_name, warn_key = warning_name.split('.', 1)
        device_data = self.device_manager.devices.get(device_name, {})
        warnings_data = device_data.get('warnings', {})
        warning_info = warnings_data.get(warn_key, {})
        
        description = warning_info.get('description', 'No description available.')
        messagebox.showinfo(f"Warning: {warning_name}", f"Description:\n{description}\n\nUsage:\nthrow {warning_name}")
    
    def delete_warning(self):
        """Delete selected warning."""
        from tkinter import messagebox
        import json
        import os
        
        warning_name = self.get_selected_warning()
        if not warning_name:
            return
        
        device_name, warn_key = warning_name.split('.', 1)
        
        response = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete warning:\n\n{warning_name}\n\n" +
                                       "This will modify the JSON file and cannot be undone.")
        if not response:
            return
        
        try:
            json_path = os.path.join('devices', device_name, 'warnings.json')
            if not os.path.exists(json_path):
                messagebox.showerror("Error", f"Warnings file not found: {json_path}")
                return
            
            with open(json_path, 'r') as f:
                warnings_data = json.load(f)
            
            if warn_key in warnings_data:
                del warnings_data[warn_key]
                
                with open(json_path, 'w') as f:
                    json.dump(warnings_data, f, indent=4)
                
                messagebox.showinfo("Success", f"Warning '{warning_name}' deleted successfully!")
                self.device_manager.reload_device_modules()
                self.refresh()
            else:
                messagebox.showerror("Error", f"Warning '{warn_key}' not found in JSON.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete warning:\n{str(e)}")

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
        
        # Extract device name from full command name (e.g., "device.move_abs" -> "device")
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
        title_text = "Edit Device" if self.edit_mode else "Add Device"
        title_label = ttk.Label(main_frame, text=title_text,
                               font=theme.FONT_LARGE_BOLD,
                               foreground=theme.COMMAND_COLOR)
        title_label.pack(pady=(0, 20))
        
        if not self.edit_mode:
            # For add mode, go straight to folder selection
            info_label = ttk.Label(main_frame,
                                  text="Select the device folder (e.g., my-device/definition).\n" +
                                       "The folder should contain config.json and JSON files (commands.json, telemetry.json, etc.)",
                                  font=theme.FONT_SMALL,
                                  foreground=theme.COMMENT_COLOR,
                                  justify=tk.LEFT)
            info_label.pack(pady=(0, 15))
            
            # Auto-open folder dialog (use update_idletasks to ensure window is ready)
            self.update_idletasks()
            self.after(200, self.browse_device_folder)
        else:
            # Info text for edit mode
            info_label = ttk.Label(main_frame,
                                  text="Editing device configuration.",
                                  font=theme.FONT_SMALL,
                                  foreground=theme.COMMENT_COLOR,
                                  justify=tk.LEFT)
            info_label.pack(pady=(20, 0))
        
        # Buttons (only show for edit mode, add mode auto-closes after folder selection)
        if self.edit_mode:
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
        
        # In edit mode, there are no input fields to populate
        # The edit mode just allows rediscovering devices
        if hasattr(self, 'name_entry'):
            self.name_entry.insert(0, self.original_device_name)
    
    def toggle_copy_device(self):
        """Enable/disable the copy device dropdown."""
        if hasattr(self, 'copy_device_dropdown'):
            if self.copy_var.get():
                self.copy_device_dropdown.config(state='readonly')
            else:
                self.copy_device_dropdown.config(state='disabled')
    
    def browse_device_folder(self):
        """Open folder dialog to select device folder and immediately process it."""
        from tkinter import filedialog, messagebox
        import os
        import json
        
        initial_dir = None
        # Try to use the first device path if available
        try:
            from main import get_device_paths
            device_paths = get_device_paths()
            if device_paths:
                # Use parent directory of first device path
                first_path = device_paths[0]
                initial_dir = os.path.dirname(first_path)
        except Exception:
            pass
        
        # Temporarily release grab to allow file dialog to open
        self.grab_release()
        try:
            folder_path = filedialog.askdirectory(
                title="Select Device Folder",
                initialdir=initial_dir,
                mustexist=True
            )
        except Exception as e:
            self.grab_set()  # Re-grab on error
            messagebox.showerror("Error", f"Failed to open folder dialog:\n{e}")
            self.destroy()
            return
        finally:
            # Re-grab after dialog closes
            self.grab_set()
        
        if not folder_path:
            # User cancelled - close dialog
            self.destroy()
            return
        
        # Device folders should point to root (e.g., my-device/), not definition/
        # Check if user selected definition/ folder - if so, use parent as root
        device_root_path = folder_path
        if os.path.basename(folder_path) == 'definition':
            device_root_path = os.path.dirname(folder_path)
        
        # Check for definition subfolder and config.json
        definition_path = os.path.join(device_root_path, 'definition')
        if not os.path.isdir(definition_path):
            # Check if the root folder itself contains definition files (for backward compatibility)
            has_config = os.path.exists(os.path.join(device_root_path, 'config.json'))
            has_commands = os.path.exists(os.path.join(device_root_path, 'commands.json'))
            has_telemetry = os.path.exists(os.path.join(device_root_path, 'telemetry.json'))
            
            if has_config or has_commands or has_telemetry:
                # Root folder contains definition files, use it directly
                definition_path = device_root_path
            else:
                # No definition folder and no files in root - ask user
                response = messagebox.askyesno(
                    "Folder Selection",
                    f"The selected folder doesn't appear to contain a device definition.\n\n"
                    f"Selected: {device_root_path}\n\n"
                    f"Expected structure: {device_root_path}/definition/ with config.json\n\n"
                    f"Would you like to use this folder anyway?",
                    icon='warning'
                )
                if not response:
                    self.destroy()
                    return
                definition_path = device_root_path
        
        # Check for config.json to get device name
        config_path = os.path.join(definition_path, 'config.json')
        device_name = None
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    device_name = config.get('device_name') or config.get('name')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read config.json:\n{e}")
                self.destroy()
                return
        
        if not device_name:
            # Try to infer from folder name
            device_name = os.path.basename(device_root_path)
            response = messagebox.askyesno(
                "Device Name",
                f"Could not find device name in config.json.\n\n"
                f"Use '{device_name}' as the device name?",
                icon='question'
            )
            if not response:
                self.destroy()
                return
        
        # Verify it's a valid device folder
        has_commands = os.path.exists(os.path.join(definition_path, 'commands.json'))
        has_telemetry = os.path.exists(os.path.join(definition_path, 'telemetry.json'))
        
        if not (has_commands or has_telemetry):
            response = messagebox.askyesno(
                "Confirm Folder",
                f"The selected folder doesn't appear to contain device definition files.\n\n"
                f"Definition path: {definition_path}\n\n"
                f"A device definition folder should contain commands.json and/or telemetry.json.\n\n"
                f"Would you like to use this folder anyway?",
                icon='warning'
            )
            if not response:
                self.destroy()
                return
        
        # Helper method to show panels for connected devices after reconnect
        def _show_connected_panels_after_reconnect():
            """Show status panels for devices that are already connected after re-add."""
            print("[DEBUG] Checking for connected devices to show panels...")
            
            device_modules = self.device_manager.get_device_modules()
            all_states = self.device_manager.get_all_device_states()
            print(f"[DEBUG _show_connected] device_modules: {list(device_modules.keys())}")
            print(f"[DEBUG _show_connected] all_states: {all_states}")
            
            # Get the panel directly and show it
            gui_refs = self.device_manager.shared_gui_refs
            for device_name in device_modules.keys():
                device_state = all_states.get(device_name, {})
                if device_state.get('connected'):
                    print(f"[DEBUG _show_connected] {device_name} is connected, showing panel")
                    # Get the panel widget directly and pack it
                    panel = gui_refs.get(f'{device_name}_panel')
                    if panel:
                        try:
                            # Show the panel by calling pack() on it
                            panel.pack(side="top", fill="x", padx=5, pady=2)
                            print(f"[DEBUG _show_connected] Packed panel for {device_name}")
                        except Exception as e:
                            print(f"[DEBUG _show_connected] Error packing panel for {device_name}: {e}")
                    else:
                        print(f"[DEBUG _show_connected] Panel widget not found for {device_name}")
        
        self._show_connected_panels_after_reconnect = _show_connected_panels_after_reconnect
        
        # Add device root path to config (not definition path)
        try:
            from main import add_device_path, get_device_paths
            success = add_device_path(device_root_path)
            
            if not success:
                messagebox.showerror("Error", f"Failed to add device path to config.\n\nPath: {device_root_path}")
                self.destroy()
                return
            
            # Reload device paths from config and rediscover devices
            self.device_manager.device_paths = get_device_paths()
            self.device_manager.discover_devices()
            
            # Check if device was actually loaded
            loaded_devices = self.device_manager.get_device_modules()
            if device_name not in loaded_devices:
                # Device didn't load - show error with discovery logs
                logs = self.device_manager.get_discovery_logs()
                recent_logs = "\n".join(logs[-10:]) if logs else "No logs available"
                messagebox.showerror(
                    "Device Added But Not Loaded",
                    f"Device path was added to config, but the device module failed to load.\n\n"
                    f"Device: {device_name}\n"
                    f"Root path: {device_root_path}\n"
                    f"Definition path: {definition_path}\n\n"
                    f"Discovery logs:\n{recent_logs}\n\n"
                    f"Check that gui.py exists in the definition folder or device root."
                )
            else:
                messagebox.showinfo("Success", f"Device added:\n{device_name}\n\n"
                                               f"Root path: {device_root_path}\n"
                                               f"Definition path: {definition_path}\n\n"
                                               f"Device should now be available.")
            
            # Refresh status panels on the left sidebar
            shared_gui_refs = getattr(self.device_manager, 'shared_gui_refs', None)
            if shared_gui_refs:
                status_bar_container = shared_gui_refs.get('status_bar_container')
                if status_bar_container:
                    # Preserve current variable values before destroying panels
                    # This prevents values from being reset to "---" when panels are recreated
                    import tkinter as tk
                    preserved_values = {}
                    device_modules = self.device_manager.get_device_modules()
                    for device_name, device_data in device_modules.items():
                        # Get variables from the mapping (explicit gui_var)
                        device_vars_map = self.device_manager.get_all_device_variable_names().get(device_name, {})
                        for var_name, schema_key in device_vars_map.items():
                            var = shared_gui_refs.get(var_name)
                            if var:
                                try:
                                    preserved_values[var_name] = var.get()
                                except tk.TclError:
                                    pass  # Variable might not exist yet
                        
                        # Also preserve auto-generated variables (device_name_key_var pattern)
                        # Check telemetry schema for all keys and generate var names
                        telemetry_data = device_data.get('telemetry_data', {})
                        for schema_key, details in telemetry_data.items():
                            # Get gui_var if explicit, otherwise auto-generate
                            gui_var_name = details.get('gui_var', f"{device_name}_{schema_key}_var")
                            if gui_var_name not in preserved_values:
                                var = shared_gui_refs.get(gui_var_name)
                                if var:
                                    try:
                                        preserved_values[gui_var_name] = var.get()
                                    except tk.TclError:
                                        pass
                    
                    # Clear all panel references from shared_gui_refs before destroying
                    # (clear all *_panel keys, not just current devices)
                    panel_keys_to_remove = [key for key in shared_gui_refs.keys() if key.endswith('_panel')]
                    for panel_key in panel_keys_to_remove:
                        del shared_gui_refs[panel_key]
                    
                    # Clear all existing device panels (but keep the container itself)
                    for widget in list(status_bar_container.winfo_children()):
                        widget.destroy()
                    # Rebuild device panels with updated device list
                    self.device_manager.create_all_gui_components(status_bar_container)
                    
                    # Restore preserved variable values after panels are recreated
                    for var_name, value in preserved_values.items():
                        var = shared_gui_refs.get(var_name)
                        if var:
                            try:
                                if isinstance(var, tk.StringVar):
                                    var.set(str(value))
                                elif isinstance(var, tk.DoubleVar):
                                    var.set(float(value))
                            except (tk.TclError, ValueError, TypeError):
                                pass  # Skip if variable type doesn't match or doesn't exist
                    
                    # Update "searching for devices" panel visibility
                    from src.comms import update_searching_panel_visibility
                    update_searching_panel_visibility(shared_gui_refs)
                    
                    # Force UI update to ensure panels are visible
                    root = shared_gui_refs.get('root')
                    if root:
                        root.update_idletasks()
            
            # Get root window for scheduling callbacks (dialog will be destroyed)
            root = shared_gui_refs.get('root')
            
            # Trigger auto-connect for USB devices after a delay
            if hasattr(self.device_manager, 'auto_connect_usb_devices') and root:
                root.after(500, self.device_manager.auto_connect_usb_devices)
                # After auto-connect completes, check for connected devices and show their panels
                root.after(2000, self._show_connected_panels_after_reconnect)
            
            # Also update searching panel visibility after a short delay
            from src.comms import update_searching_panel_visibility
            if root:
                root.after(100, lambda: update_searching_panel_visibility(shared_gui_refs))
            
            if self.on_save:
                self.on_save()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add device:\n{str(e)}")
        
        self.destroy()
    
    def save_device(self):
        """Save the device (add device folder to config or create new)."""
        from tkinter import messagebox
        import json
        import os
        
        try:
            old_device_name = self.original_device_name if self.edit_mode else None
            
            if self.edit_mode:
                # Edit mode: just rediscover devices (no input fields to read)
                self.device_manager.discover_devices()
            else:
                # Add mode: select or create device folder
                device_path = None
                
                # Check if user selected a folder
                if hasattr(self, 'folder_path_var') and self.folder_path_var.get():
                    device_path = self.folder_path_var.get().strip()
                    
                    if not os.path.isdir(device_path):
                        messagebox.showerror("Error", f"Selected folder does not exist:\n{device_path}")
                        return
                    
                    # Verify it's a valid device folder (has gui.py or commands.json)
                    has_gui = os.path.exists(os.path.join(device_path, 'gui.py'))
                    has_commands = os.path.exists(os.path.join(device_path, 'commands.json'))
                    
                    if not (has_gui or has_commands):
                        response = messagebox.askyesno(
                            "Confirm Folder",
                            f"The selected folder doesn't appear to contain a device definition.\n\n"
                            f"Folder: {device_path}\n\n"
                            f"A device folder should contain gui.py and/or commands.json.\n\n"
                            f"Would you like to use this folder anyway?",
                            icon='warning'
                        )
                        if not response:
                            return
                    
                    # Add device path to config
                    try:
                        from main import add_device_path
                        add_device_path(device_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to add device path to config:\n{e}")
                        return
                    
                    # Rediscover devices to load the new one
                    self.device_manager.discover_devices()
                    
                    # Extract device name from path for display
                    device_name_display = os.path.basename(device_path)
                    messagebox.showinfo("Success", f"Device folder added:\n{device_path}\n\n"
                                                   f"Device '{device_name_display}' should now be available.")
                else:
                    # No folder selected - create new device folder
                    # This path requires name_entry which doesn't exist in current add mode
                    # Add mode uses browse_device_folder() instead
                    messagebox.showerror("Error", "Please select a device folder using the folder browser.")
                    return
                    
                    # The code below is unreachable but kept for reference
                    # Prompt user to select where to create it
                    from tkinter import filedialog
                    
                    create_path = filedialog.askdirectory(
                        title="Select Location for New Device Folder",
                        mustexist=True
                    )
                    
                    if not create_path:
                        return  # User cancelled
                    
                    # Would need name_entry here, but it doesn't exist in add mode
                    device_name = "new_device"  # Fallback
                    device_path = os.path.join(create_path, device_name)
                    
                    if os.path.exists(device_path):
                        messagebox.showerror("Error", f"Folder already exists:\n{device_path}")
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
                        # Find source device path
                        source_path = None
                        try:
                            from main import get_device_paths
                            device_paths = get_device_paths()
                            for path in device_paths:
                                # Check if it's the device folder itself
                                if os.path.basename(path) == copy_from_device:
                                    source_path = path
                                    break
                        except Exception:
                            pass
                        
                        if source_path:
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
from src import theme

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
                    
                    # Add device path to config
                    try:
                        from main import add_device_path
                        add_device_path(device_path)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to add device path to config:\n{e}")
                        return
                    
                    messagebox.showinfo("Success", f"Device folder created:\n{device_path}\n\n"
                                                   f"Device '{device_name}' should now be available.")
            
            # Always rediscover devices to pick up new/renamed devices
            self.device_manager.discover_devices()
            
            if self.on_save:
                self.on_save()
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save device:\n{str(e)}")


def create_command_reference(parent, script_editor_widget, device_manager):
    """Legacy function name for backward compatibility. Creates a DevicePanel."""
    return DevicePanel(parent, script_editor_widget, device_manager)

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
