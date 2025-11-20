import os
import tkinter as tk
from . import connection_config
from .devices import DeviceRegistry, DeviceState, DeviceSimulatorManager


class DeviceManager:
    """
    Facade for managing devices - delegates to specialized modules.
    
    This class provides a unified interface to:
    - DeviceRegistry: Device discovery and loading
    - DeviceState: Connection state tracking
    - DeviceSimulatorManager: Device simulation
    """
    
    def __init__(self, shared_gui_refs, device_paths=None):
        """
        Initialize DeviceManager.
        
        Args:
            shared_gui_refs: Dictionary of shared GUI references
            device_paths: List of individual device folder paths (each path should be a device folder)
        """
        self.shared_gui_refs = shared_gui_refs
        self.telemetry_callbacks = {}  # device_name -> list of callback functions
        
        # Only use explicitly configured device paths (no defaults, no auto-scanning)
        self.device_paths = device_paths if device_paths and isinstance(device_paths, list) else []
        
        # Initialize the specialized modules
        self.registry = DeviceRegistry(self.device_paths)
        self.state = DeviceState()
        self.simulator = DeviceSimulatorManager(self.registry, self.state, shared_gui_refs)
        
        # Load devices from configured paths
        self.discover_devices()

    # ========== Logging ==========
    
    def log(self, message):
        """Adds a log message to the discovery logs."""
        print(message)  # Also print to console for immediate feedback
        self.registry.discovery_logs.append(message)

    # ========== Device Discovery & Loading ==========
    
    def discover_devices(self):
        """
        Loads device modules from explicitly configured device paths.
        Each path should be a device root folder (e.g., my-device/).
        The code will look for a definition/ subfolder or use the root if it contains definition files.
        Device name is read from config.json in the definition folder.
        """
        self.log("Loading devices from configured paths...")
        
        # Discover devices using registry
        self.registry.discover_devices()
        
        # Initialize state for each discovered device
        for device_name, device_data in self.registry.get_device_modules().items():
            # Load saved connection config
            saved_config = connection_config.load_connection_config(device_name)
            connection_method = 'network'
            serial_port = None
            if saved_config:
                connection_method = saved_config.get('connection_method', 'network')
                serial_port = saved_config.get('serial_port')
            
            # Initialize the state for this device
            self.state.initialize_device(device_name, serial_port)
            self.state.update_state(device_name, {
                'connection_method': connection_method,
            })
            
            self.log(f"Successfully loaded device module: {device_name}")
            
            # Auto-connect to USB if that was the saved preference
            if connection_method == 'usb' and serial_port:
                self.log(f"{device_name}: Will attempt USB connection on {serial_port}")
                # Connection will be attempted when GUI is ready

    def reload_device_modules(self):
        """
        Reloads the JSON configuration files (commands, telemetry, events) for all devices.
        Useful after editing JSON files through the GUI.
        """
        device_names = list(self.registry.get_device_modules().keys())
        for device_name in device_names:
            self.reload_single_device(device_name)

    def reload_single_device(self, device_name):
        """
        Reloads the JSON configuration files for a single device.
        """
        success = self.registry.reload_single_device(device_name, self.shared_gui_refs)
        if success:
            # Refresh syntax highlighter if available
            if 'syntax_highlighter' in self.shared_gui_refs:
                self.shared_gui_refs['syntax_highlighter'].refresh_keywords()
                self.log(f"Refreshed syntax highlighter for {device_name}")
        return success

    # ========== Device Registry Accessors ==========
    
    def get_device_modules(self):
        """Returns the dictionary of loaded device modules."""
        return self.registry.get_device_modules()

    def get_all_device_names(self):
        """Returns a list of the names of all loaded devices."""
        return self.registry.get_all_device_names()

    def get_discovery_logs(self):
        """Returns the list of discovery log messages."""
        return self.registry.get_discovery_logs()

    def get_device_config(self, device_name):
        """
        Returns the config.json data for a device.
        
        Args:
            device_name: Name of the device
            
        Returns:
            dict or None: Config dictionary if found, None otherwise
        """
        return self.registry.get_device_config(device_name)

    def get_all_scripting_commands(self):
        """
        Aggregates scripting command definitions from all discovered devices.
        Also includes built-in script commands.
        """
        return self.registry.get_all_scripting_commands()

    def get_device_scripting_commands(self, device_name):
        """Returns the scripting commands for a specific device."""
        return self.registry.get_device_scripting_commands(device_name)

    def get_all_device_variable_names(self):
        """
        Collects all GUI variable names from all devices and maps them back to their schema keys.
        Returns a dictionary like: {'device': {'device_x_pos_var': 'x_pos', ...}, ...}
        """
        return self.registry.get_all_device_variable_names()

    def get_all_events(self):
        """
        Aggregates event definitions from all discovered devices.
        Returns a dictionary with event names as keys and their details as values.
        """
        return self.registry.get_all_events()

    def get_device_events(self, device_name):
        """Returns the events for a specific device."""
        return self.registry.get_device_events(device_name)

    # ========== GUI Creation ==========
    
    def create_all_gui_components(self, parent_container):
        """
        Iterates through all loaded devices and calls their GUI creation functions.
        Also ensures status variables are added to shared_gui_refs for all devices.
        """
        devices = self.registry.get_device_modules()
        for device_name, device_data in devices.items():
            # Ensure status_var is in shared_gui_refs (needed even for devices without GUI)
            status_var_key = f'status_var_{device_name}'
            if status_var_key not in self.shared_gui_refs:
                if 'status_var' in device_data:
                    self.shared_gui_refs[status_var_key] = device_data['status_var']
                else:
                    # Create a default status_var if it doesn't exist
                    self.shared_gui_refs[status_var_key] = tk.StringVar(value=f'{device_name.capitalize()}')
            
            # Create GUI components if the device has a gui module
            gui_module = device_data.get('gui')
            if gui_module and hasattr(gui_module, 'create_gui_components'):
                panel = gui_module.create_gui_components(parent_container, self.shared_gui_refs)
                self.shared_gui_refs[f'{device_name}_panel'] = panel
                panel.pack_forget()  # Hide by default
                self.log(f"Created GUI panel for {device_name}")

    # ========== Command Functions ==========
    
    def get_all_command_functions(self):
        """
        Aggregates command functions from all discovered devices.
        """
        all_commands = {}
        devices = self.registry.get_device_modules()
        for device_name, device_data in devices.items():
            sender = self.get_device_sender(device_name)
            
            # Add the generic sender for the script processor
            all_commands[f"send_{device_name}"] = sender

            # Dynamically create functions for GUI actions defined in JSON
            for command_name, details in device_data.get('scripting_commands', {}).items():
                if 'gui_action' in details:
                    action_name = details['gui_action']
                    # Use a closure to capture the command_name correctly
                    all_commands[action_name] = lambda cmd=command_name: sender(cmd)

        # Add global commands
        all_commands['abort'] = self.send_global_abort
        return all_commands

    def get_device_sender(self, device_name):
        """Returns a lambda function that sends a message to a specific device."""
        from . import comms  # Local import to avoid circular dependency
        return lambda msg: comms.send_to_device(device_name, msg, self.shared_gui_refs)

    def send_global_abort(self):
        """Sends a cancel command to all connected devices."""
        from . import comms  # Local import
        # Pass the entire shared_gui_refs dictionary to the logger
        comms.log_to_terminal("--- GLOBAL CANCEL TRIGGERED ---", self.shared_gui_refs)
        
        devices = self.registry.get_device_modules()
        for device_name in devices.keys():
            # A more robust implementation would check if the device is actually connected
            sender = self.get_device_sender(device_name)
            sender("cancel")

    # ========== Device State Management ==========
    
    def get_device_state(self, device_name):
        """Returns the connection state for a specific device."""
        return self.state.get_state(device_name)

    def get_all_device_states(self):
        """Returns the dictionary of all device connection states."""
        return self.state.get_all_states()

    def update_device_state(self, device_name, new_state):
        """Updates the connection state for a specific device."""
        self.state.update_state(device_name, new_state)
    
    def set_connection_method(self, device_name, method, serial_port=None):
        """
        Sets the connection method for a device.
        
        Args:
            device_name: Name of the device
            method: 'network' or 'usb'
            serial_port: Serial port name if method is 'usb', None otherwise
        """
        self.state.set_connection_method(device_name, method, serial_port)
        self.log(f"{device_name}: Connection method set to {method}" + 
                (f" ({serial_port})" if serial_port else ""))
    
    def get_connection_method(self, device_name):
        """Returns the connection method for a device ('network' or 'usb')."""
        method, _ = self.state.get_connection_method(device_name)
        return method if method else 'network'
    
    def auto_connect_usb_devices(self):
        """
        Automatically connects to devices that were last connected via USB.

        Returns:
            bool: True if at least one device connected successfully, False otherwise.
        """
        from . import serial_comms
        from . import comms
        
        any_usb_connected = False
        
        from .comms import update_searching_panel_visibility
        import time
        
        all_states = self.state.get_all_states()
        for device_name, device_state in all_states.items():
            if device_state.get('connection_method') == 'usb' and device_state.get('serial_port'):
                # Skip if already connected and receiving telemetry
                if device_state.get('connected'):
                    self.log(f"{device_name}: Already connected via USB, skipping auto-connect")
                    continue
                
                port = device_state['serial_port']
                
                # Skip VIRTUAL_COM unless the device is actually being simulated
                if port == "VIRTUAL_COM" and not self.simulator.is_simulator_running(device_name):
                    self.log(f"{device_name}: Skipping VIRTUAL_COM (device not being simulated)")
                    continue
                
                self.log(f"{device_name}: Auto-connecting to USB on {port}")
                
                # Don't update status variable yet - wait for actual connection confirmation
                # The status will be updated when the first message arrives
                
                # Start USB listener
                try:
                    success = serial_comms.connect_serial_device(
                        port,
                        device_name,
                        comms.handle_serial_message,
                        self.shared_gui_refs,
                        self
                    )
                    
                    if success:
                        comms.log_to_terminal(f"{device_name}: Attempting USB connection on {port}...", self.shared_gui_refs)
                        any_usb_connected = True

                        # Don't mark as connected yet - wait for first message to confirm
                        # This prevents premature timeout if device takes a moment to start streaming
                        # The status will be updated by handle_serial_message when first message arrives
                        self.update_device_state(device_name, {
                            "connection_method": "usb",
                            "serial_port": port,
                            "last_rx": 0  # Will be updated when first message arrives
                        })
                        
                        # Send discovery commands with retries to prompt a response from the firmware
                        # The firmware should respond with telemetry chunks
                        import time
                        time.sleep(0.5)  # Initial delay for serial port to be ready
                        for attempt in range(3):
                            self.log(f"{device_name}: Sending DISCOVER_DEVICE command (attempt {attempt + 1}/3)")
                            serial_comms.send_serial_command(port, "DISCOVER_DEVICE")
                            time.sleep(0.2)  # Small delay between attempts
                        
                        # Don't update status_var or show panel yet - wait for actual connection
                        # The panel will be shown and status updated when the first message arrives
                    else:
                        comms.log_to_terminal(f"{device_name}: Failed to auto-connect to {port}", self.shared_gui_refs)
                        
                        # Reset device state to network on failure
                        self.update_device_state(device_name, {
                            "connection_method": "network",
                            "serial_port": None
                        })
                        
                        # Reset status text
                        status_var = self.shared_gui_refs.get(f'status_var_{device_name}')
                        if status_var:
                            status_var.set(f"{device_name.capitalize()} (Disconnected)")
                except Exception as e:
                    comms.log_to_terminal(f"{device_name}: Error auto-connecting to {port}: {e}", self.shared_gui_refs)
        
        return any_usb_connected

    def try_usb_reconnect(self, device_name, serial_port, gui_refs):
        """
        Attempts to reconnect a USB device. Called by monitor thread for hotplug support.
        Silent mode - no error spam if port isn't available.
        """
        from . import serial_comms
        from . import comms
        
        # Check if port is already connected
        with serial_comms.serial_lock:
            if serial_port in serial_comms.serial_connections:
                return  # Already connected
        
        # Try to connect (silent mode - no error messages or success spam)
        success = serial_comms.connect_serial_device(
            serial_port,
            device_name,
            comms.handle_serial_message,
            gui_refs,
            self,
            silent=True  # Suppress errors for hotplug attempts
        )
        
        # Success is silent - the normal connection message will appear when telemetry arrives

    # ========== Simulator Management ==========
    
    def start_simulator(self, device_name, connection_type='network'):
        """
        Start a simulator thread for a specific device.
        
        Args:
            device_name: Name of the device to simulate
            connection_type: 'network' for local network (127.0.0.1) or 'usb' for virtual USB
        """
        self.simulator.start_simulator(device_name, connection_type)
    
    def stop_simulator(self, device_name):
        """Stop the simulator thread for a specific device."""
        self.simulator.stop_simulator(device_name)

    # ========== Telemetry Callbacks ==========
    
    def register_telemetry_callback(self, device_name, callback):
        """
        Registers a callback function to be called when telemetry is received from a device.
        Callback signature: callback(device_name, telemetry_dict)
        """
        if device_name not in self.telemetry_callbacks:
            self.telemetry_callbacks[device_name] = []
        self.telemetry_callbacks[device_name].append(callback)
    
    def unregister_telemetry_callback(self, device_name, callback):
        """
        Unregisters a telemetry callback function for a device.
        """
        if device_name in self.telemetry_callbacks:
            try:
                self.telemetry_callbacks[device_name].remove(callback)
            except ValueError:
                pass  # Callback wasn't in the list
    
    def notify_telemetry_callbacks(self, device_name, telemetry_dict):
        """
        Calls all registered callbacks for a device with the telemetry data.
        """
        if device_name in self.telemetry_callbacks:
            for callback in self.telemetry_callbacks[device_name]:
                try:
                    callback(device_name, telemetry_dict)
                except Exception as e:
                    print(f"[ERROR] Telemetry callback error for {device_name}: {e}")

    # ========== Legacy Compatibility Properties ==========
    # These properties maintain backward compatibility with code that accesses
    # internal structures directly (e.g., self.device_manager.devices)
    
    @property
    def devices(self):
        """Legacy access to device modules dictionary."""
        return self.registry.get_device_modules()
    
    @property
    def device_state(self):
        """Legacy access to device state dictionary."""
        return self.state.get_all_states()
    
    @property
    def discovery_logs(self):
        """Legacy access to discovery logs list."""
        return self.registry.get_discovery_logs()
    
    @property
    def simulator_threads(self):
        """Legacy access to simulator threads dictionary."""
        return self.simulator.simulator_threads
