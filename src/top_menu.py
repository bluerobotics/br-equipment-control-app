import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from tkinter import Menu
from . import theme
import os
import webbrowser
import platform
from _version import __version__


def open_github_repo():
    """Opens the GitHub repository in the browser."""
    webbrowser.open('https://github.com/bluerobotics/br-equipment-control-app')


def create_top_menu(parent, file_commands, edit_commands, script_commands, settings_commands, gui_refs, autosave_var, ui_scale_var, set_ui_scale_callback):
    """
    Creates the main application menu bar.
    """
    # Import here to avoid circular dependencies
    from .codegen.generator import show_code_generator
    from .firmware import open_firmware_manager
    
    # Create device commands
    device_commands = {
        'generate_cpp_code': lambda: show_code_generator(parent, gui_refs),
        'open_firmware_manager': lambda: open_firmware_manager(parent, gui_refs)
    }
    
    menubar = Menu(parent, 
                   bg=theme.WIDGET_BG, 
                   fg=theme.FG_COLOR,
                   activebackground=theme.PRIMARY_ACCENT,
                   activeforeground=theme.FG_COLOR,
                   relief=tk.FLAT,
                   bd=0)
    
    # File Menu
    file_menu = Menu(menubar, tearoff=0, 
                     bg=theme.WIDGET_BG, 
                     fg=theme.FG_COLOR,
                     activebackground=theme.PRIMARY_ACCENT,
                     activeforeground=theme.FG_COLOR)
    file_menu.add_command(label="New Script", command=file_commands['new'])
    file_menu.add_command(label="Open Script...", command=file_commands['open'])
    file_menu.add_command(label="Save", command=file_commands['save'])
    file_menu.add_command(label="Save As...", command=file_commands['save_as'])
    file_menu.add_separator(background=theme.WIDGET_BORDER)
    file_menu.add_checkbutton(label="Autosave", onvalue=True, offvalue=False, variable=autosave_var,
                              selectcolor=theme.PRIMARY_ACCENT) # Color for checkmark
    file_menu.add_separator(background=theme.WIDGET_BORDER)
    
    # Recent files submenu
    recent_files_menu = Menu(file_menu, tearoff=0, 
                             bg=theme.WIDGET_BG, 
                             fg=theme.FG_COLOR,
                             activebackground=theme.PRIMARY_ACCENT,
                             activeforeground=theme.FG_COLOR)
    file_menu.add_cascade(label="Recent Files", menu=recent_files_menu)
    file_menu.add_separator(background=theme.WIDGET_BORDER)
    file_menu.add_command(label="Validate Script", command=script_commands['validate'], accelerator="Ctrl+Shift+V")
    file_menu.add_separator(background=theme.WIDGET_BORDER)
    if 'show_latest_system_log' in file_commands:
        file_menu.add_command(label="Show Latest System Log", command=file_commands['show_latest_system_log'])
    file_menu.add_separator(background=theme.WIDGET_BORDER)
    file_menu.add_command(label="Exit", command=parent.quit)
    
    menubar.add_cascade(label="File", menu=file_menu)

    # --- Edit Menu ---
    edit_menu = Menu(menubar, tearoff=0, 
                     bg=theme.WIDGET_BG, 
                     fg=theme.FG_COLOR,
                     activebackground=theme.PRIMARY_ACCENT,
                     activeforeground=theme.FG_COLOR)
    edit_menu.add_command(label="Undo", command=edit_commands['undo'], accelerator="Ctrl+Z")
    edit_menu.add_command(label="Redo", command=edit_commands['redo'], accelerator="Ctrl+Y")
    edit_menu.add_separator(background=theme.WIDGET_BORDER)
    edit_menu.add_command(label="Cut", command=edit_commands['cut'], accelerator="Ctrl+X")
    edit_menu.add_command(label="Copy", command=edit_commands['copy'], accelerator="Ctrl+C")
    edit_menu.add_command(label="Paste", command=edit_commands['paste'], accelerator="Ctrl+V")
    edit_menu.add_separator(background=theme.WIDGET_BORDER)
    edit_menu.add_command(label="Find", command=edit_commands['find'], accelerator="Ctrl+F")
    edit_menu.add_command(label="Replace", command=edit_commands['replace'], accelerator="Ctrl+H")
    menubar.add_cascade(label="Edit", menu=edit_menu)

    # --- Devices Menu ---
    devices_menu = Menu(menubar,
                        tearoff=0,
                        bg=theme.WIDGET_BG,
                        fg=theme.FG_COLOR,
                        activebackground=theme.PRIMARY_ACCENT,
                        activeforeground=theme.FG_COLOR)
    devices_menu.add_command(label="Firmware Manager...", command=device_commands['open_firmware_manager'])
    devices_menu.add_separator(background=theme.WIDGET_BORDER)
    devices_menu.add_command(label="C++ Code Generator...", command=device_commands['generate_cpp_code'])
    menubar.add_cascade(label="Devices", menu=devices_menu)

    # --- Settings Menu ---
    settings_menu = Menu(menubar, tearoff=0, 
                         bg=theme.WIDGET_BG, 
                         fg=theme.FG_COLOR,
                         activebackground=theme.PRIMARY_ACCENT,
                         activeforeground=theme.FG_COLOR)
    settings_menu.add_command(label="Change Device Folder...", command=settings_commands['change_device_folder'])
    if 'show_paths' in settings_commands:
        settings_menu.add_command(label="Show Application Paths...", command=settings_commands['show_paths'])
        settings_menu.add_separator(background=theme.WIDGET_BORDER)

    # UI Scale submenu
    scale_menu = Menu(settings_menu, tearoff=0,
                      bg=theme.WIDGET_BG,
                      fg=theme.FG_COLOR,
                      activebackground=theme.PRIMARY_ACCENT,
                      activeforeground=theme.FG_COLOR)
    
    if platform.system() == 'Darwin':  # macOS
        # Use simple Small/Medium/Large options for macOS
        scale_options = [
            ("Small", 0.85),
            ("Medium", 1.0),
            ("Large", 1.2),
        ]
    else:  # Windows and others
        # Use percentage scaling for Windows (where it works properly)
        scale_options = [
            ("90%", 0.9),
            ("100%", 1.0),
            ("110%", 1.1),
            ("120%", 1.2),
            ("130%", 1.3),
            ("140%", 1.4),
            ("150%", 1.5),
            ("160%", 1.6),
            ("175%", 1.75),
            ("200%", 2.0),
            ("225%", 2.25),
            ("250%", 2.5),
            ("275%", 2.75),
            ("300%", 3.0),
            ("325%", 3.25),
            ("350%", 3.5),
            ("375%", 3.75),
            ("400%", 4.0),
        ]
    
    for label, value in scale_options:
        scale_menu.add_radiobutton(
            label=label,
            variable=ui_scale_var,
            value=value,
            command=lambda v=value: set_ui_scale_callback(v)
        )
    
    # Label changes based on platform
    scale_label = "Text Size" if platform.system() == 'Darwin' else "UI Scale"
    settings_menu.add_cascade(label=scale_label, menu=scale_menu)
    menubar.add_cascade(label="Settings", menu=settings_menu)

    # --- Help Menu ---
    help_menu = tk.Menu(menubar, tearoff=0, bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                       activebackground=theme.PRIMARY_ACCENT,
                       activeforeground=theme.FG_COLOR)
    help_menu.add_command(label="GitHub Repository", command=open_github_repo)
    help_menu.add_command(label="About", command=lambda: show_about_window(parent))
    menubar.add_cascade(label="Help", menu=help_menu)

    parent.config(menu=menubar)

    return menubar, recent_files_menu


