import tkinter as tk
from tkinter import ttk
import threading
import comms
from scripting_gui import create_scripting_interface
from status_panel import create_status_bar
from terminal import create_terminal_panel
import json
import os
import theme  # Import the new theme file
import tkinter.font as tkfont
import platform
import ctypes
from queue import Queue, Empty
import device_actions # Import the new device actions
from device_manager import DeviceManager # Import the new DeviceManager
from data_logger import DataLogger # Import the data logger
import datetime

from _version import __version__

# Import GUI components
from top_menu import create_top_menu
from command_reference import create_command_reference
from device_actions import create_device_commands

GUI_UPDATE_INTERVAL_MS = 100

class CollapsiblePanel(ttk.Frame):
    """A collapsible panel with a side trigger bar."""
    def __init__(self, parent, text="Controls", width=350, **kwargs):
        super().__init__(parent, style='TFrame', **kwargs)
        self.text = text
        self.width = width
        self.is_collapsed = True  # start collapsed by default

        self.trigger_canvas = tk.Canvas(self, width=30, bg=theme.SECONDARY_ACCENT, highlightthickness=0)
        self.trigger_canvas.pack(side=tk.LEFT, fill=tk.Y)

        self.content_panel = ttk.Frame(self, width=self.width, style='TFrame')
        # Start collapsed: don't pack content
        self.content_panel.pack_propagate(False)
        self.configure(width=int(self.trigger_canvas.cget('width')))

        self.draw_trigger_text()
        self.trigger_canvas.bind("<Button-1>", self.toggle_panel)
        self.trigger_canvas.bind("<Enter>", lambda e: self.trigger_canvas.config(bg=theme.PRIMARY_ACCENT))
        self.trigger_canvas.bind("<Leave>", lambda e: self.trigger_canvas.config(bg=theme.SECONDARY_ACCENT))

    def get_content_frame(self):
        return self.content_panel

    def draw_trigger_text(self):
        self.trigger_canvas.delete("all")
        display_text = "Show " + self.text if self.is_collapsed else "Hide " + self.text
        self.trigger_canvas.create_text(15, 150, text=display_text, angle=90, font=theme.FONT_BOLD, fill=theme.FG_COLOR, anchor="center")

    def _update_parent_sash(self):
        """If this panel is in a Panedwindow, update the sash position."""
        self.update_idletasks()
        try:
            pw = self.master
            if isinstance(pw, ttk.Panedwindow):
                panes = pw.panes()
                if str(self) in panes:
                    sash_index = panes.index(str(self)) - 1
                    if sash_index >= 0:
                        trigger_width = self.trigger_canvas.winfo_width()
                        total_width = pw.winfo_width()
                        
                        if self.is_collapsed:
                            # Move sash to make this pane only trigger_width wide
                            target_pos = total_width - trigger_width
                            # Add a small buffer for the sash itself
                            if target_pos < total_width - 5:
                                target_pos -= 5
                            pw.sashpos(sash_index, target_pos)
                        else:
                            # Move sash to make this pane its full configured width
                            target_pos = total_width - self.width
                            pw.sashpos(sash_index, target_pos)
        except Exception:
            pass # Fail silently

    def toggle_panel(self, event=None):
        if self.is_collapsed:
            # Expand to configured width
            self.content_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.configure(width=self.width)
        else:
            # Collapse to trigger width
            self.content_panel.pack_forget()
            self.configure(width=int(self.trigger_canvas.cget('width')))
        self.is_collapsed = not self.is_collapsed
        self.draw_trigger_text()
        self.after(10, self._update_parent_sash) # Let geometry manager update before moving sash

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title(f"BR Equipment Control App - v{__version__}")
        self.root.configure(bg=theme.BG_COLOR)

        # Thread-safe queue for GUI updates
        self.gui_queue = Queue()

        # Configure ttk styles to match the theme
        self.style = ttk.Style()
        self.style.theme_use('clam') # Use a theme that allows full color customization

        # General widget styling
        self.style.configure('.', background=theme.BG_COLOR, foreground=theme.FG_COLOR, font=theme.FONT_NORMAL)
        self.style.map('.', background=[('active', theme.SECONDARY_ACCENT)])

        # Frame styling
        self.style.configure('TFrame', background=theme.BG_COLOR)

        # Notebook (Tabs) styling
        self.style.configure('TNotebook', background=theme.BG_COLOR, borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                            background=theme.WIDGET_BG, 
                            foreground=theme.FG_COLOR, 
                            padding=[10, 5],
                            borderwidth=0)
        self.style.map('TNotebook.Tab',
                      background=[('selected', theme.BG_COLOR), ('active', theme.SECONDARY_ACCENT)],
                      foreground=[('selected', theme.PRIMARY_ACCENT), ('active', theme.FG_COLOR)],
                      expand=[('selected', [1, 1, 1, 0])])

        # Label styling
        self.style.configure('TLabel', background=theme.BG_COLOR, foreground=theme.FG_COLOR, font=theme.FONT_NORMAL)
        self.style.configure('Header.TLabel', font=theme.FONT_BOLD)

        # Button styling
        self.style.configure('TButton', background=theme.WIDGET_BG, foreground=theme.FG_COLOR, borderwidth=1, focusthickness=3, focuscolor=theme.PRIMARY_ACCENT)
        self.style.map('TButton',
            background=[('active', theme.PRIMARY_ACCENT)],
            foreground=[('active', theme.FG_COLOR)]
        )

        # Entry styling
        self.style.configure('TEntry', fieldbackground=theme.WIDGET_BG, foreground=theme.FG_COLOR, insertcolor=theme.FG_COLOR)
        
        # --- Custom Button Styles ---
        self.style.configure('Green.TButton', background=theme.SUCCESS_GREEN, foreground='black', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.SUCCESS_GREEN)
        self.style.map('Green.TButton', 
            background=[('pressed', theme.PRESSED_GREEN), ('active', theme.ACTIVE_GREEN)],
            foreground=[('pressed', 'black'), ('active', 'black')],
            relief=[('pressed', 'sunken'), ('active', 'raised')],
            bordercolor=[('active', theme.FG_COLOR), ('!active', theme.SUCCESS_GREEN)]
        )
        # New style for when the script is actively running (button is disabled)
        self.style.configure('Running.Green.TButton', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.RUNNING_GREEN)
        self.style.map('Running.Green.TButton', 
            foreground=[('disabled', 'white')],
            background=[('disabled', theme.RUNNING_GREEN)]
        )

        self.style.configure('Red.TButton', background=theme.ERROR_RED, foreground='black', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.ERROR_RED)
        self.style.map('Red.TButton', 
            background=[('disabled', theme.COMMENT_COLOR), ('pressed', theme.PRESSED_RED), ('active', theme.ACTIVE_RED)],
            foreground=[('disabled', theme.BG_COLOR), ('pressed', 'black'), ('active', 'black')],
            relief=[('pressed', 'sunken'), ('active', 'raised')],
            bordercolor=[('disabled', theme.COMMENT_COLOR), ('active', theme.FG_COLOR), ('!active', theme.ERROR_RED)]
        )
        # New style for when the script is held
        self.style.configure('Holding.Red.TButton', background=theme.HOLDING_RED, foreground='white', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.HOLDING_RED)
        self.style.map('Holding.Red.TButton', 
            background=[('pressed', theme.PRESSED_HOLDING_RED), ('active', theme.ACTIVE_HOLDING_RED)],
            foreground=[('pressed', 'white'), ('active', 'white')],
            relief=[('pressed', 'sunken'), ('active', 'raised')],
            bordercolor=[('active', theme.FG_COLOR), ('!active', theme.HOLDING_RED)]
        )
        
        self.style.configure('Small.TButton', font=theme.FONT_NORMAL)

        # Custom style for the toggle-like Checkbutton
        self.style.configure('OrangeToggle.TButton', font=theme.FONT_BOLD)
        self.style.map('OrangeToggle.TButton',
            foreground=[('selected', 'black'), ('!selected', theme.FG_COLOR)],
            background=[
                ('selected', 'pressed', theme.PRESSED_ORANGE),
                ('selected', 'active', theme.ACTIVE_ORANGE),
                ('selected', theme.PRESSED_ORANGE), # Make the "on" state darker
                ('!selected', 'pressed', theme.PRESSED_GRAY),
                ('!selected', 'active', theme.SECONDARY_ACCENT),
                ('!selected', theme.WIDGET_BG)
            ],
            relief=[('pressed', 'sunken'), ('active', 'raised')]
        )

        # Blue accent button used for utility actions
        self.style.configure('Blue.TButton', background=theme.PRIMARY_ACCENT, foreground='black', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.PRIMARY_ACCENT)
        self.style.map('Blue.TButton', 
            background=[('pressed', theme.PRESSED_BLUE), ('active', theme.ACTIVE_BLUE)],
            foreground=[('pressed', 'black'), ('active', 'black')],
            relief=[('pressed', 'sunken'), ('active', 'raised')],
            bordercolor=[('active', theme.FG_COLOR), ('!active', theme.PRIMARY_ACCENT)]
        )

        # Ghost/neutral button for low-emphasis actions
        self.style.configure('Ghost.TButton', background=theme.WIDGET_BG, foreground=theme.FG_COLOR, borderwidth=1)
        self.style.map('Ghost.TButton', background=[('active', theme.SECONDARY_ACCENT)])

        # Additional accent buttons for differentiation
        self.style.configure('Yellow.TButton', background=theme.WARNING_YELLOW, foreground='black', font=theme.FONT_BOLD)
        self.style.map('Yellow.TButton', background=[('active', '#F0CD8C')])
        self.style.configure('Gray.TButton', background=theme.SECONDARY_ACCENT, foreground=theme.FG_COLOR, font=theme.FONT_BOLD)
        self.style.map('Gray.TButton', background=[('active', '#505868')])

        # Card-like containers and subtle labels
        self.style.configure('Card.TLabelframe', background=theme.CARD_BG, foreground=theme.FG_COLOR)
        self.style.configure('Card.TLabelframe.Label', background=theme.CARD_BG, foreground=theme.FG_COLOR, font=theme.FONT_BOLD)
        self.style.configure('Card.TFrame', background=theme.CARD_BG)
        self.style.configure('Subtle.TLabel', background=theme.CARD_BG, foreground=theme.COMMENT_COLOR, font=theme.FONT_NORMAL)
        self.style.configure('CardBorder.TFrame', background=theme.SECONDARY_ACCENT)

        # Custom Progress Bar (for torque meters)
        self.style.configure('Card.Vertical.TProgressbar', background=theme.PRIMARY_ACCENT, troughcolor=theme.CARD_BG)
 
        # Treeview (used in command reference)
        self.style.configure("Treeview",
            background=theme.WIDGET_BG,
            foreground=theme.FG_COLOR,
            fieldbackground=theme.WIDGET_BG,
            borderwidth=1
        )
        self.style.map("Treeview",
            background=[('selected', theme.SELECTION_BG)],
            foreground=[('selected', theme.SELECTION_FG)]
        )
        self.style.map("Treeview.Heading",
            background=[('active', theme.PRIMARY_ACCENT), ('!active', theme.SECONDARY_ACCENT)],
            foreground=[('active', theme.FG_COLOR), ('!active', theme.FG_COLOR)]
        )

        # Paned Window Separator
        self.style.configure('TPanedwindow', background=theme.BG_COLOR)
        self.style.configure('TPanedwindow.Sash', background=theme.SECONDARY_ACCENT, sashthickness=6)

        self.root.state('zoomed') # Start maximized

        self.autosave_var = tk.BooleanVar(value=True)
        
        # Initialize the status variable first, as other components need it.
        self.status_var = tk.StringVar(value="Initializing...")

        # Initialize basic shared refs.
        self.shared_gui_refs = {
            'root': self.root,
            'error_state_var': tk.StringVar(value='No Error'),
            "reset_and_hide_panel": self.reset_and_hide_panel,
            "show_panel": self.show_panel,
            "gui_queue": self.gui_queue
        }
        
        # --- Device Management ---
        # DeviceManager needs shared_gui_refs to exist, but it can be populated after.
        self.device_manager = DeviceManager(self.shared_gui_refs)
        self.device_modules = self.device_manager.get_device_modules()
        self.discovery_logs = self.device_manager.get_discovery_logs()
        self.shared_gui_refs['device_manager'] = self.device_manager
        
        # --- Data Logger ---
        self.data_logger = DataLogger(self.shared_gui_refs)
        self.shared_gui_refs['data_logger'] = self.data_logger

        # --- Populate device-specific shared refs ---
        for device_name, device_data in self.device_modules.items():
             self.shared_gui_refs[f'status_var_{device_name}'] = device_data['status_var']
        
        # Command functions are now aggregated by the device manager
        self.command_funcs = self.device_manager.get_all_command_functions()
        self.shared_gui_refs['command_funcs'] = self.command_funcs
        
        self.create_widgets()
        self.load_last_script()

    def initialize_shared_variables(self):
        # This method's logic has been moved into __init__ to resolve a startup dependency issue.
        pass

    def reset_and_hide_panel(self, device_key):
        """Resets all associated variables for a device and hides its panel."""
        # Hide the panel first
        panel = self.shared_gui_refs.get(f'{device_key}_panel')
        if panel:
            panel.pack_forget()

        # Get the schema and variable mappings for this device
        device_vars_map = self.device_manager.get_all_device_variable_names().get(device_key, {})
        device_schema = self.device_manager.get_device_modules().get(device_key, {}).get('telem_schema', {})

        # Iterate over the gui_var -> schema_key mapping
        for var_name, schema_key in device_vars_map.items():
            var = self.shared_gui_refs.get(var_name)
            if var and schema_key in device_schema:
                default_value = device_schema[schema_key].get('default', None)
                
                # Use a generic reset value if 'default' isn't in the schema
                if default_value is None:
                    if isinstance(var, tk.StringVar):
                        default_value = "---"
                    elif isinstance(var, tk.DoubleVar):
                        default_value = 0.0
                    else:
                        continue # Skip if type is unknown
                
                # Set the value, handling type conversions
                try:
                    if isinstance(var, tk.StringVar):
                        # The default schema value might be a number, so convert to string
                        var.set(str(default_value))
                    elif isinstance(var, tk.DoubleVar):
                        var.set(float(default_value))
                except (ValueError, TypeError):
                    # Fallback if the default value is incompatible with the var type
                    var.set("---" if isinstance(var, tk.StringVar) else 0.0)

        # Also handle the main status_var for the device, which isn't in the schema
        status_var_name = f'status_var_{device_key}'
        status_var = self.shared_gui_refs.get(status_var_name)
        if status_var and isinstance(status_var, tk.StringVar):
            status_var.set(f"{device_key.capitalize()}")

    def show_panel(self, device_key):
        """Makes a device's status panel visible."""
        panel = self.shared_gui_refs.get(f'{device_key}_panel')
        if panel:
            panel.pack(side=tk.TOP, fill="x", expand=False, pady=(0, 8))

    def initialize_command_functions(self):
        # This method is now obsolete and can be removed.
        # Its logic has been merged into initialize_shared_variables.
        pass

    def setup_styles(self):
        """
        Configures the application's styles.
        """
        # The styles are now configured in __init__
        pass

    def create_widgets(self):
        """
        Creates the main UI layout and populates it with components.
        """
        # --- Main Layout Frames ---
        main_frame = ttk.Frame(self.root, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a horizontal splitter for center content and commands (resizable)
        splitter = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL, style='TPanedwindow')
        splitter.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)

        # Central container for the main content (left pane of splitter)
        center_container = ttk.Frame(splitter, style='TFrame')
        splitter.add(center_container, weight=1)
        
        # Left-side container for the status bar
        status_panel_width = 550 if platform.system() == "Windows" else 400
        left_bar_frame = ttk.Frame(center_container, width=status_panel_width, style='TFrame')
        left_bar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        left_bar_frame.pack_propagate(False)

        # Main content area (scripting, console)
        main_content_frame = ttk.Frame(center_container, style='TFrame')
        main_content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        terminal_widgets = create_terminal_panel(main_content_frame, self.shared_gui_refs)
        self.shared_gui_refs.update(terminal_widgets)

        # --- Log device discovery messages to the GUI terminal ---
        if 'terminal_cb' in self.shared_gui_refs:
            terminal_cb = self.shared_gui_refs['terminal_cb']
            for log_msg in self.discovery_logs:
                timestr = datetime.datetime.now().strftime("[%H:%M:%S.%f]")[:-3]
                full_msg = f"{timestr} [SYSTEM] {log_msg}\n"
                terminal_cb(full_msg)

        terminal_widgets['terminal_frame'].pack(side=tk.BOTTOM, fill=tk.X, expand=False, pady=(0, 10))


        # --- Populate UI Components ---
        # Commands panel lives in the splitter (right pane), resizable
        cmd_ref_collapsible = CollapsiblePanel(splitter, text="Commands", width=800)
        splitter.add(cmd_ref_collapsible) # Add the pane
        cmd_ref_collapsible.get_content_frame().pack_propagate(True)

        def set_initial_sash_pos(event=None):
            # This function runs once after the window is drawn to set the sash.
            # We unbind immediately to ensure it's not called again on resize.
            splitter.unbind("<Configure>")

            def position_sash():
                """Calculates and sets the sash position."""
                trigger_width = int(cmd_ref_collapsible.trigger_canvas.cget('width'))
                splitter_width = splitter.winfo_width()
                # Position sash so the right pane is only trigger_width wide,
                # leaving a few pixels for the sash handle itself.
                target_pos = splitter_width - (trigger_width + 5)
                if target_pos > 0:
                    splitter.sashpos(0, target_pos)

            # Schedule this to run after a short delay. This allows the Tkinter
            # event loop to process all initial geometry calculations, ensuring
            # winfo_width() returns a correct, stable value.
            splitter.after(10, position_sash)

        # Bind to the splitter's configure event, which fires when it's first sized.
        splitter.bind("<Configure>", set_initial_sash_pos, add="+")

        # Populate the collapsible panels' content frames
        cmd_ref_content = cmd_ref_collapsible.get_content_frame()

        # Create scripting GUI in the main content area
        self.scripting_gui_refs = create_scripting_interface(
            main_content_frame, 
            self.command_funcs, 
            self.shared_gui_refs, 
            self.autosave_var
        )
        
        # Now that the script editor exists, populate the command reference
        self.command_reference_instance = create_command_reference(
            cmd_ref_content, 
            self.scripting_gui_refs['script_editor'],
            self.device_manager
        )
        self.command_reference_instance.pack(fill=tk.BOTH, expand=True)
        self.command_reference_instance.refresh()
        
        # --- Shared GUI References ---
        # This MUST be set AFTER the command_reference_instance is created.
        self.shared_gui_refs['refresh_commands_ref'] = self.refresh_command_components
        
        # "Searching for devices..." panel
        self.searching_frame = ttk.Frame(left_bar_frame, style='Card.TFrame')
        self.searching_label = ttk.Label(self.searching_frame, text="Searching for devices", font=theme.FONT_NORMAL, style='Subtle.TLabel')
        self.searching_label.pack(pady=10, padx=10)
        self.shared_gui_refs['searching_frame'] = self.searching_frame
        self.searching_frame.pack(side=tk.TOP, fill="x", expand=False, pady=(0, 8))
        
        # Populate the left status bar
        status_widgets_dict = create_status_bar(left_bar_frame, self.shared_gui_refs)
        self.shared_gui_refs.update(status_widgets_dict)

        # --- DYNAMIC DEVICE GUI CREATION ---
        # The create_status_bar function now returns a container for device panels
        device_panel_container = self.shared_gui_refs.get('status_bar_container')
        if device_panel_container:
            self.device_manager.create_all_gui_components(device_panel_container)

        # Hide panels by default (redundant but safe)
        for device_name in self.device_modules.keys():
            panel = self.shared_gui_refs.get(f'{device_name}_panel')
            if panel:
                panel.pack_forget()


        # Create Top Menu (and pass it the file commands from the scripting GUI)
        file_commands = self.scripting_gui_refs['file_commands']
        edit_commands = self.scripting_gui_refs['edit_commands']
        script_commands = {
            'validate': self.validate_script
        }
        device_commands = create_device_commands(self.root, self.shared_gui_refs)
        self.menubar, self.recent_files_menu = create_top_menu(self.root, file_commands, edit_commands, script_commands, device_commands, self.autosave_var)

        # Pass the recent files menu reference to the scripting gui
        self.scripting_gui_refs['update_recent_menu_callback'](self.recent_files_menu)
        
        # Bind keyboard shortcuts
        self.root.bind("<Control-Shift-V>", lambda e: self.validate_script())
        self.root.bind("<Control-Shift-v>", lambda e: self.validate_script())  # lowercase variant

        # --- Store references for dynamic updates ---
        self.shared_gui_refs['add_device_panels_ref'] = self.add_new_device_panels
        
        # --- Register window close handler ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # --- macOS: Intercept Cmd+Q quit command ---
        if platform.system() == 'Darwin':  # macOS
            # Override the default quit behavior
            self.root.createcommand('::tk::mac::Quit', self.on_closing)

    def refresh_command_components(self):
        """Refreshes all UI components that depend on the list of commands."""
        # 1. Refresh the main command function dictionary
        self.command_funcs = self.device_manager.get_all_command_functions()
        self.shared_gui_refs['command_funcs'] = self.command_funcs
        
        # 2. Refresh the command reference panel
        if hasattr(self, 'command_reference_instance') and self.command_reference_instance:
            self.command_reference_instance.refresh()
            
        # 3. Refresh the syntax highlighter
        if self.scripting_gui_refs and self.scripting_gui_refs.get('syntax_highlighter'):
            self.scripting_gui_refs['syntax_highlighter'].refresh_keywords()

    def add_new_device_panels(self, device_names):
        """Creates and packs the GUI panels for newly discovered devices."""
        device_panel_container = self.shared_gui_refs.get('status_bar_container')
        if device_panel_container:
            for device_name in device_names:
                # This is a simplified version of the logic in DeviceManager.create_all_gui_components
                modules = self.device_manager.get_device_modules().get(device_name)
                if modules and hasattr(modules.get('gui'), 'create_gui_components'):
                    panel = modules['gui'].create_gui_components(device_panel_container, self.shared_gui_refs)
                    self.shared_gui_refs[f'{device_name}_panel'] = panel
                    panel.pack_forget() # Hide by default


    def validate_script(self):
        """
        Validates the current script and shows results in a dialog.
        """
        from tkinter import messagebox
        from script_validator import validate_script
        
        # Get the current script content
        script_content = self.scripting_gui_refs['get_script_content']()
        
        # Get all scripting commands
        scripting_commands = self.device_manager.get_all_scripting_commands()
        
        # Run validation
        errors = validate_script(script_content, scripting_commands)
        
        if not errors:
            # Check for device connectivity issues
            from script_processor import ScriptRunner
            import shlex
            
            required_devices = set()
            for line in script_content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = shlex.split(line)
                except ValueError:
                    parts = line.split()
                
                if not parts:
                    continue
                
                command_word = parts[0].lower()
                
                # Check if this is a script-only command
                if command_word in ['wait', 'wait_for', 'cycle', 'queue_for_logging', 
                                   'unqueue_for_logging', 'start_logging', 'stop_logging']:
                    continue
                
                # Check if command is device-specific
                command_info = scripting_commands.get(command_word)
                if not command_info:
                    for cmd_key in scripting_commands:
                        if cmd_key.lower() == command_word.lower():
                            command_info = scripting_commands[cmd_key]
                            break
                
                if command_info:
                    device = command_info.get('device')
                    if device and device not in ['script', 'both']:
                        required_devices.add(device)
            
            # Check device connectivity
            warnings = []
            for device_name in required_devices:
                device_state = self.device_manager.get_device_state(device_name)
                if not device_state or not device_state.get('connected'):
                    warnings.append(f"• {device_name} is not connected")
            
            if warnings:
                warning_msg = "Script syntax is valid, but the following devices are not connected:\n\n" + "\n".join(warnings)
                messagebox.showwarning("Script Validation - Warnings", warning_msg)
            else:
                messagebox.showinfo("Script Validation", "✓ Script is valid and all required devices are connected!")
        else:
            # Show errors
            error_msg = "Script validation found the following errors:\n\n"
            for error in errors[:10]:  # Limit to first 10 errors
                error_msg += f"Line {error['line']}: {error['error']}\n"
            
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more error(s)"
            
            messagebox.showerror("Script Validation Failed", error_msg)
    
    def setup_menu(self):
        """
        Sets up the top menu bar.
        """
        pass # This method is not fully implemented in the original file, so it's left empty.

    def on_closing(self):
        """
        Handles the window close event, checking for unsaved changes before exiting.
        """
        
        # Check for active logging sessions
        if self.data_logger.has_active_logs():
            from tkinter import messagebox
            active_logs = self.data_logger.get_active_logs()
            log_names = [os.path.basename(path) for path in active_logs.keys()]
            log_list = "\n".join(log_names)
            
            response = messagebox.askyesno(
                "Active Logging Sessions",
                f"The following log files are still active:\n\n{log_list}\n\nDo you want to close the application anyway?\n(Logging will be stopped)",
                icon='warning'
            )
            
            if not response:
                return
            
            # Stop all logging before closing
            self.data_logger.cleanup()
        
        # Ask the scripting GUI to check for unsaved changes before closing
        check_result = self.scripting_gui_refs['check_unsaved']()
        if check_result:
            # Terminate simulator if it's running
            if device_actions.simulator_process and device_actions.simulator_process.poll() is None:
                device_actions.simulator_process.terminate()
            self.root.destroy()
        else:
            pass  # User cancelled closing

    def load_last_script(self):
        """
        Loads the most recently opened script on startup if one exists.
        """
        try:
            with open("recent_files.json", 'r') as f:
                recent_files = json.load(f)
            if recent_files:
                last_script_path = recent_files[0]
                if os.path.exists(last_script_path):
                    # We need to call this after the main loop has started processing events
                    self.root.after(100, lambda: self.scripting_gui_refs['load_specific_script'](last_script_path))
        except (FileNotFoundError, json.JSONDecodeError, IndexError):
            # No recent files, or file is corrupt. Do nothing.
            pass

    def run(self):
        """
        Starts the communication threads and the main event loop.
        """
        # Start the communication threads, calling functions from the comms module
        threading.Thread(target=comms.recv_loop, args=(self.shared_gui_refs, self.device_manager), daemon=True).start()
        threading.Thread(target=comms.monitor_connections, args=(self.shared_gui_refs, self.device_manager), daemon=True).start()
        threading.Thread(target=comms.discovery_loop, args=(self.shared_gui_refs,), daemon=True).start()
        self.animate_searching_text()
        self.process_gui_queue()
        self.root.mainloop()

    def animate_searching_text(self):
        """Animates the searching text with trailing dots."""
        base_text = "Searching for devices"
        dot_count = 0
        def update_text():
            nonlocal dot_count
            dots = "." * (dot_count % 4)
            # Add padding with spaces to prevent the label from resizing
            self.searching_label.config(text=f"{base_text}{dots:<3}")
            dot_count += 1
            self.root.after(400, update_text)
        update_text()

    def process_gui_queue(self):
        """Processes messages from the GUI queue to safely update the UI."""
        try:
            while True:
                task, args, kwargs = self.gui_queue.get_nowait()
                task(*args, **kwargs)
        except Empty:
            pass  # Queue is empty, do nothing
        finally:
            self.root.after(100, self.process_gui_queue)


