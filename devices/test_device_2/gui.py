"""
GUI module for test_device_2 device.

This module contains device-specific GUI components and panels.
"""

import tkinter as tk
from tkinter import ttk
import theme

def create_device_panel(parent, device_manager):
    """
    Create and return the device-specific control panel.
    
    Args:
        parent: Parent tkinter widget
        device_manager: Reference to the DeviceManager instance
    
    Returns:
        ttk.Frame: The device control panel
    """
    frame = ttk.Frame(parent, style='TFrame')
    
    # Add your device-specific GUI here
    label = ttk.Label(frame, 
                     text=f"TEST_DEVICE_2 Control Panel",
                     font=theme.FONT_LARGE_BOLD,
                     foreground=theme.PRIMARY_ACCENT)
    label.pack(pady=20)
    
    # TODO: Add device-specific controls
    
    return frame
