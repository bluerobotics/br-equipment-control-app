"""
Quick Launch Panel

Provides a sidebar panel with large, touchscreen-friendly buttons that
open and immediately run pre-configured .breq scripts.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os

from src import theme
from src.config import get_quick_launch_scripts, set_quick_launch_scripts
from src.logging.terminal import log_to_terminal


class QuickLaunchPanel(ttk.Frame):
    """Vertical stack of large script-launch buttons for the left sidebar."""

    POLL_INTERVAL_MS = 500

    def __init__(self, parent, shared_gui_refs, scripting_gui_refs=None, **kwargs):
        super().__init__(parent, style='Card.TFrame', **kwargs)
        self.shared_gui_refs = shared_gui_refs
        self.scripting_gui_refs = scripting_gui_refs
        self._buttons = {}        # idx -> tk.Button
        self._running_idx = None  # index of the currently-running script button (for visual state)
        self._poll_id = None

        self._build_header()
        self._button_container = ttk.Frame(self, style='Card.TFrame')
        self._button_container.pack(side=tk.TOP, fill='x')
        self._rebuild_buttons()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_scripting_refs(self, scripting_gui_refs):
        """Set (or update) scripting GUI references after construction."""
        self.scripting_gui_refs = scripting_gui_refs

    def refresh(self):
        """Reload config and rebuild buttons."""
        self._rebuild_buttons()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        header = ttk.Frame(self, style='Card.TFrame')
        header.pack(side=tk.TOP, fill='x', padx=8, pady=(8, 2))

        ttk.Label(
            header,
            text="Scripts",
            font=(theme.FONT_FAMILY, theme.get_font_size(), 'bold'),
            style='TLabel',
            background=theme.CARD_BG,
        ).pack(side=tk.LEFT)

        add_btn = ttk.Button(
            header,
            text="+",
            style='Ghost.TButton',
            width=3,
            command=self._open_config_dialog,
        )
        add_btn.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Button construction
    # ------------------------------------------------------------------

    def _rebuild_buttons(self):
        for widget in self._button_container.winfo_children():
            widget.destroy()
        self._buttons.clear()

        scripts = get_quick_launch_scripts()
        if not scripts:
            ttk.Label(
                self._button_container,
                text="No scripts configured.\nClick + to add.",
                style='Subtle.TLabel',
                justify=tk.CENTER,
            ).pack(pady=10, padx=10)
            return

        for idx, entry in enumerate(scripts):
            if not isinstance(entry, dict):
                continue
            name = entry.get('name', 'Unnamed')
            path = entry.get('path', '')
            btn = tk.Button(
                self._button_container,
                text=name,
                font=(theme.FONT_FAMILY, 14, 'bold'),
                bg=theme.WIDGET_BG,
                fg=theme.PRIMARY_ACCENT,
                activebackground=theme.SECONDARY_ACCENT,
                activeforeground=theme.FG_COLOR,
                relief='flat',
                bd=1,
                highlightbackground=theme.SECONDARY_ACCENT,
                highlightthickness=1,
                cursor='hand2',
                height=2,
                command=lambda p=path, i=idx: self._on_button_click(i, p),
            )
            btn.pack(side=tk.TOP, fill='x', padx=8, pady=(4, 0))
            self._buttons[idx] = btn

    # ------------------------------------------------------------------
    # Launch logic
    # ------------------------------------------------------------------

    def _on_button_click(self, btn_idx, filepath):
        if not os.path.isfile(filepath):
            log_to_terminal(f"Script not found: {filepath}", self.shared_gui_refs)
            return

        runner = self.shared_gui_refs.get('script_runner')
        if runner and runner.is_alive():
            log_to_terminal("A script is already running", self.shared_gui_refs)
            return

        # Clear stale error-hold state from a previous run so
        # handle_cycle_start doesn't try to resume a dead runner.
        if runner and getattr(runner, 'is_held', False):
            runner.is_held = False

        if not self.scripting_gui_refs:
            log_to_terminal("Scripting interface not ready yet", self.shared_gui_refs)
            return

        open_fn = self.scripting_gui_refs.get('open_script_in_tab')
        run_fn = self.scripting_gui_refs.get('run_active_tab')

        if open_fn:
            open_fn(filepath)
        if run_fn:
            run_fn()

        self._set_running(btn_idx)

    # ------------------------------------------------------------------
    # Running-state visual feedback
    # ------------------------------------------------------------------

    def _set_running(self, btn_idx):
        self._running_idx = btn_idx
        btn = self._buttons.get(btn_idx)
        if btn:
            btn.configure(bg=theme.RUNNING_GREEN, fg='white')
        self._start_polling()

    def _clear_running(self):
        if self._running_idx is not None:
            btn = self._buttons.get(self._running_idx)
            if btn and btn.winfo_exists():
                btn.configure(bg=theme.WIDGET_BG, fg=theme.PRIMARY_ACCENT)
            self._running_idx = None

    def _start_polling(self):
        if self._poll_id is not None:
            return
        self._poll_running()

    def _poll_running(self):
        runner = self.shared_gui_refs.get('script_runner')
        if runner and runner.is_alive():
            self._poll_id = self.after(self.POLL_INTERVAL_MS, self._poll_running)
        else:
            self._clear_running()
            self._poll_id = None

    # ------------------------------------------------------------------
    # Configuration dialog
    # ------------------------------------------------------------------

    def _open_config_dialog(self):
        show_quick_launch_config(self.winfo_toplevel(), self)


# ======================================================================
# Configuration dialog (standalone so it can be called from the menu too)
# ======================================================================

def show_quick_launch_config(parent, panel=None):
    """Open the Quick Launch Scripts configuration dialog.

    Args:
        parent: Tk parent window for the dialog.
        panel: Optional QuickLaunchPanel instance to refresh after saving.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Manage Quick Launch Scripts")
    dialog.configure(bg=theme.BG_COLOR)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(True, True)
    dialog.minsize(500, 350)

    # ----- State -----
    scripts = get_quick_launch_scripts()
    entries = [dict(e) for e in scripts]  # deep-ish copy

    # ----- Widgets -----
    frame = ttk.Frame(dialog, padding=16, style='TFrame')
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    ttk.Label(
        frame, text="Quick Launch Scripts", font=theme.FONT_LARGE_BOLD, style='TLabel'
    ).grid(row=0, column=0, sticky='w', pady=(0, 8))

    # Listbox in a card frame
    list_frame = ttk.Frame(frame, style='Card.TFrame')
    list_frame.grid(row=1, column=0, sticky='nsew')
    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)

    listbox = tk.Listbox(
        list_frame,
        bg=theme.WIDGET_BG,
        fg=theme.FG_COLOR,
        selectbackground=theme.SELECTION_BG,
        selectforeground=theme.SELECTION_FG,
        font=theme.FONT_NORMAL,
        relief='flat',
        bd=0,
        highlightthickness=0,
        activestyle='none',
    )
    listbox.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    listbox.configure(yscrollcommand=scrollbar.set)

    def _refresh_listbox():
        listbox.delete(0, tk.END)
        for e in entries:
            listbox.insert(tk.END, f"{e['name']}  —  {e['path']}")

    _refresh_listbox()

    # ----- Right-side button column -----
    btn_frame = ttk.Frame(frame, style='TFrame')
    btn_frame.grid(row=1, column=1, sticky='ns', padx=(8, 0))

    def _add_entry():
        _show_add_edit_dialog(dialog, entries, None, _refresh_listbox)

    def _edit_entry():
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        _show_add_edit_dialog(dialog, entries, idx, _refresh_listbox)

    def _remove_entry():
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        entries.pop(idx)
        _refresh_listbox()

    def _move_up():
        sel = listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        entries[idx - 1], entries[idx] = entries[idx], entries[idx - 1]
        _refresh_listbox()
        listbox.selection_set(idx - 1)

    def _move_down():
        sel = listbox.curselection()
        if not sel or sel[0] >= len(entries) - 1:
            return
        idx = sel[0]
        entries[idx], entries[idx + 1] = entries[idx + 1], entries[idx]
        _refresh_listbox()
        listbox.selection_set(idx + 1)

    for text, cmd, style in [
        ("Add...", _add_entry, 'Blue.TButton'),
        ("Edit...", _edit_entry, 'Ghost.TButton'),
        ("Remove", _remove_entry, 'Red.TButton'),
        ("Move Up", _move_up, 'Ghost.TButton'),
        ("Move Down", _move_down, 'Ghost.TButton'),
    ]:
        ttk.Button(btn_frame, text=text, command=cmd, style=style, width=12).pack(
            pady=(0, 4)
        )

    # Allow double-click to edit
    listbox.bind('<Double-Button-1>', lambda e: _edit_entry())

    # ----- OK / Cancel -----
    bottom = ttk.Frame(frame, style='TFrame')
    bottom.grid(row=2, column=0, columnspan=2, sticky='e', pady=(12, 0))

    def _on_ok():
        set_quick_launch_scripts(entries)
        if panel:
            panel.refresh()
        dialog.destroy()

    ttk.Button(bottom, text="OK", style='Blue.TButton', command=_on_ok, width=10).pack(
        side=tk.RIGHT, padx=(8, 0)
    )
    ttk.Button(
        bottom, text="Cancel", style='Ghost.TButton', command=dialog.destroy, width=10
    ).pack(side=tk.RIGHT)

    # Center on parent
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f'+{max(0, x)}+{max(0, y)}')