def main():
    """
    Initializes the main application window, creates the primary UI layout,
    and starts the communication threads.
    """
    # --- Make the application DPI-aware on Windows ---
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Could not set DPI awareness: {e}")

    root = tk.Tk()
    
    theme.dark_title_bar(root) # Set dark title bar

    # --- Set Application Icon ---
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set the top-left window icon (uses .png)
        png_path = os.path.join(script_dir, 'assets', 'icon.png')
        if os.path.exists(png_path):
            img = tk.PhotoImage(file=png_path)
            root.tk.call('wm', 'iconphoto', root._w, img)
        else:
             print(f"Could not find icon.png at '{png_path}'.")

        # Set the taskbar icon (requires .ico on Windows)
        if platform.system() == "Windows":
            ico_path = os.path.join(script_dir, 'assets', 'icon.ico')
            if os.path.exists(ico_path):
                # This is the most reliable way to set the taskbar icon
                root.iconbitmap(ico_path)
                
                # Force Windows to associate the icon with the app
                myappid = u'tekbic.st8erboi.st8erboi-controller.1.0' 
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            else:
                print("NOTE: To set the taskbar icon on Windows, 'icon.ico' must exist in the assets folder.")

    except Exception as e:
        print(f"An error occurred while setting the icon: {e}")
        
    app = MainApplication(root)
    app.run()


if __name__ == "__main__":
    main()
