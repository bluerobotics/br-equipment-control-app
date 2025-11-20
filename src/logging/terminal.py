import tkinter as tk
from tkinter import ttk
from src import theme
import re
import datetime


def log_to_terminal(msg, gui_refs):
    """Safely logs a message to the GUI terminal by placing it on the queue."""
    # Filter debug messages based on checkbox
    if "_DEBUG:" in msg:
        show_debug_var = gui_refs.get('show_debug_var')
        if show_debug_var and not show_debug_var.get():
            return  # Debug messages hidden, don't log
    
    # Create timestamp with milliseconds (keep closing bracket)
    timestr = datetime.datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "]"
    full_msg = f"{timestr} {msg}\n"
    
    # Also log to system logger if available
    # The logger will see the timestamp in full_msg and won't add another one
    try:
        from .system import get_system_logger
        logger = get_system_logger()
        if logger:
            # Pass message with timestamp - logger will detect it and not add another
            logger.log_message(full_msg.rstrip('\n'), is_error=False)
    except Exception:
        pass  # Ignore errors in logging system
    
    terminal_cb = gui_refs.get('terminal_cb')
    gui_queue = gui_refs.get('gui_queue')

    if terminal_cb and gui_queue:
        # The terminal_cb function itself is what needs to run in the main thread.
        gui_queue.put((terminal_cb, (full_msg,), {}))
    else:
        # Fallback for when GUI elements aren't available
        print(full_msg)


def create_terminal_panel(parent, shared_gui_refs):
    """
    Creates the terminal display panel at the bottom of the window.
    Returns a dictionary of references to the created widgets.
    """
    # Use a themed frame for consistent styling
    bottom_frame = ttk.Frame(parent, style='Card.TFrame')
    
    # Options frame at the bottom - pack first so it doesn't get squeezed out
    options_frame = ttk.Frame(bottom_frame, style='Card.TFrame')
    options_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 5), padx=10)

    # Terminal container fills remaining space
    terminal_container = ttk.Frame(bottom_frame, style='Card.TFrame')
    terminal_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0), padx=10)
    terminal_container.grid_rowconfigure(0, weight=1)
    terminal_container.grid_columnconfigure(0, weight=1)

    # Remove fixed height - let the PanedWindow control the size
    terminal = tk.Text(terminal_container, bg=theme.WIDGET_BG, fg=theme.TERMINAL_FG_COLOR, 
                       insertbackground=theme.FG_COLOR, wrap="word",
                       highlightbackground=theme.SECONDARY_ACCENT, highlightthickness=1, bd=0, 
                       font=("Consolas", 9))
    terminal.grid(row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(terminal_container, command=terminal.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    terminal['yscrollcommand'] = scrollbar.set

    # Configure text tags for syntax highlighting
    terminal.tag_config("error", foreground=theme.ERROR_RED)
    terminal.tag_config("success", foreground=theme.SUCCESS_GREEN)
    terminal.tag_config("warning", foreground=theme.WARNING_YELLOW)
    terminal.tag_config("info", foreground=theme.PRIMARY_ACCENT)
    terminal.tag_config("system", foreground=theme.TERMINAL_FG_COLOR)
    terminal.tag_config("disconnect", foreground=theme.ERROR_RED)
    terminal.tag_config("connect", foreground=theme.SUCCESS_GREEN)
    terminal.tag_config("command", foreground=theme.BUSY_BLUE)
    terminal.tag_config("telemetry", foreground=theme.COMMENT_COLOR)

    def insert_colored_message(msg):
        """Insert message with appropriate color based on content."""
        if not msg:
            return
        
        # Check for Python console messages first - they should be white
        if "[python]" in msg.lower():
            tag = "system"  # White/default color
        else:
            # Determine color tag based on message content
            tag = "system"  # Default
            msg_upper = msg.upper()
            
            # Check for error messages
            if any(keyword in msg_upper for keyword in ["ERROR", "_ERROR:", "FAILED", "FAULT", "EXCEPTION"]):
                tag = "error"
            # Check for success/done messages
            elif any(keyword in msg_upper for keyword in ["_DONE:", "SUCCESS", "COMPLETE", "OK]"]):
                tag = "success"
            # Check for warnings
            elif any(keyword in msg_upper for keyword in ["WARNING", "WARN", "_RECOVERY:"]):
                tag = "warning"
            # Check for disconnect messages
            elif any(keyword in msg_upper for keyword in ["DISCONNECT", "OFFLINE", "LOST CONNECTION"]):
                tag = "disconnect"
            # Check for connect messages
            elif any(keyword in msg_upper for keyword in ["CONNECT", "ONLINE", "DISCOVERED"]):
                tag = "connect"
            # Check for command messages
            elif "[CMD SENT" in msg:
                tag = "command"
            # Check for telemetry messages
            elif "_TELEM:" in msg:
                tag = "telemetry"
            # Check for info messages
            elif any(keyword in msg_upper for keyword in ["_INFO:", "_START:", "[SYSTEM]"]):
                tag = "info"
        
        # Insert with appropriate tag
        terminal.insert(tk.END, msg, tag)
        terminal.see(tk.END)

    # Create checkboxes for the options frame (already packed above)
    show_telemetry_var = tk.BooleanVar(value=False)
    show_discovery_var = tk.BooleanVar(value=False)
    show_debug_var = tk.BooleanVar(value=False)  # Default to False - Debug messages hidden by default
    show_python_console_var = tk.BooleanVar(value=False)  # Default to False - Python messages hidden by default

    # Use a style that inherits the correct background from the theme
    style = ttk.Style()
    style.configure("Terminal.TCheckbutton", background=theme.CARD_BG, foreground=theme.FG_COLOR, font=("Segoe UI", 8))
    style.map("Terminal.TCheckbutton", background=[('active', theme.CARD_BG)])

    telemetry_check = ttk.Checkbutton(options_frame, text="Show Telemetry", variable=show_telemetry_var,
                                      style="Terminal.TCheckbutton")
    telemetry_check.pack(side=tk.LEFT, padx=5)

    discovery_check = ttk.Checkbutton(options_frame, text="Show Discovery", variable=show_discovery_var,
                                     style="Terminal.TCheckbutton")
    discovery_check.pack(side=tk.LEFT, padx=5)

    debug_check = ttk.Checkbutton(options_frame, text="Show Debug", variable=show_debug_var,
                                  style="Terminal.TCheckbutton")
    debug_check.pack(side=tk.LEFT, padx=5)

    python_console_check = ttk.Checkbutton(options_frame, text="Show Python Console", variable=show_python_console_var,
                                          style="Terminal.TCheckbutton")
    python_console_check.pack(side=tk.LEFT, padx=5)

    # Return a dictionary of the created widgets and their references
    return {
        'terminal': terminal,
        'terminal_cb': insert_colored_message,
        'terminal_frame': bottom_frame,
        'show_telemetry_var': show_telemetry_var,
        'show_discovery_var': show_discovery_var,
        'show_debug_var': show_debug_var,
        'show_python_console_var': show_python_console_var
    }