def show_about_window(parent):
    """Shows an About window with app information."""
    # Create or reuse about window
    if hasattr(show_about_window, '_window') and show_about_window._window:
        if show_about_window._window.winfo_exists():
            show_about_window._window.lift()
            return
    
    about_window = tk.Toplevel(parent)
    about_window.title("About BR Equipment Control App")
    about_window.geometry("500x350")
    about_window.configure(bg=theme.BG_COLOR)
    about_window.resizable(False, False)
    about_window.transient(parent)
    
    # Center the window
    about_window.update_idletasks()
    x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
    y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
    about_window.geometry(f"+{x}+{y}")
    
    # Main frame with padding
    main_frame = ttk.Frame(about_window, padding=30)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # App name
    app_name_label = ttk.Label(
        main_frame,
        text="BR Equipment Control App",
        font=("Segoe UI", 18, "bold"),
        foreground=theme.FG_COLOR
    )
    app_name_label.pack(pady=(0, 10))
    
    # Version
    version_label = ttk.Label(
        main_frame,
        text=f"Version {__version__}",
        font=("Segoe UI", 11),
        foreground=theme.COMMENT_COLOR
    )
    version_label.pack(pady=(0, 20))
    
    # Description
    description_text = (
        "A comprehensive control application for Blue Robotics equipment,\n"
        "including script-based automation, device management, and\n"
        "firmware updates."
    )
    description_label = ttk.Label(
        main_frame,
        text=description_text,
        font=("Segoe UI", 9),
        foreground=theme.FG_COLOR,
        justify=tk.CENTER
    )
    description_label.pack(pady=(0, 20))
    
    # GitHub link
    github_frame = ttk.Frame(main_frame)
    github_frame.pack(pady=(0, 20))
    
    github_label = ttk.Label(
        github_frame,
        text="GitHub: ",
        font=("Segoe UI", 9),
        foreground=theme.FG_COLOR
    )
    github_label.pack(side=tk.LEFT)
    
    github_link = ttk.Label(
        github_frame,
        text="github.com/bluerobotics/br-equipment-control-app",
        font=("Segoe UI", 9, "underline"),
        foreground=theme.PRIMARY_ACCENT,
        cursor="hand2"
    )
    github_link.pack(side=tk.LEFT)
    
    def open_github(event=None):
        webbrowser.open('https://github.com/bluerobotics/br-equipment-control-app')
    
    github_link.bind("<Button-1>", open_github)
    
    # Copyright
    copyright_label = ttk.Label(
        main_frame,
        text="© Blue Robotics",
        font=("Segoe UI", 8),
        foreground=theme.COMMENT_COLOR
    )
    copyright_label.pack(pady=(0, 20))
    
    # Close button
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X)
    
    close_button = ttk.Button(
        button_frame,
        text="Close",
        command=about_window.destroy,
        style="Blue.TButton"
    )
    close_button.pack(side=tk.RIGHT)
    
    # Store window reference
    show_about_window._window = about_window
    
    # Clean up on close
    def on_close():
        show_about_window._window = None
        about_window.destroy()
    
    about_window.protocol("WM_DELETE_WINDOW", on_close)