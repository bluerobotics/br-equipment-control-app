"""
System logger that captures all terminal output and logs it to a file.
Tracks file size and prompts user when exceeding 100MB.
"""

import os
import sys
import datetime
import threading
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import messagebox

# Maximum log file size (100MB)
MAX_LOG_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

class SystemLogger:
    """Captures all terminal output and logs it to a file."""
    
    def __init__(self, logs_dir: Optional[Path] = None, gui_refs: Optional[dict] = None):
        """
        Initialize the system logger.
        
        Args:
            logs_dir: Directory to store log files. If None, uses default location.
            gui_refs: Dictionary of GUI references (for terminal output). Can be set later.
        """
        self.logs_dir = logs_dir or self._get_default_logs_dir()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session log file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = self.logs_dir / f"session_{timestamp}.log"
        
        self.log_file = None
        self.file_size = 0
        self.logging_enabled = True
        self.size_warning_shown = False  # Track if we've already shown the size warning
        self.lock = threading.Lock()
        self._gui_refs = gui_refs  # Store GUI references for terminal output
        
        # Save original stdout/stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create log file and start capturing
        self._start_logging()
    
    def set_gui_refs(self, gui_refs: dict):
        """Set GUI references (for terminal output) after logger initialization."""
        self._gui_refs = gui_refs
    
    def _get_default_logs_dir(self) -> Path:
        """Get the default logs directory."""
        try:
            if sys.platform == 'win32':
                base_dir = Path(os.environ.get('APPDATA', Path.home() / '.br-equipment-control-app'))
                logs_dir = base_dir / 'BR Equipment Control' / 'logs'
            elif sys.platform == 'darwin':
                logs_dir = Path.home() / 'Library' / 'Application Support' / 'BR Equipment Control' / 'logs'
            else:
                base_dir = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
                logs_dir = base_dir / 'br-equipment-control-app' / 'logs'
        except Exception:
            # Fallback to logs directory in app folder
            logs_dir = Path(__file__).parent.parent / 'logs'
        
        return logs_dir
    
    def _start_logging(self):
        """Start logging by opening the log file and redirecting stdout/stderr."""
        try:
            self.log_file = open(self.log_file_path, 'w', encoding='utf-8')
            self.file_size = 0
            
            # Write header
            header = f"=== BR Equipment Control App Session Log ===\n"
            header += f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += f"Log file: {self.log_file_path}\n"
            header += f"{'=' * 60}\n\n"
            self._write_to_file(header)
            
            # Redirect stdout/stderr
            sys.stdout = LogWriter(self, self.original_stdout, is_error=False)
            sys.stderr = LogWriter(self, self.original_stderr, is_error=True)
            
        except Exception as e:
            print(f"[SYSTEM LOGGER ERROR] Failed to start logging: {e}", file=self.original_stderr)
    
    def _write_to_file(self, text: str):
        """Write text to the log file, checking size limits."""
        if not self.logging_enabled or not self.log_file:
            return
        
        with self.lock:
            try:
                # Check file size (only prompt once)
                if self.file_size >= MAX_LOG_SIZE_BYTES and not self.size_warning_shown:
                    if self.logging_enabled:
                        self._prompt_user_about_size()
                        self.size_warning_shown = True
                    if not self.logging_enabled:
                        return  # User chose to stop logging
                
                # Write to file
                self.log_file.write(text)
                self.log_file.flush()
                self.file_size += len(text.encode('utf-8'))
                
            except Exception as e:
                print(f"[SYSTEM LOGGER ERROR] Failed to write to log file: {e}", file=self.original_stderr)
    
    def _prompt_user_about_size(self):
        """Prompt user when log file exceeds 1GB."""
        if not self.logging_enabled:
            return
        
        try:
            # Create a simple Tkinter root if it doesn't exist
            root = tk._default_root
            if root is None:
                root = tk.Tk()
                root.withdraw()  # Hide the window
            
            response = messagebox.askyesno(
                "System Log File Size Warning",
                f"The system log file has exceeded 100MB.\n\n"
                f"File: {self.log_file_path}\n"
                f"Size: {self.file_size / (1024**2):.2f} MB\n\n"
                f"Would you like to continue logging?\n\n"
                f"(Click 'Yes' to continue, 'No' to stop logging)",
                icon='warning'
            )
            
            if not response:
                self.logging_enabled = False
                self._write_to_file(f"\n[SYSTEM LOGGER] Logging stopped by user at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        except Exception as e:
            # If GUI is not available, disable logging
            print(f"[SYSTEM LOGGER ERROR] Could not prompt user: {e}", file=self.original_stderr)
            self.logging_enabled = False
    
    def log_message(self, message: str, is_error: bool = False):
        """
        Log a message directly (used by log_to_terminal).
        
        Args:
            message: The message to log
            is_error: Whether this is an error message
        """
        if not self.logging_enabled:
            return
        
        # Add timestamp if not already present (check for proper timestamp format)
        import re
        has_timestamp = bool(re.match(r'^\[\d{2}:\d{2}:\d{2}\.\d+', message))
        
        if not has_timestamp:
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S.%f]")[:-3]
            formatted_message = f"{timestamp} {message}\n"
        else:
            formatted_message = f"{message}\n" if not message.endswith('\n') else message
        
        self._write_to_file(formatted_message)
    
    def stop_logging(self):
        """Stop logging and restore stdout/stderr."""
        with self.lock:
            if self.log_file:
                footer = f"\n{'=' * 60}\n"
                footer += f"Session ended: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                footer += f"Final file size: {self.file_size / (1024**2):.2f} MB\n"
                footer += f"{'=' * 60}\n"
                try:
                    self.log_file.write(footer)
                    self.log_file.flush()
                    self.log_file.close()
                except Exception:
                    pass
                self.log_file = None
            
            # Restore stdout/stderr
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
    
    def get_log_file_path(self) -> Path:
        """Get the path to the current log file."""
        return self.log_file_path


