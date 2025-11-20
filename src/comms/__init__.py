"""
Communications Package - Network and serial communication.

This package handles all device communication including:
- Network (UDP) communication
- Serial (USB) communication  
- Message parsing and routing
- Connection monitoring
"""

# Import from network module (was comms.py)
from .network import (
    devices_lock,
    handle_serial_message,
    show_recovery_warning,
    send_to_device,
    update_searching_panel_visibility,
    monitor_connections,
    discover_devices,
    recv_loop
)

# Import from serial module (was serial_comms.py)
from .serial import (
    serial_lock,
    serial_connections,
    list_serial_ports,
    connect_serial_device,
    disconnect_serial_device,
    send_serial_command,
    detect_device_on_port,
    is_device_connected_serial
)

__all__ = [
    # Network comms
    'devices_lock',
    'handle_serial_message',
    'show_recovery_warning',
    'send_to_device',
    'update_searching_panel_visibility',
    'monitor_connections',
    'discover_devices',
    'recv_loop',
    # Serial comms
    'serial_lock',
    'serial_connections',
    'list_serial_ports',
    'connect_serial_device',
    'disconnect_serial_device',
    'send_serial_command',
    'detect_device_on_port',
    'is_device_connected_serial'
]

