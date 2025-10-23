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
    generate_command_parser_header,
    generate_command_parser_cpp
)

def generate_headers_for_device(device_name):
    """Generate headers for a single device."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    device_dir = os.path.join(script_dir, 'devices', device_name)
    
    commands_json_path = os.path.join(device_dir, 'commands.json')
    telemetry_json_path = os.path.join(device_dir, 'telemetry.json')
    
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
        
        # Generate all files
        commands_h = generate_command_header(commands, device_name)
        responses_h = generate_responses_header(telemetry, device_name)
        parser_h = generate_command_parser_header(commands, device_name)
        parser_cpp = generate_command_parser_cpp(commands, device_name)
        
        # Save all files
        commands_h_path = os.path.join(device_dir, 'commands.h')
        responses_h_path = os.path.join(device_dir, 'responses.h')
        parser_h_path = os.path.join(device_dir, 'command_parser.h')
        parser_cpp_path = os.path.join(device_dir, 'command_parser.cpp')
        
        with open(commands_h_path, 'w', encoding='utf-8') as f:
            f.write(commands_h)
        
        with open(responses_h_path, 'w', encoding='utf-8') as f:
            f.write(responses_h)
        
        with open(parser_h_path, 'w', encoding='utf-8') as f:
            f.write(parser_h)
        
        with open(parser_cpp_path, 'w', encoding='utf-8') as f:
            f.write(parser_cpp)
        
        print(f"  [OK] Generated 4 files for {device_name}")
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

