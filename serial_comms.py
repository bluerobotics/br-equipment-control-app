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
        print(f"[SERIAL] Connected to {device_key} on {port_name}")
        
        # Store the serial object in the connection info
        with serial_lock:
            if port_name in serial_connections:
                serial_connections[port_name]['serial'] = ser
        
        while True:
            with serial_lock:
                if port_name not in serial_connections:
                    # Thread was stopped
                    break
                    
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        message_callback(device_key, line, gui_refs, device_manager)
                except Exception as e:
                    print(f"[SERIAL ERROR] {port_name}: {e}")
            
            time.sleep(0.01)  # Small delay to prevent CPU hogging
        
        ser.close()
        print(f"[SERIAL] Disconnected from {device_key} on {port_name}")
        
    except Exception as e:
        print(f"[SERIAL ERROR] Failed to connect to {port_name}: {e}")
        with serial_lock:
            if port_name in serial_connections:
                del serial_connections[port_name]


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
                ser = conn_info['serial']
                ser.write((command + '\n').encode('utf-8'))
                return True
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

