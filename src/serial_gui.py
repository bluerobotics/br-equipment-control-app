"""
Serial Number GUI Components

Provides GUI widgets for managing serial numbers, including:
- Serial number entry
- Auto-increment toggle
- Scanner status indicator
- Quick actions
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from . import theme
from .serial_number import get_serial_manager, save_serial_to_config
from .scanner import get_scanner_handler, get_manual_input


class SerialNumberPanel(ttk.Frame):
    """
    A panel for managing serial numbers in the application.
    Displays current serial, allows manual entry, shows scanner status.
    """
    
    def __init__(self, parent, shared_gui_refs, **kwargs):
        super().__init__(parent, **kwargs)
        self.shared_gui_refs = shared_gui_refs
        self.serial_manager = get_serial_manager()
        self.scanner_handler = get_scanner_handler()
        self.manual_input = get_manual_input()
        
        # Variables
        self.serial_var = tk.StringVar(value=self.serial_manager.get_serial() or "")
        self.auto_increment_var = tk.BooleanVar(value=self.serial_manager.get_auto_increment())
        self.scanner_status_var = tk.StringVar(value="")
        self._skip_next_autosave = False  # Flag to prevent double-save on scanner input
        
        # Register callbacks
        self.scanner_handler.register_callback(self._on_scanner_input)
        self.manual_input.register_callback(self._on_manual_input)
        self.serial_manager.register_scanner_callback(self._on_serial_updated)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the GUI widgets for the serial number panel."""
        # Main content frame
        content_frame = ttk.Frame(self, style='Card.TFrame')
        content_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Top row: Title + Entry
        top_row = ttk.Frame(content_frame, style='Card.TFrame')
        top_row.pack(fill=tk.X, padx=5, pady=(5, 5))
        
        ttk.Label(
            top_row,
            text="Serial Number:",
            font=theme.FONT_BOLD,
            style='TLabel'
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        self.serial_entry = ttk.Entry(
            top_row,
            textvariable=self.serial_var,
            width=20,
            font=theme.FONT_NORMAL
        )
        self.serial_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Auto-save when text changes (with debounce)
        self._autosave_timer = None
        self.serial_var.trace_add('write', lambda *args: self._on_text_changed())
        
        # Bottom row: Options + Status
        bottom_row = ttk.Frame(content_frame, style='Card.TFrame')
        bottom_row.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Auto-increment checkbox with custom styling
        checkbox_frame = ttk.Frame(bottom_row, style='Card.TFrame')
        checkbox_frame.pack(side=tk.LEFT)
        
        # Create a styled checkbox with proper size
        self.auto_increment_check = ttk.Checkbutton(
            checkbox_frame,
            text="Auto-increment",
            variable=self.auto_increment_var,
            command=self._on_auto_increment_changed,
            style='TCheckbutton'
        )
        self.auto_increment_check.pack(side=tk.LEFT)
        
        # Try to configure checkbox size to match font
        try:
            # Get the current font size and set indicator size
            import tkinter.font as tkfont
            default_font = tkfont.nametofont("TkDefaultFont")
            font_size = default_font.actual()['size']
            indicator_size = max(12, font_size + 2)  # At least 12px, or font size + 2
            
            style = ttk.Style()
            # Note: On Windows, checkbox size is system-controlled, but we can try
            style.configure('TCheckbutton', font=('TkDefaultFont', font_size))
        except Exception:
            pass  # If styling fails, use defaults
        
        # Clear button
        ttk.Button(
            bottom_row,
            text="Clear",
            command=self._on_clear,
            style='Ghost.TButton',
            width=8
        ).pack(side=tk.RIGHT, padx=0)
        
        # Scanner status indicator (right side)
        self.scanner_status_label = ttk.Label(
            bottom_row,
            textvariable=self.scanner_status_var,
            font=('TkDefaultFont', 8),
            style='Subtle.TLabel'
        )
        self.scanner_status_label.pack(side=tk.RIGHT, padx=(5, 8))
        
        # Info label at bottom
        info_text = "Scan barcode/QR code or type manually (auto-saves)"
        ttk.Label(
            content_frame,
            text=info_text,
            font=('TkDefaultFont', 8),
            style='Subtle.TLabel',
            wraplength=280
        ).pack(side=tk.LEFT, padx=5, pady=(0, 5))
    
    def _on_text_changed(self):
        """Handle text changes in the serial entry (auto-save with debounce)."""
        # Skip auto-save if currently processing scanner input (to avoid double-save)
        if hasattr(self, '_skip_next_autosave') and self._skip_next_autosave:
            self._skip_next_autosave = False
            return
        
        # Cancel previous timer if exists
        if self._autosave_timer:
            self.after_cancel(self._autosave_timer)
        
        # Schedule auto-save after 800ms of inactivity
        self._autosave_timer = self.after(800, self._auto_save)
    
    def _auto_save(self):
        """Auto-save the serial number to config and manager."""
        try:
            serial = self.serial_var.get().strip()
            
            # If empty, clear the serial number
            if not serial:
                self.serial_manager.reset()
                save_serial_to_config(None, self.auto_increment_var.get())
                
                # Log to terminal (simple, non-blocking)
                print("[SERIAL] Serial number cleared (auto-saved)")
            else:
                # Save the serial number
                self.serial_manager.set_serial(serial)
                save_serial_to_config(serial, self.auto_increment_var.get())
                
                # Also notify manual input handler
                self.manual_input.submit_serial(serial)
                
                # Log to terminal (simple, non-blocking)
                print(f"[SERIAL] Set to: {serial} (auto-saved)")
        except Exception as e:
            print(f"[SERIAL] Error during auto-save: {e}")
    
    def _on_clear(self):
        """Clear the current serial number."""
        self.serial_var.set("")
        self.serial_manager.reset()
        save_serial_to_config(None, self.auto_increment_var.get())
        self._flash_status("Serial cleared", duration=1500)
        
        # Log to terminal
        from src.logging import log_to_terminal
        log_to_terminal("[SERIAL] Serial number cleared", self.shared_gui_refs)
    
    def _on_auto_increment_changed(self):
        """Handle auto-increment toggle."""
        enabled = self.auto_increment_var.get()
        self.serial_manager.set_auto_increment(enabled)
        
        # Save to config
        current_serial = self.serial_manager.get_serial()
        save_serial_to_config(current_serial, enabled)
        
        status = "enabled" if enabled else "disabled"
        self._flash_status(f"Auto-increment {status}", duration=1500)
    
    def _on_scanner_input(self, data: str):
        """Handle scanner input."""
        print(f"[SERIAL] _on_scanner_input ENTRY: data='{data}'")
        
        try:
            # Check if widget still exists
            if not self.winfo_exists():
                print(f"[SERIAL] Widget destroyed, ignoring scan")
                return
            
            # Since scanner callbacks are called from key events (main thread),
            # we can process directly without scheduling
            print(f"[SERIAL] Setting skip flag")
            self._skip_next_autosave = True
            
            # Update the GUI
            print(f"[SERIAL] Setting serial_var to: '{data}'")
            self.serial_var.set(data)
            print(f"[SERIAL] serial_var.set() completed")
            
            # Reset flag
            self._skip_next_autosave = False
            
            # Save to manager
            print(f"[SERIAL] Calling serial_manager.set_serial()")
            self.serial_manager.set_serial(data)
            print(f"[SERIAL] Manager updated")
            
            # Save to config
            print(f"[SERIAL] Calling save_serial_to_config()")
            save_serial_to_config(data, self.auto_increment_var.get())
            print(f"[SERIAL] Config saved")
            
            # Show status
            print(f"[SERIAL] Calling _flash_status()")
            self._flash_status(f"Scanned: {data}", duration=2000, color='green')
            print(f"[SERIAL] Flash status displayed")
            
            print(f"[SERIAL] _on_scanner_input COMPLETE: {data}")
            
        except Exception as e:
            print(f"[SERIAL] EXCEPTION in _on_scanner_input: {e}")
            import traceback
            traceback.print_exc()
            # Reset flag on error
            self._skip_next_autosave = False
    
    def _on_manual_input(self, data: str):
        """Handle manual input submission."""
        self.serial_manager.set_serial(data)
        
        # Save to config
        save_serial_to_config(data, self.auto_increment_var.get())
        
        # Log to terminal
        from src.logging import log_to_terminal
        log_to_terminal(f"[SERIAL] Set to: {data}", self.shared_gui_refs)
    
    def _on_serial_updated(self, serial: str):
        """Callback when serial number is updated by the manager."""
        # Update GUI to reflect new serial
        self.serial_var.set(serial)
    
    def _flash_status(self, message: str, duration: int = 1500, color: Optional[str] = None):
        """
        Temporarily display a status message.
        """
        self.scanner_status_var.set(message)
        
        # Reset after duration
        def reset():
            if self.scanner_status_var.get() == message:
                self.scanner_status_var.set("")
        
        self.after(duration, reset)


def create_serial_panel(parent, shared_gui_refs) -> SerialNumberPanel:
    """
    Create and return a SerialNumberPanel widget.
    """
    panel = SerialNumberPanel(parent, shared_gui_refs, style='Card.TFrame')
    return panel


class SerialNumberDialog(tk.Toplevel):
    """
    A dialog window for managing serial number settings.
    Includes advanced options like prefix, padding, etc.
    """
    
    def __init__(self, parent, shared_gui_refs):
        super().__init__(parent)
        self.shared_gui_refs = shared_gui_refs
        self.serial_manager = get_serial_manager()
        
        self.title("Serial Number Settings")
        self.configure(bg=theme.BG_COLOR)
        self.transient(parent)
        self.resizable(False, False)
        
        # Variables
        self.serial_var = tk.StringVar(value=self.serial_manager.get_serial() or "")
        self.auto_increment_var = tk.BooleanVar(value=self.serial_manager.get_auto_increment())
        
        self._create_widgets()
        
        # Center on parent
        self.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width() // 2 - 200,
            parent.winfo_rooty() + parent.winfo_height() // 2 - 150
        ))
    
    def _create_widgets(self):
        """Create dialog widgets."""
        frame = ttk.Frame(self, padding=20, style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Current serial
        ttk.Label(
            frame,
            text="Current Serial Number:",
            style='TLabel'
        ).grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        entry = ttk.Entry(
            frame,
            textvariable=self.serial_var,
            width=30,
            font=theme.FONT_NORMAL
        )
        entry.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        entry.focus()
        
        # Auto-increment
        ttk.Checkbutton(
            frame,
            text="Auto-increment after each use",
            variable=self.auto_increment_var
        ).grid(row=2, column=0, sticky='w', pady=(0, 15))
        
        # Info
        info_text = (
            "The serial number will be automatically added to log filenames.\n\n"
            "Use <serial> in filenames as a placeholder, e.g.:\n"
            "  'test_<serial>.csv' → 'test_SN001.csv'\n\n"
            "Or it will be added automatically:\n"
            "  'data.csv' → 'data_SN001.csv'"
        )
        ttk.Label(
            frame,
            text=info_text,
            style='Subtle.TLabel',
            wraplength=350,
            justify=tk.LEFT
        ).grid(row=3, column=0, sticky='w', pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(frame, style='TFrame')
        button_frame.grid(row=4, column=0, sticky='e')
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            style='Ghost.TButton'
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._on_save,
            style='Blue.TButton'
        ).pack(side=tk.RIGHT)
        
        # Bind Enter to save
        entry.bind('<Return>', lambda e: self._on_save())
    
    def _on_save(self):
        """Save settings and close dialog."""
        serial = self.serial_var.get().strip()
        auto_increment = self.auto_increment_var.get()
        
        # Update manager
        if serial:
            self.serial_manager.set_serial(serial)
        else:
            self.serial_manager.reset()
        
        self.serial_manager.set_auto_increment(auto_increment)
        
        # Save to config
        save_serial_to_config(serial if serial else None, auto_increment)
        
        # Log to terminal
        from src.logging import log_to_terminal
        log_to_terminal(f"[SERIAL] Settings saved: {serial or 'None'}, auto-increment: {auto_increment}", self.shared_gui_refs)
        
        self.destroy()


def show_serial_dialog(parent, shared_gui_refs):
    """
    Show the serial number settings dialog.
    """
    dialog = SerialNumberDialog(parent, shared_gui_refs)
    dialog.grab_set()
    parent.wait_window(dialog)

