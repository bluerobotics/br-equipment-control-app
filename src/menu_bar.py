import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from tkinter import Menu
from . import theme
import os
import webbrowser
import platform
from _version import __version__




def create_top_menu(parent, file_commands, edit_commands, script_commands, settings_commands, gui_refs, autosave_var, ui_scale_var, set_ui_scale_callback, font_var=None, set_font_callback=None, font_size_var=None, set_font_size_callback=None, serial_panel_visible_var=None, view_commands=None):
    """
    Creates the main application menu bar.
    """
    # Import here to avoid circular dependencies
    from .codegen.generator import show_code_generator
    from .firmware import open_firmware_manager
    from .device.error_log import show_error_log_window
    from .device.nvm_dump import show_nvm_dump_window
    
    # Create device commands
    device_commands = {
        'generate_cpp_code': lambda: show_code_generator(parent, gui_refs),
        'open_firmware_manager': lambda: open_firmware_manager(parent, gui_refs),
        'dump_error_log': lambda: show_error_log_window(parent, gui_refs),
        'dump_nvm': lambda: show_nvm_dump_window(parent, gui_refs)
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
    file_menu.add_command(label="New Tab", command=file_commands['new'], accelerator="Ctrl+N")
    file_menu.add_command(label="Open Script...", command=file_commands['open'])
    file_menu.add_command(label="Save", command=file_commands['save'])
    file_menu.add_command(label="Save As...", command=file_commands['save_as'])
    if 'close_tab' in file_commands:
        file_menu.add_command(label="Close Tab", command=file_commands['close_tab'], accelerator="Ctrl+W")
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

    # --- View Menu ---
    if view_commands:
        view_menu = Menu(menubar, tearoff=0,
                         bg=theme.WIDGET_BG,
                         fg=theme.FG_COLOR,
                         activebackground=theme.PRIMARY_ACCENT,
                         activeforeground=theme.FG_COLOR)
        if 'toggle_editor' in view_commands:
            view_menu.add_command(
                label="Toggle Script Editor",
                command=view_commands['toggle_editor'],
                accelerator="Ctrl+E"
            )
        menubar.add_cascade(label="View", menu=view_menu)

    # --- Devices Menu ---
    devices_menu = Menu(menubar,
                        tearoff=0,
                        bg=theme.WIDGET_BG,
                        fg=theme.FG_COLOR,
                        activebackground=theme.PRIMARY_ACCENT,
                        activeforeground=theme.FG_COLOR)
    devices_menu.add_command(label="Firmware Manager...", command=device_commands['open_firmware_manager'])
    devices_menu.add_separator(background=theme.WIDGET_BORDER)
    devices_menu.add_command(label="Dump NVM...", command=device_commands['dump_nvm'])
    devices_menu.add_separator(background=theme.WIDGET_BORDER)
    devices_menu.add_command(label="Dump Error Log...", command=device_commands['dump_error_log'])
    devices_menu.add_separator(background=theme.WIDGET_BORDER)
    devices_menu.add_command(label="C++ Code Generator...", command=device_commands['generate_cpp_code'])
    menubar.add_cascade(label="Devices", menu=devices_menu)

    # --- Settings Menu ---
    settings_menu = Menu(menubar, tearoff=0, 
                         bg=theme.WIDGET_BG, 
                         fg=theme.FG_COLOR,
                         activebackground=theme.PRIMARY_ACCENT,
                         activeforeground=theme.FG_COLOR)
    
    # Show Serial Number Panel toggle
    if 'toggle_serial_panel' in settings_commands and serial_panel_visible_var is not None:
        settings_menu.add_checkbutton(
            label="Show Serial Number Panel",
            onvalue=True,
            offvalue=False,
            variable=serial_panel_visible_var,
            command=settings_commands['toggle_serial_panel'],
            selectcolor=theme.PRIMARY_ACCENT
        )
        settings_menu.add_separator(background=theme.WIDGET_BORDER)
    
    # Serial Number Settings
    if 'serial_settings' in settings_commands:
        settings_menu.add_command(label="Serial Number Settings...", command=settings_commands['serial_settings'])
        settings_menu.add_separator(background=theme.WIDGET_BORDER)

    # Quick Launch Scripts
    if 'manage_quick_launch' in settings_commands:
        settings_menu.add_command(label="Manage Quick Launch Scripts...", command=settings_commands['manage_quick_launch'])
        settings_menu.add_separator(background=theme.WIDGET_BORDER)
    
    # Cycle Statistics
    def show_cycle_stats():
        from .stats import get_stats, format_duration, format_cycle_time, format_yield
        
        stats = get_stats()
        all_stats = stats.get_all_stats()
        
        # Create popup window - let it auto-size to content
        popup = tk.Toplevel(parent)
        popup.title("Cycle Statistics")
        popup.configure(bg=theme.BG_COLOR)
        popup.resizable(True, True)
        popup.transient(parent)
        popup.grab_set()
        
        # Title
        title = tk.Label(
            popup,
            text="Cycle Statistics",
            font=(theme.FONT_FAMILY, 24, 'bold'),
            foreground=theme.PRIMARY_ACCENT,
            bg=theme.BG_COLOR
        )
        title.pack(pady=(20, 20))
        
        # Stats container
        stats_frame = tk.Frame(popup, bg=theme.BG_COLOR)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        def add_stat_row(frame, label, value, row):
            lbl = tk.Label(frame, text=label, font=(theme.FONT_FAMILY, 14),
                          foreground=theme.COMMENT_COLOR, bg=theme.BG_COLOR, anchor='w')
            lbl.grid(row=row, column=0, sticky='w', pady=5)
            val = tk.Label(frame, text=str(value), font=(theme.FONT_FAMILY, 14, 'bold'),
                          foreground=theme.FG_COLOR, bg=theme.BG_COLOR, anchor='e')
            val.grid(row=row, column=1, sticky='e', pady=5, padx=(20, 0))
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Operations Section
        tk.Label(stats_frame, text="── Operations ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR).grid(row=row, column=0, columnspan=2, pady=(10, 5), sticky='w')
        row += 1
        add_stat_row(stats_frame, "Since Host Boot:", str(all_stats['operations_since_boot']), row); row += 1
        add_stat_row(stats_frame, "Total:", str(all_stats['operations_total']), row); row += 1
        
        # Cycle Times Section
        tk.Label(stats_frame, text="── Cycle Times ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR).grid(row=row, column=0, columnspan=2, pady=(15, 5), sticky='w')
        row += 1
        add_stat_row(stats_frame, "Last Cycle:", format_cycle_time(all_stats['last_cycle_time']), row); row += 1
        # This Job Avg
        this_job_label = f"This Job Avg ({all_stats['current_job']}):" if all_stats['current_job'] else "This Job Avg:"
        add_stat_row(stats_frame, this_job_label, format_cycle_time(all_stats['job_average_cycle_time']), row); row += 1
        # Last Job Avg (only show if we have a last job)
        if all_stats['last_job']:
            last_job_label = f"Last Job Avg ({all_stats['last_job']}):"
            add_stat_row(stats_frame, last_job_label, format_cycle_time(all_stats['last_job_average_cycle_time']), row); row += 1
        # Only show "Last 100" if we have at least 1 sample
        if all_stats['sample_size_100'] > 0:
            add_stat_row(stats_frame, f"Avg (Last {all_stats['sample_size_100']}):", 
                         format_cycle_time(all_stats['average_cycle_time_100']), row); row += 1
        # Only show "Last 1000" if we have at least 100 samples
        if all_stats['sample_size_1000'] >= 100:
            add_stat_row(stats_frame, f"Avg (Last {all_stats['sample_size_1000']}):", 
                         format_cycle_time(all_stats['average_cycle_time_1000']), row); row += 1
        add_stat_row(stats_frame, "Avg (Total):", format_cycle_time(all_stats['average_cycle_time_total']), row); row += 1
        
        # Yield Section
        tk.Label(stats_frame, text="── Yield ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR).grid(row=row, column=0, columnspan=2, pady=(15, 5), sticky='w')
        row += 1
        # This Job
        this_job_yield_label = f"This Job ({all_stats['current_job']}):" if all_stats['current_job'] else "This Job:"
        add_stat_row(stats_frame, this_job_yield_label, format_yield(all_stats['yield_job']), row); row += 1
        # Last Job (only show if we have a last job)
        if all_stats['last_job']:
            last_job_yield_label = f"Last Job ({all_stats['last_job']}):"
            add_stat_row(stats_frame, last_job_yield_label, format_yield(all_stats['yield_last_job']), row); row += 1
        # Only show "Last 100" if we have at least 1 sample
        if all_stats['sample_size_100'] > 0:
            add_stat_row(stats_frame, f"Last {all_stats['sample_size_100']}:", format_yield(all_stats['yield_100']), row); row += 1
        # Only show "Last 1000" if we have at least 100 samples
        if all_stats['sample_size_1000'] >= 100:
            add_stat_row(stats_frame, f"Last {all_stats['sample_size_1000']}:", format_yield(all_stats['yield_1000']), row); row += 1
        add_stat_row(stats_frame, "Total:", format_yield(all_stats['yield_total']), row); row += 1
        
        # Exit Stats button (larger for touchscreen)
        tk.Button(popup, text="Exit Stats", command=popup.destroy, font=(theme.FONT_FAMILY, 18, 'bold'),
                 bg=theme.WIDGET_BG, fg=theme.FG_COLOR, activebackground='#444444',
                 activeforeground=theme.FG_COLOR, relief='raised', borderwidth=2,
                 padx=40, pady=12, cursor='hand2').pack(pady=(20, 30))
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f'+{x}+{y}')
    
    settings_menu.add_command(label="Cycle Statistics...", command=show_cycle_stats)
    settings_menu.add_separator(background=theme.WIDGET_BORDER)
    
    if 'show_paths' in settings_commands:
        settings_menu.add_command(label="Show Application Paths...", command=settings_commands['show_paths'])
        settings_menu.add_separator(background=theme.WIDGET_BORDER)

    # UI Scale submenu (affects UI elements only, not fonts)
    scale_menu = Menu(settings_menu, tearoff=0,
                      bg=theme.WIDGET_BG,
                      fg=theme.FG_COLOR,
                      activebackground=theme.PRIMARY_ACCENT,
                      activeforeground=theme.FG_COLOR)
    
    scale_options = [
        ("80%", 0.8),
        ("90%", 0.9),
        ("100%", 1.0),
        ("110%", 1.1),
        ("120%", 1.2),
        ("130%", 1.3),
        ("140%", 1.4),
        ("150%", 1.5),
        ("175%", 1.75),
        ("200%", 2.0),
    ]
    
    for label, value in scale_options:
        scale_menu.add_radiobutton(
            label=label,
            variable=ui_scale_var,
            value=value,
            command=lambda v=value: set_ui_scale_callback(v)
        )
    
    settings_menu.add_cascade(label="UI Scale", menu=scale_menu)
    
    # Font Family submenu
    if font_var is not None and set_font_callback is not None:
        font_menu = Menu(settings_menu, tearoff=0,
                         bg=theme.WIDGET_BG,
                         fg=theme.FG_COLOR,
                         activebackground=theme.PRIMARY_ACCENT,
                         activeforeground=theme.FG_COLOR)
        
        for display_name, font_family in theme.get_available_fonts():
            font_menu.add_radiobutton(
                label=display_name,
                variable=font_var,
                value=font_family,
                command=lambda f=font_family: set_font_callback(f)
            )
        
        settings_menu.add_cascade(label="Font Family", menu=font_menu)
    
    # Font Size submenu
    if font_size_var is not None and set_font_size_callback is not None:
        font_size_menu = Menu(settings_menu, tearoff=0,
                              bg=theme.WIDGET_BG,
                              fg=theme.FG_COLOR,
                              activebackground=theme.PRIMARY_ACCENT,
                              activeforeground=theme.FG_COLOR)
        
        # Font sizes from 8pt to 30pt
        font_sizes = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30]
        
        for size in font_sizes:
            font_size_menu.add_radiobutton(
                label=f"{size} pt",
                variable=font_size_var,
                value=size,
                command=lambda s=size: set_font_size_callback(s)
            )
        
        settings_menu.add_cascade(label="Font Size", menu=font_size_menu)
    
    menubar.add_cascade(label="Settings", menu=settings_menu)

    # --- Help Menu ---
    help_menu = tk.Menu(menubar, tearoff=0, bg=theme.WIDGET_BG, fg=theme.FG_COLOR,
                       activebackground=theme.PRIMARY_ACCENT,
                       activeforeground=theme.FG_COLOR)
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
    about_window.configure(bg=theme.BG_COLOR)
    about_window.resizable(False, False)
    about_window.transient(parent)
    
    # Main frame with padding
    main_frame = ttk.Frame(about_window, padding=30)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Logo
    try:
        import os
        import sys
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
        # Go up to project root if we're in src/
        if os.path.basename(script_dir) == 'src':
            script_dir = os.path.dirname(script_dir)
        icon_path = os.path.join(script_dir, 'assets', 'icon.png')
        
        if os.path.exists(icon_path):
            logo_img = tk.PhotoImage(file=icon_path)
            # Subsample to make it smaller (reduce by factor of 2)
            logo_img = logo_img.subsample(2, 2)
            logo_label = ttk.Label(main_frame, image=logo_img)
            logo_label.image = logo_img  # Keep a reference
            logo_label.pack(pady=(0, 20))
    except Exception as e:
        print(f"Could not load logo for About window: {e}")
    
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
    copyright_label.pack(pady=(0, 0))
    
    # Center the window after all content is packed
    about_window.update_idletasks()
    x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
    y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
    about_window.geometry(f"+{x}+{y}")
    
    # Store window reference
    show_about_window._window = about_window
    
    # Clean up on close
    def on_close():
        show_about_window._window = None
        about_window.destroy()
    
    about_window.protocol("WM_DELETE_WINDOW", on_close)