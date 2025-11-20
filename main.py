import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import subprocess
import os

# Add libs directory to path for bundled dependencies (e.g., pyserial)
# This allows the app to work on macOS/Linux when running from source
# Skip this when running as a PyInstaller bundle (sys.frozen is set)
if not getattr(sys, 'frozen', False):
    project_root = os.path.dirname(os.path.abspath(__file__))
    libs_path = os.path.join(project_root, "libs")
    if os.path.exists(libs_path) and libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from src import comms
from src.scripting_gui import create_scripting_interface, load_recent_files, RECENT_FILES_PATH
from src.status_panel import create_status_bar
from src.terminal import create_terminal_panel
import json
from src import theme  # Import the new theme file
import tkinter.font as tkfont
import platform
import ctypes
from queue import Queue, Empty
from src.device_manager import DeviceManager # Import the new DeviceManager
from src.data_logger import DataLogger # Import the data logger
import datetime
from pathlib import Path

from _version import __version__

# Import GUI components
from src.top_menu import create_top_menu
from src.device_panel import create_command_reference, AddDeviceDialog

GUI_UPDATE_INTERVAL_MS = 100

def _resolve_config_file():
    """Determine a writable path for the app configuration file."""
    fallback_dir = Path.home() / '.br-equipment-control-app'

    try:
        if sys.platform == 'win32':
            base_dir = Path(os.environ.get('APPDATA', fallback_dir))
            config_dir = base_dir / 'BR Equipment Control'
        elif sys.platform == 'darwin':
            config_dir = Path.home() / 'Library' / 'Application Support' / 'BR Equipment Control'
        else:
            base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
            config_dir = base_dir / 'br-equipment-control-app'
    except Exception as e:
        print(f"Warning determining config directory: {e}")
        config_dir = fallback_dir

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning creating config directory at {config_dir}: {e}")
        config_dir = fallback_dir
        config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir / 'app_config.json'

CONFIG_FILE = _resolve_config_file()

def load_config():
    """Load the persisted application configuration."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open('r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning reading config file: {e}")
    return {}

def save_config(config):
    """Persist the application configuration safely."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open('w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_device_paths():
    """Get the list of device folder paths from config."""
    config = load_config()
    device_paths = config.get('device_paths', [])
    
    # Filter out invalid paths
    valid_paths = [p for p in device_paths if os.path.isdir(p)]
    
    # If we had invalid paths, save the cleaned list
    if len(valid_paths) != len(device_paths):
        config['device_paths'] = valid_paths
        save_config(config)
    
    return valid_paths

def add_device_path(device_path):
    """Add a device path to the config."""
    try:
        config = load_config()
        device_paths = config.get('device_paths', [])
        
        # Normalize path and add if not already present
        normalized_path = os.path.normpath(device_path)
        if normalized_path not in device_paths:
            device_paths.append(normalized_path)
            config['device_paths'] = device_paths
            save_config(config)
        return True
    except Exception as e:
        print(f"Error adding device path: {e}")
        return False

def remove_device_path(device_path):
    """Remove a device path from the config."""
    try:
        config = load_config()
        device_paths = config.get('device_paths', [])
        
        # Normalize the path to remove - try both absolute and relative comparisons
        # First normalize as-is (matching how add_device_path stores it)
        normalized_path = os.path.normpath(os.path.normcase(device_path))
        
        # Also get absolute version for comparison
        abs_normalized_path = os.path.normpath(os.path.normcase(os.path.abspath(device_path)))
        
        # Try to find and remove the path
        found = False
        for i, stored_path in enumerate(device_paths):
            # Normalize stored path both ways
            normalized_stored = os.path.normpath(os.path.normcase(stored_path))
            abs_normalized_stored = os.path.normpath(os.path.normcase(os.path.abspath(stored_path)))
            
            # Match if either normalized version matches
            if normalized_stored == normalized_path or abs_normalized_stored == abs_normalized_path:
                device_paths.pop(i)
                found = True
                break
        
        if found:
            config['device_paths'] = device_paths
            save_config(config)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error removing device path: {e}")
        import traceback
        traceback.print_exc()
        return False

# Keep old function for backward compatibility (deprecated)
def get_devices_path():
    """Deprecated: Get first device path from list. Use get_device_paths() instead."""
    device_paths = get_device_paths()
    if device_paths:
        return device_paths[0]
    return None

