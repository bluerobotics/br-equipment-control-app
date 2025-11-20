"""
UI Package - User interface components for the Equipment Control App.

This package contains all GUI-related code including the main application
window, panels, dialogs, and UI utilities.
"""

from .app import MainApplication, CollapsiblePanel
from .status_panel import create_status_bar

__all__ = [
    'MainApplication',
    'CollapsiblePanel',
    'create_status_bar'
]

