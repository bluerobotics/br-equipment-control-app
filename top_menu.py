import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from tkinter import Menu
import theme
import os
import webbrowser


def open_documentation():
    """Opens the README.md file in the default web browser or text editor."""
    filepath = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(filepath):
        # Using webbrowser is a cross-platform way to open the file
        # It will open in a browser, which renders Markdown nicely.
        webbrowser.open(f'file://{os.path.realpath(filepath)}')
    else:
        messagebox.showerror("Documentation Not Found", f"Could not find README.md at:\n{filepath}")


def create_top_menu(parent, file_commands, edit_commands, device_commands, autosave_var):
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
    file_menu.add_command(label="Exit", command=parent.quit)
    
    menubar.add_cascade(label="File", menu=file_menu)

    # --- NEW: Edit Menu ---
    edit_menu = Menu(menubar, tearoff=0, 
                     bg=theme.WIDGET_BG, 
                     fg=theme.FG_COLOR,
                     activebackground=theme.PRIMARY_ACCENT,
                     activeforeground=theme.FG_COLOR)
    edit_menu.add_command(label="Find/Replace", command=edit_commands['find_replace'], accelerator="Ctrl+F")
    menubar.add_cascade(label="Edit", menu=edit_menu)

    # --- NEW: Devices Menu ---
    devices_menu = Menu(menubar, tearoff=0,
                        bg=theme.WIDGET_BG,
                        fg=theme.FG_COLOR,
                        activebackground=theme.PRIMARY_ACCENT,
                        activeforeground=theme.FG_COLOR)
    devices_menu.add_command(label="Run Simulator", command=device_commands['run_simulator'])
    devices_menu.add_separator(background=theme.WIDGET_BORDER)
    devices_menu.add_command(label="Scan for New Device Modules", command=device_commands['scan_for_devices'])
    devices_menu.add_command(label="Show Known Devices", command=device_commands['show_known_devices'])
    menubar.add_cascade(label="Devices", menu=devices_menu)

    # --- Help Menu ---
    help_menu = tk.Menu(menubar, tearoff=0, bg=theme.WIDGET_BG, fg=theme.FG_COLOR)
    help_menu.add_command(label="Documentation", command=open_documentation)
    help_menu.add_command(label="About", command=lambda: show_about_window(parent))
    menubar.add_cascade(label="Help", menu=help_menu)

    parent.config(menu=menubar)

    return menubar, recent_files_menu


def show_about_window(parent):
    """Displays the 'About' window with version and author information."""
    messagebox.showinfo(
        "About BR Equipment Control App",
        "BR Equipment Control App\n\n"
        "Version: 1.2\n"
        "Release Date: 2025-10-13\n\n"
        "Author: Eldin Miller-Stead",
        parent=parent
    )