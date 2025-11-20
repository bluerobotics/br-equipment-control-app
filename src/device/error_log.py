"""
Error Log Viewer - Displays device error logs in a dedicated window.

This module provides a GUI for dumping and viewing internal error logs
from devices, with syntax highlighting and clipboard support.
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from .. import theme
import time


def show_error_log_window(parent, gui_refs):
    """Shows a window to select a device, dump its error log, and display the output."""
    # Import here to avoid circular dependencies
    from ..comms import network
    
    device_manager = gui_refs.get('device_manager')
    if not device_manager:
        messagebox.showwarning("No Device Manager", "Device manager not initialized.")
        return
    
    # Get list of connected devices
    connected_devices = []
    for device_name in device_manager.get_all_device_names():
        device_state = device_manager.get_device_state(device_name)
        if device_state and device_state.get('connected'):
            connected_devices.append(device_name)
    
    if not connected_devices:
        messagebox.showinfo("No Devices", "No devices are currently connected.")
        return
    
    # Create main window
    window = tk.Toplevel(parent)
    window.title("Device Error Log")
    window.configure(bg=theme.BG_COLOR)
    window.transient(parent)
    
    # Don't set geometry yet - let it auto-size based on content
    # We'll set a minimum size after packing everything
    
    # Main container
    main_frame = tk.Frame(window, bg=theme.BG_COLOR)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top frame - device selection and controls
    top_frame = tk.Frame(main_frame, bg=theme.BG_COLOR)
    top_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Device selection
    device_label = tk.Label(
        top_frame,
        text="Device:",
        bg=theme.BG_COLOR,
        fg=theme.FG_COLOR,
        font=("Segoe UI", 10)
    )
    device_label.pack(side=tk.LEFT, padx=(0, 5))
    
    # Map display names to device keys
    device_display_map = {d.capitalize(): d for d in connected_devices}
    display_names = list(device_display_map.keys())
    
    selected_display = tk.StringVar(value=display_names[0])
    
    # Style the combobox for dark theme (use unique style name to avoid conflicts)
    combo_style = ttk.Style()
    # Don't call theme_use - it resets the global theme for the entire app!
    # Instead, just configure a custom style based on the current theme
    combo_style.configure('ErrorLog.TCombobox',
                         fieldbackground=theme.WIDGET_BG,
                         background=theme.WIDGET_BG,
                         foreground=theme.FG_COLOR,
                         arrowcolor=theme.FG_COLOR,
                         bordercolor=theme.WIDGET_BORDER,
                         lightcolor=theme.WIDGET_BG,
                         darkcolor=theme.WIDGET_BG,
                         selectbackground=theme.PRIMARY_ACCENT,
                         selectforeground=theme.FG_COLOR)
    combo_style.map('ErrorLog.TCombobox',
                   fieldbackground=[('readonly', theme.WIDGET_BG)],
                   foreground=[('readonly', theme.FG_COLOR)])
    
    device_dropdown = ttk.Combobox(
        top_frame,
        textvariable=selected_display,
        values=display_names,
        state='readonly',
        width=20,
        style='ErrorLog.TCombobox'
    )
    device_dropdown.pack(side=tk.LEFT, padx=(0, 10))
    device_dropdown.current(0)
    
    def get_device_key():
        """Get the actual device key from the selected display name."""
        return device_display_map[selected_display.get()]
    
    # Dump button
    dump_btn = tk.Button(
        top_frame,
        text="Dump Error Log",
        bg=theme.PRIMARY_ACCENT,
        fg=theme.BG_COLOR,  # Dark text on bright button
        font=("Segoe UI", 10, "bold"),
        relief=tk.FLAT,
        padx=15,
        pady=5,
        cursor="hand2",
        activebackground=theme.SECONDARY_ACCENT,
        activeforeground=theme.BG_COLOR
    )
    dump_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    # Clear button
    clear_btn = tk.Button(
        top_frame,
        text="Clear",
        bg=theme.WIDGET_BG,
        fg=theme.FG_COLOR,
        font=("Segoe UI", 10),
        relief=tk.FLAT,
        padx=15,
        pady=5,
        cursor="hand2"
    )
    clear_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    # Copy button
    copy_btn = tk.Button(
        top_frame,
        text="Copy to Clipboard",
        bg=theme.WIDGET_BG,
        fg=theme.FG_COLOR,
        font=("Segoe UI", 10),
        relief=tk.FLAT,
        padx=15,
        pady=5,
        cursor="hand2"
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    # Status label
    status_label = tk.Label(
        top_frame,
        text="Ready",
        bg=theme.BG_COLOR,
        fg=theme.COMMENT_COLOR,
        font=("Segoe UI", 9)
    )
    status_label.pack(side=tk.RIGHT)
    
    # Text area for log output
    text_frame = tk.Frame(main_frame, bg=theme.WIDGET_BORDER, bd=1)
    text_frame.pack(fill=tk.BOTH, expand=True)
    
    text_area = scrolledtext.ScrolledText(
        text_frame,
        wrap=tk.WORD,
        bg=theme.WIDGET_BG,
        fg=theme.FG_COLOR,
        insertbackground=theme.FG_COLOR,
        font=("Consolas", 9),
        relief=tk.FLAT,
        padx=5,
        pady=5
    )
    text_area.pack(fill=tk.BOTH, expand=True)
    
    # Configure text tags for different log levels
    text_area.tag_config("header", foreground=theme.PRIMARY_ACCENT, font=("Consolas", 9, "bold"))
    text_area.tag_config("debug", foreground=theme.COMMENT_COLOR)
    text_area.tag_config("info", foreground=theme.FG_COLOR)
    text_area.tag_config("warning", foreground="#FFA500")
    text_area.tag_config("error", foreground="#FF6B6B")
    text_area.tag_config("critical", foreground="#FF0000", font=("Consolas", 9, "bold"))
    
    # Variables for message capture
    capturing = {'active': False, 'messages': [], 'complete': False}
    capture_start_time = {'time': 0}
    capture_start_index = {'index': '1.0'}  # Track terminal position when dump starts
    
    def append_log_line(line):
        """Append a line to the text area with appropriate formatting."""
        text_area.insert(tk.END, line + "\n")
        
        # Apply formatting based on content
        line_start = text_area.index(f"end-2l linestart")
        line_end = text_area.index(f"end-2l lineend")
        
        if "===" in line or "ERROR LOG" in line or "END ERROR LOG" in line:
            text_area.tag_add("header", line_start, line_end)
        elif "DEBUG:" in line:
            text_area.tag_add("debug", line_start, line_end)
        elif "INFO:" in line:
            text_area.tag_add("info", line_start, line_end)
        elif "WARN:" in line:
            text_area.tag_add("warning", line_start, line_end)
        elif "ERROR:" in line:
            text_area.tag_add("error", line_start, line_end)
        elif "CRIT:" in line:
            text_area.tag_add("critical", line_start, line_end)
        
        text_area.see(tk.END)
    
    def poll_terminal_for_log():
        """Poll the terminal widget for new error log messages."""
        try:
            # Get the terminal text widget from gui_refs
            terminal_widget = gui_refs.get('terminal')
            if not terminal_widget:
                return
            
            # Get only NEW text from terminal (since we started the dump request)
            terminal_content = terminal_widget.get(capture_start_index['index'], tk.END)
            
            # Look for our device's messages since we started
            device_name = get_device_key().upper()
            lines = terminal_content.split('\n')
            
            found_start = False
            found_end = False
            
            for line in lines:
                # Look for messages from our device
                if device_name in line:
                    # Check if this is the start of error log
                    if "=== ERROR LOG:" in line:
                        found_start = True
                        capturing['messages'].clear()  # Clear any previous partial data
                    
                    if found_start:
                        # Extract the actual log content
                        content = line
                        
                        # Strip timestamp
                        if content.startswith('['):
                            bracket_end = content.find(']')
                            if bracket_end != -1:
                                content = content[bracket_end + 1:].strip()
                        
                        # Strip status type
                        if content.startswith('['):
                            bracket_end = content.find(']')
                            if bracket_end != -1:
                                content = content[bracket_end + 1:].strip()
                                if content.startswith(':'):
                                    content = content[1:].strip()
                        
                        # Strip device prefix
                        for prefix in [f"{device_name}_INFO:", f"{device_name}_DONE:"]:
                            if content.startswith(prefix):
                                content = content[len(prefix):].strip()
                                break
                        
                        # Skip if empty or just the command
                        if content and content != "dump_error_log":
                            # Only add if not already added
                            if content not in capturing['messages']:
                                capturing['messages'].append(content)
                                append_log_line(content)
                        
                        # Check for end
                        if "=== END ERROR LOG ===" in line or ("dump_error_log" in line and "DONE" in line):
                            found_end = True
            
            # Check if we're done
            if found_end and found_start:
                capturing['active'] = False
                capturing['complete'] = True
                elapsed = time.time() - capture_start_time['time']
                status_label.config(text=f"Completed ({elapsed:.1f}s)")
                dump_btn.config(state='normal')
            elif capturing['active']:
                # Keep polling
                window.after(100, poll_terminal_for_log)
                
        except Exception as e:
            # Silently fail to avoid cluttering console
            pass
    
    def on_dump():
        """Handle dump button click."""
        device_name = get_device_key()
        
        # Clear text area
        text_area.delete(1.0, tk.END)
        
        # Update status
        status_label.config(text="Dumping error log...")
        dump_btn.config(state='disabled')
        
        # Capture the current terminal position - only scan NEW messages from this point forward
        terminal_widget = gui_refs.get('terminal')
        if terminal_widget:
            capture_start_index['index'] = terminal_widget.index(tk.END)
        
        # Start capturing
        capturing['active'] = True
        capturing['complete'] = False
        capturing['messages'] = []
        capture_start_time['time'] = time.time()
        
        # Add header
        append_log_line(f"=== Requesting error log from {device_name.upper()} ===")
        append_log_line("")
        
        # Send command
        network.send_to_device(device_name, "dump_error_log", gui_refs)
        
        # Start polling terminal for messages
        window.after(500, poll_terminal_for_log)  # Start polling after 500ms
        
        # Set timeout
        def check_timeout():
            if capturing['active'] and not capturing['complete']:
                capturing['active'] = False
                status_label.config(text="Timeout - no response received")
                dump_btn.config(state='normal')
                append_log_line("")
                append_log_line("=== Timeout waiting for response ===")
        
        window.after(10000, check_timeout)  # 10 second timeout
    
    def on_clear():
        """Clear the text area."""
        text_area.delete(1.0, tk.END)
        status_label.config(text="Cleared")
    
    def on_copy():
        """Copy text area content to clipboard."""
        content = text_area.get(1.0, tk.END).strip()
        if content:
            window.clipboard_clear()
            window.clipboard_append(content)
            status_label.config(text="Copied to clipboard")
            window.after(2000, lambda: status_label.config(text="Ready"))
        else:
            status_label.config(text="Nothing to copy")
    
    # Connect button commands
    dump_btn.config(command=on_dump)
    clear_btn.config(command=on_clear)
    copy_btn.config(command=on_copy)
    
    # Set minimum size and let window auto-size to content
    window.minsize(800, 500)
    
    # Update to calculate actual size needed
    window.update_idletasks()
    
    # Set preferred size (not too big, not too small)
    window_width = max(800, min(window.winfo_reqwidth() + 40, 1000))
    window_height = max(500, min(window.winfo_reqheight() + 40, 700))
    
    # Center the window
    x = (window.winfo_screenwidth() // 2) - (window_width // 2)
    y = (window.winfo_screenheight() // 2) - (window_height // 2)
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Initial instruction
    text_area.insert(1.0, "Click 'Dump Error Log' to retrieve error log from the selected device.\n\n")
    text_area.insert(tk.END, "The error log contains diagnostic information including:\n")
    text_area.insert(tk.END, "  • USB connection events\n")
    text_area.insert(tk.END, "  • Commands received\n")
    text_area.insert(tk.END, "  • System state changes\n")
    text_area.insert(tk.END, "  • Errors and warnings\n")

