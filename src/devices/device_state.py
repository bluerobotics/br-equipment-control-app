"""
Device State - Manages connection state for all devices.

This module handles:
- Connection state tracking (USB/Network, connected/disconnected)
- IP addresses, serial ports, firmware versions
- Connection method switching
- State updates and queries
"""


class DeviceState:
    """Manages connection state for all devices."""
    
    def __init__(self):
        """Initialize DeviceState."""
        self.device_state = {}  # device_name -> state dict
    
    def initialize_device(self, device_name, serial_port=None):
        """
        Initialize state for a new device.
        
        Args:
            device_name: Name of the device
            serial_port: Optional serial port for USB connection
        """
        if device_name not in self.device_state:
            self.device_state[device_name] = {
                'ip': None,
                'last_rx': 0,
                'connection_method': 'usb' if serial_port else 'network',
                'serial_port': serial_port,
                'connected': False,
                'last_discovery_attempt': 0,
                'simulated': False,
                'firmware_version': None,
                'fw_prompt_version': None,
                'fw_update_in_progress': False,
                'fw_check_scheduled': False,
            }
    
    def get_state(self, device_name):
        """
        Get the state dictionary for a device.
        
        Args:
            device_name: Name of the device
            
        Returns:
            dict: State dictionary or None if device not found
        """
        return self.device_state.get(device_name)
    
    def get_all_states(self):
        """Get all device states."""
        return self.device_state.copy()
    
    def update_state(self, device_name, new_state):
        """
        Update state for a device.
        
        Args:
            device_name: Name of the device
            new_state: Dictionary of state updates to apply
        """
        if device_name in self.device_state:
            self.device_state[device_name].update(new_state)
    
    def set_connection_method(self, device_name, method, serial_port=None):
        """
        Set the connection method for a device.
        
        Args:
            device_name: Name of the device
            method: 'usb' or 'network'
            serial_port: Serial port name (for USB connections)
        """
        if device_name not in self.device_state:
            self.initialize_device(device_name, serial_port)
        
        self.device_state[device_name]['connection_method'] = method
        if method == 'usb' and serial_port:
            self.device_state[device_name]['serial_port'] = serial_port
        
        # Save to config
        from .. import connection_config
        try:
            connection_config.save_connection_method(device_name, method, serial_port)
        except Exception as e:
            print(f"Failed to save connection config for {device_name}: {e}")
    
    def get_connection_method(self, device_name):
        """
        Get the connection method for a device.
        
        Args:
            device_name: Name of the device
            
        Returns:
            tuple: (method, serial_port) or (None, None) if not found
        """
        if device_name in self.device_state:
            state = self.device_state[device_name]
            return state.get('connection_method'), state.get('serial_port')
        return None, None
    
    def is_connected(self, device_name):
        """
        Check if a device is connected.
        
        Args:
            device_name: Name of the device
            
        Returns:
            bool: True if connected, False otherwise
        """
        state = self.get_state(device_name)
        return state.get('connected', False) if state else False
    
    def is_simulated(self, device_name):
        """
        Check if a device is simulated.
        
        Args:
            device_name: Name of the device
            
        Returns:
            bool: True if simulated, False otherwise
        """
        state = self.get_state(device_name)
        return state.get('simulated', False) if state else False
    
    def clear_all(self):
        """Clear all device states."""
        self.device_state.clear()
    
    def remove_device(self, device_name):
        """
        Remove a device from state tracking.
        
        Args:
            device_name: Name of the device to remove
        """
        if device_name in self.device_state:
            del self.device_state[device_name]

