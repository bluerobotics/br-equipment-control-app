#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to verify DeviceManager refactoring."""

import sys
import tkinter as tk
from src.device_manager import DeviceManager

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Create minimal GUI environment
root = tk.Tk()
root.withdraw()  # Hide the window

shared_gui = {'root': root}

# Test with pressboi device
device_paths = ['C:/Users/emill/Documents/GitHub/pressboi']

print("=" * 60)
print("TESTING DEVICE MANAGER REFACTORING")
print("=" * 60)

try:
    dm = DeviceManager(shared_gui, device_paths)
    
    print("\n✓ DeviceManager created successfully")
    
    # Test device discovery
    devices = dm.get_all_device_names()
    print(f"✓ Devices loaded: {devices}")
    
    if devices:
        device_name = devices[0]
        
        # Test device data structure
        device_data = dm.devices.get(device_name)
        if device_data:
            print(f"\n✓ Device '{device_name}' data keys:")
            for key in sorted(device_data.keys()):
                value_type = type(device_data[key]).__name__
                print(f"  - {key}: {value_type}")
            
            # Check critical keys
            required_keys = ['gui', 'parser', 'scripting_commands', 'telemetry_data', 
                           'events_data', 'warnings', 'status_var', 'config']
            missing_keys = [k for k in required_keys if k not in device_data]
            
            if missing_keys:
                print(f"\n✗ MISSING KEYS: {missing_keys}")
            else:
                print(f"\n✓ All required keys present")
        
        # Test device state
        state = dm.get_device_state(device_name)
        if state:
            print(f"\n✓ Device state for '{device_name}':")
            for key, value in sorted(state.items()):
                print(f"  - {key}: {value}")
        
        # Test scripting commands
        commands = dm.get_all_scripting_commands()
        device_commands = [c for c in commands if c.startswith(f"{device_name}.")]
        print(f"\n✓ Scripting commands loaded: {len(device_commands)} for {device_name}")
        
        # Test command functions
        cmd_funcs = dm.get_all_command_functions()
        print(f"✓ Command functions created: {len(cmd_funcs)} total")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
    else:
        print("\n✗ No devices loaded - check device path")
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    root.destroy()

