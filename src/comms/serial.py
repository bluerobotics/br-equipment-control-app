"""
USB Serial Communication Module for BR Equipment Control App

This module handles USB serial communication with devices as an alternative
to network-based communication. It provides device discovery, message parsing,
and command sending over serial ports.
"""

import serial
import serial.tools.list_ports
import threading
import time
import datetime
from queue import Queue, Empty

# Constants
SERIAL_BAUD_RATE = 9600
SERIAL_TIMEOUT = 0.1
DEVICE_POLL_INTERVAL = 0.5

# Global state
serial_connections = {}  # port_name -> {serial, thread, queue, device_key}
serial_lock = threading.Lock()


def list_serial_ports():
    """
    Returns a list of available serial ports.
    
    Returns:
        list: List of (port, description) tuples
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]


def detect_device_on_port(port_name, timeout=2.0, device_manager=None):
    """
    Attempts to detect what device is on a serial port by listening for messages.
    Uses USB identifiers from device configs to match devices.
    
    Args:
        port_name (str): The serial port to check
        timeout (float): How long to wait for device identification
        device_manager: Device manager instance to get USB identifiers from device configs
        
    Returns:
        str or None: Device key if detected, None otherwise
    """
    try:
        ser = serial.Serial(port_name, SERIAL_BAUD_RATE, timeout=SERIAL_TIMEOUT)
        start_time = time.time()
        
        # Build identifier map from device configs
        identifier_map = {}
        if device_manager:
            for device_name in device_manager.get_all_device_names():
                config = device_manager.get_device_config(device_name)
                if config and 'usb_identifiers' in config:
                    for identifier in config['usb_identifiers']:
                        identifier_map[identifier.upper()] = device_name
        
        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                line_upper = line.upper()
                
                # Check against all registered USB identifiers
                for identifier, device_name in identifier_map.items():
                    if identifier in line_upper:
                        ser.close()
                        return device_name
            
            time.sleep(0.1)
        
        ser.close()
        return None
    except Exception as e:
        print(f"Error detecting device on {port_name}: {e}")
        return None


def serial_listener_thread(port_name, device_key, message_callback, gui_refs, device_manager, silent=False):
    """
    Background thread that reads from a serial port and processes messages.
    
    Args:
        port_name (str): The serial port to read from
        device_key (str): The device key (e.g. 'device')
        message_callback (callable): Function to call with received messages (device_key, message, gui_refs, device_manager)
        gui_refs (dict): GUI references
        device_manager: DeviceManager instance
        silent (bool): If True, suppress error messages (for hotplug attempts)
    """
    try:
        ser = serial.Serial(port_name, SERIAL_BAUD_RATE, timeout=SERIAL_TIMEOUT)
        
        # Toggle DTR to reset the USB connection state
        # This helps clear any stale state from previous sessions
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.2)
        
        # Aggressively flush/drain any stale data in the buffers from previous session
        # This is critical to prevent 58-second delays from queued data
        ser.reset_input_buffer()  # Clear input (RX) buffer
        ser.reset_output_buffer()  # Clear output (TX) buffer
        
        # Read and discard any pending data (drain the pipe)
        ser.timeout = 0.01  # Very short timeout for draining
        start_drain = time.time()
        bytes_drained = 0
        while time.time() - start_drain < 2.0:  # Drain for up to 2 seconds
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                bytes_drained += len(chunk)
            else:
                break  # No more data
        
        if bytes_drained > 0:
            print(f"[SERIAL] Drained {bytes_drained} stale bytes from {port_name}")
        
        # Restore normal timeout
        ser.timeout = SERIAL_TIMEOUT
        
        # One more flush after draining
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        if not silent:
            print(f"[SERIAL] Connected to {device_key} on {port_name}")
        
        # Store the serial object in the connection info
        with serial_lock:
            if port_name in serial_connections:
                serial_connections[port_name]['serial'] = ser
        
        # Debug: Track if we're receiving any data
        last_data_time = time.time()
        has_received_data = False
        
        while True:
            with serial_lock:
                if port_name not in serial_connections:
                    # Thread was stopped
                    break
            
            # Check if USB port is still physically connected
            try:
                if not ser.is_open:
                    print(f"[SERIAL] Port {port_name} closed unexpectedly (USB disconnected)")
                    break
            except Exception as e:
                print(f"[SERIAL] Error checking port status for {port_name}: {e}")
                break
            
            # Update last data time
            now = time.time()
            if has_received_data:
                last_data_time = now
            
            # Check for timeout if we've received data before
            # This detects when USB cable is unplugged (no more data coming)
            if has_received_data and (now - last_data_time) > 3.0:
                print(f"[SERIAL] No data received from {port_name} for 3 seconds (USB likely disconnected)")
                break
                    
            # Read ALL available lines, not just one per loop iteration
            try:
                in_waiting = ser.in_waiting
            except Exception as e:
                print(f"[SERIAL] Error reading from {port_name}: {e} (USB likely disconnected)")
                break
            
            while in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        has_received_data = True
                        last_data_time = now
                        
                        # Check if device is configured for USB before processing messages
                        # If network is configured, read and discard to drain the buffer
                        should_process = True  # Default to processing
                        if device_manager:
                            try:
                                device_state = device_manager.get_device_state(device_key)
                                if device_state and device_state.get('connection_method') != 'usb':
                                    # Network is configured, don't process USB messages
                                    should_process = False
                            except Exception:
                                # If there's any error checking state, default to processing
                                pass
                        
                        if not should_process:
                            # Drain the buffer but don't process the message
                            in_waiting = ser.in_waiting  # Check for more data
                            continue
                        
                        message_callback(device_key, line, gui_refs, device_manager)
                    
                    # Check for more data
                    try:
                        in_waiting = ser.in_waiting
                    except Exception:
                        # Port likely disconnected
                        break
                        
                except Exception as e:
                    print(f"[SERIAL ERROR] {port_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    break  # Exit the while loop on error
            
            time.sleep(0.01)  # Small delay to prevent CPU hogging
        
        # Close the serial port
        try:
            ser.close()
        except Exception:
            pass  # Port might already be closed
        
        print(f"[SERIAL] Disconnected from {device_key} on {port_name}")
        
        # Update device state to disconnected
        if device_manager:
            from .network import devices_lock
            with devices_lock:
                device_manager.update_device_state(device_key, {
                    "connected": False
                })
        
        # Log disconnect to GUI terminal
        if gui_refs:
            from src.logging import log_to_terminal
            log_to_terminal(f"{device_key.capitalize()} Disconnected", gui_refs)
            
            # Hide the panel and reset variables
            reset_and_hide_fn = gui_refs.get('reset_and_hide_panel')
            if reset_and_hide_fn:
                gui_queue = gui_refs.get('gui_queue')
                if gui_queue:
                    gui_queue.put((reset_and_hide_fn, (device_key,), {}))
                else:
                    reset_and_hide_fn(device_key)
            
            # Update searching panel visibility
            from .network import update_searching_panel_visibility
            gui_queue = gui_refs.get('gui_queue')
            if gui_queue:
                gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
            else:
                update_searching_panel_visibility(gui_refs)
        
        # Clean up serial connection entry
        with serial_lock:
            if port_name in serial_connections:
                del serial_connections[port_name]
        
    except Exception as e:
        if not silent:
            print(f"[SERIAL ERROR] Failed to connect to {port_name}: {e}")
        with serial_lock:
            if port_name in serial_connections:
                del serial_connections[port_name]
        
        # Update device state to reflect connection failure
        if device_manager:
            # Only update if the device hasn't already connected via network
            from .network import devices_lock
            
            with devices_lock:
                current_state = device_manager.get_device_state(device_key)
                if current_state:
                    # If device already connected via network, don't interfere
                    if current_state.get('connected') and current_state.get('connection_method') == 'network':
                        print(f"[SERIAL] {device_key} already connected via network, skipping USB failure cleanup")
                        return
                    
                    # Mark as disconnected but keep serial_port and connection_method (for hotplug reconnection)
                    device_manager.update_device_state(device_key, {
                        "connected": False
                    })
            
            # Update UI to show disconnected state and hide panel
            status_var = gui_refs.get(f'status_var_{device_key}')
            if status_var:
                current_status = status_var.get()
                # Don't update if status already shows a valid connection (IP or COM)
                if "(Disconnected)" in current_status or "Attempting" in current_status or device_key.capitalize() in current_status:
                    gui_queue = gui_refs.get('gui_queue')
                    disconnected_text = f"{device_key.capitalize()} (Disconnected)"
                    if gui_queue:
                        gui_queue.put((status_var.set, (disconnected_text,), {}))
                    else:
                        status_var.set(disconnected_text)
            
            # Hide the status panel
            reset_and_hide_fn = gui_refs.get('reset_and_hide_panel')
            if reset_and_hide_fn:
                gui_queue = gui_refs.get('gui_queue')
                if gui_queue:
                    gui_queue.put((reset_and_hide_fn, (device_key,), {}))
                else:
                    reset_and_hide_fn(device_key)
            
            # Update searching panel visibility
            from .network import update_searching_panel_visibility
            gui_queue = gui_refs.get('gui_queue')
            if gui_queue:
                gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
            else:
                update_searching_panel_visibility(gui_refs)


def connect_serial_device(port_name, device_key, message_callback, gui_refs, device_manager, silent=False):
    """
    Connects to a device on a serial port and starts listening.
    
    Args:
        port_name (str): The serial port to connect to
        device_key (str): The device key (e.g. 'device')
        message_callback (callable): Function to call with received messages (device_key, message, gui_refs, device_manager)
        gui_refs (dict): GUI references
        device_manager: DeviceManager instance
        silent (bool): If True, suppress error messages (for hotplug attempts)
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    with serial_lock:
        if port_name in serial_connections:
            if not silent:
                print(f"[SERIAL] Already connected to {port_name}")
            return True  # Already connected is success, not failure
        
        # Start listener thread
        thread = threading.Thread(
            target=serial_listener_thread,
            args=(port_name, device_key, message_callback, gui_refs, device_manager, silent),
            daemon=True
        )
        thread.start()
        
        serial_connections[port_name] = {
            'device_key': device_key,
            'thread': thread,
            'port': port_name
        }
        
        return True


