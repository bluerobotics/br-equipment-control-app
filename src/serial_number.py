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
        self.current_job: Optional[str] = None
        self.current_op: Optional[str] = None
        self.current_serial: Optional[str] = None
        self.auto_increment: bool = False  # Changed default to False
        self.scanner_target: str = "job"  # "job", "op", or "serial" - default to job
        self.prefix: str = ""
        self.counter: int = 1
        self.padding: int = 4  # Zero-padding width (e.g., 0001)
        self.scanner_callbacks: list = []  # Callbacks when scanner input is received
        
    def set_job(self, job: str):
        """
        Set the current job number manually.
        """
        with self.lock:
            self.current_job = job
    
    def get_job(self) -> Optional[str]:
        """
        Get the current job number.
        """
        with self.lock:
            return self.current_job
    
    def set_op(self, op: str):
        """
        Set the current operator number manually.
        """
        with self.lock:
            self.current_op = op
    
    def get_op(self) -> Optional[str]:
        """
        Get the current operator number.
        """
        with self.lock:
            return self.current_op
    
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
    
    def set_scanner_target(self, target: str):
        """
        Set which field the scanner populates: "job", "op", or "serial".
        """
        with self.lock:
            if target in ["job", "op", "serial"]:
                self.scanner_target = target
    
    def get_scanner_target(self) -> str:
        """
        Get the current scanner target field.
        """
        with self.lock:
            return self.scanner_target
    
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
        Reset job, op, and serial numbers to None.
        """
        with self.lock:
            self.current_job = None
            self.current_op = None
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
    
    def on_scanner_input(self, text: str):
        """
        Called when a scanner provides input.
        Updates the current job, op, or serial based on scanner_target and notifies callbacks.
        """
        with self.lock:
            target = self.scanner_target
            if target == "job":
                self.current_job = text
            elif target == "op":
                self.current_op = text
            else:  # "serial"
                self.current_serial = text
            callbacks = list(self.scanner_callbacks)
        
        # Call callbacks outside the lock to avoid deadlocks
        for callback in callbacks:
            try:
                callback(text)
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


def format_filename_with_serial(base_filename: str, serial: Optional[str] = None, job: Optional[str] = None, op: Optional[str] = None) -> str:
    """
    Format a filename with job number, op number, and/or serial number.
    Only replaces placeholders if they exist in the filename - does NOT auto-append.
    
    Examples:
        base_filename="test_<job>_<op>_<serial>.csv", job="001", op="42", serial="123" -> "test_001_42_123.csv"
        base_filename="log_<job>.csv", job="001" -> "log_001.csv"
        base_filename="data.csv", serial="123", job="001" -> "data.csv" (no placeholders, no change)
    """
    result = base_filename
    
    # Replace <job> placeholder
    if '<job>' in result:
        result = result.replace('<job>', job if job else '')
    
    # Replace <op> placeholder
    if '<op>' in result:
        result = result.replace('<op>', op if op else '')
    
    # Replace <serial> placeholder
    if '<serial>' in result:
        result = result.replace('<serial>', serial if serial else '')
    
    # Clean up multiple underscores
    result = result.replace('__', '_')
    
    return result


def save_serial_to_config(job: Optional[str], op: Optional[str], serial: Optional[str], auto_increment: bool, scanner_target: str):
    """
    Save current job number, op number, serial number, auto-increment setting, and scanner target to config.
    """
    try:
        from src.config import load_config, save_config
        config = load_config()
        config['job_number'] = job
        config['op_number'] = op
        config['serial_number'] = serial
        config['serial_auto_increment'] = auto_increment
        config['serial_scanner_target'] = scanner_target
        save_config(config)
    except Exception as e:
        print(f"[ERROR] Failed to save serial number to config: {e}")


def load_serial_from_config() -> tuple[Optional[str], Optional[str], Optional[str], bool, str]:
    """
    Load job number, op number, serial number, auto-increment setting, and scanner target from config.
    Returns (job, op, serial, auto_increment, scanner_target)
    """
    try:
        from src.config import load_config
        config = load_config()
        job = config.get('job_number', None)
        op = config.get('op_number', None)
        serial = config.get('serial_number', None)
        auto_increment = config.get('serial_auto_increment', False)  # Default to False
        scanner_target = config.get('serial_scanner_target', 'job')  # Default to job
        return (job, op, serial, auto_increment, scanner_target)
    except Exception as e:
        print(f"[ERROR] Failed to load serial number from config: {e}")
        return (None, None, None, False, 'serial')


def initialize_serial_manager():
    """
    Initialize the serial manager with saved config values.
    Should be called on application startup.
    """
    manager = get_serial_manager()
    job, op, serial, auto_increment, scanner_target = load_serial_from_config()
    
    if job is not None:
        manager.set_job(job)
    if op is not None:
        manager.set_op(op)
    if serial is not None:
        manager.set_serial(serial)
    manager.set_auto_increment(auto_increment)
    manager.set_scanner_target(scanner_target)
    
    print(f"[SERIAL] Initialized - job: {job}, op: {op}, serial: {serial}, auto-increment: {auto_increment}, scanner target: {scanner_target}")

