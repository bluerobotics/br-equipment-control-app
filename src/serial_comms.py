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


def detect_device_on_port(port_name, timeout=2.0):
    """
    Attempts to detect what device is on a serial port by listening for messages.
    
    Args:
        port_name (str): The serial port to check
        timeout (float): How long to wait for device identification
        
    Returns:
        str or None: Device key (e.g. 'pressboi', 'fillhead') if detected, None otherwise
    """
    try:
        ser = serial.Serial(port_name, SERIAL_BAUD_RATE, timeout=SERIAL_TIMEOUT)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                # Look for device identifiers in messages
                if 'PRESSBOI_' in line or 'Pressboi' in line:
                    ser.close()
                    return 'pressboi'
                elif 'FILLHEAD_' in line or 'Fillhead' in line:
                    ser.close()
                    return 'fillhead'
                elif 'GANTRY_' in line or 'Gantry' in line:
                    ser.close()
                    return 'gantry'
                elif 'PRESSURIZER_' in line or 'Pressurizer' in line:
                    ser.close()
                    return 'pressurizer'
            time.sleep(0.1)
        
        ser.close()
        return None
    except Exception as e:
        print(f"Error detecting device on {port_name}: {e}")
        return None


def serial_listener_thread(port_name, device_key, message_callback, gui_refs, device_manager):
    """
    Background thread that reads from a serial port and processes messages.
    
    Args:
        port_name (str): The serial port to read from
        device_key (str): The device key (e.g. 'pressboi')
        message_callback (callable): Function to call with received messages (device_key, message, gui_refs, device_manager)
        gui_refs (dict): GUI references
        device_manager: DeviceManager instance
    """
    try:
        ser = serial.Serial(port_name, SERIAL_BAUD_RATE, timeout=SERIAL_TIMEOUT)
        # Give the port a moment to fully initialize
        time.sleep(0.1)
        print(f"[SERIAL] Connected to {device_key} on {port_name}")
        
        # Store the serial object in the connection info
        with serial_lock:
            if port_name in serial_connections:
                serial_connections[port_name]['serial'] = ser
        
        # Debug: Track if we're receiving any data
        last_data_time = time.time()
        has_received_data = False
        
        # Chunk reassembly state
        chunk_buffer = []  # Stores chunks: [(chunk_num, total_chunks, data), ...]
        
        while True:
            with serial_lock:
                if port_name not in serial_connections:
                    # Thread was stopped
                    break
            
            # Update last data time
            now = time.time()
            if has_received_data:
                last_data_time = now
                    
            # Read ALL available lines, not just one per loop iteration
            while ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        has_received_data = True
                        
                        # Check if this is a chunked message
                        if line.startswith("CHUNK_"):
                            # Parse: CHUNK_1/5:data
                            try:
                                header_end = line.index(":")
                                header = line[6:header_end]  # Skip "CHUNK_"
                                chunk_num, total_chunks = map(int, header.split("/"))
                                data = line[header_end + 1:]
                                
                                # Add to buffer
                                chunk_buffer.append((chunk_num, total_chunks, data))
                                
                                # Check if we have all chunks
                                if len(chunk_buffer) == total_chunks:
                                    # Sort by chunk number and reassemble
                                    chunk_buffer.sort(key=lambda x: x[0])
                                    full_message = ''.join([chunk[2] for chunk in chunk_buffer])
                                    chunk_buffer.clear()
                                    
                                    # Process the reassembled message
                                    message_callback(device_key, full_message, gui_refs, device_manager)
                                elif len(chunk_buffer) > total_chunks:
                                    # Too many chunks, reset
                                    chunk_buffer.clear()
                            except (ValueError, IndexError):
                                # Malformed chunk, ignore
                                pass
                        else:
                            # Normal message (not chunked)
                            message_callback(device_key, line, gui_refs, device_manager)
                except Exception as e:
                    print(f"[SERIAL ERROR] {port_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    break  # Exit the while loop on error
            
            time.sleep(0.01)  # Small delay to prevent CPU hogging
        
        ser.close()
        print(f"[SERIAL] Disconnected from {device_key} on {port_name}")
        
    except Exception as e:
        print(f"[SERIAL ERROR] Failed to connect to {port_name}: {e}")
        with serial_lock:
            if port_name in serial_connections:
                del serial_connections[port_name]
        
        # Update device state to reflect connection failure
        if device_manager:
            # Only update if the device hasn't already connected via network
            from . import comms
            from .comms import devices_lock
            
            with devices_lock:
                current_state = device_manager.get_device_state(device_key)
                if current_state:
                    # If device already connected via network, don't interfere
                    if current_state.get('connected') and current_state.get('connection_method') == 'network':
                        print(f"[SERIAL] {device_key} already connected via network, skipping USB failure cleanup")
                        return
                    
                    # Device is not connected yet, so update to fall back to network
                    device_manager.update_device_state(device_key, {
                        "connection_method": "network",
                        "serial_port": None,
                        "connected": False
                    })
            
            # Update UI to show disconnected state only if not already connected
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
            
            # Update searching panel visibility
            gui_queue = gui_refs.get('gui_queue')
            if gui_queue:
                gui_queue.put((comms.update_searching_panel_visibility, (gui_refs,), {}))
            else:
                comms.update_searching_panel_visibility(gui_refs)


def connect_serial_device(port_name, device_key, message_callback, gui_refs, device_manager):
    """
    Connects to a device on a serial port and starts listening.
    
    Args:
        port_name (str): The serial port to connect to
        device_key (str): The device key (e.g. 'pressboi')
        message_callback (callable): Function to call with received messages (device_key, message, gui_refs, device_manager)
        gui_refs (dict): GUI references
        device_manager: DeviceManager instance
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    with serial_lock:
        if port_name in serial_connections:
            print(f"[SERIAL] Already connected to {port_name}")
            return False
        
        # Start listener thread
        thread = threading.Thread(
            target=serial_listener_thread,
            args=(port_name, device_key, message_callback, gui_refs, device_manager),
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
                    return True
                else:
                    # Serial object not ready yet
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

