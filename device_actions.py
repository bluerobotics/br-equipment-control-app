import subprocess
import sys
import os
import tkinter as tk
from tkinter import messagebox
import comms
import time

# --- Global State ---
simulator_process = None

def get_simulator_path():
    """Gets the absolute path to the simulator script."""
    # Assumes the script is located at <project_root>/st8erboi-simulator/simulator.py
    # This is a bit fragile but works for the current structure.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    return os.path.join(project_root, 'st8erboi-simulator', 'simulator.py')

def run_simulator(parent):
    """Launches the device simulator in a new process."""
    global simulator_process
    simulator_path = get_simulator_path()

    if not os.path.exists(simulator_path):
        messagebox.showerror("Error", f"Simulator script not found at:\n{simulator_path}", parent=parent)
        return

    if simulator_process and simulator_process.poll() is None:
        # messagebox.showinfo("Info", "Simulator is already running.", parent=parent) # Removed as requested
        return

    try:
        # Use the same Python executable that's running this script
        python_executable = sys.executable
        simulator_process = subprocess.Popen([python_executable, simulator_path])
        # messagebox.showinfo("Success", "Device simulator started in a new window.", parent=parent) # Removed as requested
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start simulator:\n{e}", parent=parent)

def scan_for_devices(gui_refs):
    """
    Triggers a filesystem scan for new device modules and then a network scan
    to find all known devices.
    """
    device_manager = gui_refs.get('device_manager')
    if not device_manager:
        comms.log_to_terminal("[ERROR] Device Manager not found during scan.", gui_refs)
        return

    # 1. Scan filesystem for new devices and load them
    newly_loaded = device_manager.scan_and_load_new_devices()

    # 2. If new devices were found, update the UI components
    if newly_loaded:
        # Add the GUI panels for the new devices
        add_panels_func = gui_refs.get('add_device_panels_ref')
        if add_panels_func:
            add_panels_func(newly_loaded)
        
        # Refresh the command reference and syntax highlighting
        refresh_commands_func = gui_refs.get('refresh_commands_ref')
        if refresh_commands_func:
            refresh_commands_func()

    # 3. Trigger a network broadcast to find IPs for all known devices (including new ones)
    comms.discover_devices(gui_refs)
    comms.log_to_terminal("[SYSTEM] Network device scan triggered.", gui_refs)


def show_known_devices(parent, gui_refs):
    """Displays a list of all known (loaded) devices and their current status."""
    device_manager = gui_refs.get('device_manager')
    if not device_manager:
        messagebox.showerror("Error", "Device Manager not found.", parent=parent)
        return

    with comms.devices_lock:
        device_states = device_manager.get_all_device_states()
        if not device_states:
            message = "No device modules are currently loaded."
        else:
            message = "Known Device Modules:\n\n"
            for name, info in device_states.items():
                status = "Connected" if info.get('connected') else "Disconnected"
                ip = info.get('ip', "N/A")
                last_seen_raw = info.get('last_rx', 0)
                last_seen = f"{time.time() - last_seen_raw:.1f}s ago" if last_seen_raw > 0 else "Never"
                
                message += f"- {name.capitalize()}\n"
                message += f"  Status: {status}\n"
                message += f"  IP: {ip}\n"
                message += f"  Last Seen: {last_seen}\n\n"

    messagebox.showinfo("Known Devices", message, parent=parent)

def create_device_commands(parent, gui_refs):
    """
    Creates a dictionary of device-related commands.
    This helps keep the menu creation code clean by preparing the lambdas.
    """
    return {
        'run_simulator': lambda: run_simulator(parent),
        'scan_for_devices': lambda: scan_for_devices(gui_refs),
        'show_known_devices': lambda: show_known_devices(parent, gui_refs)
    }
