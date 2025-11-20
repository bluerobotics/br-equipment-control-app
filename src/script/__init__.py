"""
Script Package - Script execution, validation, and GUI.

This package handles all script-related functionality including:
- Script parsing and execution
- Script validation
- Scripting GUI interface
"""

from .processor import ScriptRunner, SCRIPT_COMMANDS
from .validator import validate_single_line, validate_script
from .gui import create_scripting_interface, load_recent_files, RECENT_FILES_PATH

__all__ = [
    'ScriptRunner',
    'SCRIPT_COMMANDS',
    'validate_single_line',
    'validate_script',
    'create_scripting_interface',
    'load_recent_files',
    'RECENT_FILES_PATH'
]

