import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import os
import sys

LIST_PORTS_UNAVAILABLE_SENTINEL = None


def _import_pyserial():
    candidates = [
        None,  # default site-packages
        getattr(sys, "base_prefix", ""),
        getattr(sys, "prefix", ""),
    ]

    user_site = None
    try:
        import site
        user_site = site.getusersitepackages()
    except Exception:
        user_site = None

    if isinstance(user_site, str):
        candidates.append(user_site)

    project_root = os.path.dirname(os.path.abspath(__file__))
    local_lib = os.path.join(project_root, "libs")
    candidates.append(local_lib)

    for path in candidates:
        if not path or not isinstance(path, str):
            continue
        if path not in sys.path:
            sys.path.append(path)
        try:
            from serial.tools import list_ports  # type: ignore[import, no-redef]

            return list_ports
        except ImportError:
            continue

    return LIST_PORTS_UNAVAILABLE_SENTINEL


list_ports = _import_pyserial()

from . import theme
from .clearcore_firmware import (
    get_device_firmware_configs,
    compare_versions,
    get_release_history,
    start_manual_update,
)


def open_firmware_manager(parent, gui_refs):
    """
    Opens (or focuses) the firmware manager window.
    """
    existing = gui_refs.get('firmware_manager_window')
    if existing and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return existing

    window = FirmwareManagerWindow(parent, gui_refs)
    if window.winfo_exists():
        gui_refs['firmware_manager_window'] = window
    return window


