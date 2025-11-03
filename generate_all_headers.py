"""
Script to generate C++ files for all devices.
Run this script whenever you update commands.json or telemetry.json files.
"""

import os
import sys
from code_generator import (
    load_json, 
    generate_command_header, 
    generate_responses_header,
    generate_commands_cpp,
    generate_variables_header,
    generate_variables_cpp,
    generate_events_header,
    generate_events_cpp
)

def generate_headers_for_device(device_name):
    """Generate headers for a single device."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    device_dir = os.path.join(script_dir, 'devices', device_name)
    
    commands_json_path = os.path.join(device_dir, 'commands.json')
    telemetry_json_path = os.path.join(device_dir, 'telemetry.json')
    events_json_path = os.path.join(device_dir, 'events.json')
    
    # Check if files exist
    if not os.path.exists(commands_json_path):
        print(f"  [SKIP] Skipping {device_name}: commands.json not found")
        return False
    
    if not os.path.exists(telemetry_json_path):
        print(f"  [SKIP] Skipping {device_name}: telemetry.json not found")
        return False
    
    try:
        # Load JSON files
        commands = load_json(commands_json_path)
        telemetry = load_json(telemetry_json_path)
        
        # Load events.json if it exists (optional)
        events = {}
        if os.path.exists(events_json_path):
            events = load_json(events_json_path)
        
        # Generate all files
        commands_h = generate_command_header(commands, device_name)
        responses_h = generate_responses_header(telemetry, device_name)
        commands_cpp = generate_commands_cpp(commands, device_name)
        variables_h = generate_variables_header(telemetry, device_name)
        variables_cpp = generate_variables_cpp(telemetry, device_name)
        events_h = generate_events_header(events, device_name)
        events_cpp = generate_events_cpp(events, device_name)
        
        # Create generated/ subfolder
        gen_dir = os.path.join(device_dir, 'generated')
        os.makedirs(gen_dir, exist_ok=True)
        
        # Save all files to generated/ folder
        commands_h_path = os.path.join(gen_dir, 'commands.h')
        responses_h_path = os.path.join(gen_dir, 'responses.h')
        commands_cpp_path = os.path.join(gen_dir, 'commands.cpp')
        variables_h_path = os.path.join(gen_dir, 'variables.h')
        variables_cpp_path = os.path.join(gen_dir, 'variables.cpp')
        events_h_path = os.path.join(gen_dir, 'events.h')
        events_cpp_path = os.path.join(gen_dir, 'events.cpp')
        
        with open(commands_h_path, 'w', encoding='utf-8') as f:
            f.write(commands_h)
        
        with open(responses_h_path, 'w', encoding='utf-8') as f:
            f.write(responses_h)
        
        with open(commands_cpp_path, 'w', encoding='utf-8') as f:
            f.write(commands_cpp)
        
        with open(variables_h_path, 'w', encoding='utf-8') as f:
            f.write(variables_h)
        
        with open(variables_cpp_path, 'w', encoding='utf-8') as f:
            f.write(variables_cpp)
        
        with open(events_h_path, 'w', encoding='utf-8') as f:
            f.write(events_h)
        
        with open(events_cpp_path, 'w', encoding='utf-8') as f:
            f.write(events_cpp)
        
        print(f"  [OK] Generated 7 files for {device_name} in generated/ folder")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error generating headers for {device_name}: {e}")
        return False

def main():
    """Generate headers for all devices."""
    print("=" * 80)
    print("Generating C++ Headers for All Devices")
    print("=" * 80)
    print()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    devices_dir = os.path.join(script_dir, 'devices')
    
    # Find all device directories
    devices = []
    for item in os.listdir(devices_dir):
        item_path = os.path.join(devices_dir, item)
        if os.path.isdir(item_path) and not item.startswith('_'):
            devices.append(item)
    
    if not devices:
        print("No device directories found!")
        return
    
    print(f"Found {len(devices)} device(s): {', '.join(devices)}")
    print()
    
    # Generate headers for each device
    success_count = 0
    for device in devices:
        if generate_headers_for_device(device):
            success_count += 1
    
    print()
    print("=" * 80)
    print(f"Complete! Generated headers for {success_count}/{len(devices)} device(s)")
    print("=" * 80)

if __name__ == '__main__':
    main()

