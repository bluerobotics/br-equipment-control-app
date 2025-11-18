"""
Connection Configuration Manager

Saves and loads device connection preferences (USB vs Network).
"""

import json
import os
from pathlib import Path

CONFIG_FILE = Path.home() / '.br_equipment_control' / 'connections.json'


def ensure_config_dir():
    """Ensures the config directory exists."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_connection_config(device_name, connection_method, serial_port=None):
    """
    Saves the connection configuration for a device.
    
    Args:
        device_name (str): Name of the device
        connection_method (str): 'network' or 'usb'
        serial_port (str): Serial port name if USB, None otherwise
    """
    ensure_config_dir()
    
    # Load existing config
    config = load_all_connection_configs()
    
    # Update device config
    config[device_name] = {
        'connection_method': connection_method,
        'serial_port': serial_port
    }
    
    # Save to file
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving connection config: {e}")


def load_connection_config(device_name):
    """
    Loads the connection configuration for a device.
    
    Args:
        device_name (str): Name of the device
        
    Returns:
        dict or None: {'connection_method': 'usb'/'network', 'serial_port': 'COM10' or None}
    """
    config = load_all_connection_configs()
    return config.get(device_name)


def load_all_connection_configs():
    """
    Loads all connection configurations.
    
    Returns:
        dict: {device_name: {'connection_method': ..., 'serial_port': ...}}
    """
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading connection config: {e}")
        return {}


def clear_connection_config(device_name):
    """
    Clears the connection configuration for a device.
    
    Args:
        device_name (str): Name of the device
    """
    ensure_config_dir()
    config = load_all_connection_configs()
    
    if device_name in config:
        del config[device_name]
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error clearing connection config: {e}")

