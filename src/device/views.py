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
        # Exit button (top left, fixed position) - make it visible!
        exit_btn = tk.Button(
            self,
            text="Exit Operator Mode (Esc)",
            command=self._on_close_request,
            font=(theme.FONT_FAMILY, 14, 'bold'),
            bg=theme.ERROR_RED,
            fg='white',
            activebackground=theme.HOLDING_RED,
            activeforeground='white',
            relief='raised',
            borderwidth=3,
            padx=20,
            pady=10,
            cursor='hand2'
        )
        exit_btn.place(x=30, y=30)
        
        # Main container - pack with expand to center vertically
        main_container = tk.Frame(self, bg=theme.BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Spacer to push content down (1 unit of expand)
        top_spacer = tk.Frame(main_container, bg=theme.BG_COLOR)
        top_spacer.pack(fill=tk.BOTH, expand=True)
        
        # Content container (no expand - just its natural size)
        content_container = tk.Frame(main_container, bg=theme.BG_COLOR)
        content_container.pack()
        
        # Control buttons (Run, Hold, Reset)
        btn_container = tk.Frame(content_container, bg=theme.BG_COLOR)
        btn_container.pack(pady=(0, 40))
        self._create_control_buttons(btn_container)
        
        # Custom content area (to be populated by device-specific views)
        self.custom_content_frame = tk.Frame(content_container, bg=theme.BG_COLOR)
        self.custom_content_frame.pack()
        
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
            activebackground=theme.SUCCESS_GREEN,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.run_btn.pack(side=tk.LEFT, padx=20)
        
        self.hold_btn = tk.Button(
            parent,
            text="Hold",
            command=handle_feed_hold,
            font=button_font,
            bg=theme.ERROR_RED,
            fg='black',
            activebackground=theme.ERROR_RED,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.hold_btn.pack(side=tk.LEFT, padx=20)
        
        self.reset_btn = tk.Button(
            parent,
            text="Reset",
            command=handle_reset,
            font=button_font,
            bg=theme.PRIMARY_ACCENT,
            fg='black',
            activebackground=theme.PRIMARY_ACCENT,
            activeforeground='black',
            relief='raised',
            borderwidth=4,
            width=button_width,
            height=button_height,
            cursor='hand2'
        )
        self.reset_btn.pack(side=tk.LEFT, padx=20)
        
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
            
    def set_custom_content(self, content_widget):
        """
        Set custom device-specific content.
        
        Args:
            content_widget: Widget to display in the custom content area
        """
        # Clear existing content
        for widget in self.custom_content_frame.winfo_children():
            widget.destroy()
            
        # Pack new content
        content_widget.pack(fill=tk.BOTH, expand=True)


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
    
    # Load device-specific operator view content
    view_creator = load_operator_view(device_name, device_data)
    if view_creator:
        try:
            # Create custom content, passing view_id if available
            custom_widget = view_creator(view.custom_content_frame, shared_gui_refs, view_id)
            if custom_widget:
                view.set_custom_content(custom_widget)
        except Exception as e:
            print(f"[VIEWS] Error creating operator view content for {device_name}: {e}")
            import traceback
            traceback.print_exc()
    else:
        # Show message if no custom view available
        msg = ttk.Label(
            view.custom_content_frame,
            text=f"No operator view defined for {device_name}",
            font=theme.FONT_NORMAL,
            foreground=theme.COMMENT_COLOR,
            style='Subtle.TLabel'
        )
        for widget in view.custom_content_frame.winfo_children():
            widget.destroy()
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

