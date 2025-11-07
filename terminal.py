import tkinter as tk
from tkinter import ttk
import theme
import re

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

    # Use a style that inherits the correct background from the theme
    style = ttk.Style()
    style.configure("Terminal.TCheckbutton", background=theme.CARD_BG, foreground=theme.FG_COLOR, font=("Segoe UI", 8))
    style.map("Terminal.TCheckbutton", background=[('active', theme.CARD_BG)])

    telemetry_check = ttk.Checkbutton(options_frame, text="Show Raw Telemetry", variable=show_telemetry_var,
                                      style="Terminal.TCheckbutton")
    telemetry_check.pack(side=tk.LEFT, padx=5)

    discovery_check = ttk.Checkbutton(options_frame, text="Show Raw Discovery", variable=show_discovery_var,
                                      style="Terminal.TCheckbutton")
    discovery_check.pack(side=tk.LEFT, padx=5)

    # Return a dictionary of the created widgets and their references
    return {
        'terminal': terminal,
        'terminal_cb': insert_colored_message,
        'terminal_frame': bottom_frame,
        'show_telemetry_var': show_telemetry_var,
        'show_discovery_var': show_discovery_var
    }