def _show_add_edit_dialog(parent, entries, edit_index, refresh_cb):
    """Small sub-dialog for adding or editing a single entry."""
    is_edit = edit_index is not None
    title = "Edit Script Entry" if is_edit else "Add Script Entry"

    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=theme.BG_COLOR)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.resizable(True, False)

    frame = ttk.Frame(dlg, padding=16, style='TFrame')
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Display Name:", style='TLabel').grid(
        row=0, column=0, sticky='w', padx=(0, 8), pady=4
    )
    name_var = tk.StringVar(value=entries[edit_index]['name'] if is_edit else '')
    name_entry = ttk.Entry(frame, textvariable=name_var, width=40)
    name_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=4)

    ttk.Label(frame, text="Script Path:", style='TLabel').grid(
        row=1, column=0, sticky='w', padx=(0, 8), pady=4
    )
    path_var = tk.StringVar(value=entries[edit_index]['path'] if is_edit else '')
    path_entry = ttk.Entry(frame, textvariable=path_var, width=40)
    path_entry.grid(row=1, column=1, sticky='ew', pady=4)

    def _browse():
        initial = os.path.dirname(path_var.get()) if path_var.get() else ''
        fp = filedialog.askopenfilename(
            parent=dlg,
            title="Select Script File",
            initialdir=initial or None,
            filetypes=[("BREQ Scripts", "*.breq"), ("All Files", "*.*")],
        )
        if fp:
            path_var.set(fp)
            if not name_var.get():
                name_var.set(os.path.splitext(os.path.basename(fp))[0])

    ttk.Button(frame, text="Browse", style='Blue.TButton', command=_browse).grid(
        row=1, column=2, padx=(4, 0), pady=4
    )

    # OK / Cancel
    btn_row = ttk.Frame(frame, style='TFrame')
    btn_row.grid(row=2, column=0, columnspan=3, sticky='e', pady=(12, 0))

    def _on_ok():
        n = name_var.get().strip()
        p = path_var.get().strip()
        if not n or not p:
            return
        entry = {'name': n, 'path': p}
        if is_edit:
            entries[edit_index] = entry
        else:
            entries.append(entry)
        refresh_cb()
        dlg.destroy()

    ttk.Button(btn_row, text="OK", style='Blue.TButton', command=_on_ok, width=10).pack(
        side=tk.RIGHT, padx=(8, 0)
    )
    ttk.Button(
        btn_row, text="Cancel", style='Ghost.TButton', command=dlg.destroy, width=10
    ).pack(side=tk.RIGHT)

    name_entry.focus_set()

    dlg.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - dlg.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - dlg.winfo_height()) // 2
    dlg.geometry(f'+{max(0, x)}+{max(0, y)}')
