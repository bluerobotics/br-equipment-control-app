import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from tkinter import Menu
import theme
import os
import webbrowser
from _version import __version__


def open_documentation():
    """Opens the README.md file in the default web browser or text editor."""
    filepath = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(filepath):
        # Using webbrowser is a cross-platform way to open the file
        # It will open in a browser, which renders Markdown nicely.
        webbrowser.open(f'file://{os.path.realpath(filepath)}')
    else:
        messagebox.showerror("Documentation Not Found", f"Could not find README.md at:\n{filepath}")


def create_top_menu(parent, file_commands, edit_commands, script_commands, device_commands, settings_commands, autosave_var, ui_scale_var, set_ui_scale_callback):
    """
    Creates the main application menu bar.
    """
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
    file_menu.add_command(label="Generate C++ Code...", command=device_commands['generate_cpp_code'])
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
    menubar.add_cascade(label="Devices", menu=devices_menu)

    # --- Settings Menu ---
    settings_menu = Menu(menubar, tearoff=0, 
                         bg=theme.WIDGET_BG, 
                         fg=theme.FG_COLOR,
                         activebackground=theme.PRIMARY_ACCENT,
                         activeforeground=theme.FG_COLOR)
    settings_menu.add_command(label="Change Device Folder...", command=settings_commands['change_device_folder'])

    # UI Scale submenu
    scale_menu = Menu(settings_menu, tearoff=0,
                      bg=theme.WIDGET_BG,
                      fg=theme.FG_COLOR,
                      activebackground=theme.PRIMARY_ACCENT,
                      activeforeground=theme.FG_COLOR)
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
    settings_menu.add_cascade(label="UI Scale", menu=scale_menu)
    menubar.add_cascade(label="Settings", menu=settings_menu)

    # --- Help Menu ---
    help_menu = tk.Menu(menubar, tearoff=0, bg=theme.WIDGET_BG, fg=theme.FG_COLOR)
    help_menu.add_command(label="Documentation", command=open_documentation)
    help_menu.add_command(label="About", command=lambda: show_about_window(parent))
    menubar.add_cascade(label="Help", menu=help_menu)

    parent.config(menu=menubar)

    return menubar, recent_files_menu


def show_about_window(parent):
    """Opens the GitHub repository in the browser."""
    webbrowser.open('https://github.com/bluerobotics/br-equipment-control-app')