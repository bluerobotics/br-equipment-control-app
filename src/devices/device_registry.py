"""
Device Registry - Handles device discovery, loading, and module management.

This module is responsible for:
- Scanning device paths and discovering devices
- Loading device definitions (JSON configs, Python modules)
- Managing device data structures (commands, telemetry, events)
- Reloading device modules when definitions change
"""

import os
import importlib
import importlib.util
import sys
import json
import tkinter as tk


class DeviceRegistry:
    """Manages device discovery and loading from configured paths."""
    
    def __init__(self, device_paths=None):
        """
        Initialize DeviceRegistry.
        
        Args:
            device_paths: List of device folder paths to scan
        """
        self.devices = {}  # device_name -> device_data dict
        self.discovery_logs = []
        self.device_paths = device_paths if device_paths and isinstance(device_paths, list) else []
    
    def log(self, message):
        """Log a discovery message."""
        print(f"[python] {message}")
        self.discovery_logs.append(message)
    
    def get_discovery_logs(self):
        """Get all discovery log messages."""
        return self.discovery_logs.copy()
    
    def _load_module_from_path(self, device_name, module_name, device_path):
        """
        Load a Python module from a specific file path.
        Returns the module if successful, None otherwise.
        """
        module_file = os.path.join(device_path, f"{module_name}.py")
        if not os.path.exists(module_file):
            return None
        
        try:
            # Create a unique module name to avoid conflicts
            full_module_name = f"devices.{device_name}.{module_name}"
            
            # Load the module from file
            spec = importlib.util.spec_from_file_location(full_module_name, module_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[full_module_name] = module
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            self.log(f"Error loading {module_name} for {device_name}: {e}")
        
        return None
    
    def discover_devices(self):
        """
        Loads device modules from explicitly configured device paths.
        Each path should be a device root folder (e.g., my-device/).
        The code will look for a definition/ subfolder or use the root if it contains definition files.
        Device name is read from config.json in the definition folder.
        """
        self.log("Loading devices from configured paths...")
        
        # Clear existing devices to pick up deletions/renames
        self.devices.clear()
        
        # Clear firmware config cache when devices are rediscovered
        try:
            from ..clearcore_firmware import clear_firmware_config_cache
            clear_firmware_config_cache()
        except Exception:
            pass  # Ignore if firmware module not available
        
        # Track device names we've already loaded to avoid duplicates
        loaded_device_names = set()
        
        # Iterate over all device paths (each should be a device root folder)
        for device_root_path in self.device_paths:
            if not os.path.isdir(device_root_path):
                self.log(f"Device path not found at '{device_root_path}'")
                continue
            
            # Find definition folder (could be definition/ subfolder or root itself)
            definition_path = os.path.join(device_root_path, 'definition')
            if not os.path.isdir(definition_path):
                # Check if root contains definition files (backward compatibility)
                if os.path.exists(os.path.join(device_root_path, 'config.json')) or \
                   os.path.exists(os.path.join(device_root_path, 'commands.json')):
                    definition_path = device_root_path
                else:
                    self.log(f"No definition folder found at '{device_root_path}/definition' and no definition files in root")
                    continue
            
            # Read device name from config.json
            config_path = os.path.join(definition_path, 'config.json')
            device_name = None
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        device_name = config.get('device_name') or config.get('name')
                except Exception as e:
                    self.log(f"Failed to read config.json from '{definition_path}': {e}")
            
            # Fallback: infer from root folder name
            if not device_name:
                device_name = os.path.basename(device_root_path)
                self.log(f"Device name not found in config.json, using '{device_name}'")
            
            if device_name in loaded_device_names:
                self.log(f"Device '{device_name}' already loaded, skipping duplicate at '{device_root_path}'")
                continue
            
            # Load the device
            if self._load_device_from_path(device_name, definition_path):
                loaded_device_names.add(device_name)
                self.log(f"Successfully loaded device module: {device_name}")
    
    def _load_device_from_path(self, device_name, definition_path):
        """
        Load a device from its definition path.
        Returns True if successful, False otherwise.
        """
        try:
            # Load scripting commands from JSON
            scripting_commands = {}
            json_path = os.path.join(definition_path, 'commands.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    scripting_commands = json.load(f)
            
            # Load telemetry schema
            telemetry_data = {}
            schema_path = os.path.join(definition_path, 'telemetry.json')
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    telemetry_data = json.load(f)
            
            # Load events
            events_data = {}
            events_path = os.path.join(definition_path, 'events.json')
            if os.path.exists(events_path):
                with open(events_path, 'r') as f:
                    events_data = json.load(f)
            
            # Load Python modules (gui, simulator)
            gui_module = self._load_module_from_path(device_name, 'gui', definition_path)
            simulator_module = self._load_module_from_path(device_name, 'simulator', definition_path)
            parser_module = self._load_module_from_path(device_name, 'parser', definition_path)
            
            # Load warnings from JSON (always from definition folder)
            warnings_data = {}
            warnings_path = os.path.join(definition_path, 'warnings.json')
            if os.path.exists(warnings_path):
                with open(warnings_path, 'r') as f:
                    warnings_data = json.load(f)
            
            # Store device data (use old key names for backward compatibility)
            self.devices[device_name] = {
                'name': device_name,
                'path': definition_path,
                'gui': gui_module,  # Use 'gui' not 'gui_module' for compatibility
                'parser': parser_module,
                'simulator': simulator_module,
                'scripting_commands': scripting_commands,
                'telemetry_data': telemetry_data,
                'events_data': events_data,
                'warnings': warnings_data,
                'config': {},  # Keep for consistent structure
                'status_var': None,  # Will be created during GUI init
            }
            
            return True
            
        except Exception as e:
            self.log(f"Failed to load device '{device_name}' from '{definition_path}': {e}")
            return False
    
    def reload_device_modules(self):
        """Reload all device modules (for development)."""
        for device_name in list(self.devices.keys()):
            self.reload_single_device(device_name)
    
    def reload_single_device(self, device_name):
        """Reload a single device's definition files."""
        if device_name not in self.devices:
            self.log(f"Device '{device_name}' not found for reload")
            return False
        
        device_path = self.devices[device_name]['path']
        
        # Reload commands.json
        json_path = os.path.join(device_path, 'commands.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                self.devices[device_name]['scripting_commands'] = json.load(f)
                self.log(f"Reloaded commands.json for {device_name}")
        
        # Reload telemetry.json
        schema_path = os.path.join(device_path, 'telemetry.json')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                self.devices[device_name]['telemetry_data'] = json.load(f)
                self.log(f"Reloaded telemetry.json for {device_name}")
        
        # Reload events.json
        events_path = os.path.join(device_path, 'events.json')
        if os.path.exists(events_path):
            with open(events_path, 'r') as f:
                self.devices[device_name]['events_data'] = json.load(f)
                self.log(f"Reloaded events.json for {device_name}")
        
        # Reload warnings.json
        warnings_path = os.path.join(device_path, 'warnings.json')
        if os.path.exists(warnings_path):
            with open(warnings_path, 'r') as f:
                self.devices[device_name]['warnings'] = json.load(f)
                self.log(f"Reloaded warnings.json for {device_name}")
        
        return True
    
    def get_device_modules(self):
        """Get all loaded device modules."""
        return self.devices.copy()
    
    def get_all_device_names(self):
        """Get list of all loaded device names."""
        return list(self.devices.keys())
    
    def get_device_config(self, device_name):
        """
        Returns the config.json data for a device.
        
        Args:
            device_name: Name of the device
            
        Returns:
            dict: Config data or None if not found
        """
        if device_name not in self.devices:
            return None
        
        device_path = self.devices[device_name]['path']
        
        # Check both definition_path/config.json and definition_path/../config.json
        config_path = os.path.join(device_path, 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Failed to read config.json for {device_name}: {e}")
        
        return None

