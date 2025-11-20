"""
Application Configuration Management

Handles loading, saving, and managing application configuration including
device paths, window geometry, and other persistent settings.
"""

import json
import os
import sys
from pathlib import Path


def _resolve_config_file():
    """Determine a writable path for the app configuration file."""
    fallback_dir = Path.home() / '.br-equipment-control-app'

    try:
        if sys.platform == 'win32':
            base_dir = Path(os.environ.get('APPDATA', fallback_dir))
            config_dir = base_dir / 'BR Equipment Control'
        elif sys.platform == 'darwin':
            config_dir = Path.home() / 'Library' / 'Application Support' / 'BR Equipment Control'
        else:
            base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
            config_dir = base_dir / 'br-equipment-control-app'
    except Exception as e:
        print(f"Warning determining config directory: {e}")
        config_dir = fallback_dir

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning creating config directory at {config_dir}: {e}")
        config_dir = fallback_dir
        config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir / 'app_config.json'


CONFIG_FILE = _resolve_config_file()


def load_config():
    """Load the persisted application configuration."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open('r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning reading config file: {e}")
    return {}


def save_config(config):
    """Persist the application configuration safely."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open('w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def get_device_paths():
    """Get the list of device folder paths from config."""
    config = load_config()
    device_paths = config.get('device_paths', [])
    
    # Filter out invalid paths
    valid_paths = [p for p in device_paths if os.path.isdir(p)]
    
    # If we had invalid paths, save the cleaned list
    if len(valid_paths) != len(device_paths):
        config['device_paths'] = valid_paths
        save_config(config)
    
    return valid_paths


def add_device_path(device_path):
    """Add a device path to the config."""
    try:
        config = load_config()
        device_paths = config.get('device_paths', [])
        
        # Normalize path and add if not already present
        normalized_path = os.path.normpath(device_path)
        if normalized_path not in device_paths:
            device_paths.append(normalized_path)
            config['device_paths'] = device_paths
            save_config(config)
        return True
    except Exception as e:
        print(f"Error adding device path: {e}")
        return False


def remove_device_path(device_path):
    """Remove a device path from the config."""
    try:
        config = load_config()
        device_paths = config.get('device_paths', [])
        
        # Normalize the path to remove - try both absolute and relative comparisons
        # First normalize as-is (matching how add_device_path stores it)
        normalized_path = os.path.normpath(os.path.normcase(device_path))
        
        # Also get absolute version for comparison
        abs_normalized_path = os.path.normpath(os.path.normcase(os.path.abspath(device_path)))
        
        # Try to find and remove the path
        found = False
        for i, stored_path in enumerate(device_paths):
            # Normalize stored path both ways
            normalized_stored = os.path.normpath(os.path.normcase(stored_path))
            abs_normalized_stored = os.path.normpath(os.path.normcase(os.path.abspath(stored_path)))
            
            # Match if either normalized version matches
            if normalized_stored == normalized_path or abs_normalized_stored == abs_normalized_path:
                device_paths.pop(i)
                found = True
                break
        
        if found:
            config['device_paths'] = device_paths
            save_config(config)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error removing device path: {e}")
        import traceback
        traceback.print_exc()
        return False


# Keep old function for backward compatibility (deprecated)
def get_devices_path():
    """Deprecated: Get first device path from list. Use get_device_paths() instead."""
    device_paths = get_device_paths()
    if device_paths:
        return device_paths[0]
    return None


def get_font_family():
    """Get the preferred font family from config."""
    config = load_config()
    return config.get('font_family', None)  # None means use default


def set_font_family(font_family):
    """Save the preferred font family to config."""
    try:
        config = load_config()
        config['font_family'] = font_family
        save_config(config)
        return True
    except Exception as e:
        print(f"Error saving font family: {e}")
        return False


def get_font_size():
    """Get the preferred font size from config."""
    config = load_config()
    return config.get('font_size', 11)  # Default to 11pt


def set_font_size(font_size):
    """Save the preferred font size to config."""
    try:
        config = load_config()
        config['font_size'] = font_size
        save_config(config)
        return True
    except Exception as e:
        print(f"Error saving font size: {e}")
        return False

