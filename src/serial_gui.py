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
        self.configure(padding=10)
        self.shared_gui_refs = shared_gui_refs
        self.serial_manager = get_serial_manager()
        self.scanner_handler = get_scanner_handler()
        self.manual_input = get_manual_input()
        
        # Variables
        self.job_var = tk.StringVar(value=self.serial_manager.get_job() or "")
        self.op_var = tk.StringVar(value=self.serial_manager.get_op() or "")
        self.serial_var = tk.StringVar(value=self.serial_manager.get_serial() or "")
        self.auto_increment_var = tk.BooleanVar(value=self.serial_manager.get_auto_increment())
        
        # Validate scanner target (if "op" was saved, default to "job")
        scanner_target = self.serial_manager.get_scanner_target()
        if scanner_target == "op":
            scanner_target = "job"
            self.serial_manager.set_scanner_target("job")
        self.scanner_target_var = tk.StringVar(value=scanner_target)
        self.scanner_status_var = tk.StringVar(value="")
        self._skip_next_autosave = False  # Flag to prevent double-save on scanner input
        
        # Register callbacks
        self.scanner_handler.register_callback(self._on_scanner_input)
        self.manual_input.register_callback(self._on_manual_input)
        self.serial_manager.register_scanner_callback(self._on_serial_updated)
        
        self._create_widgets()
    
    def _configure_combobox_style(self):
        """Configure dark theme for the scanner combobox and Card frame."""
        try:
            style = ttk.Style()
            
            # Configure Card.TFrame to use lighter widget background
            style.configure(
                'Card.TFrame',
                background=theme.WIDGET_BG
            )
            
            # Configure Combobox
            style.configure(
                'Scanner.TCombobox',
                fieldbackground=theme.WIDGET_BG,
                background=theme.WIDGET_BG,
                foreground=theme.FG_COLOR,
                bordercolor=theme.SECONDARY_ACCENT
            )
            style.map(
                'Scanner.TCombobox',
                fieldbackground=[('readonly', theme.WIDGET_BG), ('disabled', theme.SECONDARY_ACCENT)],
                foreground=[('readonly', theme.FG_COLOR), ('disabled', theme.COMMENT_COLOR)]
            )
            # Configure the dropdown list to use dark theme
            self.option_add('*TCombobox*Listbox*Background', theme.WIDGET_BG)
            self.option_add('*TCombobox*Listbox*Foreground', theme.FG_COLOR)
        except Exception as e:
            print(f"[SERIAL] Failed to configure styles: {e}")
    
    def _create_widgets(self):
        """Create the GUI widgets for the serial number panel."""
        # Main content frame
        content_frame = ttk.Frame(self, style='Card.TFrame')
        content_frame.pack(fill=tk.X)
        
        # Op Number row (moved to top)
        op_row = ttk.Frame(content_frame, style='Card.TFrame')
        op_row.pack(fill=tk.X, pady=(0, 2))
        
        self.op_entry = tk.Entry(
            op_row,
            textvariable=self.op_var,
            width=18,
            font=theme.FONT_NORMAL,
            justify='left',
            bg=theme.BG_COLOR,
            fg=theme.FG_COLOR,
            insertbackground=theme.PRIMARY_ACCENT,
            selectbackground=theme.SELECTION_BG,
            selectforeground=theme.SELECTION_FG,
            relief='solid',
            borderwidth=1,
            highlightthickness=0
        )
        self.op_entry.pack(side=tk.RIGHT)
        
        op_label = ttk.Label(
            op_row,
            text="Op Number:",
            font=theme.FONT_BOLD,
            style='TLabel',
            background=theme.WIDGET_BG
        )
        op_label.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Job Number row
        job_row = ttk.Frame(content_frame, style='Card.TFrame')
        job_row.pack(fill=tk.X, pady=(2, 2))
        
        self.job_entry = tk.Entry(
            job_row,
            textvariable=self.job_var,
            width=18,
            font=theme.FONT_NORMAL,
            justify='left',
            bg=theme.BG_COLOR,
            fg=theme.FG_COLOR,
            insertbackground=theme.PRIMARY_ACCENT,
            selectbackground=theme.SELECTION_BG,
            selectforeground=theme.SELECTION_FG,
            relief='solid',
            borderwidth=1,
            highlightthickness=0
        )
        self.job_entry.pack(side=tk.RIGHT)
        
        job_label = ttk.Label(
            job_row,
            text="Job Number:",
            font=theme.FONT_BOLD,
            style='TLabel',
            background=theme.WIDGET_BG
        )
        job_label.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Serial Number row
        serial_row = ttk.Frame(content_frame, style='Card.TFrame')
        serial_row.pack(fill=tk.X, pady=(2, 5))
        
        self.serial_entry = tk.Entry(
            serial_row,
            textvariable=self.serial_var,
            width=18,
            font=theme.FONT_NORMAL,
            justify='left',
            bg=theme.BG_COLOR,
            fg=theme.FG_COLOR,
            insertbackground=theme.PRIMARY_ACCENT,
            selectbackground=theme.SELECTION_BG,
            selectforeground=theme.SELECTION_FG,
            relief='solid',
            borderwidth=1,
            highlightthickness=0
        )
        self.serial_entry.pack(side=tk.RIGHT)
        
        serial_label = ttk.Label(
            serial_row,
            text="Serial Number:",
            font=theme.FONT_BOLD,
            style='TLabel',
            background=theme.WIDGET_BG
        )
        serial_label.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Auto-save when text changes (with debounce)
        self._autosave_timer = None
        self.job_var.trace_add('write', lambda *args: self._on_text_changed())
        self.op_var.trace_add('write', lambda *args: self._on_text_changed())
        self.serial_var.trace_add('write', lambda *args: self._on_text_changed())
        
        # Bottom row: Options + Status
        bottom_row = ttk.Frame(content_frame, style='Card.TFrame')
        bottom_row.pack(fill=tk.X, pady=(0, 5))
        
        # Auto-increment checkbox with custom styling
        checkbox_frame = ttk.Frame(bottom_row, style='Card.TFrame')
        checkbox_frame.pack(side=tk.RIGHT)
        
        # Create a styled checkbox with proper size
        self.auto_increment_check = tk.Checkbutton(
            checkbox_frame,
            text="Auto-increment",
            variable=self.auto_increment_var,
            command=self._on_auto_increment_changed,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            selectcolor=theme.WIDGET_BG,
            activebackground=theme.WIDGET_BG,
            activeforeground=theme.FG_COLOR,
            font=('TkDefaultFont', 9),
            relief='flat',
            borderwidth=0,
            highlightthickness=0
        )
        self.auto_increment_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Scanner target selector
        scanner_frame = ttk.Frame(bottom_row, style='Card.TFrame')
        scanner_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        scanner_label = ttk.Label(
            scanner_frame,
            text="Scanner→",
            font=('TkDefaultFont', 9),
            style='TLabel',
            background=theme.WIDGET_BG
        )
        scanner_label.pack(side=tk.LEFT, padx=(0, 3))
        
        # Configure combobox style to match firmware manager
        self._configure_combobox_style()
        
        self.scanner_combo = ttk.Combobox(
            scanner_frame,
            textvariable=self.scanner_target_var,
            values=["job", "serial"],
            state="readonly",
            width=8,
            font=('TkDefaultFont', 9),
            style='Scanner.TCombobox'
        )
        self.scanner_combo.pack(side=tk.LEFT)
        self.scanner_combo.bind('<<ComboboxSelected>>', lambda e: self._on_scanner_target_changed())
        
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
        
        # Scanner status indicator (right side)
        self.scanner_status_label = ttk.Label(
            bottom_row,
            textvariable=self.scanner_status_var,
            font=('TkDefaultFont', 8),
            style='Subtle.TLabel',
            background=theme.WIDGET_BG
        )
        self.scanner_status_label.pack(side=tk.RIGHT, padx=(5, 8))
        
        # Info label at bottom
        info_text = "Scan barcode/QR or type manually (auto-saves)"
        info_label = ttk.Label(
            content_frame,
            text=info_text,
            font=('TkDefaultFont', 8),
            style='Subtle.TLabel',
            background=theme.WIDGET_BG
        )
        info_label.pack(side=tk.RIGHT, pady=(0, 0))
    
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
        """Auto-save the job, op, and serial numbers to config and manager."""
        try:
            job = self.job_var.get().strip() or None
            op = self.op_var.get().strip() or None
            serial = self.serial_var.get().strip() or None
            auto_increment = self.auto_increment_var.get()
            scanner_target = self.scanner_target_var.get()
            
            # Update manager
            if job:
                self.serial_manager.set_job(job)
            else:
                self.serial_manager.current_job = None
            
            if op:
                self.serial_manager.set_op(op)
            else:
                self.serial_manager.current_op = None
            
            if serial:
                self.serial_manager.set_serial(serial)
                # Also notify manual input handler
                self.manual_input.submit_serial(serial)
            else:
                self.serial_manager.current_serial = None
            
            # Save to config
            save_serial_to_config(job, op, serial, auto_increment, scanner_target)
            
            # Log to terminal (simple, non-blocking)
            print(f"[SERIAL] Auto-saved - Job: {job}, Op: {op}, Serial: {serial}")
        except Exception as e:
            print(f"[SERIAL] Error during auto-save: {e}")
    
    def _on_clear(self):
        """Clear job, op, and serial numbers."""
        self.job_var.set("")
        self.op_var.set("")
        self.serial_var.set("")
        self.serial_manager.reset()
        save_serial_to_config(None, None, None, self.auto_increment_var.get(), self.scanner_target_var.get())
        self._flash_status("All fields cleared", duration=1500)
        
        # Log to terminal
        from src.logging import log_to_terminal
        log_to_terminal("[SERIAL] Job, Op, and Serial numbers cleared", self.shared_gui_refs)
    
    def _on_auto_increment_changed(self):
        """Handle auto-increment toggle."""
        enabled = self.auto_increment_var.get()
        self.serial_manager.set_auto_increment(enabled)
        
        # Save to config
        current_job = self.serial_manager.get_job()
        current_op = self.serial_manager.get_op()
        current_serial = self.serial_manager.get_serial()
        save_serial_to_config(current_job, current_op, current_serial, enabled, self.scanner_target_var.get())
        
        status = "enabled" if enabled else "disabled"
        self._flash_status(f"Auto-increment {status}", duration=1500)
    
    def _on_scanner_target_changed(self):
        """Handle scanner target selection change."""
        target = self.scanner_target_var.get()
        self.serial_manager.set_scanner_target(target)
        
        # Save to config
        current_job = self.serial_manager.get_job()
        current_op = self.serial_manager.get_op()
        current_serial = self.serial_manager.get_serial()
        save_serial_to_config(current_job, current_op, current_serial, self.auto_increment_var.get(), target)
        
        field_name = "Job" if target == "job" else "Serial"
        self._flash_status(f"Scanner→{field_name}", duration=1500)
    
    def _on_scanner_input(self, data: str):
        """Handle scanner input - routes to job, op, or serial based on scanner_target."""
        print(f"[SERIAL] _on_scanner_input ENTRY: data='{data}'")
        
        try:
            # Check if widget still exists
            if not self.winfo_exists():
                print(f"[SERIAL] Widget destroyed, ignoring scan")
                return
            
            # Determine target field
            target = self.scanner_target_var.get()
            print(f"[SERIAL] Scanner target: {target}")
            
            # Since scanner callbacks are called from key events (main thread),
            # we can process directly without scheduling
            print(f"[SERIAL] Setting skip flag")
            self._skip_next_autosave = True
            
            # Update the GUI based on target
            if target == "job":
                print(f"[SERIAL] Setting job_var to: '{data}'")
                self.job_var.set(data)
                self.serial_manager.set_job(data)
                field_name = "Job"
            elif target == "op":
                print(f"[SERIAL] Setting op_var to: '{data}'")
                self.op_var.set(data)
                self.serial_manager.set_op(data)
                field_name = "Op"
            else:  # "serial"
                print(f"[SERIAL] Setting serial_var to: '{data}'")
                self.serial_var.set(data)
                self.serial_manager.set_serial(data)
                field_name = "Serial"
            
            print(f"[SERIAL] Field updated")
            
            # Reset flag
            self._skip_next_autosave = False
            
            # Save to config
            print(f"[SERIAL] Calling save_serial_to_config()")
            save_serial_to_config(
                self.serial_manager.get_job(),
                self.serial_manager.get_op(),
                self.serial_manager.get_serial(),
                self.auto_increment_var.get(),
                target
            )
            print(f"[SERIAL] Config saved")
            
            # Show status
            print(f"[SERIAL] Calling _flash_status()")
            self._flash_status(f"Scanned {field_name}: {data}", duration=2000, color='green')
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
        save_serial_to_config(
            self.serial_manager.get_job(),
            self.serial_manager.get_op(),
            data,
            self.auto_increment_var.get(),
            self.scanner_target_var.get()
        )
        
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
        self.job_var = tk.StringVar(value=self.serial_manager.get_job() or "")
        self.op_var = tk.StringVar(value=self.serial_manager.get_op() or "")
        self.serial_var = tk.StringVar(value=self.serial_manager.get_serial() or "")
        self.auto_increment_var = tk.BooleanVar(value=self.serial_manager.get_auto_increment())
        
        # Validate scanner target (if "op" was saved, default to "job")
        scanner_target = self.serial_manager.get_scanner_target()
        if scanner_target == "op":
            scanner_target = "job"
        self.scanner_target_var = tk.StringVar(value=scanner_target)
        
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
        
        # Current op (moved to top)
        ttk.Label(
            frame,
            text="Current Op Number:",
            style='TLabel'
        ).grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        op_entry = ttk.Entry(
            frame,
            textvariable=self.op_var,
            width=30,
            font=theme.FONT_NORMAL
        )
        op_entry.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        op_entry.focus()
        
        # Current job
        ttk.Label(
            frame,
            text="Current Job Number:",
            style='TLabel'
        ).grid(row=2, column=0, sticky='w', pady=(0, 5))
        
        job_entry = ttk.Entry(
            frame,
            textvariable=self.job_var,
            width=30,
            font=theme.FONT_NORMAL
        )
        job_entry.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        
        # Current serial
        ttk.Label(
            frame,
            text="Current Serial Number:",
            style='TLabel'
        ).grid(row=4, column=0, sticky='w', pady=(0, 5))
        
        serial_entry = ttk.Entry(
            frame,
            textvariable=self.serial_var,
            width=30,
            font=theme.FONT_NORMAL
        )
        serial_entry.grid(row=5, column=0, sticky='ew', pady=(0, 10))
        
        # Auto-increment
        ttk.Checkbutton(
            frame,
            text="Auto-increment serial after each use",
            variable=self.auto_increment_var
        ).grid(row=6, column=0, sticky='w', pady=(0, 15))
        
        # Info
        info_text = (
            "Job, Op, and Serial numbers can be used in log filenames via placeholders.\n\n"
            "Use <job>, <op>, and <serial> in filenames as placeholders, e.g.:\n"
            "  'test_<job>_<op>_<serial>.csv' → 'test_001_42_123.csv'\n\n"
            "Without placeholders, numbers are NOT added automatically."
        )
        ttk.Label(
            frame,
            text=info_text,
            style='Subtle.TLabel',
            wraplength=350,
            justify=tk.LEFT
        ).grid(row=7, column=0, sticky='w', pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(frame, style='TFrame')
        button_frame.grid(row=8, column=0, sticky='e')
        
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
        job_entry.bind('<Return>', lambda e: self._on_save())
        op_entry.bind('<Return>', lambda e: self._on_save())
        serial_entry.bind('<Return>', lambda e: self._on_save())
    
    def _on_save(self):
        """Save settings and close dialog."""
        job = self.job_var.get().strip() or None
        op = self.op_var.get().strip() or None
        serial = self.serial_var.get().strip() or None
        auto_increment = self.auto_increment_var.get()
        scanner_target = self.scanner_target_var.get()
        
        # Update manager
        if job:
            self.serial_manager.set_job(job)
        else:
            self.serial_manager.current_job = None
        
        if op:
            self.serial_manager.set_op(op)
        else:
            self.serial_manager.current_op = None
        
        if serial:
            self.serial_manager.set_serial(serial)
        else:
            self.serial_manager.current_serial = None
        
        self.serial_manager.set_auto_increment(auto_increment)
        self.serial_manager.set_scanner_target(scanner_target)
        
        # Save to config
        save_serial_to_config(job, op, serial, auto_increment, scanner_target)
        
        # Log to terminal
        from src.logging import log_to_terminal
        log_to_terminal(f"[SERIAL] Settings saved - Job: {job or 'None'}, Op: {op or 'None'}, Serial: {serial or 'None'}, auto-increment: {auto_increment}", self.shared_gui_refs)
        
        self.destroy()


def show_serial_dialog(parent, shared_gui_refs):
    """
    Show the serial number settings dialog.
    """
    dialog = SerialNumberDialog(parent, shared_gui_refs)
    dialog.grab_set()
    parent.wait_window(dialog)

