"""
Barcode/QR Code Scanner Module

Supports USB and Bluetooth barcode/QR code scanners.
Most USB/Bluetooth scanners emulate a keyboard, so we capture keyboard input.
"""

import threading
import queue
import time
from typing import Optional, Callable
import tkinter as tk


class ScannerInputHandler:
    """
    Handles input from barcode/QR scanners that emulate keyboard input.
    
    Most barcode scanners work as HID (Human Interface Devices) and emulate
    keyboard input, typing the barcode/QR code followed by Enter.
    
    This handler captures rapid keyboard input and detects scanner patterns.
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.enabled = False
        self.buffer = ""
        self.last_input_time = 0
        self.timeout = 0.5  # 500ms timeout between inputs
        self.callbacks: list[Callable[[str], None]] = []
        self.widget: Optional[tk.Widget] = None
        self.min_length = 3  # Minimum barcode length
        self.max_length = 100  # Maximum barcode length
        self.scanner_mode = False  # Flag to indicate we're receiving scanner input
        
        # Timer for buffer timeout
        self.timer: Optional[threading.Timer] = None
    
    def enable(self, widget: tk.Widget):
        """
        Enable scanner input handling on a specific widget.
        The widget should be the main window or a focused entry widget.
        """
        with self.lock:
            self.enabled = True
            self.widget = widget
            
            # Create a custom binding tag for scanner that runs FIRST
            widget.bindtags(('ScannerPrevent',) + widget.bindtags())
            widget.bind_class('ScannerPrevent', '<Key>', self._on_key_event, add='+')
    
    def disable(self):
        """
        Disable scanner input handling.
        """
        with self.lock:
            self.enabled = False
            self.scanner_mode = False
            self.buffer = ""
            if self.widget:
                try:
                    # Remove the ScannerPrevent bindtag we added
                    bindtags = list(self.widget.bindtags())
                    if 'ScannerPrevent' in bindtags:
                        bindtags.remove('ScannerPrevent')
                        self.widget.bindtags(tuple(bindtags))
                    # Unbind the class binding
                    self.widget.unbind_class('ScannerPrevent', '<Key>')
                except Exception as e:
                    print(f"[SCANNER] Error during disable: {e}")
            self.widget = None
    
    def _on_key_event(self, event):
        """
        Handle keyboard events from the scanner.
        """
        if not self.enabled:
            return
        
        # Check what widget has focus
        focused_widget = self.widget.focus_get()
        text_editor_has_focus = False
        if focused_widget:
            widget_class = focused_widget.winfo_class()
            text_editor_has_focus = (widget_class == 'Text')
        
        current_time = time.time()
        
        # Check if this is part of a rapid input sequence (scanner)
        time_diff = current_time - self.last_input_time
        
        # Detect scanner input: VERY rapid typing (< 20ms between characters)
        # Normal human typing is > 50ms, scanners are typically < 10ms
        is_scanner_speed = time_diff < 0.02 and self.buffer
        
        if event.keysym == 'Return' or event.keysym == 'KP_Enter':
            # Enter key pressed - end of barcode
            with self.lock:
                buffer_len = len(self.buffer)
                has_buffer = bool(self.buffer)
            
            if has_buffer and self.min_length <= buffer_len <= self.max_length:
                # Valid barcode/QR code scanned
                with self.lock:
                    scanned_data = self.buffer
                    self.buffer = ""
                    self.scanner_mode = False  # Exit scanner mode
                    
                    # Cancel any pending timer
                    if self.timer:
                        self.timer.cancel()
                        self.timer = None
                
                print(f"[SCANNER] Detected scan: {scanned_data}")
                print(f"[SCANNER] SCANNER MODE DEACTIVATED")
                
                # Notify callbacks
                self._notify_callbacks(scanned_data)
                
                # ALWAYS prevent the Enter key from propagating when we detected a scan
                return 'break'
            else:
                # Invalid length or no buffer
                if has_buffer:
                    print(f"[SCANNER] Invalid buffer length {buffer_len}, clearing")
                with self.lock:
                    self.buffer = ""
                    self.scanner_mode = False  # Exit scanner mode
        
        elif len(event.char) == 1 and event.char.isprintable():
            # Printable character
            # If too much time has passed, reset buffer (not a scanner)
            if time_diff > self.timeout and self.buffer:
                with self.lock:
                    self.buffer = ""
                    self.scanner_mode = False  # Exit scanner mode
            
            # Add character to buffer BEFORE deciding to block
            with self.lock:
                self.buffer += event.char
                current_buffer_len = len(self.buffer)
                self.last_input_time = current_time
                
                # Set a timer to clear buffer if no more input
                if self.timer:
                    self.timer.cancel()
                
                def clear_buffer():
                    with self.lock:
                        # Only clear if buffer hasn't been updated
                        if (time.time() - self.last_input_time) >= self.timeout:
                            if self.buffer:
                                print(f"[SCANNER] Timeout - clearing buffer: {self.buffer}")
                            self.buffer = ""
                            self.scanner_mode = False  # Exit scanner mode on timeout
                
                self.timer = threading.Timer(self.timeout * 2, clear_buffer)
                self.timer.daemon = True
                self.timer.start()
            
            # Decide whether to block based on scanner detection and widget focus
            # If Text widget has focus, be aggressive - block ALL rapid input
            if text_editor_has_focus:
                # Script editor has focus - block anything that might be a scanner
                if is_scanner_speed or current_buffer_len >= 2:
                    if not self.scanner_mode:
                        self.scanner_mode = True
                        print(f"[SCANNER] SCANNER MODE ACTIVATED (Text widget has focus)")
                    print(f"[SCANNER] BLOCKING char '{event.char}' (protecting Text widget, buffer: {current_buffer_len})")
                    return 'break'
                else:
                    # First character and not rapid yet - tentatively block it too
                    # We'll wait to see if it becomes a scan
                    print(f"[SCANNER] TENTATIVELY BLOCKING first char '{event.char}' (Text has focus, waiting for 2nd char)")
                    return 'break'
            
            # No Text widget focus - normal scanner detection
            if is_scanner_speed:
                # Detected scanner - enter scanner mode
                if not self.scanner_mode:
                    self.scanner_mode = True
                    print(f"[SCANNER] SCANNER MODE ACTIVATED (rapid input detected < 20ms)")
                print(f"[SCANNER] BLOCKING char '{event.char}' (buffer: {current_buffer_len}, time_diff: {time_diff*1000:.1f}ms)")
                return 'break'
            elif self.scanner_mode:
                # We're in scanner mode (previously detected) - keep blocking even if speed changes
                print(f"[SCANNER] BLOCKING char '{event.char}' (scanner mode active, buffer: {current_buffer_len})")
                return 'break'
            else:
                # Not scanner - normal typing, allow it
                # Only log first few chars to avoid spam
                if current_buffer_len <= 3:
                    print(f"[SCANNER] Allowing char '{event.char}' (not scanner, time_diff: {time_diff*1000:.1f}ms)")
        
        self.last_input_time = current_time
    
    def register_callback(self, callback: Callable[[str], None]):
        """
        Register a callback to be called when a barcode/QR code is scanned.
        """
        with self.lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[str], None]):
        """
        Unregister a callback.
        """
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def _notify_callbacks(self, data: str):
        """
        Notify all registered callbacks with scanned data.
        """
        print(f"[SCANNER] _notify_callbacks called with data: '{data}'")
        
        # Make a copy of callbacks while holding lock
        with self.lock:
            callbacks = list(self.callbacks)
        
        print(f"[SCANNER] Found {len(callbacks)} registered callbacks")
        
        # Call callbacks outside lock to avoid deadlocks
        for i, callback in enumerate(callbacks):
            try:
                print(f"[SCANNER] Calling callback {i+1}/{len(callbacks)}: {callback}")
                callback(data)
                print(f"[SCANNER] Callback {i+1} completed successfully")
            except Exception as e:
                print(f"[SCANNER] ERROR: Callback {i+1} failed: {e}")
                import traceback
                traceback.print_exc()
    
    def set_min_length(self, length: int):
        """Set minimum valid barcode length."""
        with self.lock:
            self.min_length = max(1, length)
    
    def set_max_length(self, length: int):
        """Set maximum valid barcode length."""
        with self.lock:
            self.max_length = max(1, length)
    
    def set_timeout(self, timeout: float):
        """Set timeout between characters (in seconds)."""
        with self.lock:
            self.timeout = max(0.1, timeout)


class ManualSerialInput:
    """
    Simple wrapper for manual serial number entry via GUI.
    """
    
    def __init__(self):
        self.callbacks: list[Callable[[str], None]] = []
    
    def register_callback(self, callback: Callable[[str], None]):
        """Register a callback for when a serial is manually entered."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[str], None]):
        """Unregister a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def submit_serial(self, serial: str):
        """Submit a manually entered serial number."""
        if serial:
            for callback in self.callbacks:
                try:
                    callback(serial)
                except Exception as e:
                    print(f"[ERROR] Manual serial callback failed: {e}")


# Global instances
_scanner_handler: Optional[ScannerInputHandler] = None
_manual_input: Optional[ManualSerialInput] = None
_init_lock = threading.Lock()


def get_scanner_handler() -> ScannerInputHandler:
    """Get the global ScannerInputHandler instance (singleton)."""
    global _scanner_handler
    with _init_lock:
        if _scanner_handler is None:
            _scanner_handler = ScannerInputHandler()
        return _scanner_handler


def get_manual_input() -> ManualSerialInput:
    """Get the global ManualSerialInput instance (singleton)."""
    global _manual_input
    with _init_lock:
        if _manual_input is None:
            _manual_input = ManualSerialInput()
        return _manual_input


def initialize_scanner(root_widget: tk.Widget):
    """
    Initialize the scanner handler with the main window.
    Should be called after the main window is created.
    """
    handler = get_scanner_handler()
    handler.enable(root_widget)
    print("[SCANNER] Scanner input handler initialized")


def cleanup_scanner():
    """
    Cleanup scanner resources.
    Should be called on application exit.
    """
    handler = get_scanner_handler()
    handler.disable()
    print("[SCANNER] Scanner input handler cleaned up")