class FirmwareManagerWindow(tk.Toplevel):
    """Top-level window that allows users to check firmware versions and trigger updates."""

    REFRESH_INTERVAL_MS = 2000

    def __init__(self, parent, gui_refs):
        super().__init__(parent)
        self.title("Firmware Manager")
        self.configure(bg=theme.BG_COLOR)
        self.resizable(True, True)
        self.geometry("1100x780")
        self.minsize(900, 660)

        self.gui_refs = gui_refs
        self.device_manager = gui_refs.get('device_manager')
        if not self.device_manager:
            messagebox.showerror(
                "Unavailable",
                "Device manager is not available; cannot manage firmware.",
                parent=self
            )
            self.destroy()
            return

        self.release_cache = {}
        self.rows = {}
        self._refresh_job = None
        self.command_funcs = gui_refs.get('command_funcs', {})
        self.update_in_progress = False
        self.nvm_views = {}
        self._previous_nvm_cb = gui_refs.get('show_nvm_dump_cb')
        self.gui_refs['show_nvm_dump_cb'] = self.display_nvm_dump

        self.style = ttk.Style(self)
        self._configure_styles()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        self.refresh_device_states()
        self.refresh_all_releases()
        
        # Request firmware versions for all connected devices
        for device_key in self.rows.keys():
            self._request_device_version(device_key)

    def _build_ui(self):
        # Create canvas and scrollbar
        canvas = tk.Canvas(self, bg=theme.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for mousewheel binding
        self._canvas = canvas
        
        # Bind mousewheel
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        container = ttk.Frame(scrollable_frame, style='TFrame', padding=(20, 20, 20, 12))
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)

        header = ttk.Label(
            container,
            text="Manage firmware for supported ClearCore devices.",
            style='Header.TLabel'
        )
        header.grid(row=0, column=0, sticky='w', pady=(0, 8))
        
        note = ttk.Label(
            container,
            text="Note: Firmware flashing is only supported over USB connections.",
            style='Subtle.TLabel',
            foreground=theme.WARNING_YELLOW
        )
        note.grid(row=1, column=0, sticky='w', pady=(0, 16))

        all_devices = get_device_firmware_configs(self.device_manager)
        if not all_devices:
            ttk.Label(container, text="No ClearCore devices are configured.", style='TLabel').grid(row=2, column=0, sticky='w')
            return
        
        # Filter to only show connected devices
        connected_devices = []
        for device_key, config in all_devices.items():
            state = self.device_manager.get_device_state(device_key) or {}
            if state.get('connected'):
                connected_devices.append((device_key, config))
        
        devices = sorted(connected_devices, key=lambda item: item[0])
        
        if not devices:
            ttk.Label(container, text="No ClearCore devices are currently connected.", style='TLabel').grid(row=2, column=0, sticky='w')
            return

        for idx, (device_key, config) in enumerate(devices, start=2):
            frame = ttk.LabelFrame(
                container,
                text=config.get('label', device_key.capitalize()),
                style='Card.TLabelframe',
                padding=(16, 12)
            )
            frame.grid(row=idx, column=0, sticky='nsew', pady=(0, 12))
            frame.columnconfigure(1, weight=1)
            frame.rowconfigure(4, weight=1)
            container.rowconfigure(idx, weight=1)

            connection_var = tk.StringVar(value="Disconnected")
            current_var = tk.StringVar(value="Unknown")
            latest_var = tk.StringVar(value="—")
            status_var = tk.StringVar(value="Idle")
            release_var = tk.StringVar()
            conn_var = tk.StringVar(value="Not connected")

            ttk.Label(frame, text="Connection:", style='Subtle.TLabel').grid(row=0, column=0, sticky='w')
            conn_label = ttk.Label(frame, textvariable=conn_var, style='TLabel')
            conn_label.grid(row=0, column=1, sticky='w')

            ttk.Label(frame, text="Current Version:", style='Subtle.TLabel').grid(row=1, column=0, sticky='w', pady=(4, 0))
            current_label = ttk.Label(frame, textvariable=current_var, style='TLabel')
            current_label.grid(row=1, column=1, sticky='w', pady=(4, 0))

            ttk.Label(frame, text="Latest Release:", style='Subtle.TLabel').grid(row=2, column=0, sticky='w', pady=(4, 0))
            latest_label = ttk.Label(frame, textvariable=latest_var, style='TLabel')
            latest_label.grid(row=2, column=1, sticky='w', pady=(4, 0))

            ttk.Label(frame, text="Available Releases:", style='Subtle.TLabel').grid(row=3, column=0, sticky='nw', pady=(6, 0))
            release_combo = ttk.Combobox(
                frame,
                textvariable=release_var,
                state='readonly',
                width=28,
                style='Firmware.TCombobox'
            )
            release_combo.grid(row=3, column=1, sticky='we', pady=(6, 0))
            release_combo.bind("<<ComboboxSelected>>", lambda _evt, key=device_key: self.on_release_selected(key))

            notes_label = ttk.Label(frame, text="Release Notes:", style='Subtle.TLabel')
            notes_label.grid(row=4, column=0, sticky='nw', pady=(6, 0))
            notes_widget = scrolledtext.ScrolledText(
                frame,
                height=6,
                width=50,
                wrap=tk.WORD,
                background=theme.WIDGET_BG,
                foreground=theme.FG_COLOR,
                borderwidth=0,
                font=getattr(theme, "FONT_SMALL", theme.FONT_NORMAL),
            )
            notes_widget.grid(row=4, column=1, sticky='nsew', pady=(6, 0))
            notes_widget.configure(
                state='disabled',
                cursor='arrow',
                relief='flat',
                highlightthickness=0
            )

            status_label = ttk.Label(frame, textvariable=status_var, style='Status.TLabel', wraplength=520, justify='left')
            status_label.grid(row=5, column=0, columnspan=2, sticky='we', pady=(10, 8))

            button_row = ttk.Frame(frame, style='TFrame')
            button_row.grid(row=6, column=0, columnspan=2, sticky='w')

            check_button = ttk.Button(
                button_row,
                text="Refresh Releases",
                command=lambda key=device_key: self.refresh_releases(key),
                style='Blue.TButton'
            )
            check_button.grid(row=0, column=0, padx=(0, 8))

            flash_button = ttk.Button(
                button_row,
                text="Flash Selected Release",
                command=lambda key=device_key: self.flash_selected(key),
                style='Green.TButton'
            )
            flash_button.grid(row=0, column=1, padx=(0, 8))
            
            flash_file_button = ttk.Button(
                button_row,
                text="Flash from File…",
                command=lambda key=device_key: self.flash_from_file(key),
                style='Green.TButton'
            )
            flash_file_button.grid(row=0, column=2)

            nvm_row = ttk.Frame(frame, style='TFrame')
            nvm_row.grid(row=8, column=0, columnspan=2, sticky='w', pady=(6, 0))

            dump_button = ttk.Button(
                nvm_row,
                text="Dump NVM…",
                command=lambda key=device_key: self.dump_nvm(key),
                style='Ghost.TButton'
            )
            dump_button.pack(side=tk.LEFT, padx=(0, 8))

            reset_button = ttk.Button(
                nvm_row,
                text="Clear Firmware (Reset NVM)",
                command=lambda key=device_key: self.reset_nvm(key),
                style='Gray.TButton'
            )
            reset_button.pack(side=tk.LEFT, padx=(0, 8))

            clear_button = ttk.Button(
                nvm_row,
                text="Clear Status",
                command=lambda key=device_key: self.clear_status(key),
                style='Ghost.TButton'
            )
            clear_button.pack(side=tk.LEFT)

            self.rows[device_key] = {
                'current_var': current_var,
                'latest_var': latest_var,
                'status_var': status_var,
                'check_button': check_button,
                'flash_button': flash_button,
                'release_var': release_var,
                'release_combo': release_combo,
                'release_notes': notes_widget,
                'current_label': current_label,
                'conn_var': conn_var,
                'conn_label': conn_label,
                'latest_label': latest_label,
                'releases': {},
                'config': config,
                'status_label': status_label
            }


    def refresh_device_states(self):
        if not self.device_manager:
            return

        for device_key, row in self.rows.items():
            state = self.device_manager.get_device_state(device_key) or {}
            connected = bool(state.get('connected'))
            
            # Update connection status display
            conn_var = row.get('conn_var')
            conn_label = row.get('conn_label')
            if conn_var and conn_label:
                if connected:
                    conn_method = state.get('connection_method', 'Unknown')
                    conn_port = state.get('connection_port', '')
                    
                    # For USB connections, the port IS the method (e.g., "COM10")
                    # For UDP connections, method is "UDP" and port might be IP:port
                    if conn_method and conn_method.startswith('COM'):
                        conn_var.set(f"Connected via USB ({conn_method})")
                    elif conn_port:
                        conn_var.set(f"Connected via {conn_method} ({conn_port})")
                    else:
                        conn_var.set(f"Connected via {conn_method}")
                    conn_label.configure(foreground=theme.SUCCESS_GREEN)
                else:
                    conn_var.set("Not connected")
                    conn_label.configure(foreground=theme.ERROR_RED)

            firmware_version = state.get('firmware_version') or "Unknown"
            row['current_var'].set(firmware_version)
            self._apply_current_version_style(device_key)

            in_progress = bool(state.get('fw_update_in_progress'))
            self._update_button_states(row, connected, in_progress)

            if in_progress:
                row['status_var'].set("Firmware update in progress...")

            self._update_current_from_state(device_key)

        self._refresh_job = self.after(self.REFRESH_INTERVAL_MS, self.refresh_device_states)

    def refresh_all_releases(self):
        for idx, device_key in enumerate(self.rows.keys()):
            self.after(idx * 200, lambda key=device_key: self.refresh_releases(key))

    def _update_button_states(self, row, connected, in_progress):
        check_btn = row['check_button']
        flash_btn = row['flash_button']

        check_btn_state = tk.NORMAL
        has_release = bool(row['release_var'].get())
        flash_btn_state = tk.NORMAL if connected and not in_progress and has_release else tk.DISABLED

        check_btn.configure(state=check_btn_state)
        flash_btn.configure(state=flash_btn_state)

    def refresh_releases(self, device_key, on_complete=None):
        row = self.rows.get(device_key)
        if not row:
            return

        self._request_device_version(device_key)
        row['status_var'].set("Fetching releases from GitHub...")

        def worker():
            try:
                releases = get_release_history(device_key, limit=8, force_refresh=True)
                if not releases:
                    raise RuntimeError("No releases with firmware assets were found.")

                def handle_success():
                    self.release_cache[device_key] = releases[0]
                    row['latest_var'].set(releases[0]['version'])
                    self._populate_release_list(device_key, releases)
                    self._update_status_after_check(device_key, releases[0])
                    latest_label = row.get('latest_label')
                    if latest_label:
                        latest_label.configure(foreground=theme.SUCCESS_GREEN)
                    self._apply_current_version_style(device_key)
                    if on_complete:
                        on_complete(releases)

                self._run_on_ui(handle_success)
            except Exception as exc:
                def handle_failure():
                    row['status_var'].set(f"Update check failed: {exc}")
                    row['release_var'].set('')
                    row['release_combo'].configure(values=[])
                    self._update_release_notes(row['release_notes'], "Failed to load releases.")
                    latest_label = row.get('latest_label')
                    if latest_label:
                        latest_label.configure(foreground=theme.FG_COLOR)
                    self.release_cache.pop(device_key, None)
                    self._apply_current_version_style(device_key)
                    self._update_button_states(row, (self.device_manager.get_device_state(device_key) or {}).get('connected'), False)
                self._run_on_ui(handle_failure)

        threading.Thread(target=worker, daemon=True).start()

    def flash_selected(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return

        selected_version = row['release_var'].get()
        releases = row.get('releases', {})
        info = releases.get(selected_version)

        def start_with_info(release_info):
            try:
                row['status_var'].set("Preparing firmware update...")
                self.update_in_progress = True
                start_manual_update(
                    device_key,
                    self.gui_refs,
                    self.device_manager,
                    release_info=release_info,
                    status_callback=self._make_status_callback(device_key)
                )
            except Exception as exc:
                row['status_var'].set(f"Failed to start update: {exc}")
                self.update_in_progress = False
                messagebox.showerror("Firmware Update", str(exc), parent=self)

        if info:
            start_with_info(info)
        else:
            # Fetch release info first, then retry once data is available
            self.refresh_releases(
                device_key,
                on_complete=lambda _releases: self.flash_selected(device_key)
            )
    
    def flash_from_file(self, device_key):
        """Flash firmware from a user-selected .uf2 file."""
        row = self.rows.get(device_key)
        if not row:
            return
        
        # Open file dialog to select .uf2 file
        file_path = filedialog.askopenfilename(
            parent=self,
            title=f"Select {device_key.capitalize()} Firmware File",
            filetypes=[
                ("UF2 Firmware Files", "*.uf2"),
                ("All Files", "*.*")
            ]
        )
        
        if not file_path:
            return  # User cancelled
        
        # Verify file exists and is readable
        if not os.path.isfile(file_path):
            messagebox.showerror("Invalid File", f"File not found: {file_path}", parent=self)
            return
        
        # Create a minimal release_info dict with local file
        release_info = {
            'version': os.path.basename(file_path),
            'local_file': file_path,
            'notes': f'Custom firmware from: {os.path.basename(file_path)}'
        }
        
        try:
            row['status_var'].set(f"Flashing from file: {os.path.basename(file_path)}...")
            self.update_in_progress = True
            start_manual_update(
                device_key,
                self.gui_refs,
                self.device_manager,
                release_info=release_info,
                status_callback=self._make_status_callback(device_key)
            )
        except Exception as exc:
            row['status_var'].set(f"Failed to flash from file: {exc}")
            self.update_in_progress = False
            messagebox.showerror("Firmware Flash", str(exc), parent=self)

    def _make_status_callback(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return lambda *_: None

        status_var = row['status_var']

        def update_status(message):
            status_var.set(message)
            lowercase = message.lower()
            if any(token in lowercase for token in ["preparing firmware update", "downloading", "waiting for bootloader", "copying"]):
                self.update_in_progress = True
            if any(token in lowercase for token in ["firmware update complete", "firmware update failed", "update failed", "update complete"]):
                self.update_in_progress = False

        return update_status

    def send_device_command(self, device_key, command):
        send_func = self.command_funcs.get(f"send_{device_key}")
        if not send_func:
            return False
        try:
            send_func(command)
            return True
        except Exception:
            return False

    def dump_nvm(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return
        view = self._ensure_nvm_view(device_key, reset=True)
        if not view:
            return
        text_widget = view['text']
        text_widget.configure(state='normal')
        label = row.get('config', {}).get('label', device_key.capitalize())
        text_widget.insert(tk.END, f"{label} NVM Dump\n")
        text_widget.insert(tk.END, "Address  : Hex Bytes                                         |ASCII|\n")
        text_widget.insert(tk.END, "-" * 80 + "\n")
        text_widget.configure(state='disabled')
        if self.send_device_command(device_key, "dump_nvm"):
            row['status_var'].set("Dumping NVM… (see viewer for results)")
        else:
            row['status_var'].set("Unable to send dump_nvm command.")

    def reset_nvm(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return
        if self.send_device_command(device_key, "reset_nvm"):
            row['status_var'].set("Reset command sent (device will restore factory calibration).")
        else:
            row['status_var'].set("Unable to send reset_nvm command.")

    def clear_status(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return
        row['status_var'].set("Idle")

    def _ensure_nvm_view(self, device_key, reset=False):
        view = self.nvm_views.get(device_key)
        if not view or not view['window'].winfo_exists():
            window = tk.Toplevel(self)
            window.title(f"{device_key.capitalize()} NVM Dump")
            window.configure(bg=theme.BG_COLOR)
            text_widget = scrolledtext.ScrolledText(
                window,
                width=100,
                height=32,
                wrap=tk.NONE,
                background=theme.WIDGET_BG,
                foreground=theme.FG_COLOR,
                borderwidth=0,
                font=getattr(theme, "FONT_NORMAL", ("Consolas", 10))
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.configure(state='disabled')
            view = {'window': window, 'text': text_widget}
            self.nvm_views[device_key] = view
        else:
            text_widget = view['text']
            window = view['window']

        if reset:
            text_widget.configure(state='normal')
            text_widget.delete('1.0', tk.END)
            text_widget.configure(state='disabled')

        window.lift()
        return view

    def display_nvm_dump(self, device_key, payload):
        view = self._ensure_nvm_view(device_key)
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

    def _update_status_after_check(self, device_key, release_info):
        row = self.rows.get(device_key)
        if not row:
            return

        current = row['current_var'].get()
        latest = release_info.get('version')

        if not current or current in ("Unknown", "---"):
            row['status_var'].set(f"Latest available firmware: {latest}")
            return

        try:
            comparison = compare_versions(current, latest)
        except Exception:
            row['status_var'].set(f"Latest available firmware: {latest}")
            return

        if comparison >= 0:
            row['status_var'].set("Device firmware is already up to date.")
        else:
            row['status_var'].set(f"Update available: {latest}")

    def _run_on_ui(self, callback):
        if self.winfo_exists():
            self.after(0, callback)

    def _request_device_version(self, device_key):
        if not self.device_manager:
            return

        state = self.device_manager.get_device_state(device_key) or {}
        if not state.get('connected'):
            return
        
        # Always request version to ensure we have the latest
        try:
            from . import comms
            comms.discover_devices(self.gui_refs)
            row = self.rows.get(device_key)
            if row and not state.get('firmware_version'):
                row['status_var'].set("Requesting device firmware version...")
        except Exception:
            pass

        # Schedule a near-term refresh to capture the new version if it arrives.
        self.after(500, lambda: self._update_current_from_state(device_key))

    def _update_current_from_state(self, device_key):
        row = self.rows.get(device_key)
        if not row or not self.device_manager:
            return

        state = self.device_manager.get_device_state(device_key) or {}
        firmware_version = state.get('firmware_version')
        if firmware_version:
            row['current_var'].set(firmware_version)
            self._update_button_states(row, state.get('connected'), state.get('fw_update_in_progress'))
            self._apply_current_version_style(device_key)

    def _populate_release_list(self, device_key, releases):
        row = self.rows.get(device_key)
        if not row:
            return

        release_combo = row['release_combo']
        release_var = row['release_var']
        notes_widget = row['release_notes']

        version_strings = [rel['version'] for rel in releases]
        row['releases'] = {rel['version']: rel for rel in releases}

        release_combo.configure(values=version_strings)
        if version_strings:
            release_var.set(version_strings[0])
            self.on_release_selected(device_key)
            latest_label = row.get('latest_label')
            if latest_label:
                latest_label.configure(foreground=theme.SUCCESS_GREEN)
        else:
            release_var.set('')
            release_combo.configure(values=[])
            self._update_release_notes(notes_widget, "No releases available.")
            latest_label = row.get('latest_label')
            if latest_label:
                latest_label.configure(foreground=theme.FG_COLOR)

        self._update_button_states(row, (self.device_manager.get_device_state(device_key) or {}).get('connected'), False)

    def on_release_selected(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return

        selected_version = row['release_var'].get()
        release_info = row['releases'].get(selected_version)
        notes_widget = row['release_notes']

        if not release_info:
            self._update_release_notes(notes_widget, "Select a release to view its changelog.")
            self._update_button_states(row, (self.device_manager.get_device_state(device_key) or {}).get('connected'), False)
            return

        changelog = release_info.get('body', '').strip() or "(No changelog provided.)"
        summary = changelog.strip()
        self._update_release_notes(notes_widget, summary)

        state = self.device_manager.get_device_state(device_key) or {}
        self._update_button_states(row, state.get('connected'), state.get('fw_update_in_progress'))
        row['status_var'].set(f"Ready to flash {selected_version}.")
        self._apply_current_version_style(device_key)

    def _update_release_notes(self, widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', tk.END)
        widget.insert(tk.END, text)
        widget.configure(state='disabled')

    def _apply_current_version_style(self, device_key):
        row = self.rows.get(device_key)
        if not row:
            return
        current_label = row.get('current_label')
        if not current_label:
            return

        current = row['current_var'].get()
        latest_info = self.release_cache.get(device_key)

        if not latest_info or not latest_info.get('version'):
            current_label.configure(foreground=theme.FG_COLOR)
            return

        latest = latest_info.get('version')
        if not current or current in ("Unknown", "---"):
            current_label.configure(foreground=theme.FG_COLOR)
            return

        try:
            comparison = compare_versions(current, latest)
        except Exception:
            current_label.configure(foreground=theme.FG_COLOR)
            return

        if comparison >= 0:
            current_label.configure(foreground=theme.SUCCESS_GREEN)
        else:
            current_label.configure(foreground=theme.WARNING_YELLOW)


    def _configure_styles(self):
        try:
            self.style.configure(
                'Firmware.TCombobox',
                fieldbackground=theme.WIDGET_BG,
                background=theme.WIDGET_BG,
                foreground=theme.FG_COLOR,
                bordercolor=theme.SECONDARY_ACCENT
            )
            self.style.map(
                'Firmware.TCombobox',
                fieldbackground=[('readonly', theme.WIDGET_BG), ('disabled', theme.SECONDARY_ACCENT)],
                foreground=[('readonly', theme.FG_COLOR), ('disabled', theme.COMMENT_COLOR)]
            )
            self.option_add('*TCombobox*Listbox*Background', theme.WIDGET_BG)
            self.option_add('*TCombobox*Listbox*Foreground', theme.FG_COLOR)
            self.style.configure(
                'Status.TLabel',
                font=theme.FONT_BOLD,
                foreground=theme.PRIMARY_ACCENT
            )
        except Exception:
            pass

    def _update_lan_style(self, row, connected):
        # Removed - LAN connection display no longer shown
        return
        label = row.get('lan_label')
        if not label:
            return
        if connected:
            label.configure(foreground=theme.SUCCESS_GREEN)
        else:
            label.configure(foreground=theme.ERROR_RED)

    def on_close(self):
        if self.update_in_progress:
            messagebox.showwarning(
                "Update In Progress",
                "A firmware update is still running. Please wait for it to finish before closing.",
                parent=self
            )
            return

        if self._refresh_job:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

        if self.gui_refs.get('show_nvm_dump_cb') is self.display_nvm_dump:
            if self._previous_nvm_cb:
                self.gui_refs['show_nvm_dump_cb'] = self._previous_nvm_cb
            else:
                del self.gui_refs['show_nvm_dump_cb']

        for view in list(self.nvm_views.values()):
            window = view.get('window')
            if window and window.winfo_exists():
                window.destroy()
        self.nvm_views.clear()

        if self.gui_refs.get('firmware_manager_window') is self:
            del self.gui_refs['firmware_manager_window']

        self.destroy()