class CollapsiblePanel(ttk.Frame):
    """A collapsible panel with a side trigger bar."""
    def __init__(self, parent, text="Controls", width=350, start_collapsed=True, **kwargs):
        super().__init__(parent, style='TFrame', **kwargs)
        self.text = text
        self.width = width
        self.is_collapsed = start_collapsed

        self.trigger_canvas = tk.Canvas(self, width=30, bg=theme.SECONDARY_ACCENT, highlightthickness=0)
        self.trigger_canvas.pack(side=tk.LEFT, fill=tk.Y)

        self.content_panel = ttk.Frame(self, width=self.width, style='TFrame')
        self.content_panel.pack_propagate(False)
        if self.is_collapsed:
            # Start collapsed: don't pack content
            self.configure(width=int(self.trigger_canvas.cget('width')))
        else:
            self.content_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.configure(width=self.width)
            self.after(10, self._update_parent_sash)

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

        # Load configuration and apply UI scaling as early as possible
        self.config_data = load_config()
        self.ui_scaling = self.config_data.get('ui_scaling')
        current_scaling = float(self.root.tk.call('tk', 'scaling'))

        desired_scaling = None
        if self.ui_scaling is None:
            # Use platform-specific defaults
            # macOS has good default scaling (1.33), Windows often needs 2.0
            if platform.system() == 'Darwin':  # macOS
                desired_scaling = current_scaling  # Use system default
            else:  # Windows and others
                desired_scaling = 2.0
            self.ui_scaling = desired_scaling
        else:
            desired_scaling = float(self.ui_scaling)

        if desired_scaling is not None and abs(desired_scaling - current_scaling) > 1e-6:
            try:
                # On macOS, scale fonts; on Windows/Linux, scale Tk
                if platform.system() == 'Darwin':
                    theme.set_font_scale(desired_scaling)
                else:
                    self.root.tk.call('tk', 'scaling', desired_scaling)
                    current_scaling = desired_scaling
            except Exception as e:
                print(f"Warning applying UI scaling: {e}")
                self.ui_scaling = current_scaling

        if self.config_data.get('ui_scaling') != self.ui_scaling:
            self.config_data['ui_scaling'] = self.ui_scaling
            save_config(self.config_data)

        self.ui_scale_var = tk.DoubleVar(value=self.ui_scaling)

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
        )
        
        # Error hold style - no mouseover highlight
        self.style.configure('ErrorHold.Red.TButton', background=theme.HOLDING_RED, foreground='white', font=theme.FONT_BOLD, borderwidth=1, bordercolor=theme.HOLDING_RED)
        self.style.map('ErrorHold.Red.TButton', 
            background=[('pressed', theme.PRESSED_HOLDING_RED)],  # No 'active' state
            foreground=[('pressed', 'white')],
            relief=[('pressed', 'sunken')],
        )
        
        # Disabled green button (grey)
        self.style.configure('Disabled.Green.TButton', background='#4a4a4a', foreground='#808080', font=theme.FONT_BOLD, borderwidth=1, bordercolor='#4a4a4a')
        self.style.map('Disabled.Green.TButton', 
            background=[('disabled', '#4a4a4a')],
            foreground=[('disabled', '#808080')],
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
        self.style.configure('Error.TFrame', background='#2d0f0f')  # Darker red background for error state

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
        # Get device paths from config (only explicitly added paths, no auto-scanning)
        device_paths = get_device_paths()
        
        # DeviceManager needs shared_gui_refs to exist, but it can be populated after.
        self.device_manager = DeviceManager(self.shared_gui_refs, device_paths=device_paths)
        self.device_modules = self.device_manager.get_device_modules()
        self.discovery_logs = self.device_manager.get_discovery_logs()
        self.shared_gui_refs['device_manager'] = self.device_manager
        
        # Check if no devices are loaded and prompt user to add one
        if not self.device_modules:
            response = messagebox.askyesno(
                "No Devices Loaded",
                "You don't have any devices loaded.\n\n"
                "Would you like to add a device now?\n\n"
                "You can add devices later from the Devices pane.",
                icon='question'
            )
            if response:
                # Schedule the dialog to open after the window is created
                self.root.after(100, self._prompt_add_device)
        
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
        
        # Set GUI references in system logger so Python console messages appear in terminal
        try:
            from src.system_logger import get_system_logger
            logger = get_system_logger()
            if logger:
                logger.set_gui_refs(self.shared_gui_refs)
        except Exception:
            pass  # Ignore if logger not available
        
        self.load_last_script()

    def initialize_shared_variables(self):
        # This method's logic has been moved into __init__ to resolve a startup dependency issue.
        pass
    
    def _prompt_add_device(self):
        """Prompt user to select device folder when no devices are loaded."""
        from tkinter import filedialog
        try:
            # Go straight to folder browser
            device_root_path = filedialog.askdirectory(
                title="Select Device Folder",
                parent=self.root
            )
            
            if not device_root_path:
                return  # User cancelled
            
            # Check if user selected definition/ folder - if so, use parent as root
            import os
            if os.path.basename(device_root_path) == 'definition':
                device_root_path = os.path.dirname(device_root_path)
            
            # Add device path
            success = add_device_path(device_root_path)
            if success:
                # Reload and refresh
                self.device_manager.device_paths = get_device_paths()
                self.device_manager.discover_devices()
                self._on_device_added()
            else:
                messagebox.showerror("Error", f"Failed to add device path to config.\n\nPath: {device_root_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add device:\n{e}")
    
    def _show_connected_panels_after_add(self):
        """Show status panels for devices that are already connected after adding device."""
        device_modules = self.device_manager.get_device_modules()
        all_states = self.device_manager.get_all_device_states()
        
        for device_name in device_modules.keys():
            device_state = all_states.get(device_name, {})
            if device_state.get('connected'):
                panel = self.shared_gui_refs.get(f'{device_name}_panel')
                if panel:
                    try:
                        # Check if panel is already visible
                        try:
                            panel.pack_info()
                        except tk.TclError:
                            # Not packed yet, pack it now
                            panel.pack(side="top", fill="x", padx=5, pady=2)
                    except Exception as e:
                        print(f"Error packing panel for {device_name}: {e}")
        
        # Adjust status panel width to accommodate new panels
        if hasattr(self, 'adjust_status_panel_width'):
            # Call multiple times with increasing delays to handle async layout
            self.root.after(50, self.adjust_status_panel_width)
            self.root.after(200, self.adjust_status_panel_width)
            self.root.after(500, self.adjust_status_panel_width)
    
    def _on_device_added(self):
        """Callback when a device is added - refresh the UI."""
        # Reload device modules
        self.device_modules = self.device_manager.get_device_modules()
        
        # Update shared refs
        for device_name, device_data in self.device_modules.items():
            self.shared_gui_refs[f'status_var_{device_name}'] = device_data['status_var']
        
        # Update command functions
        self.command_funcs = self.device_manager.get_all_command_functions()
        self.shared_gui_refs['command_funcs'] = self.command_funcs
        
        # Refresh command reference if it exists
        if hasattr(self, 'command_reference_instance') and self.command_reference_instance:
            self.command_reference_instance.refresh()
        
        # Refresh syntax highlighter for newly added devices (delayed to ensure editor is ready)
        # Retry multiple times since the script editor might not be opened yet
        for device_name in self.device_modules.keys():
            self.root.after(500, lambda dn=device_name: self.device_manager.reload_single_device(dn))
            self.root.after(2000, lambda dn=device_name: self.device_manager.reload_single_device(dn))
            self.root.after(5000, lambda dn=device_name: self.device_manager.reload_single_device(dn))
        
        # Refresh status panels - rebuild device panels
        status_bar_container = self.shared_gui_refs.get('status_bar_container')
        if status_bar_container:
            # Preserve current variable values before destroying panels
            # This prevents values from being reset to "---" when panels are recreated
            preserved_values = {}
            for device_name, device_data in self.device_modules.items():
                # Get variables from the mapping (explicit gui_var)
                device_vars_map = self.device_manager.get_all_device_variable_names().get(device_name, {})
                for var_name, schema_key in device_vars_map.items():
                    var = self.shared_gui_refs.get(var_name)
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
                        var = self.shared_gui_refs.get(gui_var_name)
                        if var:
                            try:
                                preserved_values[gui_var_name] = var.get()
                            except tk.TclError:
                                pass
            
            # Clear all panel references from shared_gui_refs before destroying
            # (clear all *_panel keys, not just current devices)
            panel_keys_to_remove = [key for key in self.shared_gui_refs.keys() if key.endswith('_panel')]
            for panel_key in panel_keys_to_remove:
                del self.shared_gui_refs[panel_key]
            
            # Clear all existing device panels (but keep the container itself)
            for widget in list(status_bar_container.winfo_children()):
                widget.destroy()
            # Rebuild device panels with updated device list
            self.device_manager.create_all_gui_components(status_bar_container)
            
            # Restore preserved variable values after panels are recreated
            for var_name, value in preserved_values.items():
                var = self.shared_gui_refs.get(var_name)
                if var:
                    try:
                        if isinstance(var, tk.StringVar):
                            var.set(str(value))
                        elif isinstance(var, tk.DoubleVar):
                            var.set(float(value))
                    except (tk.TclError, ValueError, TypeError):
                        pass  # Skip if variable type doesn't match or doesn't exist
            
            # Ensure status_bar_container is packed and visible
            try:
                status_bar_container.pack_info()
            except tk.TclError:
                # Container was unpacked, repack it
                if hasattr(self, 'left_bar_frame'):
                    status_bar_container.pack(side=tk.TOP, fill='x', expand=False)
            
            # Trigger auto-connect for USB devices
            if hasattr(self.device_manager, 'auto_connect_usb_devices'):
                self.root.after(500, self.device_manager.auto_connect_usb_devices)
                # After auto-connect completes, check for connected devices and show their panels
                # Check multiple times to catch devices that connect slowly
                self.root.after(2000, self._show_connected_panels_after_add)
                self.root.after(3000, self._show_connected_panels_after_add)
                self.root.after(4000, self._show_connected_panels_after_add)
            
            # Update status variables based on current device states
            # Use get_all_device_states which handles locking properly
            all_states = self.device_manager.get_all_device_states()
            for device_name, device_data in self.device_modules.items():
                status_var = self.shared_gui_refs.get(f'status_var_{device_name}')
                if status_var:
                    device_state = all_states.get(device_name)
                    if device_state:
                        if device_state.get('connected'):
                            # Device is connected, update status and show panel
                            conn_method = device_state.get('connection_method', 'network')
                            if conn_method == 'usb':
                                serial_port = device_state.get('serial_port', 'USB')
                                status_text = f"{device_name.capitalize()} ({serial_port})"
                            else:
                                ip = device_state.get('ip', 'Unknown')
                                status_text = f"{device_name.capitalize()} (@{ip})"
                            status_var.set(status_text)
                            
                            # Show the status panel for this connected device
                            show_panel_fn = self.shared_gui_refs.get('show_panel')
                            if show_panel_fn:
                                show_panel_fn(device_name)
                        else:
                            # Device is disconnected, set default
                            status_var.set(f"{device_name.capitalize()}")
            
            # Update "searching for devices" panel visibility
            from src.comms import update_searching_panel_visibility
            update_searching_panel_visibility(self.shared_gui_refs)
            
            # Force update the UI to ensure panels are visible
            self.root.update_idletasks()
        
        # Trigger auto-connect for USB devices after a delay to allow device discovery to complete
        def trigger_auto_connect():
            from src.comms import update_searching_panel_visibility
            if hasattr(self.device_manager, 'auto_connect_usb_devices'):
                self.device_manager.auto_connect_usb_devices()
            
            # Check for connected devices and show their panels
            # Also adjusts status panel width
            self.root.after(1000, self._show_connected_panels_after_add)
            self.root.after(2000, self._show_connected_panels_after_add)
            self.root.after(3000, self._show_connected_panels_after_add)
            self.root.after(5000, self._show_connected_panels_after_add)
            
            # Update searching panel visibility
            self.root.after(500, lambda: update_searching_panel_visibility(self.shared_gui_refs))
        
        self.root.after(1000, trigger_auto_connect)
        
        # Also update searching panel visibility immediately (in case no devices connect)
        self.root.after(100, lambda: update_searching_panel_visibility(self.shared_gui_refs))
    
    def _update_status_variables(self):
        """Update status variables based on current device states."""
        all_states = self.device_manager.get_all_device_states()
        for device_name, device_data in self.device_modules.items():
            status_var = self.shared_gui_refs.get(f'status_var_{device_name}')
            if status_var:
                device_state = all_states.get(device_name)
                if device_state:
                    if device_state.get('connected'):
                        # Device is connected, update status
                        conn_method = device_state.get('connection_method', 'network')
                        if conn_method == 'usb':
                            serial_port = device_state.get('serial_port', 'USB')
                            status_text = f"{device_name.capitalize()} ({serial_port})"
                        else:
                            ip = device_state.get('ip', 'Unknown')
                            status_text = f"{device_name.capitalize()} (@{ip})"
                        status_var.set(status_text)
                    else:
                        # Device is disconnected, set default
                        status_var.set(f"{device_name.capitalize()}")

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
            self.root.after_idle(self.adjust_status_panel_width)

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
        self.splitter = splitter

        # Left-side container for the status bar (as a child of the top-level splitter)
        left_bar_frame = ttk.Frame(splitter, style='TFrame')
        left_bar_frame.pack_propagate(True)
        self.left_bar_frame = left_bar_frame
        splitter.add(left_bar_frame, weight=0)
        
        # Central container for the main content (scripting + console)
        main_content_frame = ttk.Frame(splitter, style='TFrame')
        splitter.add(main_content_frame, weight=1)
        
        # Create vertical PanedWindow to allow resizing between scripting and terminal
        content_paned = ttk.PanedWindow(main_content_frame, orient=tk.VERTICAL)
        content_paned.pack(fill=tk.BOTH, expand=True)
        
        # Top pane for scripting area
        scripting_pane = ttk.Frame(content_paned, style='TFrame')
        
        # Bottom pane for terminal
        terminal_pane = ttk.Frame(content_paned, style='TFrame')
        
        # Add both panes
        content_paned.add(scripting_pane, weight=1)
        content_paned.add(terminal_pane, weight=0)
        
        # Store reference for sash positioning
        self.content_paned = content_paned
        
        # Bind to window visibility to set terminal height once window is actually shown
        def on_window_visible(event=None):
            def force_terminal_compact():
                try:
                    total_height = content_paned.winfo_height()
                    if total_height > 100:
                        # Set sash so terminal is exactly 220px (about 13-14 lines)
                        content_paned.sashpos(0, total_height - 220)
                except Exception as e:
                    pass
            
            # Try multiple times
            content_paned.after(50, force_terminal_compact)
            content_paned.after(200, force_terminal_compact)
            content_paned.after(400, force_terminal_compact)
        
        # Bind to map event (when widget becomes visible)
        content_paned.bind('<Map>', on_window_visible, add='+')

        terminal_widgets = create_terminal_panel(terminal_pane, self.shared_gui_refs)
        self.shared_gui_refs.update(terminal_widgets)

        # --- Log device discovery messages to the GUI terminal ---
        if 'terminal_cb' in self.shared_gui_refs:
            terminal_cb = self.shared_gui_refs['terminal_cb']
            for log_msg in self.discovery_logs:
                timestr = datetime.datetime.now().strftime("[%H:%M:%S.%f]")[:-3]
                full_msg = f"{timestr} [SYSTEM] {log_msg}\n"
                terminal_cb(full_msg)

        terminal_widgets['terminal_frame'].pack(fill=tk.BOTH, expand=True)


        # --- Populate UI Components ---
        # Commands panel lives in the splitter (right pane), resizable
        # Use platform-appropriate default width (macOS needs smaller default)
        device_pane_width = 500 if platform.system() == 'Darwin' else 800
        cmd_ref_collapsible = CollapsiblePanel(splitter, text="Devices", width=device_pane_width, start_collapsed=False)
        splitter.add(cmd_ref_collapsible) # Add the pane
        cmd_ref_collapsible.get_content_frame().pack_propagate(True)

        def set_initial_sash_pos(event=None):
            # This function runs once after the window is drawn to set the sash.
            # We unbind immediately to ensure it's not called again on resize.
            splitter.unbind("<Configure>")

            def position_sash():
                """Calculates and sets the sash position."""
                splitter_width = splitter.winfo_width()
                trigger_width = int(cmd_ref_collapsible.trigger_canvas.cget('width'))
                if cmd_ref_collapsible.is_collapsed:
                    # Position sash so the right pane is only trigger_width wide,
                    # leaving a few pixels for the sash handle itself.
                    target_pos = splitter_width - (trigger_width + 5)
                else:
                    # Keep sash wide enough to show the full panel width.
                    target_pos = splitter_width - cmd_ref_collapsible.width
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

        # Create scripting GUI in the scripting pane
        self.scripting_gui_refs = create_scripting_interface(
            scripting_pane, 
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
        
        # Add command reference to shared_gui_refs so it can be accessed by comms
        self.shared_gui_refs['command_reference'] = self.command_reference_instance
        
        # Add syntax highlighter to shared_gui_refs so it can be refreshed when devices are added
        self.shared_gui_refs['syntax_highlighter'] = self.scripting_gui_refs['syntax_highlighter']
        
        # Dynamically adjust device pane width based on content
        def adjust_device_pane_width():
            try:
                self.root.update_idletasks()
                # Get the required width of the command reference content
                req_width = self.command_reference_instance.winfo_reqwidth()
                # Add some padding for scrollbar and margins
                desired_width = req_width + 40
                # Cap it at reasonable limits (350-700px)
                desired_width = max(350, min(desired_width, 700))
                # Update the collapsible panel width
                cmd_ref_collapsible.width = desired_width
            except Exception:
                pass  # Silently ignore errors adjusting pane width
        
        # Expand the devices panel by default (after content is created and laid out)
        def expand_devices_panel():
            if cmd_ref_collapsible.is_collapsed:
                cmd_ref_collapsible.toggle_panel()
        
        # Schedule width adjustment and expansion
        self.root.after(100, adjust_device_pane_width)
        self.root.after(150, expand_devices_panel)
        self.root.after(200, adjust_device_pane_width)  # Adjust again after expansion
        self.root.after(400, expand_devices_panel)
        
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

        self.root.after(150, self.adjust_status_panel_width)


        # Create Top Menu (and pass it the file commands from the scripting GUI)
        file_commands = self.scripting_gui_refs['file_commands'].copy()  # Make a copy so we can add to it
        
        # Add system log commands
        def show_latest_system_log():
            """Open the latest system log file in a text viewer."""
            try:
                from src.system_logger import get_system_logger
                logger = get_system_logger()
                log_path = None
                
                # Try to get current session log
                if logger:
                    log_path = logger.get_log_file_path()
                    if log_path and log_path.exists():
                        self._show_text_file_viewer(log_path, "Latest System Log")
                        return
                
                # If no current session log, find the most recent log file
                if logger:
                    logs_dir = logger.logs_dir
                else:
                    # Fallback: try to determine logs directory
                    from src.system_logger import SystemLogger
                    temp_logger = SystemLogger()
                    logs_dir = temp_logger.logs_dir
                    temp_logger.stop_logging()
                
                if logs_dir.exists():
                    # Find all session log files
                    log_files = list(logs_dir.glob("session_*.log"))
                    if log_files:
                        # Sort by modification time, most recent first
                        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        log_path = log_files[0]
                        self._show_text_file_viewer(log_path, f"Latest System Log ({log_path.name})")
                        return
                
                # No log files found
                from tkinter import messagebox
                messagebox.showinfo("No Log File", "No system log files found.")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Failed to open system log: {e}")
        
        file_commands['show_latest_system_log'] = show_latest_system_log
        
        edit_commands = self.scripting_gui_refs['edit_commands']
        script_commands = {
            'validate': self.validate_script
        }
        settings_commands = {
            'change_device_folder': self.change_device_folder,
            'show_paths': self.show_paths_window
        }
        self.menubar, self.recent_files_menu = create_top_menu(
            self.root,
            file_commands,
            edit_commands,
            script_commands,
            settings_commands,
            self.shared_gui_refs,
            self.autosave_var,
            self.ui_scale_var,
            self.set_ui_scale
        )

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
                try:
                    # This is a simplified version of the logic in DeviceManager.create_all_gui_components
                    modules = self.device_manager.get_device_modules().get(device_name)
                    if modules and hasattr(modules.get('gui'), 'create_gui_components'):
                        panel = modules['gui'].create_gui_components(device_panel_container, self.shared_gui_refs)
                        self.shared_gui_refs[f'{device_name}_panel'] = panel
                        panel.pack_forget() # Hide by default
                except Exception as e:
                    print(f"Error creating GUI panel for {device_name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Update searching panel visibility after adding new device panels
            try:
                from src.comms import update_searching_panel_visibility
                update_searching_panel_visibility(self.shared_gui_refs)
            except Exception as e:
                print(f"Error updating searching panel visibility: {e}")
        
        self.root.after_idle(self.adjust_status_panel_width)


    def change_device_folder(self):
        """
        Allows the user to add or remove device folder paths.
        """
        from tkinter import simpledialog
        
        device_paths = get_device_paths()
        
        # Show current paths
        paths_text = "\n".join([f"• {p}" for p in device_paths]) if device_paths else "None"
        
        result = messagebox.askyesnocancel(
            "Manage Device Folders",
            f"Current device folders:\n{paths_text}\n\n"
            "Click 'Yes' to add a device folder\n"
            "Click 'No' to remove a device folder",
            icon='question'
        )
        
        if result is None:  # Cancel
            return
        
        if result:  # Add device folder
            new_path = filedialog.askdirectory(
                title="Select Device Folder",
                mustexist=True
            )
            
            if not new_path:
                return  # User cancelled
            
            # Verify it's a valid device folder
            has_gui = os.path.exists(os.path.join(new_path, 'gui.py'))
            has_commands = os.path.exists(os.path.join(new_path, 'commands.json'))
            is_devices_folder = os.path.basename(new_path) == 'devices'
            
            if not (has_gui or has_commands or is_devices_folder):
                response = messagebox.askyesno(
                    "Confirm Folder",
                    f"The selected folder doesn't appear to be a device folder.\n\n"
                    f"Folder: {new_path}\n\n"
                    f"A device folder should contain gui.py and/or commands.json,\n"
                    f"or be a 'devices' folder containing device subfolders.\n\n"
                    f"Would you like to add it anyway?",
                    icon='warning'
                )
                if not response:
                    return
            
            # Add to config
            if add_device_path(new_path):
                messagebox.showinfo(
                    "Success",
                    f"Device folder added:\n{new_path}\n\n"
                    "The application will reload to apply changes."
                )
                # Rediscover devices
                self.device_manager.discover_devices()
                # Refresh UI
                if hasattr(self, 'command_reference'):
                    self.command_reference.refresh()
            else:
                messagebox.showerror("Error", "Failed to add device folder.")
        
        else:  # Remove device folder
            if not device_paths:
                messagebox.showinfo("Info", "No device folders to remove.")
                return
            
            # Create a simple dialog to select which path to remove
            paths_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(device_paths)])
            selection = simpledialog.askinteger(
                "Remove Device Folder",
                f"Select the number of the folder to remove:\n\n{paths_list}\n\n"
                f"Enter number (1-{len(device_paths)}):",
                minvalue=1,
                maxvalue=len(device_paths)
            )
            
            if selection:
                path_to_remove = device_paths[selection - 1]
                if remove_device_path(path_to_remove):
                    messagebox.showinfo(
                        "Success",
                        f"Device folder removed:\n{path_to_remove}\n\n"
                        "The application will reload to apply changes."
                    )
                    # Rediscover devices
                    self.device_manager.discover_devices()
                    # Refresh UI
                    if hasattr(self, 'command_reference'):
                        self.command_reference.refresh()
                else:
                    messagebox.showerror("Error", "Failed to remove device folder.")
    
    def validate_script(self):
        """
        Validates the current script and shows results in a dialog.
        """
        from tkinter import messagebox
        from src.script_validator import validate_script
        
        # Get the current script content
        script_content = self.scripting_gui_refs['get_script_content']()
        
        # Get all scripting commands
        scripting_commands = self.device_manager.get_all_scripting_commands()
        
        # Run validation
        errors = validate_script(script_content, scripting_commands)
        
        if not errors:
            # Check for device connectivity issues
            from src.script_processor import ScriptRunner
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
            # Stop system logger
            try:
                from src.system_logger import stop_system_logger
                stop_system_logger()
            except Exception:
                pass
            
            self.root.destroy()
        else:
            pass  # User cancelled closing

    def load_last_script(self):
        """
        Loads the most recently opened script on startup if one exists.
        """
        try:
            recent_files = load_recent_files()
            if recent_files:
                last_script_path = recent_files[0]
                if os.path.exists(last_script_path):
                    # We need to call this after the main loop has started processing events
                    self.root.after(100, lambda: self.scripting_gui_refs['load_specific_script'](last_script_path))
        except (IndexError, Exception):
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
        
        # Auto-connect to devices that were last connected via USB
        self.root.after(1000, self.device_manager.auto_connect_usb_devices)
        
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

    def set_ui_scale(self, value: float):
        """Adjust tk scaling/font size, update the variable, and persist the choice."""
        if abs(float(value) - float(self.ui_scaling)) < 1e-6:
            return
        try:
            # On macOS, we scale fonts instead of Tk scaling
            if platform.system() == 'Darwin':
                theme.set_font_scale(value)
            else:
                # On Windows/Linux, use Tk scaling
                self.root.tk.call('tk', 'scaling', value)
            
            self.ui_scale_var.set(value)
            config = load_config()
            config['ui_scaling'] = float(value)
            save_config(config)
            self.ui_scaling = float(value)
            self.root.update_idletasks()
        except Exception as e:
            print(f"Error setting UI scale: {e}")
            return

        response = messagebox.askyesno(
            "Restart Required",
            "Font/UI size changes take effect after restarting the application.\n\n"
            "Restart now? Any unsaved changes will be lost."
        )
        if response:
            self.restart_application()

    def restart_application(self):
        """Restart the application process safely."""
        try:
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                args = sys.argv[1:]
                subprocess.Popen([executable] + args)
            else:
                python = sys.executable
                subprocess.Popen([python] + sys.argv)
        except Exception as e:
            messagebox.showerror("Restart Failed", f"Could not restart automatically:\n{e}")
            return
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def copy_to_clipboard(self, text: str):
        """Utility to copy text to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # Ensure clipboard is updated across platforms
    
    def _show_text_file_viewer(self, file_path: Path, title: str):
        """Open a text file in a viewer window."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            self._show_text_content_viewer(content, title)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to read file:\n{e}")
    
    def _show_text_content_viewer(self, content: str, title: str):
        """Display text content in a scrollable viewer window."""
        from tkinter import scrolledtext
        
        # Create or reuse viewer window
        if not hasattr(self, '_text_viewer_windows'):
            self._text_viewer_windows = {}
        
        if title in self._text_viewer_windows:
            window = self._text_viewer_windows[title]
            if window.winfo_exists():
                window.lift()
                return
        
        # Create new window
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("800x600")
        window.configure(bg=theme.BG_COLOR)
        
        # Create frame with padding
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            frame,
            wrap=tk.NONE,  # Don't wrap - preserve exact formatting including newlines
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            font=("Consolas", 9),
            insertbackground=theme.FG_COLOR,
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=theme.SECONDARY_ACCENT,
            highlightthickness=1
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Insert content - ensure newlines are preserved
        # Replace any \r\n with \n, then ensure all newlines are properly handled
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        text_widget.insert('1.0', normalized_content)
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Add close button
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Close", command=window.destroy).pack(side=tk.RIGHT)
        
        # Store window reference
        self._text_viewer_windows[title] = window
        
        # Clean up on close
        def on_close():
            if title in self._text_viewer_windows:
                del self._text_viewer_windows[title]
            window.destroy()
        window.protocol("WM_DELETE_WINDOW", on_close)

    def adjust_status_panel_width(self):
        """Resize the status pane based on the required width of its contents."""
        status_container = self.shared_gui_refs.get('status_bar_container')
        if not status_container or not hasattr(self, 'left_bar_frame') or not hasattr(self, 'splitter'):
            return
        try:
            # Force full update to ensure layout is calculated
            status_container.update()
            self.root.update_idletasks()
            
            required = status_container.winfo_reqwidth()
            root_width = self.root.winfo_width()
            
            # Use moderate padding to prevent text cutoff
            padding = 20
            desired = max(320, required + padding)
            
            if root_width > 0:
                desired = min(desired, int(root_width * 0.45))
            
            # Set the sash position
            self.splitter.sashpos(0, desired)
        except Exception as e:
            # Silently handle errors but don't completely fail
            pass

    def show_paths_window(self):
        """Display a window listing key application file paths."""
        if hasattr(self, '_paths_window') and self._paths_window and self._paths_window.winfo_exists():
            self._paths_window.lift()
            return

        paths = [
            ("Config File", CONFIG_FILE),
            ("Config Directory", CONFIG_FILE.parent),
            ("Recent Files", RECENT_FILES_PATH),
            ("Logs Directory", getattr(self.data_logger, 'logs_path', 'Unknown')),
            ("Device Folders", ", ".join([str(Path(p)) for p in get_device_paths()]) if self.device_manager else "Unknown"),
            ("Executable", Path(sys.executable).resolve()),
            ("Working Directory", Path.cwd()),
        ]

        self._paths_window = tk.Toplevel(self.root)
        self._paths_window.title("Application Paths")
        self._paths_window.configure(bg=theme.BG_COLOR)
        self._paths_window.transient(self.root)
        self._paths_window.resizable(True, False)

        frame = ttk.Frame(self._paths_window, padding=20, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Key application paths vary by operating system. Copy as needed.",
            style='Subtle.TLabel'
        ).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))

        for idx, (label, path_obj) in enumerate(paths, start=1):
            path_str = str(path_obj)
            ttk.Label(frame, text=f"{label}:", style='Subtle.TLabel').grid(row=idx, column=0, sticky='nw', padx=(0, 8), pady=4)

            entry = ttk.Entry(frame, width=80)
            entry.insert(0, path_str)
            entry.configure(state='readonly')
            entry.grid(row=idx, column=1, sticky='we', pady=4)

            ttk.Button(
                frame,
                text="Copy",
                style='Blue.TButton',
                command=lambda p=path_str: self.copy_to_clipboard(p)
            ).grid(row=idx, column=2, sticky='e', padx=(8, 0), pady=4)

        ttk.Button(
            frame,
            text="Close",
            style='Ghost.TButton',
            command=self._paths_window.destroy
        ).grid(row=len(paths) + 1, column=2, sticky='e', pady=(12, 0))


def main():
    """
    Initializes the main application window, creates the primary UI layout,
    and starts the communication threads.
    """
    # Initialize system logger first (before any print statements)
    try:
        from src.system_logger import initialize_system_logger
        system_logger = initialize_system_logger()
        print(f"[SYSTEM] Session log started: {system_logger.get_log_file_path()}")
    except Exception as e:
        print(f"[SYSTEM ERROR] Failed to initialize system logger: {e}")
        system_logger = None
    
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
