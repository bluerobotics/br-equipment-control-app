"""
Code Generation Package - Developer tools for generating C++ code.

This package contains utilities for generating C++ headers and implementation
files from JSON schema definitions (commands.json, telemetry.json, events.json).

Modules:
- generator: Core code generation functions and GUI
- batch: Batch processing script for generating headers for all devices
"""

from .generator import (
    load_json,
    generate_command_header,
    generate_commands_cpp,
    generate_variables_header,
    generate_variables_cpp,
    generate_events_header,
    generate_events_cpp,
    open_code_generator
)

__all__ = [
    'load_json',
    'generate_command_header',
    'generate_commands_cpp',
    'generate_variables_header',
    'generate_variables_cpp',
    'generate_events_header',
    'generate_events_cpp',
    'open_code_generator'
]

