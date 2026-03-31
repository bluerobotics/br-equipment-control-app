import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import queue
import os
import sys
import json
from pathlib import Path
from functools import partial
import re
import tkinter.font as tkfont
import platform
import webbrowser

from .validator import validate_single_line, validate_script
from .processor import ScriptRunner, SCRIPT_COMMANDS
from src import theme
from src.comms import devices_lock

# --- Find/Replace Frame ---
class FindReplaceFrame(ttk.Frame):
    def __init__(self, parent, script_editor_text, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = script_editor_text
        
        self.configure(style='Card.TFrame')

        # --- Widgets ---
        find_label = ttk.Label(self, text="Find:")
        self.find_entry = ttk.Entry(self, width=30)
        
        replace_label = ttk.Label(self, text="Replace:")
        self.replace_entry = ttk.Entry(self, width=30)
        
        self.find_next_button = ttk.Button(self, text="Find Next", command=self.find_next)
        self.replace_button = ttk.Button(self, text="Replace", command=self.replace)
        self.replace_all_button = ttk.Button(self, text="Replace All", command=self.replace_all)
        
        close_button = ttk.Button(self, text="✕", command=self.hide, style="Red.TButton", width=2)

        # --- Layout ---
        find_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.find_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.find_next_button.grid(row=0, column=2, padx=5, pady=5)
        self.replace_button.grid(row=0, column=3, padx=5, pady=5)
        
        replace_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.replace_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.replace_all_button.grid(row=1, column=2, padx=(5,5), pady=5, columnspan=2, sticky="ew")

        close_button.grid(row=0, column=4, padx=5, pady=5, sticky='e')

        self.grid_columnconfigure(1, weight=1)
        
        # Bind enter key for quick searching
        self.find_entry.bind("<Return>", self.find_next)
        self.replace_entry.bind("<Return>", self.replace)

    def show(self):
        self.pack(fill='x', pady=(5,0), padx=10)
        self.find_entry.focus_set()
        
    def hide(self):
        self.pack_forget()

    def find_next(self, event=None):
        find_text = self.find_entry.get()
        if not find_text:
            return

        start_pos = self.text_widget.index(tk.INSERT)
        found_pos = self.text_widget.search(find_text, start_pos, stopindex=tk.END)
        
        if found_pos:
            end_pos = f"{found_pos}+{len(find_text)}c"
            self.text_widget.tag_remove(tk.SEL, "1.0", tk.END)
            self.text_widget.tag_add(tk.SEL, found_pos, end_pos)
            self.text_widget.mark_set(tk.INSERT, end_pos)
            self.text_widget.see(found_pos)
        else:
            # Wrap search
            found_pos = self.text_widget.search(find_text, "1.0", stopindex=tk.END)
            if found_pos:
                end_pos = f"{found_pos}+{len(find_text)}c"
                self.text_widget.tag_remove(tk.SEL, "1.0", tk.END)
                self.text_widget.tag_add(tk.SEL, found_pos, end_pos)
                self.text_widget.mark_set(tk.INSERT, end_pos)
                self.text_widget.see(found_pos)
            else:
                 messagebox.showinfo("Not Found", f"Cannot find '{find_text}'", parent=self)

    def replace(self, event=None):
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()

        if not self.text_widget.tag_ranges(tk.SEL):
            self.find_next()
            return
        
        selected_text = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        if selected_text == find_text:
            self.text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_widget.insert(tk.SEL_FIRST, replace_text)
        
        self.find_next()

    def replace_all(self):
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        if not find_text:
            return

        count = 0
        start_pos = "1.0"
        while True:
            found_pos = self.text_widget.search(find_text, start_pos, stopindex=tk.END)
            if not found_pos:
                break
            
            end_pos = f"{found_pos}+{len(find_text)}c"
            self.text_widget.delete(found_pos, end_pos)
            self.text_widget.insert(found_pos, replace_text)
            
            # Revert to the more correct logic for advancing the cursor
            start_pos = f"{found_pos}+{len(replace_text)}c"
            count += 1
        
        messagebox.showinfo("Replace All", f"Replaced {count} occurrence(s).", parent=self)

# --- Helper Class for Placeholder Text ---
class EntryWithPlaceholder(ttk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = theme.SECONDARY_ACCENT
        self.default_fg_color = theme.FG_COLOR
        self.is_placeholder = True

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        self.put_placeholder()

    def put_placeholder(self):
        self.is_placeholder = True
        self.delete(0, tk.END)
        self.insert(0, self.placeholder)
        self.config(foreground=self.placeholder_color)

    def _clear_placeholder(self, event=None):
        if self.is_placeholder:
            self.is_placeholder = False
            self.delete(0, tk.END)
            self.config(foreground=self.default_fg_color)

    def _add_placeholder(self, event=None):
        if not self.get():
            self.put_placeholder()

    # Override get() to return empty string if it's a placeholder
    def get(self):
        if self.is_placeholder:
            return ""
        return super().get()

# --- Constants for Recent Files ---
def _resolve_recent_files_path() -> Path:
    """Determine a writable path for the recent files list."""
    fallback_dir = Path.home() / '.br-equipment-control-app'

    try:
        if sys.platform == 'win32':
            base_dir = Path(os.environ.get('APPDATA', fallback_dir))
            recent_dir = base_dir / 'BR Equipment Control'
        elif sys.platform == 'darwin':
            recent_dir = Path.home() / 'Library' / 'Application Support' / 'BR Equipment Control'
        else:
            base_dir = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local' / 'state'))
            recent_dir = base_dir / 'br-equipment-control-app'
    except Exception as e:
        print(f"Warning determining recent-files directory: {e}")
        recent_dir = fallback_dir

    try:
        recent_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning creating recent-files directory at {recent_dir}: {e}")
        recent_dir = fallback_dir
        recent_dir.mkdir(parents=True, exist_ok=True)

    return recent_dir / 'recent_files.json'


RECENT_FILES_PATH = _resolve_recent_files_path()
MAX_RECENT_FILES = 5


# --- Recent Files Management ---
def load_recent_files():
    """Loads the list of recent file paths from the config file."""
    try:
        with RECENT_FILES_PATH.open('r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_recent_files(filepaths):
    """Saves the list of recent file paths to the config file."""
    with RECENT_FILES_PATH.open('w') as f:
        json.dump(filepaths, f)


def add_to_recent_files(filepath):
    """Adds a new filepath to the top of the recent files list."""
    filepaths = load_recent_files()
    if filepath in filepaths:
        filepaths.remove(filepath)
    filepaths.insert(0, filepath)
    save_recent_files(filepaths[:MAX_RECENT_FILES])

# --- Custom Text Widget and Line Numbers (Restored and Themed) ---

class CustomText(tk.Text):
    """A text widget that notifies of changes"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config(
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.PRIMARY_ACCENT, # Cursor color
            borderwidth=0,
            highlightthickness=0, # This removes the focus border
            font=theme.FONT_NORMAL,
            selectbackground=theme.SELECTION_BG,
            selectforeground=theme.SELECTION_FG,
            inactiveselectbackground=theme.SELECTION_BG, # Keep selection color when widget loses focus
            undo=True,
            wrap=tk.NONE,
            spacing1=2,
            spacing3=2,
            padx=6,
            pady=4  # Top/bottom padding to match line number canvas
        )
        
        # Verify font is actually monospace and set tab width
        actual_font = tkfont.Font(font=self.cget("font"))
        
        # Set tab width to 4 characters based on actual font width
        tab_width = actual_font.measure(' ' * 4)
        self.config(tabs=(tab_width,))

        # Create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        cmd = (self._orig,) + args
        try:
            result = self.tk.call(cmd)
        except tk.TclError:
            return None # Can happen with Ctrl-C

        # Generate virtual events for changes
        if (args[0] in ("insert", "delete", "replace") or
            args[0:3] == ("mark", "set", "insert") or
            args[0:2] in (("xview", "moveto"), ("xview", "scroll"),
                         ("yview", "moveto"), ("yview", "scroll"))):
            self.event_generate("<<Change>>", when="tail")
        
        if args[0] in ("insert", "delete", "replace"):
            self.event_generate("<<Modified>>", when="tail")
        
        return result

class TextLineNumbers(tk.Canvas):
    """A canvas that displays line numbers for a text widget.
    
    Indented lines (parameter blocks) don't get their own line numbers -
    they're considered part of the command above them.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textwidget = None
        self._font = None
        self._line_height = None

    def attach(self, text_widget):
        self.textwidget = text_widget
        # Cache font metrics for consistent line height calculation
        self._font = tkfont.Font(font=text_widget.cget("font"))
        self._line_height = self._font.metrics("linespace")

    def redraw(self, *args):
        self.delete("all")
        
        # First pass: calculate logical line numbers (skipping indented lines)
        content = self.textwidget.get("1.0", "end-1c")
        lines = content.split('\n')
        logical_line_map = {}  # physical line -> logical line number (or None for indented)
        logical_num = 1
        
        for physical_idx, line in enumerate(lines):
            physical_line = physical_idx + 1
            # Check if line is indented (starts with whitespace)
            if line and (line[0] == '\t' or line[0] == ' '):
                # Indented line - no line number
                logical_line_map[physical_line] = None
            else:
                # Non-indented line - gets a line number
                logical_line_map[physical_line] = logical_num
                logical_num += 1
        
        # Second pass: draw the line numbers (right-aligned with padding)
        i = self.textwidget.index("@0,0")
        width = self.winfo_width()
        padding_right = 8  # Pixels of padding on the right
        padding_top = 4    # Match the text widget's pady
        
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None: 
                break
            # dline returns (x, y, width, height, baseline)
            # y is relative to the text widget's visible area (after padding)
            # Add padding_top to match the text widget's pady
            y = dline[1] + padding_top
            
            physical_line = int(str(i).split(".")[0])
            logical_num = logical_line_map.get(physical_line)
            
            if logical_num is not None:
                # Right-align: position from right edge minus padding
                # Use "ne" anchor so the number aligns with top of line
                self.create_text(width - padding_right, y, anchor="ne", text=str(logical_num), 
                                 font=theme.FONT_NORMAL, fill=theme.SECONDARY_ACCENT)
            # Indented lines get no number displayed
            
            i = self.textwidget.index(f"{i}+1line")

# --- Syntax Highlighter ---
class SyntaxHighlighter:
    def __init__(self, text_widget, device_keywords, script_keywords, device_manager=None):
        self.text = text_widget
        self.device_keywords = device_keywords
        self.script_keywords = script_keywords
        self.device_manager = device_manager
        self.valid_string_params = set()  # Will hold all valid enum/option values
        self.all_variables = []  # Will hold all device.variable names
        self.all_warnings = []  # Will hold all device.warning names
        self.all_reports = []  # Will hold all device.report_name
        self.all_views = []  # Will hold all device.view_id
        self._load_valid_string_params()
        self._load_all_variables()
        self._load_all_warnings()
        self._load_all_reports()
        self._load_all_views()
        
        self.tags = {
            'device': {'foreground': theme.DEVICE_COLOR, 'font': theme.FONT_BOLD},  # Purple for device namespace
            'command': {'foreground': theme.COMMAND_COLOR, 'font': theme.FONT_BOLD},
            'script_command': {'foreground': theme.SCRIPT_COMMAND_COLOR, 'font': theme.FONT_BOLD},
            'variable': {'foreground': theme.VARIABLE_COLOR},  # Green for variables (device.variable)
            'warning': {'foreground': theme.ERROR_RED},  # Red for warnings (device.warning)
            'report': {'foreground': '#E8E4D9'},  # Warm off-white/cream for reports (device.report_name)
            'view': {'foreground': '#B0A3D4'},  # Lavender for views (device.view_id)
            'parameter': {'foreground': theme.PARAMETER_COLOR},
            'string': {'foreground': theme.PARAMETER_COLOR},  # Strings use parameter color (orange)
            'logging_session': {'foreground': theme.WARNING_YELLOW},  # Yellow for logging session names
            'comment': {'foreground': theme.COMMENT_COLOR},
            'colon': {'foreground': theme.SELECTION_FG, 'font': theme.FONT_BOLD} # SELECTION_FG is white
        }
        self._configure_tags()
        # Use a flag to prevent re-highlighting while highlighting is in progress
        self._highlighting = False
        # Bind to the custom <<Modified>> event, which fires on any text change.
        self.text.bind('<<Modified>>', self.highlight)
        print(f"[SYNTAX] Highlighter initialized: {len(self.device_keywords)} device cmds, {len(self.script_keywords)} script cmds")
    
    def _load_valid_string_params(self):
        """Extract valid enum choices and flag keywords from all commands.
        
        Only highlights:
        - Enum choices (like 'abort', 'retract', 'hold', 'skip') - actual values user selects
        - Flag keywords (like 'open') - typing the word enables a boolean flag
        
        Does NOT highlight:
        - Keyword labels (like 'force_min', 'endpoint_max') - these are just identifiers
        - Units (like 'mm', 'kg', 'J') - these are descriptive labels
        """
        self.valid_string_params = set()
        if not self.device_manager:
            return
        
        all_commands = self.device_manager.get_all_scripting_commands()
        for cmd_name, cmd_details in all_commands.items():
            params = cmd_details.get('params', [])
            for param in params:
                # Get enum or options list - these are actual value choices
                choices = param.get('enum') or param.get('options')
                if choices:
                    for choice in choices:
                        self.valid_string_params.add(choice.lower())
                
                # Flag-type parameters - typing the keyword enables the flag
                if param.get('type') == 'flag':
                    # Use the keyword field if present, otherwise use parameter name
                    keyword = param.get('keyword') or param.get('parameter', '')
                    if keyword:
                        self.valid_string_params.add(keyword.lower())
    
    def _load_all_variables(self):
        """Load all telemetry variables from all devices."""
        self.all_variables = []
        if not self.device_manager:
            return
        
        for device_name in self.device_manager.get_all_device_names():
            device_data = self.device_manager.devices.get(device_name, {})
            telemetry_data = device_data.get('telemetry_data', {})
            
            for param_name in telemetry_data.keys():
                full_var_name = f"{device_name}.{param_name}"
                self.all_variables.append(full_var_name)
    
    def _load_all_warnings(self):
        """Load all warnings from all devices."""
        self.all_warnings = []
        if not self.device_manager:
            return
        
        for device_name in self.device_manager.get_all_device_names():
            device_data = self.device_manager.devices.get(device_name, {})
            warnings_data = device_data.get('warnings', {})
            
            for warning_name in warnings_data.keys():
                full_warning_name = f"{device_name}.{warning_name}"
                self.all_warnings.append(full_warning_name)

    def _load_all_reports(self):
        """Load all report commands from all devices."""
        self.all_reports = []
        if not self.device_manager:
            return
        
        for device_name in self.device_manager.get_all_device_names():
            device_data = self.device_manager.devices.get(device_name, {})
            reports_data = device_data.get('reports_data', {})
            
            for report_name in reports_data.keys():
                full_report_name = f"{device_name}.{report_name}"
                self.all_reports.append(full_report_name)

    def _load_all_views(self):
        """Load all view commands from all devices."""
        self.all_views = []
        if not self.device_manager:
            return
        
        for device_name in self.device_manager.get_all_device_names():
            device_data = self.device_manager.devices.get(device_name, {})
            views_data = device_data.get('views_data', {})
            
            for view_id in views_data.keys():
                full_view_name = f"{device_name}.{view_id}"
                self.all_views.append(full_view_name)

    def refresh_keywords(self):
        """Re-fetches the keywords from the device manager and re-highlights the text."""
        # This assumes the device_manager reference passed in initially is still valid
        # and has been updated with the new device info.
        all_commands = self.device_manager.get_all_scripting_commands()
        all_commands.update(SCRIPT_COMMANDS)  # Add the generic script commands
        
        self.device_keywords = [cmd for cmd, details in all_commands.items() if details.get('device') not in ['script', 'both']]
        self.script_keywords = [cmd for cmd, details in all_commands.items() if details.get('device') in ['script', 'both']]
        
        # Add the hardcoded script commands (like CYCLE, REPEAT) to the script keywords
        self.script_keywords.extend(list(SCRIPT_COMMANDS.keys()))
        
        self._load_valid_string_params()  # Refresh valid string params too
        self._load_all_variables()  # Refresh variables too
        self._load_all_warnings()  # Refresh warnings too
        self._load_all_reports()  # Refresh reports too
        self._load_all_views()  # Refresh views too
        self.highlight()


    def _configure_tags(self):
        try:
            for tag_name, tag_config in self.tags.items():
                self.text.tag_configure(tag_name, **tag_config)
            print(f"[SYNTAX] Configured {len(self.tags)} highlighting tags")
        except Exception as e:
            print(f"[SYNTAX ERROR] Failed to configure tags: {e}")
            import traceback
            traceback.print_exc()

    def highlight(self, event=None):
        # Use 'end-1c' to avoid highlighting the final newline which can cause issues
        content = self.text.get("1.0", "end-1c")
        
        # A small delay to prevent rapid, sequential updates from fighting each other.
        self.text.after(10, self._apply_highlight, content)

    def _apply_highlight(self, content):
        # Remove all tags first to prevent stacking
        try:
            for tag in self.tags.keys():
                self.text.tag_remove(tag, "1.0", "end")
        except Exception as e:
            print(f"[SYNTAX ERROR] Failed to remove tags: {e}")
            return

        # Highlight device commands (support dot notation)
        if self.device_keywords:
            # Match word characters and dots for commands like "device.move"
            # Allow whitespace, comma, or start of line before, and whitespace, comma, or end after
            keyword_pattern = r'(?:^|(?<=\s)|(?<=,))(' + '|'.join(re.escape(k) for k in self.device_keywords) + r')(?=\s|,|$)'
            for match in re.finditer(keyword_pattern, content, re.IGNORECASE | re.MULTILINE):
                start, end = match.span(1)
                full_command = match.group(1)
                
                # Check if it has a dot (device.command format)
                if '.' in full_command:
                    dot_pos = full_command.index('.')
                    # Highlight device part (before dot) in purple
                    device_end = start + dot_pos
                    self.text.tag_add("device", f"1.0+{start}c", f"1.0+{device_end}c")
                    # Highlight command part (after dot) in blue
                    command_start = start + dot_pos + 1
                    self.text.tag_add("command", f"1.0+{command_start}c", f"1.0+{end}c")
                else:
                    # No dot, just highlight the whole thing as a command
                    self.text.tag_add("command", f"1.0+{start}c", f"1.0+{end}c")
        
        # Highlight variables (device.variable format) - purple.green
        if self.all_variables:
            variable_pattern = r'(?:^|(?<=\s)|(?<=,))(' + '|'.join(re.escape(v) for v in self.all_variables) + r')(?=\s|,|$)'
            for match in re.finditer(variable_pattern, content, re.IGNORECASE | re.MULTILINE):
                start, end = match.span(1)
                full_variable = match.group(1)
                
                # Variables always have a dot (device.variable format)
                if '.' in full_variable:
                    dot_pos = full_variable.index('.')
                    # Highlight device part (before dot) in purple
                    device_end = start + dot_pos
                    self.text.tag_add("device", f"1.0+{start}c", f"1.0+{device_end}c")
                    # Highlight variable part (after dot) in green
                    variable_start = start + dot_pos + 1
                    self.text.tag_add("variable", f"1.0+{variable_start}c", f"1.0+{end}c")
        
        # Highlight warnings (device.warning format) - purple.red
        if self.all_warnings:
            warning_pattern = r'(?:^|(?<=\s)|(?<=,))(' + '|'.join(re.escape(w) for w in self.all_warnings) + r')(?=\s|,|$)'
            for match in re.finditer(warning_pattern, content, re.IGNORECASE | re.MULTILINE):
                start, end = match.span(1)
                full_warning = match.group(1)
                
                # Warnings always have a dot (device.warning format)
                if '.' in full_warning:
                    dot_pos = full_warning.index('.')
                    # Highlight device part (before dot) in purple
                    device_end = start + dot_pos
                    self.text.tag_add("device", f"1.0+{start}c", f"1.0+{device_end}c")
                    # Highlight warning part (after dot) in red
                    warning_start = start + dot_pos + 1
                    self.text.tag_add("warning", f"1.0+{warning_start}c", f"1.0+{end}c")

        # Highlight reports (device.report_name format) - purple.dark_green
        if self.all_reports:
            report_pattern = r'(?:^|(?<=\s)|(?<=,))(' + '|'.join(re.escape(r) for r in self.all_reports) + r')(?=\s|,|$)'
            for match in re.finditer(report_pattern, content, re.IGNORECASE | re.MULTILINE):
                start, end = match.span(1)
                full_report = match.group(1)
                
                # Reports always have a dot (device.report_name format)
                if '.' in full_report:
                    dot_pos = full_report.index('.')
                    # Highlight device part (before dot) in purple
                    device_end = start + dot_pos
                    self.text.tag_add("device", f"1.0+{start}c", f"1.0+{device_end}c")
                    # Highlight report part (after dot) in dark green
                    report_start = start + dot_pos + 1
                    self.text.tag_add("report", f"1.0+{report_start}c", f"1.0+{end}c")

        # Highlight views (device.view_id format) - purple.lavender
        if self.all_views:
            view_pattern = r'(?:^|(?<=\s)|(?<=,))(' + '|'.join(re.escape(v) for v in self.all_views) + r')(?=\s|,|$)'
            for match in re.finditer(view_pattern, content, re.IGNORECASE | re.MULTILINE):
                start, end = match.span(1)
                full_view = match.group(1)
                
                # Views always have a dot (device.view_id format)
                if '.' in full_view:
                    dot_pos = full_view.index('.')
                    # Highlight device part (before dot) in purple
                    device_end = start + dot_pos
                    self.text.tag_add("device", f"1.0+{start}c", f"1.0+{device_end}c")
                    # Highlight view part (after dot) in lavender
                    view_start = start + dot_pos + 1
                    self.text.tag_add("view", f"1.0+{view_start}c", f"1.0+{end}c")

        # Highlight script commands
        if self.script_keywords:
            keyword_pattern = r'\b(' + '|'.join(re.escape(k) for k in self.script_keywords) + r')\b'
            for match in re.finditer(keyword_pattern, content, re.IGNORECASE):
                start, end = match.span()
                self.text.tag_add("script_command", f"1.0+{start}c", f"1.0+{end}c")
                
                # For logging commands, highlight device names in purple
                cmd = match.group(1).lower()
                if cmd in ['start_logging', 'stop_logging', 'queue_for_logging', 'unqueue_for_logging']:
                    # Find the rest of the line after the command
                    line_start_pos = content.rfind('\n', 0, start) + 1
                    line_end_pos = content.find('\n', end)
                    if line_end_pos == -1:
                        line_end_pos = len(content)
                    
                    params_text = content[end:line_end_pos].strip()
                    if params_text:
                        # Skip whitespace after command
                        params_start = end
                        while params_start < line_end_pos and content[params_start].isspace():
                            params_start += 1
                        
                        # For start_logging and stop_logging, first parameter is the session name (yellow)
                        if cmd in ['start_logging', 'stop_logging']:
                            # Look for quoted string or single word (session name)
                            session_match = re.match(r'"([^"]*)"', content[params_start:line_end_pos])
                            if session_match:
                                # Found quoted string - highlight the entire quoted string including quotes
                                session_end = params_start + len(session_match.group(0))
                                self.text.tag_add("logging_session", f"1.0+{params_start}c", f"1.0+{session_end}c")
                                # Move past the session name for device highlighting
                                params_start = session_end
                            else:
                                # No quotes - look for first word (session name)
                                session_match = re.match(r'(\w+)', content[params_start:line_end_pos])
                                if session_match:
                                    session_name = session_match.group(1)
                                    session_end = params_start + len(session_name)
                                    # Highlight session name in yellow
                                    self.text.tag_add("logging_session", f"1.0+{params_start}c", f"1.0+{session_end}c")
                                    # Move past the session name for device highlighting
                                    params_start = session_end
                        
                        # Get all device names
                        if self.device_manager:
                            device_names = self.device_manager.get_all_device_names()
                            
                            # Parse the remaining parameters region
                            params_region = content[params_start:line_end_pos]
                            
                            # Highlight device names (including in device.variable patterns)
                            for device_name in device_names:
                                # Look for device name followed by optional dot and variable name
                                device_pattern = r'\b(' + re.escape(device_name) + r')(?:\.(\w+))?'
                                for dev_match in re.finditer(device_pattern, params_region, re.IGNORECASE):
                                    dev_start = params_start + dev_match.start(1)
                                    dev_end = params_start + dev_match.end(1)
                                    # Highlight device name in purple
                                    self.text.tag_add("device", f"1.0+{dev_start}c", f"1.0+{dev_end}c")
                                    
                                    # If there's a variable part, highlight it in burgundy
                                    if dev_match.group(2):
                                        var_start = params_start + dev_match.start(2)
                                        var_end = params_start + dev_match.end(2)
                                        self.text.tag_add("variable", f"1.0+{var_start}c", f"1.0+{var_end}c")

        # Highlight colons
        for match in re.finditer(r':', content):
            start, end = match.span()
            self.text.tag_add("colon", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight numbers (integers and floats) - but not inside comments
        for match in re.finditer(r'\b-?\d+(\.\d+)?\b', content):
            start, end = match.span()
            # Check if this is inside a comment
            line_start = content.rfind('\n', 0, start) + 1
            line_content = content[line_start:start]
            if '#' not in line_content:
                self.text.tag_add("parameter", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight valid string parameters (only those defined in enum/options)
        for match in re.finditer(r'\b([a-z_]+)\b', content, re.IGNORECASE):
            word = match.group(1).lower()
            start, end = match.span()
            
            # Skip if in a comment
            line_start = content.rfind('\n', 0, start) + 1
            line_content = content[line_start:start]
            if '#' in line_content:
                continue
            
            # Skip if it's a command keyword
            if word.upper() in [k.upper() for k in (self.device_keywords + self.script_keywords)]:
                continue
            
            # Only highlight if it's a valid string parameter AND comes after a command OR on an indented line
            if word in self.valid_string_params:
                line_before = content[line_start:start]
                has_command = any(cmd.upper() in line_before.upper() for cmd in (self.device_keywords + self.script_keywords))
                # Also check if this is an indented line (part of a parameter block)
                full_line = content[line_start:content.find('\n', start) if '\n' in content[start:] else len(content)]
                is_indented_line = full_line.startswith('\t') or full_line.startswith(' ')
                if has_command or is_indented_line:
                    self.text.tag_add("string", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight comments (do this last so it overrides other highlighting)
        for match in re.finditer(r'#.*', content):
            start, end = match.span()
            self.text.tag_add("comment", f"1.0+{start}c", f"1.0+{end}c")


# --- Themed Script Editor (Rebuilt with Line Numbers) ---

class ScriptEditor(tk.Frame):
    def __init__(self, parent, device_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(bg=theme.WIDGET_BG)
        self.device_manager = device_manager

        # --- Layout ---
        self.text = CustomText(self)
        self.linenumbers = TextLineNumbers(self, width=48, bg=theme.WIDGET_BG, highlightthickness=0, borderwidth=0)
        self.linenumbers.attach(self.text)
        
        # Create scrollbar but don't pack it - mouse wheel still works
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        
        self.linenumbers.pack(side="left", fill="y")
        # self.vsb.pack(side="right", fill="y")  # Hidden - mouse wheel still works
        self.text.pack(side="right", fill="both", expand=True)
        
        # --- Event Bindings ---
        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)
        self.text.bind("<KeyRelease>", self._highlight_current_line)
        self.text.bind("<Button-1>", self._on_change)
        # Tab behavior is handled by the Text widget's configured tab width

        self.text.tag_configure("current_line", background=theme.SECONDARY_ACCENT)
        self._highlight_current_line()
        
        # Get all commands from the manager
        all_commands = self.device_manager.get_all_scripting_commands()
        all_commands.update(SCRIPT_COMMANDS) # Add the generic script commands
        
        # --- Right-click Context Menu ---
        self.context_menu = ThemedContextMenu(self.text, all_commands)
        right_click_event = "<Button-2>" if platform.system() == 'Darwin' else "<Button-3>"
        self.text.bind(right_click_event, self.show_context_menu)

        # Separate the keywords for the highlighter based on the 'device' key
        device_keywords = [cmd for cmd, details in all_commands.items() if details.get('device') not in ['script', 'both']]
        script_keywords = [cmd for cmd, details in all_commands.items() if details.get('device') in ['script', 'both']]
        
        # Add the hardcoded script commands (like CYCLE, REPEAT) to the script keywords
        script_keywords.extend(list(SCRIPT_COMMANDS.keys()))

        self.highlighter = SyntaxHighlighter(self.text, device_keywords, list(set(script_keywords)), device_manager) # Use set to remove duplicates

    def show_context_menu(self, event):
        """Shows the right-click context menu."""
        self.context_menu.show(event)

    def add_command_to_script(self, command_text):
        """A helper method to allow the command reference to insert text."""
        self.text.insert(tk.INSERT, f"{command_text} ")
        self.text.focus_set() # Move focus back to the editor

    def _highlight_current_line(self, event=None):
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")
        self.text.tag_raise("sel") # Raise selection tag to the top of the stacking order
        # Ensure exec_highlight stays on top when running
        if self.text.tag_ranges("exec_highlight"):
            self.text.tag_raise("exec_highlight")

    def _on_change(self, event=None):
        self.linenumbers.redraw()
        self._highlight_current_line()

    # --- Proxy methods to make this class act like a Text widget ---
    def get(self, *args, **kwargs): return self.text.get(*args, **kwargs)
    def insert(self, *args, **kwargs): return self.text.insert(*args, **kwargs)
    def delete(self, *args, **kwargs): return self.text.delete(*args, **kwargs)
    def tag_add(self, *args, **kwargs): return self.text.tag_add(*args, **kwargs)
    def tag_remove(self, *args, **kwargs): return self.text.tag_remove(*args, **kwargs)
    def tag_config(self, *args, **kwargs): return self.text.tag_config(*args, **kwargs)
    def bind(self, *args, **kwargs): self.text.bind(*args, **kwargs)
    def index(self, *args, **kwargs): return self.text.index(*args, **kwargs)
    def edit_modified(self, *args, **kwargs): return self.text.edit_modified(*args, **kwargs)
    def edit_reset(self, *args, **kwargs): return self.text.edit_reset(*args, **kwargs)

# --- Themed Right-click Menu ---
class ThemedContextMenu(tk.Menu):
    def __init__(self, parent_widget, all_commands=None, **kwargs):
        super().__init__(parent_widget, tearoff=0, **kwargs)
        self.parent_widget = parent_widget
        self.all_commands = all_commands or {}

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
        self.add_command(label="Cut", command=self._cut)
        self.add_command(label="Copy", command=self._copy)
        self.add_command(label="Paste", command=self._paste)
        self.add_separator()
        self.add_command(label="Command Help...", command=self._show_command_help)

    def _cut(self):
        self.parent_widget.event_generate("<<Cut>>")

    def _copy(self):
        self.parent_widget.event_generate("<<Copy>>")

    def _paste(self):
        self.parent_widget.event_generate("<<Paste>>")
    
    def _show_command_help(self):
        """Show command help window."""
        CommandHelpWindow(self.parent_widget, self.all_commands)

    def show(self, event):
        """Updates menu state and displays it."""
        # Enable/disable based on selection
        try:
            selection = self.parent_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.entryconfig("Cut", state=tk.NORMAL)
            self.entryconfig("Copy", state=tk.NORMAL)
        except tk.TclError: # No selection
            self.entryconfig("Cut", state=tk.DISABLED)
            self.entryconfig("Copy", state=tk.DISABLED)

        # Enable/disable based on clipboard content
        try:
            clipboard = self.parent_widget.clipboard_get()
            self.entryconfig("Paste", state=tk.NORMAL)
        except tk.TclError: # No clipboard content
            self.entryconfig("Paste", state=tk.DISABLED)

        self.tk_popup(event.x_root, event.y_root)

# --- Validation Window (Themed) ---
class ValidationResultsWindow(tk.Toplevel):
    def __init__(self, parent, errors, on_close_callback=None):
        super().__init__(parent)
        self.on_close_callback = on_close_callback
        self.title("Validation Results")
        self.geometry("600x300")
        self.configure(bg=theme.WIDGET_BG)
        self.transient(parent)
        self.grab_set()
        
        text_area = tk.Text(self, wrap=tk.WORD, 
                                bg=theme.WIDGET_BG, 
                                fg=theme.FG_COLOR, 
                                font=theme.FONT_NORMAL,
                                borderwidth=0,
                                highlightthickness=0)
        text_area.pack(expand=True, fill="both", padx=10, pady=10)
        
        if not errors:
            text_area.insert(tk.END, "Validation successful! No errors found.")
        else:
            for error in errors:
                text_area.insert(tk.END, f"Line {error['line']}: {error['error']}\n")
        
        text_area.config(state=tk.DISABLED)
        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=5)
    
    def destroy(self):
        if self.on_close_callback:
            self.on_close_callback()
        super().destroy()


# --- Command Help Window ---
class CommandHelpWindow(tk.Toplevel):
    def __init__(self, parent, all_commands):
        super().__init__(parent)
        self.title("Script Command Reference")
        self.geometry("800x600")
        self.configure(bg=theme.WIDGET_BG)
        self.transient(parent)
        
        # Create main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Search box
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_commands())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Command list (left side)
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        ttk.Label(list_frame, text="Commands:").pack(anchor=tk.W)
        
        self.command_listbox = tk.Listbox(list_frame, width=30,
                                          bg=theme.WIDGET_BG,
                                          fg=theme.FG_COLOR,
                                          selectbackground=theme.PRIMARY_ACCENT,
                                          selectforeground=theme.SELECTION_FG,
                                          font=theme.FONT_NORMAL)
        self.command_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        listbox_scrollbar = ttk.Scrollbar(list_frame, command=self.command_listbox.yview)
        listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.command_listbox.config(yscrollcommand=listbox_scrollbar.set)
        
        self.command_listbox.bind('<<ListboxSelect>>', self._on_command_select)
        
        # Details panel (right side)
        details_frame = ttk.Frame(main_frame)
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(details_frame, text="Command Details:").pack(anchor=tk.W)
        
        self.details_text = tk.Text(details_frame, wrap=tk.WORD,
                                    bg=theme.WIDGET_BG,
                                    fg=theme.FG_COLOR,
                                    font=theme.FONT_NORMAL,
                                    borderwidth=1,
                                    relief=tk.SOLID)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        details_scrollbar = ttk.Scrollbar(details_frame, command=self.details_text.yview)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=details_scrollbar.set)
        
        # Configure text tags for formatting
        self.details_text.tag_configure("title", font=theme.FONT_BOLD, foreground=theme.PRIMARY_ACCENT)
        self.details_text.tag_configure("section", font=theme.FONT_BOLD)
        self.details_text.tag_configure("code", font=theme.FONT_NORMAL, background=theme.SECONDARY_ACCENT)
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=self.destroy)
        close_button.pack(pady=(10, 0))
        
        # Store commands and populate list
        self.all_commands = all_commands
        self._populate_command_list()
    
    def _populate_command_list(self):
        """Populate the command listbox with all commands."""
        self.command_listbox.delete(0, tk.END)
        
        # Sort commands by category
        script_commands = []
        device_commands = []
        
        for cmd_name, cmd_info in sorted(self.all_commands.items()):
            device = cmd_info.get('device', 'unknown')
            if device in ['script', 'both']:
                script_commands.append(cmd_name)
            else:
                device_commands.append(f"{cmd_name}")
        
        # Add script commands first
        if script_commands:
            for cmd in sorted(script_commands):
                self.command_listbox.insert(tk.END, cmd)
        
        # Add device commands
        if device_commands:
            for cmd in sorted(device_commands):
                self.command_listbox.insert(tk.END, cmd)
    
    def _filter_commands(self):
        """Filter commands based on search text."""
        search_text = self.search_var.get().lower()
        self.command_listbox.delete(0, tk.END)
        
        for cmd_name, cmd_info in sorted(self.all_commands.items()):
            if search_text in cmd_name.lower() or search_text in cmd_info.get('description', '').lower():
                self.command_listbox.insert(tk.END, cmd_name)
    
    def _on_command_select(self, event):
        """Display details for the selected command."""
        selection = self.command_listbox.curselection()
        if not selection:
            return
        
        cmd_name = self.command_listbox.get(selection[0])
        cmd_info = self.all_commands.get(cmd_name, {})
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        # Command name
        self.details_text.insert(tk.END, f"{cmd_name}\n", "title")
        self.details_text.insert(tk.END, "\n")
        
        # Description
        description = cmd_info.get('description', 'No description available.')
        self.details_text.insert(tk.END, "Description:\n", "section")
        self.details_text.insert(tk.END, f"{description}\n\n")
        
        # Parameters
        params = cmd_info.get('params', [])
        if params:
            self.details_text.insert(tk.END, "Parameters:\n", "section")
            for param in params:
                param_text = f"  • {param}\n"
                self.details_text.insert(tk.END, param_text)
            self.details_text.insert(tk.END, "\n")
        
        # Examples (special handling for logging commands)
        self.details_text.insert(tk.END, "Examples:\n", "section")
        
        if cmd_name == "queue_for_logging":
            example = """  queue_for_logging device.force device.position
  
  This queues variables for logging. They will be written
  to CSV when start_logging is called. You can also use
  an indented block:
  
  queue_for_logging
      device.force
      device.position
      device.torque"""
            self.details_text.insert(tk.END, example, "code")
        
        elif cmd_name == "start_logging":
            example = """  start_logging "test_data.csv" device
  start_logging "<date>-<time> data.csv" device1 device2
  
  Starts logging queued variables to a CSV file.
  Use <date> and <time> tags for automatic timestamps.
  
  Example workflow:
  queue_for_logging device.force device.position
  start_logging "my_data.csv" device
  # Your test commands here
  stop_logging"""
            self.details_text.insert(tk.END, example, "code")
        
        elif cmd_name == "stop_logging":
            example = """  stop_logging
  
  Stops logging and closes the CSV file.
  Use this at the end of your test."""
            self.details_text.insert(tk.END, example, "code")
        
        elif cmd_name == "unqueue_for_logging":
            example = """  unqueue_for_logging device.force
  
  Removes specific variables from the logging queue."""
            self.details_text.insert(tk.END, example, "code")
        
        elif cmd_name == "wait":
            example = """  wait 2 sec
  wait 500 ms
  
  Pauses script execution for the specified duration."""
            self.details_text.insert(tk.END, example, "code")
        
        elif cmd_name == "cycle":
            example = """  cycle 5
      device.move_abs 50 mm 10 mm/s
      wait 1 sec
      device.retract 20 mm/s
  
  Repeats the indented block 5 times."""
            self.details_text.insert(tk.END, example, "code")
        
        else:
            # Generic example for device commands
            device = cmd_info.get('device', '')
            if device and device not in ['script', 'both']:
                example = f"  {cmd_name} [parameters]"
            else:
                example = f"  {cmd_name}"
            self.details_text.insert(tk.END, example, "code")
        
        self.details_text.config(state=tk.DISABLED)


class ScriptTab:
    """Per-tab state for the multi-tab script editor."""
    __slots__ = ('editor', 'tab_frame', 'filepath', 'find_replace_frame')

    def __init__(self, editor, tab_frame, filepath=None):
        self.editor = editor
        self.tab_frame = tab_frame
        self.filepath = filepath
        self.find_replace_frame = None


class _ActiveEditorProxy:
    """Proxy that delegates attribute access to whichever ScriptEditor is currently active.

    This allows the DevicePanel (and other external consumers) to hold a single
    reference that always points to the correct tab's editor.
    """

    def __init__(self, get_active_fn):
        object.__setattr__(self, '_get_active', get_active_fn)

    def __getattr__(self, name):
        editor = object.__getattribute__(self, '_get_active')()
        if editor is not None:
            return getattr(editor, name)
        raise AttributeError(f"No active editor for attribute '{name}'")


def create_scripting_interface(parent, command_funcs, shared_gui_refs, autosave_var, initial_lock_state=False, toolbar_parent=None):
    """
    Creates the main scripting area with a tabbed editor.
    Returns a dictionary containing file commands and a callback to update the recent menu.
    
    Args:
        initial_lock_state: Initial state for the editor lock (default: False/unlocked)
        toolbar_parent: If provided, the toolbar (Run/Hold/Reset/status) is created as
            a child of this frame instead of inside the editor area.  This lets the
            caller keep the toolbar visible while collapsing the editor.
    """
    _toolbar_parent = toolbar_parent or parent

    scripting_area = ttk.Frame(parent, style='TFrame')
    scripting_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 5))

    # Get a reference to the root window for thread-safe GUI updates
    root = scripting_area.winfo_toplevel()
    
    # --- Get Device Manager and Commands ---
    device_manager = shared_gui_refs.get('device_manager')
    if not device_manager:
        # Handle case where device manager isn't available
        scripting_area.add(ttk.Label(scripting_area, text="Error: Device Manager not found."))
        return {}
    
    # Helper to get fresh commands
    def get_current_commands():
        if not device_manager:
            return SCRIPT_COMMANDS.copy()
        cmds = device_manager.get_all_scripting_commands()
        # SCRIPT_COMMANDS are already included by get_all_scripting_commands
        # but we can update just to be safe if the manager implementation changes
        cmds.update(SCRIPT_COMMANDS) 
        return cmds

    device_modules = device_manager.get_device_modules()

    # Editor widgets live directly in scripting_area (the old horizontal
    # PanedWindow only had one pane, so it was redundant).
    left_pane = scripting_area

    # --- Scripting State Variables ---
    script_runner = None
    current_run_token = None  # Unique token for the current run
    last_exec_highlight = -1
    last_selection_highlight = 1
    current_filepath = None
    feed_hold_line = None
    paused_device = None  # Track which device was paused (for resume)
    is_held_by_user = False # Flag to manage Hold state vs. a normal stop
    single_block_var = tk.BooleanVar(value=False)
    # Always start unlocked - lock will be applied after file loading if needed
    lock_editor_var = tk.BooleanVar(value=False)
    # Track script timing for cycle stats
    script_start_time = None

    # --- Tab Management State ---
    tabs = []  # List[ScriptTab]
    running_tab = None  # The ScriptTab whose script is currently executing

    # --- Message Queue & Terminal ---
    message_queue = queue.Queue()
    original_terminal_cb = shared_gui_refs.get('terminal_cb')
    if 'vacuum_check_status_var' not in shared_gui_refs:
        shared_gui_refs['vacuum_check_status_var'] = tk.StringVar(value='N/A')

    recent_files_menu_ref = None

    def terminal_wrapper(message):
        # --- Intercept ERROR and RECOVERY messages to display them prominently ---
        if "_ERROR:" in message or "_RECOVERY:" in message or "RECOVERY:" in message:
            # The root.after is crucial to prevent threading issues with Tkinter
            root.after(0, lambda: status_label.config(foreground=theme.ERROR_RED)) # Bright Red
            root.after(0, lambda: status_var.set(message))
            
            # Trigger script hold if script is running (but don't send cancel - device is already handling the error)
            nonlocal script_runner, is_held_by_user, feed_hold_line, last_exec_highlight
            if script_runner and script_runner.is_running:
                is_held_by_user = True
                feed_hold_line = last_exec_highlight
                # Don't call abort() - it would interrupt the device's error handling (e.g. retract)
                # Just put the script runner into hold state
                if hasattr(script_runner, 'is_held'):
                    script_runner.is_held = True
            # Always refresh button states to show error (even when no script running)
            root.after(0, refresh_button_states)

        # Add DONE and RECOVERY messages to queue for script processor
        if "DONE:" in message or "_RECOVERY:" in message or "RECOVERY:" in message:
            print(f"[DEBUG] terminal_wrapper adding to queue: {message}")
            message_queue.put(message)
            
            # If this is DONE: reset, clear the error state
            if "DONE:" in message and "reset" in message.lower():
                root.after(0, lambda: status_label.config(foreground=theme.PRIMARY_ACCENT))  # Clear red
                if not (script_runner and script_runner.is_running):
                    # No script running - clear the status
                    root.after(0, lambda: status_var.set("Reset complete."))
                root.after(0, refresh_button_states)
        
        if original_terminal_cb: original_terminal_cb(message)

    shared_gui_refs['terminal_cb'] = terminal_wrapper

    # --- UI Creation ---
    # Toolbar (Run/Hold/Reset/Status) goes into _toolbar_parent so the caller
    # can keep it visible independently of the editor area.
    control_frame = ttk.Frame(_toolbar_parent, style='TFrame');
    control_frame.pack(fill=tk.X, pady=(0, 0))
    
    # --- Logging Status Label (shows current log file when logging) ---
    logging_status_var = tk.StringVar(value=" ")  # Space to maintain height
    logging_status_label = ttk.Label(_toolbar_parent, textvariable=logging_status_var, anchor='w',
                                     font=theme.FONT_SMALL,
                                     foreground='#B0B0B0',
                                     background=theme.BG_COLOR)
    logging_status_label.pack(fill=tk.X, padx=10, pady=(0, 3))

    # --- Tabbed Editor Notebook ---
    style = ttk.Style()
    style.configure('ScriptTabs.TNotebook', background=theme.BG_COLOR, borderwidth=0, padding=0)
    style.configure('ScriptTabs.TNotebook.Tab',
                    background=theme.WIDGET_BG,
                    foreground=theme.COMMENT_COLOR,
                    padding=[12, 4],
                    borderwidth=0)
    style.map('ScriptTabs.TNotebook.Tab',
              background=[('selected', theme.BG_COLOR), ('active', theme.SECONDARY_ACCENT)],
              foreground=[('selected', theme.FG_COLOR), ('active', theme.FG_COLOR)],
              expand=[('selected', [1, 1, 1, 0])])
    tab_bar_frame = ttk.Frame(left_pane, style='TFrame')
    tab_bar_frame.pack(fill=tk.X, padx=10, pady=(0, 0))

    notebook = ttk.Notebook(tab_bar_frame, style='ScriptTabs.TNotebook')
    notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # "+" button to create a new empty tab
    add_tab_btn = ttk.Button(tab_bar_frame, text="+", width=3,
                             style='Ghost.TButton',
                             command=lambda: new_script())
    add_tab_btn.pack(side=tk.RIGHT, padx=(4, 0), pady=2)

    editor_container = ttk.Frame(left_pane, style='TFrame')
    editor_container.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

    # --- Tab Management Helpers ---

    def _setup_editor_for_tab(tab):
        """Configure per-editor bindings and tags for a newly created tab."""
        editor = tab.editor
        editor.tag_config("exec_highlight", background=theme.WARNING_YELLOW, foreground="black")
        editor.tag_config("selection_highlight", background=theme.SECONDARY_ACCENT)
        editor.tag_config("error_highlight", background=theme.ERROR_RED, foreground=theme.FG_COLOR)
        editor.text.config(state='disabled' if lock_editor_var.get() else 'normal')

        tab.find_replace_frame = FindReplaceFrame(tab.tab_frame, editor.text)
        editor.text.bind("<Control-f>", lambda e, t=tab: t.find_replace_frame.show())
        editor.text.bind("<Control-h>", lambda e, t=tab: t.find_replace_frame.show())

    def create_new_tab(filepath=None, content=None, switch_to=True):
        """Create a new tab with its own ScriptEditor. Returns the ScriptTab."""
        nonlocal current_filepath

        tab_frame = ttk.Frame(notebook)
        editor = ScriptEditor(tab_frame, device_manager=device_manager)
        editor.pack(fill="both", expand=True)

        tab = ScriptTab(editor, tab_frame, filepath)
        tabs.append(tab)

        if filepath:
            import tempfile
            if filepath.startswith(tempfile.gettempdir()):
                label = "Untitled"
            else:
                label = os.path.basename(filepath)
        else:
            label = "Untitled"

        notebook.add(tab_frame, text=label)
        _setup_editor_for_tab(tab)

        # Wire modification / click callbacks (late-bound so the closures defined
        # later in this function are available at call time)
        def _bind_tab_events():
            editor.bind("<<Modified>>", on_text_modified, add='+')
            editor.bind("<Button-1>", on_line_click)
        root.after(0, _bind_tab_events)

        if content:
            editor.delete('1.0', tk.END)
            editor.insert('1.0', content)
            editor.edit_modified(False)

        if switch_to:
            notebook.select(tab_frame)
            current_filepath = tab.filepath

        _save_tab_state()
        return tab

    def get_active_tab():
        """Return the currently selected ScriptTab, or None."""
        if not tabs:
            return None
        try:
            sel = notebook.select()
            if not sel:
                return tabs[0]
            current_frame = notebook.nametowidget(sel)
            for tab in tabs:
                if tab.tab_frame is current_frame:
                    return tab
        except (tk.TclError, KeyError):
            pass
        return tabs[0] if tabs else None

    def get_active_editor():
        """Return the active tab's ScriptEditor widget."""
        tab = get_active_tab()
        return tab.editor if tab else None

    def update_tab_label(tab):
        """Refresh a tab's label text (filename, modified indicator, running indicator)."""
        if tab.filepath:
            import tempfile
            if tab.filepath.startswith(tempfile.gettempdir()):
                label = "Untitled"
            else:
                label = os.path.basename(tab.filepath)
        else:
            label = "Untitled"
        try:
            if tab.editor.edit_modified():
                label += " *"
        except tk.TclError:
            pass
        if running_tab is tab:
            label = "\u25b6 " + label
        try:
            notebook.tab(tab.tab_frame, text=label)
        except tk.TclError:
            pass

    def _set_filepath(path):
        """Set the filepath for the active tab and sync current_filepath."""
        nonlocal current_filepath
        current_filepath = path
        tab = get_active_tab()
        if tab:
            tab.filepath = path
            update_tab_label(tab)

    def _sync_filepath_from_tab():
        """Sync current_filepath from the active tab."""
        nonlocal current_filepath
        tab = get_active_tab()
        current_filepath = tab.filepath if tab else None

    def close_tab(tab=None, force=False):
        """Close a tab. Returns True if closed, False if user cancelled."""
        nonlocal current_filepath
        if tab is None:
            tab = get_active_tab()
        if tab is None:
            return True

        if tab is running_tab and not force:
            messagebox.showwarning("Cannot Close Tab",
                                   "This tab is running a script. Stop the script first.")
            return False

        if not force:
            is_modified = tab.editor.edit_modified()
            import tempfile
            is_temp = tab.filepath and tab.filepath.startswith(tempfile.gettempdir())
            has_content = len(tab.editor.get('1.0', tk.END).strip()) > 0

            if is_temp and has_content:
                notebook.select(tab.tab_frame)
                _sync_filepath_from_tab()
                response = messagebox.askyesnocancel(
                    "Save Untitled Script?",
                    "This script has not been saved to a permanent location. Save it?")
                if response is True:
                    if not save_script():
                        return False
                elif response is None:
                    return False
            elif is_modified:
                notebook.select(tab.tab_frame)
                _sync_filepath_from_tab()
                name = os.path.basename(tab.filepath) if tab.filepath else "Untitled"
                response = messagebox.askyesnocancel(
                    "Unsaved Changes", f"'{name}' has unsaved changes. Save?")
                if response is True:
                    if not save_script():
                        return False
                elif response is None:
                    return False

        if tab in tabs:
            tabs.remove(tab)
        try:
            notebook.forget(tab.tab_frame)
        except tk.TclError:
            pass
        tab.tab_frame.destroy()

        if not tabs:
            create_new_tab()
        else:
            _sync_filepath_from_tab()
            update_window_title()

        _save_tab_state()
        return True

    def _on_tab_changed(event):
        """Handle notebook tab-selection changes."""
        _sync_filepath_from_tab()
        update_window_title()
        tab = get_active_tab()
        if tab:
            try:
                current_line = int(tab.editor.index(tk.INSERT).split('.')[0])
                update_selection_highlight(current_line)
            except (tk.TclError, ValueError):
                pass

    notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)

    # Right-click on tab header for close option
    def _tab_right_click(event):
        try:
            clicked_index = notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        if clicked_index < 0 or clicked_index >= len(tabs):
            return
        tab = tabs[clicked_index]
        menu = tk.Menu(notebook, tearoff=0,
                       bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                       activebackground=theme.PRIMARY_ACCENT,
                       activeforeground=theme.FG_COLOR)
        menu.add_command(label="Close Tab", command=lambda: close_tab(tab))
        menu.add_command(label="Close Other Tabs",
                         command=lambda: _close_other_tabs(tab))
        menu.tk_popup(event.x_root, event.y_root)

    def _close_other_tabs(keep_tab):
        for t in list(tabs):
            if t is not keep_tab:
                close_tab(t)

    notebook.bind("<Button-3>", _tab_right_click)

    def _save_tab_state():
        """Persist open tab file paths and active index to config."""
        try:
            from src.config import load_config, save_config
            config = load_config()
            import tempfile
            tab_paths = []
            for t in tabs:
                if t.filepath and not t.filepath.startswith(tempfile.gettempdir()):
                    tab_paths.append(t.filepath)
            config['open_script_tabs'] = tab_paths
            active = get_active_tab()
            config['active_script_tab_index'] = tabs.index(active) if active and active in tabs else 0
            save_config(config)
        except Exception:
            pass

    def _find_tab_by_filepath(filepath):
        """Find an existing tab that has the given filepath open."""
        norm = os.path.normpath(filepath)
        for tab in tabs:
            if tab.filepath and os.path.normpath(tab.filepath) == norm:
                return tab
        return None

    # Keyboard shortcuts for tab management
    root.bind("<Control-w>", lambda e: close_tab())
    root.bind("<Control-n>", lambda e: new_script())

    # Create a proxy so external consumers (DevicePanel) always talk to the active editor
    script_editor_proxy = _ActiveEditorProxy(get_active_editor)

    # Create one initial empty tab so script_editor is never None at first use
    _first_tab = create_new_tab()
    script_editor = _first_tab.editor

    # The command reference is no longer created here.

    def update_window_title():
        tab = get_active_tab()
        filename = "Untitled"
        unsaved_tag = ""
        fp = tab.filepath if tab else current_filepath
        if fp:
            filename = os.path.basename(fp)
            import tempfile
            if fp.startswith(tempfile.gettempdir()):
                filename = "Untitled"
                unsaved_tag = " (unsaved)"
        try:
            editor = tab.editor if tab else None
            modified_star = "*" if editor and editor.edit_modified() else ""
        except tk.TclError:
            modified_star = ""
        root.title(f"{filename}{modified_star}{unsaved_tag} - BR Equipment Control App")
        if tab:
            update_tab_label(tab)

    def on_text_modified(event):
        """Updates window title and triggers autosave for ALL open tabs."""
        update_window_title()

        if loading_file[0]:
            pass
        elif autosave_var.get():
            # Autosave every tab that has a filepath
            for t in tabs:
                if t.filepath and t.editor.edit_modified():
                    try:
                        with open(t.filepath, 'w') as f:
                            f.write(t.editor.get('1.0', 'end-1c'))
                        t.editor.edit_modified(False)
                        update_tab_label(t)
                    except Exception as e:
                        status_var.set(f"Autosave Error: {e}")

        tab = get_active_tab()
        if tab:
            try:
                current_line = int(tab.editor.index(tk.INSERT).split('.')[0])
                update_selection_highlight(current_line)
            except (tk.TclError, ValueError):
                pass

    # Binding for autosave/title update is now set per-tab in create_new_tab()

    status_var = tk.StringVar(value="Status: Idle")
    shared_gui_refs['status_var'] = status_var  # Make accessible to operator views

    # --- Recent Files Menu Management ---
    def update_recent_files_display():
        if not recent_files_menu_ref: return
        recent_files_menu_ref.delete(0, tk.END)
        filepaths = load_recent_files()
        if not filepaths:
            recent_files_menu_ref.add_command(label="Empty", state=tk.DISABLED)
        else:
            for path in filepaths:
                recent_files_menu_ref.add_command(label=os.path.basename(path),
                                                  command=partial(load_specific_script, path))

    def set_recent_menu_reference(menu_obj):
        nonlocal recent_files_menu_ref
        recent_files_menu_ref = menu_obj
        update_recent_files_display()

    # --- File Operations (tab-aware) ---
    def check_all_unsaved_changes():
        """Check ALL tabs for unsaved changes before app close. Returns True to proceed."""
        for tab in list(tabs):
            editor = tab.editor
            import tempfile
            is_temp = tab.filepath and tab.filepath.startswith(tempfile.gettempdir())
            has_content = len(editor.get('1.0', tk.END).strip()) > 0
            is_modified = editor.edit_modified()

            if (is_temp and has_content) or is_modified:
                notebook.select(tab.tab_frame)
                _sync_filepath_from_tab()
                name = os.path.basename(tab.filepath) if tab.filepath and not is_temp else "Untitled"
                response = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    f"'{name}' has unsaved changes. Save before closing?")
                if response is True:
                    if not save_script():
                        return False
                elif response is None:
                    return False
        return True

    def new_script():
        """Create a new empty tab."""
        nonlocal current_filepath
        import tempfile, datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"untitled_{timestamp}.txt")
        try:
            with open(temp_path, 'w') as f:
                f.write("")
        except Exception:
            temp_path = None

        tab = create_new_tab(filepath=temp_path)
        current_filepath = tab.filepath
        update_window_title()
        update_selection_highlight(1)

    def save_script():
        """Save the active tab's content."""
        nonlocal current_filepath
        tab = get_active_tab()
        if not tab:
            return False
        editor = tab.editor

        import tempfile
        is_temp = tab.filepath and tab.filepath.startswith(tempfile.gettempdir())

        if tab.filepath and not is_temp:
            try:
                with open(tab.filepath, 'w') as f:
                    f.write(editor.get('1.0', 'end-1c'))
                editor.edit_modified(False)
                current_filepath = tab.filepath
                update_window_title()
                status_var.set(f"Saved to {os.path.basename(tab.filepath)}")
                add_to_recent_files(tab.filepath)
                update_recent_files_display()
                _save_tab_state()
                return True
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save file:\n{e}")
                return False
        else:
            return save_script_as()

    def save_script_as():
        """Save the active tab with a new filename."""
        nonlocal current_filepath
        tab = get_active_tab()
        if not tab:
            return False

        import tempfile
        old_temp = None
        if tab.filepath and tab.filepath.startswith(tempfile.gettempdir()):
            old_temp = tab.filepath

        filepath = filedialog.asksaveasfilename(
            title="Save Script As", defaultextension=".breq",
            filetypes=(("BR Equipment Script files", "*.breq"),
                       ("Text files", "*.txt"), ("All files", "*.*")))
        if not filepath:
            return False

        _set_filepath(filepath)
        current_filepath = filepath
        result = save_script()

        if result and old_temp:
            try:
                os.remove(old_temp)
            except Exception:
                pass
        return result

    def load_specific_script(filepath):
        """Open *filepath* in a new tab, or switch to it if already open."""
        nonlocal current_filepath

        if not os.path.exists(filepath):
            messagebox.showerror("File Not Found", f"Could not find file:\n{filepath}")
            filepaths = load_recent_files()
            if filepath in filepaths:
                filepaths.remove(filepath)
                save_recent_files(filepaths)
            update_recent_files_display()
            return

        existing = _find_tab_by_filepath(filepath)
        if existing:
            notebook.select(existing.tab_frame)
            _sync_filepath_from_tab()
            update_window_title()
            return

        try:
            with open(filepath, 'r') as f:
                content = f.read()

            tab = create_new_tab(filepath=filepath, content=content)
            tab.editor.edit_modified(False)
            current_filepath = filepath
            update_window_title()
            update_selection_highlight(1)
            status_var.set(f"Loaded {os.path.basename(filepath)}")
            add_to_recent_files(filepath)
            update_recent_files_display()
            _save_tab_state()
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file:\n{e}")

    def load_script():
        filepath = filedialog.askopenfilename(
            title="Open Script File",
            filetypes=(("BR Equipment Script files", "*.breq"),
                       ("Text files", "*.txt"), ("All files", "*.*")))
        if not filepath:
            return
        load_specific_script(filepath)

    # --- Script Execution Logic ---
    def handle_cycle_start():
        nonlocal feed_hold_line, is_held_by_user, last_block_end_line, paused_device
        
        # Get fresh commands for execution/validation
        scripting_commands = get_current_commands()
        
        # Check if script runner is in held state (ERROR occurred)
        if script_runner and hasattr(script_runner, 'is_held') and script_runner.is_held:
            # Resume after error
            print("[RESUME] Resuming script after ERROR hold")
            script_runner.resume_after_error()
            is_held_by_user = False
            refresh_button_states()
            return
        
        is_held_by_user = False

        # Clear invalid feed_hold_line values
        if feed_hold_line == -1:
            feed_hold_line = None
        
        # Check if we're resuming before clearing feed_hold_line
        is_resuming = feed_hold_line is not None
        resume_line_num = feed_hold_line if is_resuming else None
        
        if not is_resuming:
            if not check_script_validity(): 
                return
            # Validation passed - show starting status
            status_var.set("Starting execution...")
        else:
            # Resuming from hold
            status_var.set(f"Resuming from line {feed_hold_line}...")
            
            # If we paused a device, send resume command instead of re-executing
            if paused_device:
                print(f"[RESUME] Sending resume to {paused_device} at line {feed_hold_line}")
                device_to_resume = paused_device
                paused_device = None
                feed_hold_line = None
                # Just send resume directly without ScriptRunner - don't advance line
                # The move will continue and we'll stay on the current line
                send_func_name = f'send_{device_to_resume}'
                if send_func_name in shared_gui_refs['command_funcs']:
                    shared_gui_refs['command_funcs'][send_func_name]('resume')
                    status_var.set(f"Resumed {device_to_resume} at line {resume_line_num}...")
                    # Set buttons to show we're not running anymore (move continues in background)
                    refresh_button_states()
                return

        active_ed = get_active_editor()
        if active_ed:
            active_ed.tag_remove("selection_highlight", "1.0", tk.END)

        start_line_num = 1
        if is_resuming:
            start_line_num = feed_hold_line
        else:
            try:
                start_line_num = int(last_selection_highlight)
            except (ValueError, TypeError):
                start_line_num = 1

        feed_hold_line = None

        update_selection_highlight(start_line_num)
        is_single_block = single_block_var.get()
        all_lines = active_ed.get("1.0", tk.END).splitlines() if active_ed else []

        next_valid_line_num = -1
        next_valid_line_content = ""
        for i in range(start_line_num - 1, len(all_lines)):
            line_content = all_lines[i].strip()
            if line_content and not line_content.startswith('#'):
                next_valid_line_num = i + 1
                next_valid_line_content = all_lines[i]
                break

        if next_valid_line_num == -1:
            status_var.set("End of script reached.")
            update_button_states(running=False, holding=False)
            return

        update_selection_highlight(next_valid_line_num)

        if is_single_block:
            # Check if this is a logging command or cycle with an indented block
            import shlex
            try:
                parts = shlex.split(next_valid_line_content.strip())
            except ValueError:
                parts = next_valid_line_content.strip().split()
            
            command_word = parts[0].lower() if parts else ''
            
            # Collect content including indented block if present
            # ANY command can have an indented parameter block (not just logging/cycle commands)
            block_content = next_valid_line_content
            block_end_line = next_valid_line_num
            has_indented_block = False
            
            # Get base indentation of the command line (handle tabs)
            current_line_raw = all_lines[next_valid_line_num - 1]
            base_indent_str = current_line_raw[:len(current_line_raw) - len(current_line_raw.lstrip())]
            base_indent_expanded = base_indent_str.expandtabs(4)
            base_indent_level = len(base_indent_expanded)
            
            # Look for indented lines below (start from next line)
            indented_lines = [current_line_raw]
            for idx in range(next_valid_line_num, len(all_lines)):  # Start from next line
                check_line = all_lines[idx]
                check_stripped = check_line.strip()
                
                # Skip empty lines and comments
                if not check_stripped or check_stripped.startswith('#'):
                    continue
                
                # Check indentation (handle tabs)
                check_indent_str = check_line[:len(check_line) - len(check_line.lstrip())]
                check_indent_expanded = check_indent_str.expandtabs(4)
                check_indent_level = len(check_indent_expanded)
                
                if check_indent_level > base_indent_level:
                    # This is an indented line - part of the block
                    indented_lines.append(check_line)
                    block_end_line = idx + 1
                    has_indented_block = True
                else:
                    # End of indented block
                    break
            
            # Combine into block content
            block_content = '\n'.join(indented_lines)
            
            # Store the block end line so on_step_finished knows where to go next
            last_block_end_line = block_end_line
            
            # Validate the block (not just the first line)
            # For commands with indented blocks, skip validation since they'll be collapsed by processor
            if has_indented_block:
                # It's a multi-line block, skip detailed validation
                # The script processor will collapse and validate when executing
                errors = []
            else:
                errors = validate_single_line(next_valid_line_content, next_valid_line_num, scripting_commands)
            if active_ed:
                active_ed.tag_remove("error_highlight", "1.0", tk.END)
            if errors:
                ValidationResultsWindow(scripting_area, errors)
                if active_ed:
                    active_ed.tag_add("error_highlight", f"{next_valid_line_num}.0", f"{next_valid_line_num}.end")
                status_var.set(f"Error on line {next_valid_line_num}.")
                update_button_states(running=False, holding=False)
                return
            # Check if required devices for this line are connected
            required_devices_for_line = set()
            import shlex
            try:
                check_parts = shlex.split(block_content)
            except ValueError:
                check_parts = block_content.split()
            
            for part in check_parts:
                if '.' in part:
                    device_name = part.split('.')[0].lower()
                    if device_name in device_manager.device_state:
                        required_devices_for_line.add(device_name)
            
            # Check if line command references a device
            if check_parts:
                cmd = check_parts[0].lower()
                cmd_info = scripting_commands.get(cmd)
                if cmd_info and cmd_info.get('device') not in ['script', 'both', None]:
                    required_devices_for_line.add(cmd_info['device'])
            
            # Verify devices are connected
            if required_devices_for_line:
                disconnected = []
                for dev_name in required_devices_for_line:
                    dev_state = device_manager.get_device_state(dev_name)
                    if not dev_state or not dev_state.get('connected'):
                        disconnected.append(dev_name)
                
                if disconnected:
                    error_msg = f"Cannot execute line {next_valid_line_num}: Device(s) not connected: {', '.join(disconnected)}"
                    status_var.set(error_msg)
                    if active_ed:
                        active_ed.tag_add("error_highlight", f"{next_valid_line_num}.0", f"{next_valid_line_num}.end")

                    import tkinter.messagebox as messagebox
                    messagebox.showerror(
                        "Devices Not Connected",
                        f"Cannot execute line {next_valid_line_num}.\n\nThe following devices are not connected:\n\n{', '.join(disconnected)}\n\nPlease connect the devices or start their simulators."
                    )
                    update_button_states(running=False, holding=False)
                    return
            
            run_script_from_content(block_content, next_valid_line_num - 1, is_step=True)
        else:
            content_from_line = "\n".join(all_lines[next_valid_line_num - 1:])
            run_script_from_content(content_from_line, next_valid_line_num - 1, is_step=False)

    # List to store additional button sets (for operator views)
    additional_button_sets = []
    
    def refresh_button_states():
        """Refresh button states based on ACTUAL current state."""
        # Check the actual state right now
        is_running = script_runner is not None and script_runner.is_running
        # Check both feed_hold_line and script_runner.is_held for holding state
        is_holding = feed_hold_line is not None or (script_runner and hasattr(script_runner, 'is_held') and script_runner.is_held)
        # Check if we're in error hold state (vs normal hold)
        is_error_hold = is_holding and script_runner and hasattr(script_runner, 'is_held') and script_runner.is_held
        print(f"[refresh_button_states] Running: {is_running}, Holding: {is_holding}, Error hold: {is_error_hold}")
        
        # Update all button sets (main + operator views)
        all_button_sets = [(run_button, hold_button)] + additional_button_sets
        
        for run_btn, hold_btn in all_button_sets:
            # Check if this is a ttk button (main GUI) or tk button (operator view)
            is_ttk = isinstance(run_btn, ttk.Button)
            
            if is_holding:
                if is_error_hold:
                    # Error hold - both buttons disabled, only Reset or Stop can be used
                    run_btn.config(state=tk.DISABLED, text='Run')
                    hold_btn.config(state=tk.DISABLED, text='Holding')
                    if is_ttk:
                        run_btn.config(style='Disabled.Green.TButton')
                        hold_btn.config(style='ErrorHold.Red.TButton')
                    else:
                        run_btn.config(bg='#4a4a4a', fg='#808080')
                        hold_btn.config(bg=theme.HOLDING_RED, fg='white')
                else:
                    # Normal hold (user clicked Hold) - Run can continue, Holding can be clicked
                    run_btn.config(state=tk.NORMAL, text='Run')
                    hold_btn.config(state=tk.NORMAL, text='Holding')
                    if is_ttk:
                        run_btn.config(style='Green.TButton')
                        hold_btn.config(style='Holding.Red.TButton')
                    else:
                        run_btn.config(bg=theme.SUCCESS_GREEN, fg='black')
                        hold_btn.config(bg=theme.HOLDING_RED, fg='white')
            elif is_running:
                run_btn.config(state=tk.DISABLED, text='Running...')
                hold_btn.config(state=tk.NORMAL, text='Hold')
                if is_ttk:
                    run_btn.config(style='Running.Green.TButton')
                    hold_btn.config(style='Red.TButton')
                else:
                    run_btn.config(bg=theme.RUNNING_GREEN, fg='white')
                    hold_btn.config(bg=theme.ERROR_RED, fg='black')
            else:
                run_btn.config(state=tk.NORMAL, text='Run')
                hold_btn.config(state=tk.DISABLED, text='Hold')
                if is_ttk:
                    run_btn.config(style='Green.TButton')
                    hold_btn.config(style='Red.TButton')
                else:
                    run_btn.config(bg=theme.SUCCESS_GREEN, fg='black')
                    hold_btn.config(bg=theme.ERROR_RED, fg='black')
    
    def update_button_states(running=False, holding=False):
        """Legacy function for explicit state setting."""
        refresh_button_states()

    def status_callback_handler(message, line_num):
        def update_gui():
            nonlocal last_exec_highlight, is_held_by_user, feed_hold_line

            status_var.set(message)

            if "_ERROR:" in message or "_RECOVERY:" in message or "RECOVERY:" in message:
                if script_runner and script_runner.is_running:
                    is_held_by_user = True
                    feed_hold_line = line_num if line_num != -1 else last_exec_highlight
                    shared_gui_refs['command_funcs']['abort']()
                refresh_button_states()

            # Apply execution highlight on the running tab's editor (not the active tab)
            rt_editor = running_tab.editor if running_tab else get_active_editor()
            if rt_editor and last_exec_highlight != line_num:
                if last_exec_highlight != -1:
                    rt_editor.tag_remove("exec_highlight", f"{last_exec_highlight}.0", f"{last_exec_highlight}.end")
                if line_num != -1:
                    rt_editor.tag_add("exec_highlight", f"{line_num}.0", f"{line_num}.end")
                    rt_editor.text.tag_raise("exec_highlight")
                last_exec_highlight = line_num

        root.after(0, update_gui)

    def on_run_finished(my_runner):
        nonlocal is_held_by_user, running_tab
        if my_runner is not script_runner:
            return

        if is_held_by_user:
            status_var.set(f"Hold active. Halted at line {feed_hold_line}.")
            is_held_by_user = False
        else:
            status_callback_handler("Idle", -1)
            # Script finished - clear running tab indicator
            old_running = running_tab
            running_tab = None
            if old_running:
                update_tab_label(old_running)

        refresh_button_states()

    # Track the last block end line for single block mode
    last_block_end_line = None
    
    def on_step_finished(my_runner):
        nonlocal last_block_end_line, is_held_by_user, feed_hold_line
        print(f"[on_step_finished] Called. Runner match: {my_runner is script_runner}, held: {is_held_by_user}")

        if my_runner is not script_runner:
            print(f"[on_step_finished] Runner mismatch, ignoring")
            return

        rt_editor = running_tab.editor if running_tab else get_active_editor()

        if is_held_by_user:
            held_line = last_exec_highlight if last_exec_highlight != -1 else last_selection_highlight
            status_var.set(f"Hold active. Halted at line {held_line}.")
            is_held_by_user = False
            refresh_button_states()
            return

        refresh_button_states()
        current_line_num = int(last_selection_highlight)

        if last_block_end_line and last_block_end_line > current_line_num:
            next_line_num = last_block_end_line + 1
        else:
            next_line_num = current_line_num + 1

        last_block_end_line = None

        if rt_editor:
            all_lines = rt_editor.get("1.0", tk.END).splitlines()
        else:
            all_lines = []
        next_valid_line_num = -1
        for i in range(next_line_num - 1, len(all_lines)):
            line_content = all_lines[i].strip()
            if line_content and not line_content.startswith('#'):
                next_valid_line_num = i + 1
                break

        if next_valid_line_num != -1:
            next_line_num = next_valid_line_num

        if script_runner and script_runner.is_held:
            print(f"[on_step_finished] Script in error hold, preserving error message")
        else:
            status_var.set(f"Step complete. Next line: {next_line_num}")

        def advance_highlights():
            if rt_editor:
                rt_editor.text.mark_set(tk.INSERT, f"{next_line_num}.0")
            update_selection_highlight(next_line_num, target_editor=rt_editor)

        root.after(0, advance_highlights)

    def run_script_from_content(content, line_offset=0, is_step=False):
        nonlocal script_runner, script_start_time, running_tab

        # Capture the tab that initiated execution
        running_tab = get_active_tab()
        if running_tab:
            update_tab_label(running_tab)

        mode = "SINGLE BLOCK" if is_step else "CONTINUOUS"
        first_line = content.split('\n')[0][:50] if content else ""
        print(f"[RUN] Starting {mode} mode: {first_line}")
        
        # Track start time for cycle stats (only for full script runs, not single steps)
        if not is_step:
            import time as time_module
            script_start_time = time_module.time()
            
            # Update stats with current job
            from src.stats import get_stats
            stats = get_stats()
            serial_manager = shared_gui_refs.get('serial_manager')
            if serial_manager:
                stats.set_current_job(serial_manager.get_job())
        
        # Get fresh commands for execution
        current_commands = get_current_commands()
        
        # Simple approach: callbacks just refresh state, state machine handles everything
        # NOTE: This callback is invoked from the ScriptRunner thread, NOT the main thread.
        # All Tkinter widget operations MUST be scheduled on the main thread via root.after()
        def callback():
            nonlocal script_start_time
            print(f"[CALLBACK] Completion callback fired (mode: {mode})")
            
            # Record cycle stats (only for full script runs, not single steps)
            # This doesn't touch Tkinter widgets, so it can run in any thread
            if not is_step and script_start_time is not None:
                import time as time_module
                from src.stats import get_stats
                
                cycle_time = time_module.time() - script_start_time
                passed = not (script_runner and script_runner.had_errors)
                
                stats = get_stats()
                stats.record_cycle(cycle_time, passed)
                print(f"[STATS] Recorded cycle: time={cycle_time:.2f}s, passed={passed}")
                
                script_start_time = None  # Reset for next cycle
            
            # Schedule GUI updates on the main thread (Tkinter is NOT thread-safe)
            def update_gui_on_main_thread():
                nonlocal running_tab
                refresh_button_states()

                if is_step and not is_held_by_user:
                    print(f"[CALLBACK] Advancing to next line")
                    advance_to_next_line()
                elif not is_step:
                    old_running = running_tab
                    running_tab = None
                    if old_running:
                        update_tab_label(old_running)
            
            root.after(0, update_gui_on_main_thread)
        
        # Create the runner
        script_runner = ScriptRunner(content, shared_gui_refs, status_callback_handler,
                                     callback,
                                     message_queue, current_commands, 
                                     line_offset)
        
        # Store in shared_gui_refs so operator views can access it
        shared_gui_refs['script_runner'] = script_runner
        
        script_runner.start()
        
        # Refresh button states to reflect that we're now running
        refresh_button_states()
    
    def advance_to_next_line():
        """Advance to the next executable line after a single block completes."""
        nonlocal last_block_end_line
        rt_editor = running_tab.editor if running_tab else get_active_editor()
        current_line_num = int(last_selection_highlight)

        if last_block_end_line and last_block_end_line > current_line_num:
            next_line_num = last_block_end_line + 1
        else:
            next_line_num = current_line_num + 1

        last_block_end_line = None

        if rt_editor:
            all_lines = rt_editor.get("1.0", tk.END).splitlines()
        else:
            all_lines = []
        next_valid_line_num = -1
        for i in range(next_line_num - 1, len(all_lines)):
            line_content = all_lines[i].strip()
            if line_content and not line_content.startswith('#'):
                next_valid_line_num = i + 1
                break

        if next_valid_line_num != -1:
            next_line_num = next_valid_line_num

        if script_runner and script_runner.is_held:
            print(f"[CALLBACK] Script in error hold, preserving error message")
        else:
            status_var.set(f"Step complete. Next line: {next_line_num}")

        if rt_editor:
            rt_editor.text.mark_set(tk.INSERT, f"{next_line_num}.0")
        update_selection_highlight(next_line_num, target_editor=rt_editor)

    def clear_error_highlighting():
        editor = get_active_editor()
        if editor:
            editor.tag_remove("error_highlight", "1.0", tk.END)

    def check_script_validity(show_success=False):
        editor = get_active_editor()
        script_content = editor.get("1.0", tk.END) if editor else ""
        # Get fresh commands for validation
        current_commands = get_current_commands()
        # Get reports for validation
        reports = device_manager.get_all_reports() if device_manager else {}
        errors = validate_script(script_content, current_commands, reports)
        clear_error_highlighting() # Always clear previous errors
        
        # Check that all connected devices support pause, reset, and resume
        if device_manager:
            all_commands = device_manager.get_all_scripting_commands()
            required_commands = ['pause', 'reset', 'resume']
            
            for device_name in device_manager.get_all_device_names():
                device_state = device_manager.get_device_state(device_name)
                if device_state and device_state.get('connected'):
                    # Check if this device supports all required commands
                    for required_cmd in required_commands:
                        # Commands are stored with device prefix (e.g., "device.pause")
                        full_cmd_name = f"{device_name}.{required_cmd}"
                        
                        if full_cmd_name not in all_commands:
                            error_msg = f"Device '{device_name}' does not support required command '{required_cmd}'. All connected devices must support pause, reset, and resume for script execution."
                            errors.append({
                                'line': 0,
                                'error': error_msg,
                                'type': 'device_validation'
                            })
        
        if errors:
            ValidationResultsWindow(scripting_area, errors, on_close_callback=clear_error_highlighting);
            status_var.set(f"{len(errors)} error(s) found.")
            ve = get_active_editor()
            for error in errors: 
                if error.get('line', 0) > 0 and ve:
                    line_num = error['line']
                    ve.tag_add("error_highlight", f"{line_num}.0", f"{line_num}.end")
            return False
        else:
            if show_success: 
                messagebox.showinfo("Validation Success", "Script is valid!")
            # Don't set status here - let the execution update it
            # status_var.set("Validation Successful");
            return True

    def handle_feed_hold():
        nonlocal feed_hold_line, is_held_by_user, paused_device
        print(f"[HOLD] Hold button pressed. Running: {script_runner is not None and script_runner.is_running}")
        
        if script_runner and script_runner.is_running:
            # Mark that we're pausing (but DON'T stop the ScriptRunner)
            # The ScriptRunner will keep waiting for the device's DONE message
            feed_hold_line = last_exec_highlight if last_exec_highlight != -1 else last_selection_highlight
            print(f"[HOLD] Pausing at line {feed_hold_line}")
            
            # Send pause to ALL connected devices
            paused_devices = []
            if device_manager:
                for device_name in device_manager.get_all_device_names():
                    device_state = device_manager.get_device_state(device_name)
                    if device_state and device_state.get('connected'):
                        sender_func = f"send_{device_name}"
                        if sender_func in shared_gui_refs['command_funcs']:
                            print(f"[HOLD] Sending pause to {device_name}")
                            try:
                                shared_gui_refs['command_funcs'][sender_func]('pause')
                                paused_devices.append(device_name)
                            except Exception as e:
                                print(f"[HOLD] Failed to send pause to {device_name}: {e}")
            
            # Track paused device (use first paused device for resume logic)
            if paused_devices:
                paused_device = paused_devices[0]
            else:
                paused_device = None
            
            # Update button states to show we're holding
            # ScriptRunner is still active and waiting for DONE
            status_var.set(f"Paused at line {feed_hold_line}. Press Run to resume.")
            refresh_button_states()
        else:
            # If the script isn't running, just stop all motion.
            print(f"[HOLD] Not running, just stopping motion")
            shared_gui_refs['command_funcs']['abort']()
            status_var.set("All motion stopped.")
            refresh_button_states()

    def abort_script_on_disconnect(device_key):
        """Called when a device disconnects during script execution."""
        nonlocal script_runner, feed_hold_line, is_held_by_user, last_exec_highlight, running_tab

        if script_runner and script_runner.is_running:
            print(f"[DISCONNECT] {device_key} disconnected during script - aborting script")
            script_runner.stop()

            is_held_by_user = False
            feed_hold_line = None

            rt_editor = running_tab.editor if running_tab else get_active_editor()
            if rt_editor:
                rt_editor.tag_remove("exec_highlight", "1.0", tk.END)
            last_exec_highlight = -1

            old_running = running_tab
            running_tab = None
            if old_running:
                update_tab_label(old_running)

            status_var.set(f"Script aborted: {device_key.capitalize()} disconnected")
            refresh_button_states()
    
    def handle_reset():
        nonlocal script_runner, feed_hold_line, is_held_by_user, last_exec_highlight, paused_device, running_tab
        print(f"[RESET] Reset button pressed")

        if script_runner and script_runner.is_running:
            print(f"[RESET] Stopping running script")
            script_runner.stop()

        data_logger = shared_gui_refs.get('data_logger')
        if data_logger:
            print(f"[RESET] Stopping all active logging")
            data_logger.stop_logging()
            logging_status_var.set(" ")
            device_panel = shared_gui_refs.get('device_panel')
            if device_panel and hasattr(device_panel, 'refresh'):
                device_panel.refresh()

        if script_runner and hasattr(script_runner, 'is_held'):
            script_runner.is_held = False
            script_runner.had_errors = False

        is_held_by_user = False
        paused_device = None
        feed_hold_line = None
        shared_gui_refs['command_funcs']['abort']()

        # Clear highlights on the running tab (or active tab if none running)
        rt_editor = running_tab.editor if running_tab else get_active_editor()
        if rt_editor:
            rt_editor.tag_remove("exec_highlight", "1.0", tk.END)
            rt_editor.tag_remove("error_highlight", "1.0", tk.END)
        last_exec_highlight = -1

        old_running = running_tab
        running_tab = None
        if old_running:
            update_tab_label(old_running)

        refresh_button_states()
        status_var.set("Reset complete.")

        dm = shared_gui_refs.get('device_manager')
        if dm:
            all_devices = dm.get_device_modules()
            for device_key in all_devices.keys():
                sender_func_name = f"send_{device_key}"
                if sender_func_name in shared_gui_refs['command_funcs']:
                    shared_gui_refs['command_funcs'][sender_func_name]("reset")

        feed_hold_line = None
        print(f"[RESET] Cleared feed_hold_line, resetting to line 1")

        active_editor = get_active_editor()
        if active_editor:
            active_editor.text.mark_set(tk.INSERT, "1.0")
        update_selection_highlight(1)

        status_var.set("Script reset. Ready to start from line 1.")
        refresh_button_states()

    def update_selection_highlight(line_num, target_editor=None):
        nonlocal last_selection_highlight
        editor = target_editor or get_active_editor()
        if not editor:
            return
        editor.tag_remove("selection_highlight", "1.0", tk.END)
        if line_num != -1:
            editor.tag_add("selection_highlight", f"{line_num}.0", f"{line_num}.end")
            last_selection_highlight = line_num
        if editor.text.tag_ranges("exec_highlight"):
            editor.text.tag_raise("exec_highlight")

    def on_line_click(event):
        nonlocal feed_hold_line
        editor = get_active_editor()
        if not editor:
            return
        try:
            index = editor.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            update_selection_highlight(line_num)
            feed_hold_line = None
        except (tk.TclError, ValueError):
            pass

    def set_initial_highlight():
        editor = get_active_editor()
        if editor:
            editor.text.mark_set(tk.INSERT, "1.0")
            update_selection_highlight(1)
            editor.text.see("1.0")

    root.after(200, set_initial_highlight)

    # --- Control Buttons ---
    btn_container = ttk.Frame(control_frame, style='TFrame');
    btn_container.pack(fill=tk.X, padx=10, pady=(5, 0))

    run_button = ttk.Button(btn_container, text="Run", command=handle_cycle_start,
                                    style="Green.TButton")
    run_button.pack(side=tk.LEFT, padx=(0, 5))

    hold_button = ttk.Button(btn_container, text="Hold", command=handle_feed_hold, style="Red.TButton")
    hold_button.pack(side=tk.LEFT, padx=5)

    reset_button = ttk.Button(btn_container, text="Reset", command=handle_reset, style="Blue.TButton")
    reset_button.pack(side=tk.LEFT, padx=5)

    single_block_switch = ttk.Checkbutton(btn_container, text="Single Block", variable=single_block_var,
                                          style="OrangeToggle.TButton")
    single_block_switch.pack(side=tk.LEFT, padx=5)

    # --- Lock Editor Button (right-justified) ---
    def toggle_editor_lock(*args):
        """Toggle ALL tab editors between locked (read-only) and unlocked."""
        is_locked = lock_editor_var.get()
        for t in tabs:
            t.editor.text.config(state='disabled' if is_locked else 'normal')
        if is_locked:
            lock_editor_switch.config(style="Red.TButton")
        else:
            lock_editor_switch.config(style="OrangeToggle.TButton")
        try:
            from src.config import load_config, save_config
            config = load_config()
            config['lock_editor'] = is_locked
            save_config(config)
        except Exception:
            pass

    loading_file = [False]

    def with_editor_unlocked(func, editor=None):
        """Temporarily unlock an editor to perform an operation, then restore lock state."""
        if editor is None:
            editor = get_active_editor()
        if editor is None:
            func()
            return
        was_locked = lock_editor_var.get()
        loading_file[0] = True
        if was_locked:
            editor.text.config(state='normal')
        try:
            func()
        finally:
            loading_file[0] = False
            if was_locked:
                editor.text.config(state='disabled')
    
    # Bind the variable to the toggle function (do this before creating the button)
    lock_editor_var.trace_add('write', toggle_editor_lock)
    
    lock_editor_switch = ttk.Checkbutton(btn_container, text="Lock Editor", variable=lock_editor_var,
                                         style="OrangeToggle.TButton")
    lock_editor_switch.pack(side=tk.RIGHT, padx=5)
    
    # Note: Initial lock state is applied AFTER recovery completes (see check_for_recovery function)

    refresh_button_states() # Initial state

    # --- Status Label ---
    status_label = ttk.Label(control_frame, textvariable=status_var, anchor='w', 
                             font=theme.FONT_LARGE_BOLD, 
                             foreground=theme.PRIMARY_ACCENT,
                             background=theme.BG_COLOR)
    status_label.pack(side=tk.LEFT, padx=10, pady=(5, 5), fill=tk.X, expand=True)
    update_window_title()

    # --- Callback to update status color based on message type ---
    def update_status_color(*args):
        message = status_var.get().upper()
        
        # Set color based on message content (like terminal)
        if any(keyword in message for keyword in ["ERROR", "_ERROR:", "FAILED", "FAULT", "EXCEPTION", "WARNING", "_WARNING:", "WARN"]):
            status_label.config(foreground=theme.ERROR_RED, background='#2d0f0f')
            control_frame.config(style='Error.TFrame')  # Red background
            btn_container.config(style='Error.TFrame')  # Red background for button area too
        elif any(keyword in message for keyword in ["DONE", "SUCCESS", "COMPLETE", "PASSED"]):
            status_label.config(foreground=theme.SUCCESS_GREEN, background=theme.BG_COLOR)
            control_frame.config(style='TFrame')  # Normal background
            btn_container.config(style='TFrame')
        elif any(keyword in message for keyword in ["INFO", "START", "RUNNING"]):
            status_label.config(foreground=theme.PRIMARY_ACCENT, background=theme.BG_COLOR)
            control_frame.config(style='TFrame')  # Normal background
            btn_container.config(style='TFrame')
        else:
            status_label.config(foreground=theme.PRIMARY_ACCENT, background=theme.BG_COLOR)
            control_frame.config(style='TFrame')  # Normal background
            btn_container.config(style='TFrame')

    status_var.trace_add("write", update_status_color)


    # --- Return file commands and menu update callback ---
    file_commands = {
        "new": new_script,
        "open": load_script,
        "save": save_script,
        "save_as": save_script_as,
        "validate": lambda: check_script_validity(show_success=True),
        "close_tab": lambda: close_tab(),
    }
    
    def _editor_event(event_name):
        ed = get_active_editor()
        if ed:
            ed.text.event_generate(event_name)

    def _show_find_replace():
        tab = get_active_tab()
        if tab and tab.find_replace_frame:
            tab.find_replace_frame.show()

    edit_commands = {
        "undo": lambda: _editor_event("<<Undo>>"),
        "redo": lambda: _editor_event("<<Redo>>"),
        "cut": lambda: _editor_event("<<Cut>>"),
        "copy": lambda: _editor_event("<<Copy>>"),
        "paste": lambda: _editor_event("<<Paste>>"),
        "find": _show_find_replace,
        "replace": _show_find_replace,
        "find_replace": _show_find_replace,
    }
    
    # --- Check for recovery files on startup ---
    def check_for_recovery():
        """Check for temp autosave files and offer to recover them."""
        import tempfile
        import glob
        import time

        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, "untitled_*.txt")
        temp_files = glob.glob(pattern)

        recoverable_files = []
        for tf in temp_files:
            try:
                age_seconds = time.time() - os.path.getmtime(tf)
                size = os.path.getsize(tf)
                if age_seconds > 5 and size > 0:
                    recoverable_files.append((tf, age_seconds))
            except Exception:
                pass

        if recoverable_files:
            recoverable_files.sort(key=lambda x: x[1])
            msg = f"Found {len(recoverable_files)} unsaved script(s) from a previous session.\n\n"
            msg += "Would you like to recover the most recent one?"

            response = messagebox.askyesno("Recover Unsaved Work?", msg)
            if response:
                most_recent = recoverable_files[0][0]
                try:
                    with open(most_recent, 'r') as f:
                        content = f.read()

                    # Load into the first (empty) tab
                    tab = get_active_tab()
                    if tab:
                        def _recover():
                            tab.editor.delete('1.0', tk.END)
                            tab.editor.insert('1.0', content)
                            tab.editor.edit_modified(False)
                        with_editor_unlocked(_recover, editor=tab.editor)
                        tab.filepath = most_recent
                        nonlocal current_filepath
                        current_filepath = most_recent
                        update_tab_label(tab)
                        update_window_title()
                    status_var.set("Recovered unsaved script - use 'Save As' to choose a permanent location")
                except Exception as e:
                    messagebox.showerror("Recovery Error", f"Could not recover file:\n{e}")

            if len(recoverable_files) > 1:
                cleanup = messagebox.askyesno("Clean Up",
                    f"Would you like to delete the other {len(recoverable_files)-1} old temp file(s)?")
                if cleanup:
                    for tf, _ in recoverable_files[1:]:
                        try:
                            os.remove(tf)
                        except Exception:
                            pass

        if not recoverable_files and not current_filepath:
            tab = get_active_tab()
            if tab:
                def _add_example():
                    tab.editor.insert(tk.END, "# Example Script\n# Type commands here or load a file.\n")
                    tab.editor.edit_reset()
                    tab.editor.edit_modified(False)
                with_editor_unlocked(_add_example, editor=tab.editor)

        if initial_lock_state:
            root.after(100, lambda: lock_editor_var.set(True))

    root.after(500, check_for_recovery)
    
    # Register the disconnect handler in shared_gui_refs
    shared_gui_refs['abort_script_on_disconnect'] = abort_script_on_disconnect
    
    # Store script control handlers and button registration for operator views
    shared_gui_refs['script_controls'] = {
        'handle_cycle_start': handle_cycle_start,
        'handle_feed_hold': handle_feed_hold,
        'handle_reset': handle_reset,
        'refresh_button_states': refresh_button_states,
        'register_buttons': lambda run_btn, hold_btn: additional_button_sets.append((run_btn, hold_btn)),
        'unregister_buttons': lambda run_btn, hold_btn: additional_button_sets.remove((run_btn, hold_btn)) if (run_btn, hold_btn) in additional_button_sets else None
    }
    
    # --- Logging status display functions ---
    def update_logging_status(filename=None):
        """Update the logging status display. Pass None or empty to clear."""
        if filename:
            logging_status_var.set(f"logging to {filename}")
        else:
            logging_status_var.set(" ")  # Space to maintain height
    
    shared_gui_refs['update_logging_status'] = update_logging_status
    
    return {
        "file_commands": file_commands,
        "edit_commands": edit_commands,
        "update_recent_menu_callback": set_recent_menu_reference,
        "check_unsaved": check_all_unsaved_changes,
        "load_specific_script": load_specific_script,
        "script_editor": script_editor_proxy,
        "syntax_highlighter": _first_tab.editor.highlighter,
        "scripting_commands": get_current_commands(),
        "device_modules": device_modules,
        "get_script_content": lambda: (get_active_editor().get("1.0", tk.END) if get_active_editor() else ""),
        # --- New tab API ---
        "open_script_in_tab": load_specific_script,
        "run_active_tab": handle_cycle_start,
        "get_active_tab_filepath": lambda: (get_active_tab().filepath if get_active_tab() else None),
        "get_active_editor": get_active_editor,
        "create_new_tab": create_new_tab,
        "close_tab": close_tab,
        "get_all_tabs": lambda: list(tabs),
        "notebook": notebook,
        # --- Layout frames (for collapsible editor) ---
        "toolbar_frame": _toolbar_parent,
        "editor_frame": scripting_area,
    }
