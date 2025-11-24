"""
Serial Number Management Module

Handles serial number tracking, incrementing, and integration with data logging.
Supports manual entry and barcode/QR code scanner input.
"""

import threading
from typing import Optional, Dict, Callable
from pathlib import Path


class SerialNumberManager:
    """
    Manages serial numbers for data logging and device tracking.
    Supports auto-increment and manual/scanner input.
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.current_serial: Optional[str] = None
        self.auto_increment: bool = True
        self.prefix: str = ""
        self.counter: int = 1
        self.padding: int = 4  # Zero-padding width (e.g., 0001)
        self.scanner_callbacks: list = []  # Callbacks when scanner input is received
        
    def set_serial(self, serial: str):
        """
        Set the current serial number manually.
        """
        with self.lock:
            self.current_serial = serial
    
    def get_serial(self) -> Optional[str]:
        """
        Get the current serial number without incrementing.
        """
        with self.lock:
            return self.current_serial
    
    def get_and_increment(self) -> Optional[str]:
        """
        Get the current serial number and increment if auto-increment is enabled.
        Returns None if no serial number is set.
        """
        with self.lock:
            if self.current_serial is None:
                return None
            
            current = self.current_serial
            
            if self.auto_increment:
                # Try to increment the serial number
                self.current_serial = self._increment_serial(self.current_serial)
            
            return current
    
    def _increment_serial(self, serial: str) -> str:
        """
        Increment a serial number intelligently.
        Handles various formats:
        - Pure numeric: "001" -> "002"
        - Prefix + numeric: "SN-001" -> "SN-002"
        - Mixed: "ABC123XYZ" -> "ABC124XYZ"
        """
        if not serial:
            return serial
        
        # Find the last numeric sequence in the string
        import re
        
        # Find all numeric sequences with their positions
        matches = list(re.finditer(r'\d+', serial))
        
        if not matches:
            # No numbers found, can't increment
            return serial
        
        # Get the last numeric sequence
        last_match = matches[-1]
        start, end = last_match.span()
        num_str = last_match.group()
        
        # Preserve leading zeros by padding to original width
        width = len(num_str)
        num = int(num_str)
        num += 1
        
        # Format with zero-padding
        new_num_str = str(num).zfill(width)
        
        # Reconstruct the serial number
        new_serial = serial[:start] + new_num_str + serial[end:]
        
        return new_serial
    
    def set_auto_increment(self, enabled: bool):
        """
        Enable or disable auto-increment.
        """
        with self.lock:
            self.auto_increment = enabled
    
    def get_auto_increment(self) -> bool:
        """
        Check if auto-increment is enabled.
        """
        with self.lock:
            return self.auto_increment
    
    def reset(self):
        """
        Reset the serial number to None.
        """
        with self.lock:
            self.current_serial = None
    
    def register_scanner_callback(self, callback: Callable[[str], None]):
        """
        Register a callback to be called when a barcode/QR code is scanned.
        Callback signature: callback(serial_number: str)
        """
        with self.lock:
            if callback not in self.scanner_callbacks:
                self.scanner_callbacks.append(callback)
    
    def unregister_scanner_callback(self, callback: Callable[[str], None]):
        """
        Unregister a scanner callback.
        """
        with self.lock:
            if callback in self.scanner_callbacks:
                self.scanner_callbacks.remove(callback)
    
    def on_scanner_input(self, serial: str):
        """
        Called when a scanner provides input.
        Updates the current serial and notifies callbacks.
        """
        with self.lock:
            self.current_serial = serial
            callbacks = list(self.scanner_callbacks)
        
        # Call callbacks outside the lock to avoid deadlocks
        for callback in callbacks:
            try:
                callback(serial)
            except Exception as e:
                print(f"[ERROR] Scanner callback failed: {e}")


# Global serial number manager instance
_serial_manager: Optional[SerialNumberManager] = None
_manager_lock = threading.Lock()


def get_serial_manager() -> SerialNumberManager:
    """
    Get the global SerialNumberManager instance (singleton).
    """
    global _serial_manager
    with _manager_lock:
        if _serial_manager is None:
            _serial_manager = SerialNumberManager()
        return _serial_manager


def format_filename_with_serial(base_filename: str, serial: Optional[str]) -> str:
    """
    Format a filename with serial number.
    
    Examples:
        base_filename="log.csv", serial="SN001" -> "log_SN001.csv"
        base_filename="test_<serial>.csv", serial="ABC" -> "test_ABC.csv"
        base_filename="data.csv", serial=None -> "data.csv"
    """
    if serial is None:
        # No serial number, return as-is (remove <serial> placeholder if present)
        return base_filename.replace('<serial>', '').replace('__', '_')
    
    # Check if filename has a <serial> placeholder
    if '<serial>' in base_filename:
        return base_filename.replace('<serial>', serial)
    
    # Otherwise, insert serial before the extension
    path = Path(base_filename)
    stem = path.stem
    suffix = path.suffix
    
    # Add serial as suffix to stem
    new_stem = f"{stem}_{serial}"
    return str(Path(new_stem).with_suffix(suffix))


def save_serial_to_config(serial: Optional[str], auto_increment: bool):
    """
    Save current serial number and auto-increment setting to config.
    """
    try:
        from src.config import load_config, save_config
        config = load_config()
        config['serial_number'] = serial
        config['serial_auto_increment'] = auto_increment
        save_config(config)
    except Exception as e:
        print(f"[ERROR] Failed to save serial number to config: {e}")


def load_serial_from_config() -> tuple[Optional[str], bool]:
    """
    Load serial number and auto-increment setting from config.
    Returns (serial, auto_increment)
    """
    try:
        from src.config import load_config
        config = load_config()
        serial = config.get('serial_number', None)
        auto_increment = config.get('serial_auto_increment', True)
        return (serial, auto_increment)
    except Exception as e:
        print(f"[ERROR] Failed to load serial number from config: {e}")
        return (None, True)


def initialize_serial_manager():
    """
    Initialize the serial manager with saved config values.
    Should be called on application startup.
    """
    manager = get_serial_manager()
    serial, auto_increment = load_serial_from_config()
    
    if serial is not None:
        manager.set_serial(serial)
    manager.set_auto_increment(auto_increment)
    
    print(f"[SERIAL] Initialized serial number: {serial}, auto-increment: {auto_increment}")