class LogWriter:
    """Wrapper around stdout/stderr that adds timestamps and logs to file."""
    
    def __init__(self, logger: SystemLogger, original_stream, is_error: bool = False):
        self.logger = logger
        self.original_stream = original_stream
        self.is_error = is_error
    
    def write(self, text: str):
        """Write text with timestamp to both original stream, terminal, and log file."""
        # Always write to original stream first (preserves original behavior)
        if self.original_stream is not None:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except (AttributeError, OSError):
                pass  # Stream not available (e.g., running as GUI app without console)
        
        # Log to file (preserve newlines and whitespace)
        # Strip trailing newline for processing, we'll add it back
        text_stripped = text.rstrip('\n\r')
        
        # Skip empty lines (just whitespace/newlines)
        if not text_stripped:
            return
        
        # Check if text already has a timestamp prefix (format: [HH:MM:SS.mmm)
        # Must have time format like [16:48:20.123
        import re
        has_timestamp = bool(re.match(r'^\[\d{2}:\d{2}:\d{2}\.\d+', text_stripped))
        
        # Check if message already has a tag like [SYSTEM], [SERIAL], [STATUS], etc.
        has_tag = bool(re.match(r'^\[[A-Z_]+\]', text_stripped))
        
        if not has_timestamp:
            # Add timestamp
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S.%f]")[:-3]
            
            # Only add [python] prefix if message doesn't have any tag
            if has_tag:
                # Has a tag like [SYSTEM], [SERIAL], etc. - don't add [python]
                formatted_text = f"{timestamp} {text_stripped}\n"
            elif text_stripped.startswith('[python]'):
                # Already has [python], just add timestamp
                formatted_text = f"{timestamp} {text_stripped}\n"
            else:
                # No tag at all - add both timestamp and [python] prefix
                formatted_text = f"{timestamp} [python] {text_stripped}\n"
            # Also send to terminal widget if available
            self._send_to_terminal(formatted_text)
        else:
            # Already has timestamp, just ensure it ends with newline
            formatted_text = text_stripped + '\n' if not text.endswith('\n') else text
        
        # Log to file
        self.logger._write_to_file(formatted_text)
    
    def _send_to_terminal(self, message: str):
        """Send message to terminal widget if available, checking Python console filter."""
        try:
            # Try to get the terminal callback from the logger's gui_refs if available
            if hasattr(self.logger, '_gui_refs') and self.logger._gui_refs:
                gui_refs = self.logger._gui_refs
                
                # Check if Python console messages should be shown
                show_python_var = gui_refs.get('show_python_console_var')
                if show_python_var and not show_python_var.get():
                    return  # Python console is disabled, don't show this message
                
                terminal_cb = gui_refs.get('terminal_cb')
                gui_queue = gui_refs.get('gui_queue')
                if terminal_cb and gui_queue:
                    gui_queue.put((terminal_cb, (message,), {}))
        except Exception:
            pass  # Ignore errors - terminal might not be available yet
    
    def flush(self):
        """Flush the original stream."""
        if self.original_stream is not None:
            try:
                self.original_stream.flush()
            except (AttributeError, OSError):
                pass  # Stream not available
    
    def __getattr__(self, name):
        """Delegate other attributes to original stream."""
        return getattr(self.original_stream, name)


# Global logger instance
_system_logger: Optional[SystemLogger] = None


def initialize_system_logger(logs_dir: Optional[Path] = None) -> SystemLogger:
    """
    Initialize the global system logger.
    
    Args:
        logs_dir: Directory to store log files. If None, uses default location.
    
    Returns:
        The initialized SystemLogger instance.
    """
    global _system_logger
    if _system_logger is None:
        _system_logger = SystemLogger(logs_dir)
    return _system_logger


def get_system_logger() -> Optional[SystemLogger]:
    """Get the global system logger instance."""
    return _system_logger


def stop_system_logger():
    """Stop the global system logger."""
    global _system_logger
    if _system_logger:
        _system_logger.stop_logging()
        _system_logger = None

