import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import queue
import os
import json
from functools import partial
import re
import tkinter.font as tkfont

from script_validator import validate_single_line, validate_script
from script_processor import ScriptRunner
import theme
from comms import devices_lock

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
        print(f"[DEBUG] Replace All: find='{find_text}', replace='{replace_text}'")
        if not find_text:
            return

        count = 0
        start_pos = "1.0"
        while True:
            found_pos = self.text_widget.search(find_text, start_pos, stopindex=tk.END)
            print(f"[DEBUG] Loop {count}: start_pos='{start_pos}', found_pos='{found_pos}'")
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
RECENT_FILES_CONFIG = "recent_files.json"
MAX_RECENT_FILES = 5


# --- Recent Files Management ---
def load_recent_files():
    """Loads the list of recent file paths from the config file."""
    try:
        with open(RECENT_FILES_CONFIG, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_recent_files(filepaths):
    """Saves the list of recent file paths to the config file."""
    with open(RECENT_FILES_CONFIG, 'w') as f:
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
            wrap=tk.WORD,
            spacing3=3 # Add 3 pixels of spacing after each line
        )
        
        # --- Configure Tabs for 4-space indentation ---
        font = tkfont.Font(font=self.cget("font"))
        tab_width = font.measure('    ')
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
    """A canvas that displays line numbers for a text widget."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, *args):
        self.delete("all")
        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum, 
                             font=theme.FONT_NORMAL, fill=theme.SECONDARY_ACCENT)
            i = self.textwidget.index(f"{i}+1line")

# --- Syntax Highlighter ---
class SyntaxHighlighter:
    def __init__(self, text_widget, device_keywords, script_keywords):
        self.text = text_widget
        self.device_keywords = device_keywords
        self.script_keywords = script_keywords
        self.tags = {
            'command': {'foreground': theme.COMMAND_COLOR, 'font': theme.FONT_BOLD},
            'script_command': {'foreground': theme.SCRIPT_COMMAND_COLOR, 'font': theme.FONT_BOLD},
            'parameter': {'foreground': theme.PARAMETER_COLOR},
            'comment': {'foreground': theme.COMMENT_COLOR},
            'colon': {'foreground': theme.SELECTION_FG, 'font': theme.FONT_BOLD} # SELECTION_FG is white
        }
        self._configure_tags()
        # Use a flag to prevent re-highlighting while highlighting is in progress
        self._highlighting = False
        # Bind to the custom <<Modified>> event, which fires on any text change.
        self.text.bind('<<Modified>>', self.highlight)

    def refresh_keywords(self):
        """Re-fetches the keywords from the device manager and re-highlights the text."""
        # This assumes the device_manager reference passed in initially is still valid
        # and has been updated with the new device info.
        all_commands = self.device_manager.get_all_scripting_commands()
        self.device_keywords = [cmd for cmd, details in all_commands.items() if details['device'] not in ['script', 'both']]
        self.script_keywords = [cmd for cmd, details in all_commands.items() if details['device'] in ['script', 'both']]
        self.highlight()


    def _configure_tags(self):
        for tag_name, tag_config in self.tags.items():
            self.text.tag_configure(tag_name, **tag_config)

    def highlight(self, event=None):
        # Use 'end-1c' to avoid highlighting the final newline which can cause issues
        content = self.text.get("1.0", "end-1c")
        
        # A small delay to prevent rapid, sequential updates from fighting each other.
        self.text.after(10, self._apply_highlight, content)

    def _apply_highlight(self, content):
        # Remove all tags first to prevent stacking
        for tag in self.tags.keys():
            self.text.tag_remove(tag, "1.0", "end")

        # Highlight device commands
        if self.device_keywords:
            keyword_pattern = r'\b(' + '|'.join(self.device_keywords) + r')\b'
            for match in re.finditer(keyword_pattern, content, re.IGNORECASE):
                start, end = match.span()
                self.text.tag_add("command", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight script commands
        if self.script_keywords:
            keyword_pattern = r'\b(' + '|'.join(self.script_keywords) + r')\b'
            for match in re.finditer(keyword_pattern, content, re.IGNORECASE):
                start, end = match.span()
                self.text.tag_add("script_command", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight colons
        for match in re.finditer(r':', content):
            start, end = match.span()
            self.text.tag_add("colon", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight numbers (integers and floats)
        for match in re.finditer(r'\b-?\d+(\.\d+)?\b', content):
            start, end = match.span()
            self.text.tag_add("parameter", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight comments
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
        self.linenumbers = TextLineNumbers(self, width=40, bg=theme.WIDGET_BG, highlightthickness=0, borderwidth=0)
        self.linenumbers.attach(self.text)
        
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        
        self.linenumbers.pack(side="left", fill="y")
        self.vsb.pack(side="right", fill="y")
        self.text.pack(side="right", fill="both", expand=True)
        
        # --- Event Bindings ---
        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)
        self.text.bind("<KeyRelease>", self._highlight_current_line)
        self.text.bind("<Button-1>", self._on_change)
        self.text.bind("<Tab>", self._on_tab)

        self.text.tag_configure("current_line", background=theme.SECONDARY_ACCENT)
        self._highlight_current_line()
        
        all_commands = self.device_manager.get_all_scripting_commands()
        device_keywords = [cmd for cmd, details in all_commands.items() if details['device'] not in ['script', 'both']]
        script_keywords = [cmd for cmd, details in all_commands.items() if details['device'] in ['script', 'both']]
        self.highlighter = SyntaxHighlighter(self.text, device_keywords, script_keywords)
        self.highlighter.device_manager = device_manager # Pass manager for refreshing
    
    def _on_tab(self, event):
        self.text.insert(tk.INSERT, "    ")
        return 'break' # Prevents the default tab behavior

    def _highlight_current_line(self, event=None):
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")
        self.text.tag_raise("sel") # Raise selection tag to the top of the stacking order

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


# --- GUI Creation Functions (Wiring everything up) ---
class CommandReference(ttk.Frame):
    def __init__(self, parent, script_editor_widget, device_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.script_editor_widget = script_editor_widget
        self.device_manager = device_manager
        self.all_commands = [] # Initialize to prevent race condition
        
        self.configure(style='TFrame', padding=5)

        # --- Filter Widgets ---
        filter_frame = ttk.Frame(self, style='TFrame')
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        filter_frame.grid_columnconfigure((0,1,2,3), weight=1) # Make columns resizable

        # --- Treeview ---
        tree_frame = ttk.Frame(self, style='TFrame')
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=('params', 'desc'), show='tree headings')
        
        self.tree.tag_configure('disconnected', foreground=theme.COMMENT_COLOR)

        self.filter_widgets = {} # Store widgets instead of vars
        self.columns = {'#0': 'cmd', 'params': 'params', 'desc': 'desc'}
        widths = {'#0': 200, 'params': 120, 'desc': 300}

        for i, (col_id, col_key) in enumerate(self.columns.items()):
            self.tree.heading(col_id, text=col_key.capitalize() if col_id!='#0' else 'Command')
            self.tree.column(col_id, width=widths[col_id], anchor='w')
            
            var = tk.StringVar()
            var.trace_add("write", self.apply_filters)
            
            entry = EntryWithPlaceholder(filter_frame, 
                                         textvariable=var,
                                         placeholder=f"Filter {col_key.capitalize()}...")
            entry.grid(row=0, column=i, sticky='ew', padx=(0 if i==0 else 2, 0))
            self.filter_widgets[col_key] = entry # Store the widget

        for col_id, col_key in self.columns.items():
            self.tree.heading(col_id, command=lambda c=col_id: self.sort_column(c, False))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh() # Initial population
        self.tree.after(100, lambda: self.sort_column('#0', False))

        context_menu = tk.Menu(self, tearoff=0, 
                               bg=theme.WIDGET_BG, 
                               fg=theme.FG_COLOR,
                               activebackground=theme.PRIMARY_ACCENT,
                               activeforeground=theme.FG_COLOR)
        context_menu.add_command(label="Copy Command", command=self.copy_command)
        context_menu.add_command(label="Add to Script", command=self.add_to_script)

        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.add_to_script())

    def refresh(self):
        """Clears and repopulates the treeview with the latest command data."""
        self.scripting_commands = self.device_manager.get_all_scripting_commands()
        self.all_commands = []
        for cmd, details in sorted(self.scripting_commands.items(), key=lambda item: (item[1]['device'], item[0])):
            self.all_commands.append({
                'cmd': cmd,
                'device': details['device'].capitalize(),
                'params': " ".join([p['name'] for p in details['params']]),
                'desc': details['help']
            })
        self.apply_filters()

    def populate_tree(self, commands_to_display):
        for item in self.tree.get_children():
            self.tree.delete(item)

        device_parents = {}
        with devices_lock:
            device_states = self.device_manager.get_all_device_states()
            for device_name in sorted(device_states.keys()):
                is_connected = device_states[device_name].get('connected', False)
                tags = () if is_connected else ('disconnected',)
                is_open = is_connected
                parent_id = self.tree.insert('', 'end', text=device_name.capitalize(), values=('', ''), open=is_open, tags=tags)
                device_parents[device_name] = parent_id

        for cmd_data in commands_to_display:
            device_key = cmd_data['device'].lower()
            parent_id = device_parents.get(device_key)
            if parent_id:
                tags = self.tree.item(parent_id, 'tags')
                self.tree.insert(parent_id, 'end', text=cmd_data['cmd'], values=(cmd_data['params'], cmd_data['desc']), tags=tags)

    def apply_filters(self, *args):
        filtered_commands = self.all_commands
        for col, widget in self.filter_widgets.items():
            entry = widget.get() # Use the widget's custom get()
            if entry: # The custom get() returns "" for placeholder, so this check is sufficient
                filter_text = entry.lower()
                filtered_commands = [cmd for cmd in filtered_commands if filter_text in cmd[col].lower()]
        self.populate_tree(filtered_commands)
        if hasattr(self.tree, 'sort_by'):
             self.sort_column(self.tree.sort_by, self.tree.sort_rev, True)

    def sort_column(self, col_id, reverse, preserve=False):
        header_text = self.tree.heading(col_id, "text").replace(" ▲", "").replace(" ▼", "")
        
        for cid, ckey in self.columns.items():
             self.tree.heading(cid, text=ckey.capitalize() if cid!='#0' else 'Command')
        
        arrow = " ▼" if reverse else " ▲"
        self.tree.heading(col_id, text=header_text + arrow)

        for parent_id in self.tree.get_children(''):
            if col_id == '#0':
                 l = [(self.tree.item(k)['text'], k) for k in self.tree.get_children(parent_id)]
            else:
                 l = [(self.tree.set(k, col_id), k) for k in self.tree.get_children(parent_id)]
            
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)
            for index, (val, k) in enumerate(l):
                self.tree.move(k, parent_id, index)

        self.tree.heading(col_id, command=lambda: self.sort_column(col_id, not reverse))
        self.tree.sort_by = col_id
        self.tree.sort_rev = reverse

    def get_selected_command(self):
        selected_item = self.tree.focus()
        if not selected_item: return None
        return self.tree.item(selected_item, "text")

    def copy_command(self):
        command = self.get_selected_command()
        if command: self.clipboard_clear(); self.clipboard_append(command)

    def add_to_script(self):
        command = self.get_selected_command()
        if command: self.script_editor_widget.insert(tk.INSERT, f"{command} ")

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid: self.tree.selection_set(iid); self.tree.focus(iid); self.context_menu.post(event.x_root, event.y_root)

def create_command_reference(parent, script_editor_widget, device_manager):
    # This is now a wrapper for the class
    return CommandReference(parent, script_editor_widget, device_manager)


def create_scripting_interface(parent, command_funcs, shared_gui_refs, autosave_var):
    """
    Creates the main scripting area, including the editor and command reference.
    Returns a dictionary containing file commands and a callback to update the recent menu.
    """
    scripting_area = ttk.Frame(parent, style='TFrame')
    scripting_area.pack(fill=tk.BOTH, expand=True)

    # Get a reference to the root window for thread-safe GUI updates
    root = scripting_area.winfo_toplevel()
    
    # --- Get Device Manager and Commands ---
    device_manager = shared_gui_refs.get('device_manager')
    if not device_manager:
        # Handle case where device manager isn't available
        scripting_area.add(ttk.Label(scripting_area, text="Error: Device Manager not found."))
        return {}
    scripting_commands = device_manager.get_all_scripting_commands()
    device_modules = device_manager.get_device_modules()

    paned_window = ttk.PanedWindow(scripting_area, orient=tk.HORIZONTAL, style='TPanedwindow')
    paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
    left_pane = ttk.Frame(paned_window, style='TFrame')
    paned_window.add(left_pane, weight=1) # The script editor will be the only thing here now

    # The right_pane and the command_ref_widget that was created here have been removed,
    # as the command reference is now created in its own collapsible panel in main.py.

    # --- Scripting State Variables ---
    script_runner = None
    last_exec_highlight = -1
    last_selection_highlight = 1
    current_filepath = None
    feed_hold_line = None
    is_held_by_user = False # Flag to manage Hold state vs. a normal stop
    single_block_var = tk.BooleanVar(value=False)

    # --- Message Queue & Terminal ---
    message_queue = queue.Queue()
    original_terminal_cb = shared_gui_refs.get('terminal_cb')
    if 'vacuum_check_status_var' not in shared_gui_refs:
        shared_gui_refs['vacuum_check_status_var'] = tk.StringVar(value='N/A')

    recent_files_menu_ref = None

    def terminal_wrapper(message):
        # --- Intercept ERROR messages to display them prominently ---
        if "_ERROR:" in message:
            # The root.after is crucial to prevent threading issues with Tkinter
            root.after(0, lambda: status_label.config(foreground=theme.ERROR_RED)) # Bright Red
            root.after(0, lambda: status_var.set(message))

        if "DONE:" in message: message_queue.put(message)
        if original_terminal_cb: original_terminal_cb(message)

    shared_gui_refs['terminal_cb'] = terminal_wrapper

    # --- UI Creation ---
    control_frame = ttk.Frame(left_pane, style='TFrame');
    control_frame.pack(fill=tk.X, pady=(0, 0))
    editor_frame = ttk.LabelFrame(left_pane, style='TFrame')
    editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    script_editor = ScriptEditor(editor_frame, device_manager=device_manager)
    script_editor.pack(fill="both", expand=True)

    # --- NEW: Find/Replace Frame ---
    find_replace_frame = FindReplaceFrame(left_pane, script_editor.text)
    # The frame is created but not packed, so it starts hidden.

    # Add binding to show it
    script_editor.text.bind("<Control-f>", lambda e: find_replace_frame.show())


    # Configure tags for execution and error highlighting
    script_editor.tag_config("exec_highlight", background=theme.WARNING_YELLOW, foreground="black")
    script_editor.tag_config("selection_highlight", background=theme.SECONDARY_ACCENT)
    script_editor.tag_config("error_highlight", background=theme.ERROR_RED, foreground=theme.FG_COLOR)
    
    script_editor.insert(tk.END, "# Example Script\n# Type commands here or load a file.\n")
    script_editor.edit_reset()
    script_editor.edit_modified(False)

    # The command reference is no longer created here.

    def update_window_title():
        filename = "Untitled"
        if current_filepath: filename = os.path.basename(current_filepath)
        modified_star = "*" if script_editor.edit_modified() else "";
        root.title(f"{filename}{modified_star} - BR Equipment Control App")

    def on_text_modified(event):
        """Updates window title and triggers autosave if enabled."""
        update_window_title()
        # --- Autosave Logic ---
        if autosave_var.get() and current_filepath:
            # Call the save_script function but without triggering the dialog
            try:
                with open(current_filepath, 'w') as f:
                    f.write(script_editor.get('1.0', tk.END))
                # Mark as unmodified to prevent the "unsaved" dialog
                script_editor.edit_modified(False)
                update_window_title() # Update title to remove '*'
            except Exception as e:
                status_var.set(f"Autosave Error: {e}")

        # Update the highlight to follow the cursor's current line
        current_line = int(script_editor.index(tk.INSERT).split('.')[0])
        update_selection_highlight(current_line)

    # Add the binding for autosave/title update. The highlighter binds itself.
    script_editor.bind("<<Modified>>", on_text_modified, add='+')

    status_var = tk.StringVar(value="Status: Idle")

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

    # --- File Operations ---
    def check_unsaved_changes():
        if not script_editor.edit_modified(): return True
        response = messagebox.askyesnocancel("Unsaved Changes", "You have unsaved changes. Do you want to save them?")
        if response is True:
            return save_script()
        elif response is False:
            return True
        else:
            return False

    def new_script():
        nonlocal current_filepath
        if not check_unsaved_changes(): return
        script_editor.delete('1.0', tk.END);
        script_editor.edit_modified(False);
        current_filepath = None;
        update_window_title();
        update_selection_highlight(1)

    def save_script():
        nonlocal current_filepath
        if current_filepath:
            try:
                with open(current_filepath, 'w') as f:
                    f.write(script_editor.get('1.0', tk.END))
                script_editor.edit_modified(False);
                update_window_title();
                status_var.set(f"Saved to {os.path.basename(current_filepath)}");
                add_to_recent_files(current_filepath)
                update_recent_files_display()
                return True
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save file:\n{e}");
                return False
        else:
            return save_script_as()

    def save_script_as():
        nonlocal current_filepath
        filepath = filedialog.asksaveasfilename(title="Save Script As", defaultextension=".txt",
                                                filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if not filepath: return False
        current_filepath = filepath;
        return save_script()

    def load_specific_script(filepath):
        nonlocal current_filepath
        if not check_unsaved_changes(): return
        if not os.path.exists(filepath):
            messagebox.showerror("File Not Found", f"Could not find file:\n{filepath}")
            filepaths = load_recent_files()
            if filepath in filepaths:
                filepaths.remove(filepath)
                save_recent_files(filepaths)
            update_recent_files_display()
            return
        try:
            with open(filepath, 'r') as f:
                script_editor.delete('1.0', tk.END);
                script_editor.insert('1.0', f.read())
            current_filepath = filepath;
            script_editor.edit_modified(False);
            update_window_title();
            update_selection_highlight(1);
            status_var.set(f"Loaded {os.path.basename(current_filepath)}")
            add_to_recent_files(filepath)
            update_recent_files_display()
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file:\n{e}")

    def load_script():
        filepath = filedialog.askopenfilename(title="Open Script File",
                                              filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if not filepath: return
        load_specific_script(filepath)

    # --- Script Execution Logic ---
    def handle_cycle_start():
        print("[DEBUG] handle_cycle_start called")
        nonlocal feed_hold_line, is_held_by_user
        is_held_by_user = False # Always clear hold flag on a new run attempt

        if not check_script_validity(): 
            print("[DEBUG] Script validation failed.")
            return

        start_line_num = 1
        if feed_hold_line is not None:
            start_line_num = feed_hold_line
            feed_hold_line = None
        else:
            try:
                start_line_num = int(last_selection_highlight)
            except (ValueError, TypeError):
                start_line_num = 1

        update_selection_highlight(start_line_num)
        is_single_block = single_block_var.get()
        all_lines = script_editor.get("1.0", tk.END).splitlines()

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
            on_run_finished()
            print("[DEBUG] End of script reached before start.")
            return

        update_selection_highlight(next_valid_line_num)

        if is_single_block:
            errors = validate_single_line(next_valid_line_content, next_valid_line_num, scripting_commands)
            script_editor.tag_remove("error_highlight", "1.0", tk.END)
            if errors:
                ValidationResultsWindow(scripting_area, errors)
                script_editor.tag_add("error_highlight", f"{next_valid_line_num}.0", f"{next_valid_line_num}.end")
                status_var.set(f"Error on line {next_valid_line_num}.")
                print(f"[DEBUG] Single block validation error on line {next_valid_line_num}.")
                return
            print(f"[DEBUG] Running single block: line {next_valid_line_num}, content: '{next_valid_line_content}'")
            run_script_from_content(next_valid_line_content, next_valid_line_num - 1, is_step=True)
        else:
            content_from_line = "\n".join(all_lines[next_valid_line_num - 1:])
            print(f"[DEBUG] Running script from line {next_valid_line_num}. Content passed to runner:\n---\n{content_from_line}\n---")
            run_script_from_content(content_from_line, next_valid_line_num - 1, is_step=False)

    def update_button_states(running=False, holding=False):
        if holding:
            # Script is paused. Run is enabled to resume, Hold is prominent and enabled.
            run_button.config(state=tk.NORMAL, style='Green.TButton', text='Run')
            hold_button.config(state=tk.NORMAL, style='Holding.Red.TButton', text='Holding')
        elif running:
            # Script is running. Run is disabled and prominent, Hold is enabled.
            run_button.config(state=tk.DISABLED, style='Running.Green.TButton', text='Running...')
            hold_button.config(state=tk.NORMAL, style='Red.TButton', text='Hold')
        else: # Idle
            # Script is idle. Run is enabled, Hold is disabled.
            run_button.config(state=tk.NORMAL, style='Green.TButton', text='Run')
            hold_button.config(state=tk.DISABLED, style='Red.TButton', text='Hold')

    # MODIFIED: This function now safely schedules GUI updates on the main thread.
    def status_callback_handler(message, line_num):
        def update_gui():
            nonlocal last_exec_highlight
            status_var.set(message)
            if last_exec_highlight != line_num:
                if last_exec_highlight != -1:
                    script_editor.tag_remove("exec_highlight", f"{last_exec_highlight}.0", f"{last_exec_highlight}.end")
                if line_num != -1:
                    script_editor.tag_add("exec_highlight", f"{line_num}.0", f"{line_num}.end")
                last_exec_highlight = line_num

        # Schedule the GUI update to run in the main event loop
        root.after(0, update_gui)

    def on_run_finished():
        nonlocal is_held_by_user
        if is_held_by_user:
            # This was a user-initiated hold, not the end of the script
            update_button_states(holding=True)
            status_var.set(f"Hold active. Halted at line {feed_hold_line}.")
            is_held_by_user = False # Reset the flag
        else:
            # The script finished normally
            update_button_states(running=False, holding=False)
            status_callback_handler("Idle", -1)

    def on_step_finished():
        update_button_states(running=False, holding=False)
        current_line_num = int(last_selection_highlight)
        status_var.set(f"Step complete. Next line: {current_line_num + 1}");
        root.after(0, lambda: update_selection_highlight(current_line_num + 1))

    def run_script_from_content(content, line_offset=0, is_step=False):
        nonlocal script_runner
        print(f"[DEBUG] run_script_from_content called. line_offset={line_offset}, is_step={is_step}")
        update_button_states(running=True) # Set running state visuals
        completion_callback = on_step_finished if is_step else on_run_finished
        script_runner = ScriptRunner(content, shared_gui_refs, status_callback_handler,
                                     completion_callback, message_queue, scripting_commands, line_offset);
        script_runner.start()
        print("[DEBUG] ScriptRunner thread started.")

    def clear_error_highlighting():
        script_editor.tag_remove("error_highlight", "1.0", tk.END)

    def check_script_validity(show_success=False):
        script_content = script_editor.get("1.0", tk.END);
        errors = validate_script(script_content, scripting_commands);
        clear_error_highlighting() # Always clear previous errors
        if errors:
            ValidationResultsWindow(scripting_area, errors, on_close_callback=clear_error_highlighting);
            status_var.set(f"{len(errors)} error(s) found.")
            for error in errors: line_num = error['line']; script_editor.tag_add("error_highlight", f"{line_num}.0",
                                                                                 f"{line_num}.end")
            return False
        else:
            if show_success: messagebox.showinfo("Validation Success", "Script is valid!")
            status_var.set("Validation Successful");
            return True

    def handle_feed_hold():
        nonlocal feed_hold_line, is_held_by_user
        shared_gui_refs['command_funcs']['abort']()

        if script_runner and script_runner.is_running:
            is_held_by_user = True # Signal that the stop was intentional
            feed_hold_line = last_exec_highlight
            script_runner.stop() # This will trigger on_run_finished
        else:
            # If the script isn't running, just stop all motion.
            status_var.set("All motion stopped.")
            update_button_states(running=False, holding=False)

    def handle_reset():
        nonlocal script_runner, feed_hold_line, is_held_by_user
        if script_runner and script_runner.is_running:
            script_runner.stop()
        
        is_held_by_user = False # Ensure reset clears any hold state
        shared_gui_refs['command_funcs']['abort']()

        # Explicitly clear any lingering execution highlight immediately.
        script_editor.tag_remove("exec_highlight", "1.0", tk.END)

        # Send CLEAR_ERRORS to all devices that are currently connected.
        device_manager = shared_gui_refs.get('device_manager')
        if device_manager:
            all_devices = device_manager.get_device_modules()
            for device_key in all_devices.keys():
                # The command_funcs dictionary already has the correctly scoped sender function.
                sender_func_name = f"send_{device_key}"
                if sender_func_name in shared_gui_refs['command_funcs']:
                    shared_gui_refs['command_funcs'][sender_func_name]("CLEAR_ERRORS")

        feed_hold_line = None
        update_button_states(running=False, holding=False)
        update_selection_highlight(1)
        status_var.set("Script reset. Ready to start from line 1.")

    def update_selection_highlight(line_num):
        nonlocal last_selection_highlight
        # Remove the highlight from all lines first to ensure only one is ever highlighted.
        script_editor.tag_remove("selection_highlight", "1.0", tk.END)
        if line_num != -1:
            script_editor.tag_add("selection_highlight", f"{line_num}.0", f"{line_num}.end")
            last_selection_highlight = line_num

    def on_line_click(event):
        nonlocal feed_hold_line
        index = script_editor.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        update_selection_highlight(line_num)
        # When user clicks a line, it implies they want to start from there,
        # so clear any pending feed hold resume state.
        feed_hold_line = None

    script_editor.bind("<Button-1>", on_line_click)
    update_selection_highlight(1)

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

    update_button_states(running=False, holding=False) # Initial state

    # --- Status Label ---
    status_label = ttk.Label(control_frame, textvariable=status_var, anchor='w', 
                             font=theme.FONT_LARGE_BOLD, 
                             foreground=theme.PRIMARY_ACCENT,
                             background=theme.BG_COLOR)
    status_label.pack(side=tk.LEFT, padx=10, pady=(5, 5), fill=tk.X, expand=True)
    update_window_title()

    # --- Callback to reset status color ---
    def reset_status_color(*args):
        status_label.config(foreground=theme.PRIMARY_ACCENT)

    status_var.trace_add("write", reset_status_color)


    # --- Return file commands and menu update callback ---
    file_commands = {
        "new": new_script,
        "open": load_script,
        "save": save_script,
        "save_as": save_script_as,
        "validate": lambda: check_script_validity(show_success=True)
    }
    
    edit_commands = {
        "find_replace": find_replace_frame.show
    }
    
    return {
        "file_commands": file_commands,
        "edit_commands": edit_commands,
        "update_recent_menu_callback": set_recent_menu_reference,
        "check_unsaved": check_unsaved_changes,
        "load_specific_script": load_specific_script,
        "script_editor": script_editor, # Expose the script editor widget
        "syntax_highlighter": script_editor.highlighter, # Expose for refreshing
        "scripting_commands": scripting_commands, # Expose for command reference
        "device_modules": device_modules # Expose for command reference
    }
