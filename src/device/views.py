"""
Operator Views System - Simplified operator interfaces for devices.

This module provides a framework for creating simplified operator UIs that
can be displayed on app startup. Operator views provide:
- Simplified device controls (run/hold/reset)
- Current command display
- Custom device-specific UI elements
- Protected exit with confirmation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any
from src import theme


class OperatorView(tk.Toplevel):
    """
    Base operator view window with simplified controls.
    
    Operator views provide a streamlined interface for device operation with:
    - Current command display bar
    - Run, Hold, Reset buttons
    - Custom device-specific content area
    - Protected exit confirmation
    """
    
    def __init__(self, parent, device_name: str, device_data: Dict[str, Any], 
                 shared_gui_refs: Dict[str, Any], script_runner=None, view_id: Optional[str] = None):
        """
        Initialize operator view window.
        
        Args:
            parent: Parent window
            device_name: Name of the device
            device_data: Device data dictionary
            shared_gui_refs: Shared GUI references
            script_runner: Script runner for control hooks
            view_id: Optional specific view ID to show (from views.json)
        """
        super().__init__(parent)
        
        self.device_name = device_name
        self.device_data = device_data
        self.shared_gui_refs = shared_gui_refs
        self.script_runner = script_runner
        self.view_id = view_id
        self.custom_content_frame = None
        
        # Get view name from views data if view_id is provided
        view_name = "Operator View"
        if view_id:
            views_data = device_data.get('views_data', {})
            view_def = views_data.get(view_id, {})
            view_name = view_def.get('name', view_name)
        
        # Configure window
        self.title(f"{device_name.title()} - {view_name.title()}")
        self.configure(bg=theme.BG_COLOR)
        
        # Make window fullscreen
        self.attributes('-fullscreen', True)
        
        # Set window to stay on top initially
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
        
        # Bind Escape key to exit fullscreen (with confirmation)
        self.bind('<Escape>', lambda e: self._on_close_request())
        
        # Handle close button
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)
        
        # Build UI
        self._create_ui()
        
    def _create_ui(self):
        """Create the operator view UI structure."""
        # Main container - pack with expand to center vertically
        main_container = tk.Frame(self, bg=theme.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Exit button (top left corner) - place AFTER main_container so it's on top
        # Styled to match the dark/inactive "Scan Here" button style
        exit_btn = tk.Button(
            self,
            text="Exit Operator View",
            command=self._on_close_request,
            font=(theme.FONT_FAMILY, 14, 'bold'),
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            activebackground='#444444',
            activeforeground=theme.FG_COLOR,
            relief='raised',
            borderwidth=2,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        exit_btn.place(x=20, y=20)
        exit_btn.tkraise()  # Ensure it's on top of everything
        
        # Show Stats button (top right corner)
        stats_btn = tk.Button(
            self,
            text="Show Stats",
            command=self._show_stats,
            font=(theme.FONT_FAMILY, 14, 'bold'),
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            activebackground='#444444',
            activeforeground=theme.FG_COLOR,
            relief='raised',
            borderwidth=2,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        # Place in top right - we'll update position after window is drawn
        stats_btn.place(relx=1.0, x=-20, y=20, anchor='ne')
        stats_btn.tkraise()
        
        # Spacer to push content down (1 unit of expand)
        top_spacer = tk.Frame(main_container, bg=theme.BG_COLOR)
        top_spacer.pack(fill=tk.BOTH, expand=True)
        
        # Content container
        content_container = tk.Frame(main_container, bg=theme.BG_COLOR)
        content_container.pack(fill=tk.BOTH)
        
        # Control buttons (Run, Hold, Reset)
        btn_container = tk.Frame(content_container, bg=theme.BG_COLOR)
        btn_container.pack(pady=(0, 40))
        self._create_control_buttons(btn_container)
        
        # Custom content area (to be populated by device-specific views)
        self.custom_content_frame = tk.Frame(content_container, bg=theme.BG_COLOR)
        self.custom_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Placeholder text
        placeholder = tk.Label(
            self.custom_content_frame,
            text="Loading device-specific content...",
            font=theme.FONT_NORMAL,
            foreground=theme.COMMENT_COLOR,
            bg=theme.BG_COLOR
        )
        placeholder.pack(expand=True)
        
        # Spacer to push content up (1 unit of expand)
        bottom_spacer = tk.Frame(main_container, bg=theme.BG_COLOR)
        bottom_spacer.pack(fill=tk.BOTH, expand=True)
        
    def _create_command_display(self, parent):
        """Create the current command display bar."""
        cmd_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        cmd_frame.pack(fill=tk.X, pady=(0, 10))
        
        label = ttk.Label(
            cmd_frame,
            text="Current Command:",
            font=theme.FONT_BOLD,
            foreground='#B0A3D4',  # Lavender
            style='Subtle.TLabel'
        )
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.command_var = tk.StringVar(value="No script running")
        cmd_display = ttk.Label(
            cmd_frame,
            textvariable=self.command_var,
            font=theme.FONT_NORMAL,
            foreground=theme.FG_COLOR,
            style='Subtle.TLabel'
        )
        cmd_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Hook into script runner if available
        if self.script_runner:
            self._setup_command_tracking()
            
    def _setup_command_tracking(self):
        """Setup tracking of current script command."""
        # This would hook into the script runner to display current command
        # For now, just a placeholder
        pass
        
    def _create_control_buttons(self, parent):
        """Create control buttons that mirror the main script control buttons."""
        # Get script control handlers from shared_gui_refs
        script_controls = self.shared_gui_refs.get('script_controls', {})
        handle_cycle_start = script_controls.get('handle_cycle_start')
        handle_feed_hold = script_controls.get('handle_feed_hold')
        handle_reset = script_controls.get('handle_reset')
        register_buttons = script_controls.get('register_buttons')
        
        if not all([handle_cycle_start, handle_feed_hold, handle_reset, register_buttons]):
            # Fallback if script controls not available
            tk.Label(
                parent,
                text="Script controls not available",
                font=theme.FONT_NORMAL,
                foreground=theme.COMMENT_COLOR,
                bg=theme.BG_COLOR
            ).pack()
            return
        
        # Create large centered buttons with exact same handlers as main script GUI
        button_font = (theme.FONT_FAMILY, 28, 'bold')
        button_width = 18  # Character width - all buttons same size
        button_height = 3
        
        self.run_btn = tk.Button(
            parent,
            text="Run",
            command=handle_cycle_start,
            font=button_font,
            bg=theme.SUCCESS_GREEN,
            fg='black',
            activebackground=theme.PRESSED_GREEN,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.run_btn.pack(side=tk.LEFT, padx=20)
        
        # Add hover effect for run button
        def on_run_enter(e):
            if self.run_btn['state'] != 'disabled':
                current_bg = self.run_btn.cget('bg')
                if current_bg == theme.SUCCESS_GREEN:
                    self.run_btn.config(bg=theme.ACTIVE_GREEN)
        def on_run_leave(e):
            if self.run_btn['state'] != 'disabled':
                current_text = self.run_btn.cget('text')
                if current_text == 'Run':
                    self.run_btn.config(bg=theme.SUCCESS_GREEN)
        self.run_btn.bind('<Enter>', on_run_enter)
        self.run_btn.bind('<Leave>', on_run_leave)
        
        self.hold_btn = tk.Button(
            parent,
            text="Hold",
            command=handle_feed_hold,
            font=button_font,
            bg=theme.ERROR_RED,
            fg='black',
            activebackground=theme.PRESSED_RED,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.hold_btn.pack(side=tk.LEFT, padx=20)
        
        # Add hover effect for hold button
        def on_hold_enter(e):
            if self.hold_btn['state'] != 'disabled':
                current_bg = self.hold_btn.cget('bg')
                if current_bg == theme.ERROR_RED:
                    self.hold_btn.config(bg=theme.ACTIVE_RED)
                elif current_bg == theme.HOLDING_RED:
                    self.hold_btn.config(bg=theme.ACTIVE_HOLDING_RED)
        def on_hold_leave(e):
            if self.hold_btn['state'] != 'disabled':
                current_text = self.hold_btn.cget('text')
                if current_text == 'Hold':
                    self.hold_btn.config(bg=theme.ERROR_RED)
                elif current_text == 'Holding':
                    self.hold_btn.config(bg=theme.HOLDING_RED)
        self.hold_btn.bind('<Enter>', on_hold_enter)
        self.hold_btn.bind('<Leave>', on_hold_leave)
        
        self.reset_btn = tk.Button(
            parent,
            text="Reset",
            command=handle_reset,
            font=button_font,
            bg=theme.PRIMARY_ACCENT,
            fg='black',
            activebackground=theme.PRESSED_BLUE,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.reset_btn.pack(side=tk.LEFT, padx=20)
        
        # Add hover effect for reset button
        def on_reset_enter(e):
            self.reset_btn.config(bg=theme.ACTIVE_BLUE)
        def on_reset_leave(e):
            self.reset_btn.config(bg=theme.PRIMARY_ACCENT)
        self.reset_btn.bind('<Enter>', on_reset_enter)
        self.reset_btn.bind('<Leave>', on_reset_leave)
        
        # Register these buttons so they get updated by the same state management
        register_buttons(self.run_btn, self.hold_btn)
        
        # Trigger initial state refresh
        refresh_button_states = script_controls.get('refresh_button_states')
        if refresh_button_states:
            refresh_button_states()
            
    def _on_close_request(self):
        """Handle window close request with confirmation."""
        result = messagebox.askyesno(
            "Exit Operator Mode",
            "Are you sure you want to exit operator mode?\n\n"
            "This will return to the full application interface.",
            parent=self,
            icon='warning'
        )
        
        if result:
            # Unregister buttons from state management before closing
            script_controls = self.shared_gui_refs.get('script_controls', {})
            unregister_buttons = script_controls.get('unregister_buttons')
            if unregister_buttons and hasattr(self, 'run_btn') and hasattr(self, 'hold_btn'):
                unregister_buttons(self.run_btn, self.hold_btn)
            
            self.destroy()
    
    def _show_stats(self):
        """Show cycle statistics window."""
        from src.stats import get_stats, format_duration, format_cycle_time, format_yield
        
        stats = get_stats()
        all_stats = stats.get_all_stats()
        
        # Create popup window - let it auto-size to content
        popup = tk.Toplevel(self)
        popup.title("Cycle Statistics")
        popup.configure(bg=theme.BG_COLOR)
        popup.resizable(True, True)
        
        # Center on parent
        popup.transient(self)
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
            """Add a label-value row to the stats display."""
            lbl = tk.Label(
                frame,
                text=label,
                font=(theme.FONT_FAMILY, 14),
                foreground=theme.COMMENT_COLOR,
                bg=theme.BG_COLOR,
                anchor='w'
            )
            lbl.grid(row=row, column=0, sticky='w', pady=5)
            
            val = tk.Label(
                frame,
                text=str(value),
                font=(theme.FONT_FAMILY, 14, 'bold'),
                foreground=theme.FG_COLOR,
                bg=theme.BG_COLOR,
                anchor='e'
            )
            val.grid(row=row, column=1, sticky='e', pady=5, padx=(20, 0))
        
        # Configure grid columns
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Section: Operations
        section1 = tk.Label(stats_frame, text="── Operations ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                            foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR)
        section1.grid(row=row, column=0, columnspan=2, pady=(10, 5), sticky='w')
        row += 1
        
        add_stat_row(stats_frame, "Since Host Boot:", str(all_stats['operations_since_boot']), row)
        row += 1
        add_stat_row(stats_frame, "Total:", str(all_stats['operations_total']), row)
        row += 1
        
        # Section: Cycle Times
        section2 = tk.Label(stats_frame, text="── Cycle Times ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                            foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR)
        section2.grid(row=row, column=0, columnspan=2, pady=(15, 5), sticky='w')
        row += 1
        
        add_stat_row(stats_frame, "Last Cycle:", format_cycle_time(all_stats['last_cycle_time']), row)
        row += 1
        # This Job Avg
        this_job_label = f"This Job Avg ({all_stats['current_job']}):" if all_stats['current_job'] else "This Job Avg:"
        add_stat_row(stats_frame, this_job_label, format_cycle_time(all_stats['job_average_cycle_time']), row)
        row += 1
        # Last Job Avg (only show if we have a last job)
        if all_stats['last_job']:
            last_job_label = f"Last Job Avg ({all_stats['last_job']}):"
            add_stat_row(stats_frame, last_job_label, format_cycle_time(all_stats['last_job_average_cycle_time']), row)
            row += 1
        # Only show "Last 100" if we have at least 1 sample
        if all_stats['sample_size_100'] > 0:
            add_stat_row(stats_frame, f"Avg (Last {all_stats['sample_size_100']}):", 
                         format_cycle_time(all_stats['average_cycle_time_100']), row)
            row += 1
        # Only show "Last 1000" if we have at least 100 samples
        if all_stats['sample_size_1000'] >= 100:
            add_stat_row(stats_frame, f"Avg (Last {all_stats['sample_size_1000']}):", 
                         format_cycle_time(all_stats['average_cycle_time_1000']), row)
            row += 1
        add_stat_row(stats_frame, "Avg (Total):", format_cycle_time(all_stats['average_cycle_time_total']), row)
        row += 1
        
        # Section: Yield
        section3 = tk.Label(stats_frame, text="── Yield ──", font=(theme.FONT_FAMILY, 12, 'bold'),
                            foreground=theme.SECONDARY_ACCENT, bg=theme.BG_COLOR)
        section3.grid(row=row, column=0, columnspan=2, pady=(15, 5), sticky='w')
        row += 1
        
        # This Job
        this_job_yield_label = f"This Job ({all_stats['current_job']}):" if all_stats['current_job'] else "This Job:"
        add_stat_row(stats_frame, this_job_yield_label, format_yield(all_stats['yield_job']), row)
        row += 1
        # Last Job (only show if we have a last job)
        if all_stats['last_job']:
            last_job_yield_label = f"Last Job ({all_stats['last_job']}):"
            add_stat_row(stats_frame, last_job_yield_label, format_yield(all_stats['yield_last_job']), row)
            row += 1
        # Only show "Last 100" if we have at least 1 sample
        if all_stats['sample_size_100'] > 0:
            add_stat_row(stats_frame, f"Last {all_stats['sample_size_100']}:", format_yield(all_stats['yield_100']), row)
            row += 1
        # Only show "Last 1000" if we have at least 100 samples
        if all_stats['sample_size_1000'] >= 100:
            add_stat_row(stats_frame, f"Last {all_stats['sample_size_1000']}:", format_yield(all_stats['yield_1000']), row)
            row += 1
        add_stat_row(stats_frame, "Total:", format_yield(all_stats['yield_total']), row)
        row += 1
        
        # Exit Stats button (larger for touchscreen)
        close_btn = tk.Button(
            popup,
            text="Exit Stats",
            command=popup.destroy,
            font=(theme.FONT_FAMILY, 18, 'bold'),
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            activebackground='#444444',
            activeforeground=theme.FG_COLOR,
            relief='raised',
            borderwidth=2,
            padx=40,
            pady=12,
            cursor='hand2'
        )
        close_btn.pack(pady=(20, 30))
        
        # Center window on screen
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'{width}x{height}+{x}+{y}')
            
    def set_custom_content(self, content_widget):
        """
        Set custom device-specific content.
        
        Args:
            content_widget: Widget to display in the custom content area
        """
        print(f"[VIEWS] set_custom_content called with widget: {content_widget}")
        print(f"[VIEWS] custom_content_frame exists: {self.custom_content_frame.winfo_exists()}")
        print(f"[VIEWS] custom_content_frame children before clear: {len(self.custom_content_frame.winfo_children())}")
        
        # Clear existing content
        for widget in self.custom_content_frame.winfo_children():
            widget.destroy()
        
        print(f"[VIEWS] Packing content_widget into custom_content_frame")
        # Pack new content
        content_widget.pack(fill=tk.BOTH, expand=True)
        print(f"[VIEWS] Content widget packed successfully")
        print(f"[VIEWS] custom_content_frame children after pack: {len(self.custom_content_frame.winfo_children())}")


def load_operator_view(device_name: str, device_data: Dict[str, Any]) -> Optional[Callable]:
    """
    Load operator view creation function from device module.
    
    Args:
        device_name: Name of the device
        device_data: Device data dictionary
        
    Returns:
        Operator view creation function or None if not available
    """
    try:
        # Check if device has an operator view module
        module = device_data.get('modules', {}).get('operator_view')
        if module and hasattr(module, 'create_operator_view'):
            return module.create_operator_view
    except Exception as e:
        print(f"[VIEWS] Error loading operator view for {device_name}: {e}")
        
    return None


def show_operator_view(parent, device_name: str, device_data: Dict[str, Any], 
                      shared_gui_refs: Dict[str, Any], script_runner=None, view_id: Optional[str] = None) -> Optional[OperatorView]:
    """
    Show operator view window for a device.
    
    Args:
        parent: Parent window
        device_name: Name of the device
        device_data: Device data dictionary
        shared_gui_refs: Shared GUI references
        script_runner: Script runner for control hooks
        view_id: Optional specific view ID to show (from views.json)
        
    Returns:
        OperatorView window or None if no view available
    """
    # Create base operator view window
    view = OperatorView(parent, device_name, device_data, shared_gui_refs, script_runner, view_id)
    
    print(f"[VIEWS] Loading operator view for {device_name}, view_id={view_id}")
    print(f"[VIEWS] device_data keys: {device_data.keys()}")
    print(f"[VIEWS] modules: {device_data.get('modules', {}).keys()}")
    
    # Load device-specific operator view content
    view_creator = load_operator_view(device_name, device_data)
    print(f"[VIEWS] view_creator found: {view_creator is not None}")
    
    if view_creator:
        try:
            print(f"[VIEWS] Creating custom content with view_id={view_id}")
            print(f"[VIEWS] custom_content_frame: {view.custom_content_frame}")
            
            # Clear placeholder
            for widget in view.custom_content_frame.winfo_children():
                widget.destroy()
            
            # Create custom content directly in the frame (don't use set_custom_content)
            # The view_creator will create and pack widgets directly into custom_content_frame
            view_creator(view.custom_content_frame, shared_gui_refs, view_id)
            print(f"[VIEWS] Custom content created directly in custom_content_frame")
        except Exception as e:
            print(f"[VIEWS] Error creating operator view content for {device_name}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[VIEWS] No view_creator found, showing fallback message")
        # Show message if no custom view available
        # Clear existing content first
        for widget in view.custom_content_frame.winfo_children():
            widget.destroy()
        # Then create and pack the message
        msg = ttk.Label(
            view.custom_content_frame,
            text=f"No operator view defined for {device_name}",
            font=theme.FONT_NORMAL,
            foreground=theme.COMMENT_COLOR,
            style='Subtle.TLabel'
        )
        msg.pack(pady=50)
        
    return view


# Persistence functions for operator view settings

def save_operator_view_settings(config_data: Dict[str, Any], device_name: str, 
                                show_on_startup: bool):
    """
    Save operator view settings to config.
    
    Args:
        config_data: Application config dictionary
        device_name: Name of the device
        show_on_startup: Whether to show this view on startup
    """
    if 'operator_views' not in config_data:
        config_data['operator_views'] = {}
        
    config_data['operator_views'][device_name] = {
        'show_on_startup': show_on_startup
    }


def get_operator_view_settings(config_data: Dict[str, Any], device_name: str) -> Dict[str, Any]:
    """
    Get operator view settings from config.
    
    Args:
        config_data: Application config dictionary
        device_name: Name of the device
        
    Returns:
        Settings dictionary
    """
    return config_data.get('operator_views', {}).get(device_name, {
        'show_on_startup': False
    })


def get_startup_operator_views(config_data: Dict[str, Any]) -> list:
    """
    Get list of devices that should show operator views on startup.
    
    Args:
        config_data: Application config dictionary
        
    Returns:
        List of device names
    """
    operator_views = config_data.get('operator_views', {})
    return [device for device, settings in operator_views.items() 
            if settings.get('show_on_startup', False)]

