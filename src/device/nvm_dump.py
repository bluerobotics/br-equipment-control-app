import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from src import theme


def show_nvm_dump_window(parent, gui_refs):
    """
    Opens (or focuses) a window for dumping and viewing NVM from connected devices.
    """
    existing = gui_refs.get('nvm_dump_window')
    if existing and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return existing

    window = NVMDumpWindow(parent, gui_refs)
    if window.winfo_exists():
        gui_refs['nvm_dump_window'] = window
    return window


class NVMDumpWindow(tk.Toplevel):
    """Window for dumping and viewing NVM data from connected devices."""

    def __init__(self, parent, gui_refs):
        super().__init__(parent)
        self.title("NVM Dump Viewer")
        self.configure(bg=theme.BG_COLOR)
        self.resizable(True, True)
        self.geometry("1000x700")
        self.minsize(800, 500)

        self.gui_refs = gui_refs
        self.device_manager = gui_refs.get('device_manager')
        self.command_funcs = gui_refs.get('command_funcs', {})
        self.nvm_views = {}
        
        # Register this window as the NVM dump callback handler
        self._previous_nvm_cb = gui_refs.get('show_nvm_dump_cb')
        self.gui_refs['show_nvm_dump_cb'] = self.display_nvm_dump

        if not self.device_manager:
            messagebox.showerror(
                "Unavailable",
                "Device manager is not available; cannot dump NVM.",
                parent=self
            )
            self.destroy()
            return

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_ui()

    def _build_ui(self):
        """Build the user interface."""
        # Main container
        container = ttk.Frame(self, padding=(20, 20), style='TFrame')
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        # Header
        header = ttk.Label(
            container,
            text="Non-Volatile Memory (NVM) Dump Viewer",
            style='Header.TLabel'
        )
        header.grid(row=0, column=0, sticky='w', pady=(0, 16))

        # Get connected ClearCore devices
        from src.firmware.clearcore import get_device_firmware_configs
        all_devices = get_device_firmware_configs(self.device_manager)
        
        if not all_devices:
            ttk.Label(
                container,
                text="No ClearCore devices are configured.",
                style='TLabel'
            ).grid(row=1, column=0, sticky='nw')
            return

        # Filter to only show connected devices
        connected_devices = []
        for device_key, config in all_devices.items():
            state = self.device_manager.get_device_state(device_key) or {}
            if state.get('connected'):
                connected_devices.append((device_key, config))

        if not connected_devices:
            ttk.Label(
                container,
                text="No ClearCore devices are currently connected.",
                style='TLabel'
            ).grid(row=1, column=0, sticky='nw')
            return

        # Create notebook for tabs (one per device)
        notebook = ttk.Notebook(container, style='TNotebook')
        notebook.grid(row=1, column=0, sticky='nsew', pady=(0, 0))

        for device_key, config in sorted(connected_devices, key=lambda x: x[0]):
            # Create a frame for this device
            device_frame = ttk.Frame(notebook, style='TFrame', padding=(10, 10))
            
            # Button frame at top
            button_frame = ttk.Frame(device_frame, style='TFrame')
            button_frame.pack(fill=tk.X, pady=(0, 10))

            dump_button = ttk.Button(
                button_frame,
                text="Dump NVM",
                command=lambda key=device_key: self.dump_nvm(key),
                style='Blue.TButton'
            )
            dump_button.pack(side=tk.LEFT, padx=(0, 8))

            clear_button = ttk.Button(
                button_frame,
                text="Clear View",
                command=lambda key=device_key: self.clear_view(key),
                style='Ghost.TButton'
            )
            clear_button.pack(side=tk.LEFT, padx=(0, 8))

            reset_button = ttk.Button(
                button_frame,
                text="Clear Firmware (Reset NVM)",
                command=lambda key=device_key: self.reset_nvm(key),
                style='Gray.TButton'
            )
            reset_button.pack(side=tk.LEFT)

            # Text widget for displaying dump
            text_widget = scrolledtext.ScrolledText(
                device_frame,
                wrap=tk.NONE,
                background=theme.WIDGET_BG,
                foreground=theme.FG_COLOR,
                borderwidth=1,
                relief='solid',
                font=getattr(theme, "FONT_NORMAL", ("Consolas", 10)),
                width=100,
                height=30
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.configure(state='disabled')

            # Store references
            self.nvm_views[device_key] = {
                'text': text_widget,
                'frame': device_frame
            }

            # Add tab to notebook
            label = config.get('label', device_key.capitalize())
            notebook.add(device_frame, text=label)

    def dump_nvm(self, device_key):
        """Trigger NVM dump for the specified device."""
        view = self.nvm_views.get(device_key)
        if not view:
            return

        text_widget = view['text']
        text_widget.configure(state='normal')
        text_widget.delete('1.0', tk.END)
        
        # Get device config for label
        from src.firmware.clearcore import get_device_firmware_configs
        all_devices = get_device_firmware_configs(self.device_manager)
        config = all_devices.get(device_key, {})
        label = config.get('label', device_key.capitalize())
        
        # Add header
        text_widget.insert(tk.END, f"{label} NVM Dump\n")
        text_widget.insert(tk.END, "Address  : Hex Bytes                                         |ASCII|\n")
        text_widget.insert(tk.END, "-" * 80 + "\n")
        text_widget.configure(state='disabled')

        # Send dump command
        if self.send_device_command(device_key, "dump_nvm"):
            print(f"[NVM DUMP] Requested dump for {device_key}")
        else:
            text_widget.configure(state='normal')
            text_widget.insert(tk.END, "Error: Unable to send dump_nvm command.\n")
            text_widget.configure(state='disabled')

    def reset_nvm(self, device_key):
        """Reset NVM for the specified device."""
        # Confirm action
        result = messagebox.askyesno(
            "Reset NVM",
            "This will erase all NVM data and restore factory calibration.\n\n"
            "Are you sure you want to continue?",
            parent=self
        )
        
        if not result:
            return

        if self.send_device_command(device_key, "reset_nvm"):
            messagebox.showinfo(
                "Reset NVM",
                "Reset command sent. Device will restore factory calibration.",
                parent=self
            )
        else:
            messagebox.showerror(
                "Reset NVM",
                "Unable to send reset_nvm command.",
                parent=self
            )

    def clear_view(self, device_key):
        """Clear the NVM dump view for the specified device."""
        view = self.nvm_views.get(device_key)
        if not view:
            return

        text_widget = view['text']
        text_widget.configure(state='normal')
        text_widget.delete('1.0', tk.END)
        text_widget.configure(state='disabled')

    def send_device_command(self, device_key, command):
        """Send a command to the specified device."""
        send_func = self.command_funcs.get(f"send_{device_key}")
        if not send_func:
            return False
        try:
            send_func(command)
            return True
        except Exception as e:
            print(f"[NVM DUMP] Error sending command: {e}")
            return False

    def display_nvm_dump(self, device_key, payload):
        """Display NVM dump data from a device."""
        view = self.nvm_views.get(device_key)
        if not view:
            return

        text_widget = view['text']
        text_widget.configure(state='normal')
        
        line = payload
        if payload.startswith("SUMMARY:"):
            if text_widget.index(tk.END) != "1.0":
                text_widget.insert(tk.END, "\n")
            line = payload[len("SUMMARY:"):]
        else:
            try:
                address_part, rest = payload.split(':', 1)
                hex_part, ascii_part = rest.split(':', 1)
                line = f"0x{address_part.upper()}: {hex_part.strip():<47} |{ascii_part.strip()}|"
            except ValueError:
                line = payload
        
        text_widget.insert(tk.END, line + "\n")
        text_widget.see(tk.END)
        text_widget.configure(state='disabled')

    def on_close(self):
        """Handle window close event."""
        # Restore previous NVM dump callback
        if self.gui_refs.get('show_nvm_dump_cb') is self.display_nvm_dump:
            if self._previous_nvm_cb:
                self.gui_refs['show_nvm_dump_cb'] = self._previous_nvm_cb
            else:
                self.gui_refs.pop('show_nvm_dump_cb', None)

        # Remove window reference
        if self.gui_refs.get('nvm_dump_window') is self:
            self.gui_refs.pop('nvm_dump_window', None)

        self.destroy()