def disconnect_serial_device(port_name):
    """
    Disconnects from a serial device.
    
    Args:
        port_name (str): The serial port to disconnect
        
    Returns:
        bool: True if disconnected, False if not connected
    """
    with serial_lock:
        if port_name in serial_connections:
            del serial_connections[port_name]
            return True
        return False


def send_serial_command(port_name, command):
    """
    Sends a command to a device over serial.
    
    Args:
        port_name (str): The serial port to send to
        command (str): The command string to send
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        with serial_lock:
            # Use existing connection if available
            if port_name in serial_connections:
                conn_info = serial_connections[port_name]
                if 'serial' in conn_info:
                    ser = conn_info['serial']
                    ser.write((command + '\n').encode('utf-8'))
                    ser.flush()  # Ensure data is sent immediately
                    print(f"[SERIAL] Sent command to {port_name}: {command}")
                    return True
                else:
                    # Serial object not ready yet
                    print(f"[SERIAL] Cannot send to {port_name}: serial object not ready")
                    return False
            else:
                # No existing connection, try to open temporarily
                ser = serial.Serial(port_name, SERIAL_BAUD_RATE, timeout=SERIAL_TIMEOUT)
                ser.write((command + '\n').encode('utf-8'))
                ser.close()
                return True
    except Exception as e:
        print(f"[SERIAL ERROR] Failed to send command to {port_name}: {e}")
        return False


def get_connected_serial_devices():
    """
    Returns a dictionary of currently connected serial devices.
    
    Returns:
        dict: {device_key: port_name}
    """
    with serial_lock:
        return {info['device_key']: port for port, info in serial_connections.items()}


def is_device_connected_serial(device_key):
    """
    Checks if a device is connected via serial.
    
    Args:
        device_key (str): The device key to check
        
    Returns:
        str or None: Port name if connected, None otherwise
    """
    with serial_lock:
        for port, info in serial_connections.items():
            if info['device_key'] == device_key:
                return port
    return None

