# data_logger.py

"""
Data logging module for telemetry variables.
Handles CSV file creation, writing, and management.
"""

import csv
import os
import re
import sys
import threading
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import tkinter as tk
from .terminal import log_to_terminal
from src.serial_number import get_serial_manager, format_filename_with_serial


def _resolve_logs_directory() -> Path:
    """
    Get the configured data logs directory.
    Uses OS-specific defaults if not configured.
    """
    try:
        from src.config import get_data_logs_dir
        return get_data_logs_dir()
    except Exception as e:
        print(f"Warning getting data logs directory: {e}")
        # Fallback
        fallback_dir = Path.home() / '.br-equipment-control-app' / 'data_logs'
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return fallback_dir

class DataLogger:
    """
    Manages CSV logging of telemetry variables.
    Supports multiple simultaneous log files with different variable sets.
    """
    
    def __init__(self, shared_gui_refs):
        self.shared_gui_refs = shared_gui_refs
        self.active_logs: Dict[str, dict] = {}  # filename -> log_info
        self.queued_variables: Dict[str, Set[str]] = {}  # device_name -> set of variable names
        self.lock = threading.Lock()
        self.logs_path: Path = _resolve_logs_directory()
        self.logs_dir = str(self.logs_path)
    
    def _get_unique_filename(self, base_filename: str) -> str:
        """
        Returns a unique filename by appending _1, _2, etc. if needed.
        Adds .csv extension if not present.
        Supports <date>, <time>, <job>, <op>, and <serial> tags for dynamic values.
        """
        # Get job, op, and serial numbers from serial manager
        serial_manager = get_serial_manager()
        job = serial_manager.get_job()
        op = serial_manager.get_op()
        serial = serial_manager.get_and_increment()
        
        # Replace date/time tags
        now = datetime.datetime.now()
        base_filename = base_filename.replace('<date>', now.strftime('%Y-%m-%d'))
        base_filename = base_filename.replace('<time>', now.strftime('%H-%M-%S'))
        
        # Apply job, op, and serial number formatting (handles <job>/<op>/<serial> placeholders)
        base_filename = format_filename_with_serial(base_filename, serial, job, op)
        
        # Clean up multiple consecutive spaces (from empty template tags) and trim
        base_filename = re.sub(r'\s+', ' ', base_filename).strip()
        
        if not base_filename.endswith('.csv'):
            base_filename += '.csv'
        
        filepath = os.path.join(self.logs_dir, base_filename)
        
        if not os.path.exists(filepath):
            return filepath
        
        # File exists, find a unique name
        base, ext = os.path.splitext(base_filename)
        counter = 1
        
        while True:
            new_filename = f"{base}_{counter}{ext}"
            filepath = os.path.join(self.logs_dir, new_filename)
            if not os.path.exists(filepath):
                return filepath
            counter += 1
    
    def _generate_default_filename(self, device_name: str) -> str:
        """
        Generates a default filename in the format: device_name.yyyy-mm-dd-hh-mm-ss.csv
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{device_name}.{timestamp}.csv"
        return os.path.join(self.logs_dir, filename)
    
    def _parse_variable(self, var_string: str) -> tuple:
        """
        Parses a variable string in format "device.variable" or just "variable".
        Returns (device_name, variable_name).
        """
        if '.' in var_string:
            parts = var_string.split('.', 1)
            return (parts[0], parts[1])
        else:
            # If no device specified, try to infer from currently connected devices
            # For now, return None for device
            return (None, var_string)
    
    def _get_gui_var_for_variable(self, device_name: str, variable_name: str) -> Optional[tk.Variable]:
        """
        Gets the tkinter variable associated with a device's telemetry variable.
        """
        device_manager = self.shared_gui_refs.get('device_manager')
        if not device_manager:
            return None
        
        # Get device data
        device_data = device_manager.devices.get(device_name)
        if not device_data:
            return None
        
        # Get telemetry info
        telemetry_data = device_data.get('telemetry_data', {})
        param_info = telemetry_data.get(variable_name)
        
        if not param_info:
            return None
        
        # Get GUI variable name (auto-generate if not provided, matching device_manager logic)
        gui_var_name = param_info.get('gui_var', f"{device_name}_{variable_name}_var")
        
        return self.shared_gui_refs.get(gui_var_name)
    
    def start_logging(self, filename: Optional[str], variables: List[str], frequency: Optional[float] = None) -> tuple:
        """
        Starts logging specified variables to a CSV file.
        
        Args:
            filename: CSV filename (without path). If None, generates default based on first device.
            variables: List of variable names in format "device.variable"
            frequency: Optional logging frequency in Hz. If None, syncs with incoming telemetry messages.
        
        Returns:
            (success: bool, message: str, actual_filename: str)
        """
        print(f"[TRACE] start_logging called: filename={filename}, variables={variables}")
        with self.lock:
            print(f"[TRACE] Acquired lock in start_logging")
            if not variables:
                return (False, "No variables specified for logging", None)
            
            # Parse variables and validate
            parsed_vars = []
            device_names = set()
            
            print(f"[TRACE] Parsing {len(variables)} variables")
            for var in variables:
                device_name, var_name = self._parse_variable(var)
                
                if not device_name:
                    return (False, f"Invalid variable format: '{var}'. Use 'device.variable'", None)
                
                # Check if variable exists and get type info
                print(f"[TRACE] Getting gui_var for {device_name}.{var_name}")
                gui_var = self._get_gui_var_for_variable(device_name, var_name)
                print(f"[TRACE] gui_var result: {gui_var}")
                if gui_var is None:
                    return (False, f"Unknown variable: '{var}'", None)
                
                # Get variable type from telemetry schema
                device_manager = self.shared_gui_refs.get('device_manager')
                var_type = 'float'  # Default
                if device_manager:
                    device_data = device_manager.devices.get(device_name)
                    if device_data:
                        telemetry_data = device_data.get('telemetry_data', {})
                        param_info = telemetry_data.get(var_name)
                        if param_info:
                            var_type = param_info.get('type', 'float')
                
                parsed_vars.append({
                    'device': device_name,
                    'variable': var_name,
                    'full_name': f"{device_name}.{var_name}",
                    'gui_var': gui_var,
                    'type': var_type
                })
                device_names.add(device_name)
            
            print(f"[TRACE] Parsed {len(parsed_vars)} variables from {len(device_names)} devices")
            
            # Generate filename if not provided
            if filename is None:
                # Use the first device name
                first_device = list(device_names)[0]
                filepath = self._generate_default_filename(first_device)
            else:
                filepath = self._get_unique_filename(filename)
            
            print(f"[TRACE] Generated filepath: {filepath}")
            
            # Create CSV file with headers
            print(f"[TRACE] Creating CSV file...")
            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    headers = ['date', 'time_ms', 'elapsed_s'] + [v['full_name'] for v in parsed_vars]
                    writer.writerow(headers)
                
                # Store log info
                self.active_logs[filepath] = {
                    'variables': parsed_vars,
                    'devices': device_names,
                    'file_handle': None,  # Will be opened in write mode when needed
                    'csv_writer': None,
                    'start_time': datetime.datetime.now(),
                    'callbacks': {},  # Store callback per device
                    'frequency': frequency,  # Optional logging frequency in Hz
                    'timer': None  # Timer object for frequency-based logging
                }
                
                print(f"[TRACE] Registering telemetry callbacks...")
                # Register telemetry callback for each device
                device_manager = self.shared_gui_refs.get('device_manager')
                if device_manager:
                    if frequency is None:
                        # Sync with telemetry - register callbacks
                        for device_name in device_names:
                            print(f"[TRACE] Registering callback for {device_name}")
                            # Create a closure to capture the filepath
                            callback = self._make_callback(filepath)
                            device_manager.register_telemetry_callback(device_name, callback)
                            # Store callback reference for later unregistration
                            self.active_logs[filepath]['callbacks'][device_name] = callback
                    else:
                        # Use timer-based logging at specified frequency
                        import threading
                        interval = 1.0 / frequency  # Convert Hz to seconds
                        
                        def timer_callback():
                            if filepath in self.active_logs:
                                self._log_row_from_current_values(filepath)
                                # Schedule next callback
                                timer = threading.Timer(interval, timer_callback)
                                timer.daemon = True
                                timer.start()
                                self.active_logs[filepath]['timer'] = timer
                        
                        # Start the timer
                        timer = threading.Timer(interval, timer_callback)
                        timer.daemon = True
                        timer.start()
                        self.active_logs[filepath]['timer'] = timer
                
                print(f"[TRACE] Logging to GUI terminal...")
                # Log to GUI terminal
                var_count = len(parsed_vars)
                freq_info = f" at {frequency} Hz" if frequency else " (synced with telemetry)"
                log_msg = f"Started logging {var_count} variable(s){freq_info} to {os.path.basename(filepath)}"
                log_to_terminal(log_msg, self.shared_gui_refs)
                log_to_terminal(f"[DATA LOGGER] Full path: {filepath}", self.shared_gui_refs)
                
                print(f"[TRACE] start_logging complete, returning success")
                return (True, log_msg, filepath)
                
            except Exception as e:
                return (False, f"Error creating log file: {e}", None)
    
    def stop_logging(self, filename: Optional[str] = None) -> tuple:
        """
        Stops logging to specified file, or all files if filename is None.
        
        Returns:
            (success: bool, message: str)
        """
        with self.lock:
            if filename is None:
                # Stop all logging - if none active, that's still a success (nothing to do)
                if not self.active_logs:
                    return (True, "No active logging sessions")
                
                count = len(self.active_logs)
                files_to_close = list(self.active_logs.keys())
                
                for filepath in files_to_close:
                    self._close_log_file(filepath)
                
                log_msg = f"Stopped logging to {count} file(s)"
                log_to_terminal(log_msg, self.shared_gui_refs)
                
                return (True, log_msg)
            else:
                # Stop specific file
                # Find full path
                target_path = None
                for filepath in self.active_logs.keys():
                    if os.path.basename(filepath) == filename or filepath == filename:
                        target_path = filepath
                        break
                
                if target_path is None:
                    # Not an error - file just isn't being logged
                    return (True, f"No active log with filename '{filename}'")
                
                self._close_log_file(target_path)
                log_msg = f"Stopped logging to {os.path.basename(target_path)}"
                log_to_terminal(log_msg, self.shared_gui_refs)
                
                return (True, log_msg)
    
    def _make_callback(self, filepath: str):
        """
        Creates a callback function for a specific log file.
        """
        def callback(device_name: str, telemetry_data: dict):
            try:
                self._on_telemetry_update(filepath, device_name, telemetry_data)
            except Exception as e:
                print(f"[ERROR] Exception in logging callback for {filepath}: {e}")
                import traceback
                traceback.print_exc()
        return callback
    
    def _close_log_file(self, filepath: str):
        """
        Closes a log file and removes it from active logs.
        """
        log_info = self.active_logs.get(filepath)
        if log_info:
            # Close file handle if open - flush and sync to ensure Windows writes to disk
            if log_info['file_handle']:
                try:
                    log_info['file_handle'].flush()
                    os.fsync(log_info['file_handle'].fileno())
                except Exception:
                    pass  # Ignore errors during sync (file might already be closed)
                log_info['file_handle'].close()
            
            # Cancel timer if present
            if log_info.get('timer'):
                log_info['timer'].cancel()
            
            # Unregister callbacks
            device_manager = self.shared_gui_refs.get('device_manager')
            if device_manager and 'callbacks' in log_info:
                for device_name, callback in log_info['callbacks'].items():
                    device_manager.unregister_telemetry_callback(device_name, callback)
            
            del self.active_logs[filepath]
    
    def _on_telemetry_update(self, filepath: str, device_name: str, telemetry_data: dict):
        """
        Called when telemetry is received for a device we're logging.
        Writes a new row to the CSV file.
        telemetry_data is a dict of {key: raw_value} from the parsed telemetry.
        """
        try:
            with self.lock:
                log_info = self.active_logs.get(filepath)
                if not log_info:
                    return
                
                # Check if any variables from this device are in this log
                has_device_vars = any(v['device'] == device_name for v in log_info['variables'])
                if not has_device_vars:
                    return
                
                # Get timestamp with millisecond accuracy
                now = datetime.datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
                
                # Calculate elapsed time from start in seconds with millisecond precision
                elapsed = (now - log_info['start_time']).total_seconds()
                elapsed_str = f"{elapsed:.3f}"
                
                # Collect values for this row (only for variables from this device)
                row_values = [date_str, time_str, elapsed_str]
                
                for var_info in log_info['variables']:
                    # Check if this variable belongs to the current device
                    if var_info['device'] == device_name:
                        # Get value from telemetry_data (raw values from the parsed message)
                        var_name = var_info['variable']
                        if var_name in telemetry_data:
                            value = telemetry_data[var_name]
                        else:
                            # Default to 0.00 for numeric types, '---' for others
                            var_type = var_info.get('type', 'float')
                            if var_type in ['float', 'int', 'int8', 'int16', 'int32', 'uint8', 'uint16', 'uint32']:
                                value = '0.00'
                            else:
                                value = '---'
                        row_values.append(value)
                    else:
                        # Leave blank for variables from other devices
                        row_values.append('')
                
                # Only write if we have data beyond the timestamp
                if len(row_values) > 3:  # Changed from > 1 to > 3 (date, time, elapsed)
                    # Write row to CSV
                    try:
                        # Open file in append mode if not already open
                        if log_info['file_handle'] is None or log_info['file_handle'].closed:
                            log_info['file_handle'] = open(filepath, 'a', newline='')
                            log_info['csv_writer'] = csv.writer(log_info['file_handle'])
                        
                        log_info['csv_writer'].writerow(row_values)
                        log_info['file_handle'].flush()  # Ensure data is written immediately
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to write to log file {filepath}: {e}")
        except Exception as e:
            print(f"[ERROR] Exception in _on_telemetry_update: {e}")
            import traceback
            traceback.print_exc()
    
    def _log_row_from_current_values(self, filepath: str):
        """
        Logs a row using current values from GUI variables (for timer-based logging).
        """
        try:
            with self.lock:
                log_info = self.active_logs.get(filepath)
                if not log_info:
                    return
                
                # Get timestamp with millisecond accuracy
                now = datetime.datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
                
                # Calculate elapsed time from start in seconds with millisecond precision
                elapsed = (now - log_info['start_time']).total_seconds()
                elapsed_str = f"{elapsed:.3f}"
                
                # Collect current values for all variables
                row_values = [date_str, time_str, elapsed_str]
                
                for var_info in log_info['variables']:
                    gui_var = var_info.get('gui_var')
                    if gui_var:
                        try:
                            # Get current value from GUI variable
                            value = gui_var.get()
                        except:
                            # Default to 0.00 for numeric types, '---' for others
                            var_type = var_info.get('type', 'float')
                            if var_type in ['float', 'int', 'int8', 'int16', 'int32', 'uint8', 'uint16', 'uint32']:
                                value = '0.00'
                            else:
                                value = '---'
                    else:
                        value = '---'
                    row_values.append(value)
                
                # Write row to CSV
                try:
                    # Open file in append mode if not already open
                    if log_info['file_handle'] is None or log_info['file_handle'].closed:
                        log_info['file_handle'] = open(filepath, 'a', newline='')
                        log_info['csv_writer'] = csv.writer(log_info['file_handle'])
                    
                    log_info['csv_writer'].writerow(row_values)
                    log_info['file_handle'].flush()  # Ensure data is written immediately
                    
                except Exception as e:
                    print(f"[ERROR] Failed to write to log file {filepath}: {e}")
        except Exception as e:
            print(f"[ERROR] Exception in _log_row_from_current_values: {e}")
            import traceback
            traceback.print_exc()
    
    def get_active_logs(self) -> Dict[str, dict]:
        """Returns dictionary of active log files and their info."""
        with self.lock:
            return dict(self.active_logs)
    
    def is_variable_being_logged(self, device_name: str, variable_name: str) -> bool:
        """
        Checks if a specific variable is currently being logged.
        """
        with self.lock:
            full_name = f"{device_name}.{variable_name}"
            for log_info in self.active_logs.values():
                for var_info in log_info['variables']:
                    if var_info['full_name'] == full_name:
                        return True
            return False
    
    def get_logs_for_variable(self, device_name: str, variable_name: str) -> List[str]:
        """
        Returns list of log filenames that include this variable.
        """
        with self.lock:
            full_name = f"{device_name}.{variable_name}"
            result = []
            for filepath, log_info in self.active_logs.items():
                for var_info in log_info['variables']:
                    if var_info['full_name'] == full_name:
                        result.append(os.path.basename(filepath))
                        break
            return result
    
    def has_active_logs(self) -> bool:
        """Returns True if any logs are currently active."""
        with self.lock:
            return len(self.active_logs) > 0
    
    def queue_variable(self, device_name: str, variable_name: str):
        """
        Queues a variable for logging.
        """
        with self.lock:
            if device_name not in self.queued_variables:
                self.queued_variables[device_name] = set()
            self.queued_variables[device_name].add(variable_name)
    
    def unqueue_variable(self, device_name: str, variable_name: str):
        """
        Removes a variable from the logging queue.
        """
        with self.lock:
            if device_name in self.queued_variables:
                self.queued_variables[device_name].discard(variable_name)
                # Clean up empty sets
                if not self.queued_variables[device_name]:
                    del self.queued_variables[device_name]
    
    def is_variable_queued(self, device_name: str, variable_name: str) -> bool:
        """
        Checks if a variable is queued for logging.
        """
        with self.lock:
            return device_name in self.queued_variables and variable_name in self.queued_variables[device_name]
    
    def get_queued_variables(self, device_name: str) -> List[str]:
        """
        Returns list of queued variable names for a device.
        """
        with self.lock:
            if device_name not in self.queued_variables:
                return []
            return list(self.queued_variables[device_name])
    
    def start_logging_queued(self, device_name: str, filename: Optional[str] = None) -> tuple:
        """
        Starts logging all queued variables for a device.
        
        Returns:
            (success: bool, message: str, actual_filename: str)
        """
        print(f"[TRACE] start_logging_queued called: device={device_name}, filename={filename}")
        
        # Get queued variables WITHOUT holding the lock (to avoid deadlock with start_logging)
        queued = self.get_queued_variables(device_name)
        print(f"[TRACE] Queued variables: {queued}")
        if not queued:
            return (False, f"No variables queued for {device_name}", None)
        
        # Build full variable names
        variables = [f"{device_name}.{var}" for var in queued]
        print(f"[TRACE] Full variable names: {variables}")
        
        print(f"[TRACE] Calling start_logging with variables: {variables}")
        # Start logging (which will acquire its own lock)
        result = self.start_logging(filename, variables)
        print(f"[TRACE] start_logging returned: {result}")
        return result
    
    def stop_logging_device(self, device_name: str) -> tuple:
        """
        Stops all logging sessions that include variables from this device.
        
        Returns:
            (success: bool, message: str)
        """
        with self.lock:
            files_to_stop = []
            
            # Find all log files that include variables from this device
            for filepath, log_info in self.active_logs.items():
                if device_name in log_info['devices']:
                    files_to_stop.append(filepath)
            
            if not files_to_stop:
                # Not an error - just nothing to stop
                return (True, f"No active logging sessions for {device_name}")
            
            # Stop each log file
            for filepath in files_to_stop:
                self._close_log_file(filepath)
            
            count = len(files_to_stop)
            return (True, f"Stopped {count} logging session(s) for {device_name}")
    
    def cleanup(self):
        """Closes all log files. Should be called on application exit."""
        with self.lock:
            files_to_close = list(self.active_logs.keys())
            for filepath in files_to_close:
                self._close_log_file(filepath)

