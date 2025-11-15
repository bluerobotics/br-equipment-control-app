import os
import importlib
import importlib.util
import sys
import tkinter as tk
import json
import threading
import socket
import time
import connection_config

class DeviceManager:
    def __init__(self, shared_gui_refs, devices_path=None):
        self.devices = {}
        self.device_state = {} # New dictionary for connection state
        self.discovery_logs = []
        self.shared_gui_refs = shared_gui_refs
        self.simulator_threads = {}  # device_name -> {'thread': thread, 'stop_flag': Event, 'socket': socket}
        self.telemetry_callbacks = {}  # device_name -> list of callback functions
        # Store custom devices path if provided, otherwise use default
        self.devices_path = devices_path if devices_path else os.path.join(os.path.dirname(__file__), 'devices')
        self.discover_devices()

    def _load_module_from_path(self, device_name, module_name, device_path):
        """
        Load a Python module from a specific file path.
        Returns the module if successful, None otherwise.
        """
        module_file = os.path.join(device_path, f"{module_name}.py")
        if not os.path.exists(module_file):
            return None
        
        try:
            # Create a unique module name to avoid conflicts
            full_module_name = f"devices.{device_name}.{module_name}"
            
            # Load the module from file
            spec = importlib.util.spec_from_file_location(full_module_name, module_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[full_module_name] = module
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            self.log(f"Error loading {module_name} for {device_name}: {e}")
        
        return None

    def discover_devices(self):
        """
        Dynamically discovers and loads device modules from the 'devices' directory.
        """
        self.log("Starting device discovery...")
        
        # Clear existing devices to pick up deletions/renames
        self.devices.clear()
        self.device_state.clear()
        
        devices_dir = self.devices_path
        if not os.path.isdir(devices_dir):
            self.log(f"Devices directory not found at '{devices_dir}'")
            return

        for device_name in os.listdir(devices_dir):
            device_path = os.path.join(devices_dir, device_name)
            if os.path.isdir(device_path) and not device_name.startswith('__'):
                try:
                    # Load modules from custom path
                    gui_module = self._load_module_from_path(device_name, 'gui', device_path)
                    if not gui_module:
                        self.log(f"Skipping {device_name}: gui.py not found")
                        continue
                    
                    # --- NEW: Optional Script Handlers ---
                    script_handlers_module = self._load_module_from_path(device_name, 'script_handlers', device_path)

                    # The parser module is now optional.
                    parser_module = self._load_module_from_path(device_name, 'parser', device_path)

                    # Load scripting commands from JSON
                    scripting_commands = {}
                    json_path = os.path.join(device_path, 'commands.json')
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as f:
                            scripting_commands = json.load(f)

                    # Load telemetry schema and create GUI variables
                    telemetry_data = {}
                    schema_path = os.path.join(device_path, 'telemetry.json')
                    if os.path.exists(schema_path):
                        with open(schema_path, 'r') as f:
                            telemetry_data = json.load(f)
                        # Dynamically create the tk variables (auto-generate gui_var from key)
                        for key, details in telemetry_data.items():
                            # Auto-generate gui_var if not provided: device_key_var
                            gui_var_name = details.get('gui_var', f"{device_name}_{key}_var")
                            if gui_var_name not in self.shared_gui_refs:
                                self.shared_gui_refs[gui_var_name] = tk.StringVar(value="---")

                    # Load events from JSON
                    events_data = {}
                    events_path = os.path.join(device_path, 'events.json')
                    if os.path.exists(events_path):
                        with open(events_path, 'r') as f:
                            events_data = json.load(f)

                    # Load warnings from JSON
                    warnings_data = {}
                    warnings_path = os.path.join(device_path, 'warnings.json')
                    if os.path.exists(warnings_path):
                        with open(warnings_path, 'r') as f:
                            warnings_data = json.load(f)

                    self.devices[device_name] = {
                        'gui': gui_module,
                        'parser': parser_module,
                        'script_handlers': script_handlers_module, # Store the module
                        'telemetry_data': telemetry_data, # Store the schema
                        'scripting_commands': scripting_commands, # Store loaded JSON data
                        'events_data': events_data, # Store events data
                        'warnings': warnings_data, # Store warnings data
                        'config': {}, # Keep the key for consistent structure, but it's now unused
                        'status_var': tk.StringVar(value=f'{device_name.capitalize()}')
                    }
                    # Load saved connection config
                    saved_config = connection_config.load_connection_config(device_name)
                    connection_method = 'network'
                    serial_port = None
                    if saved_config:
                        connection_method = saved_config.get('connection_method', 'network')
                        serial_port = saved_config.get('serial_port')
                    
                    # Initialize the state for this device
                    self.device_state[device_name] = {
                        "ip": None,
                        "last_rx": 0,
                        "connection_method": connection_method,
                        "serial_port": serial_port,
                        "connected": False,
                        "last_discovery_attempt": 0,
                        "simulated": False,
                        "firmware_version": None,
                        "fw_prompt_version": None,
                        "fw_update_in_progress": False,
                        "fw_check_scheduled": False
                    }
                    self.log(f"Successfully loaded device module: {device_name}")
                    
                    # Auto-connect to USB if that was the saved preference
                    if connection_method == 'usb' and serial_port:
                        self.log(f"{device_name}: Will attempt USB connection on {serial_port}")
                        # Connection will be attempted when GUI is ready

                except ImportError as e:
                    self.log(f"Failed to load device modules for '{device_name}': {e}")
                except Exception as e:
                    self.log(f"An unexpected error occurred loading '{device_name}': {e}")

    def scan_and_load_new_devices(self):
        """
        Scans the 'devices' directory for new device modules that haven't been loaded yet,
        and loads them into the running application.
        
        Returns:
            A list of the names of the newly loaded devices.
        """
        self.log("Scanning for new device modules...")
        newly_loaded = []
        devices_dir = self.devices_path
        if not os.path.isdir(devices_dir):
            self.log(f"Devices directory not found at '{devices_dir}'")
            return newly_loaded

        for device_name in os.listdir(devices_dir):
            if os.path.isdir(os.path.join(devices_dir, device_name)) and \
               not device_name.startswith('__') and \
               device_name not in self.devices:
                
                # This is a new device, so load it.
                # The original discover_devices logic is reused here implicitly.
                # We can achieve this by calling it again, but it's more efficient to just load the new one.
                # For simplicity in this refactor, we'll just log and load.
                # A more robust implementation would extract the loading logic into a helper.
                
                device_path = os.path.join(devices_dir, device_name)
                try:
                    gui_module = self._load_module_from_path(device_name, 'gui', device_path)
                    if not gui_module:
                        continue
                    
                    parser_module = self._load_module_from_path(device_name, 'parser', device_path)

                    scripting_commands = {}
                    json_path = os.path.join(device_path, 'commands.json')
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as f:
                            scripting_commands = json.load(f)

                    telemetry_data = {}
                    schema_path = os.path.join(device_path, 'telemetry.json')
                    if os.path.exists(schema_path):
                        with open(schema_path, 'r') as f:
                            telemetry_data = json.load(f)
                        for key, details in telemetry_data.items():
                            if 'gui_var' in details:
                                self.shared_gui_refs[details['gui_var']] = tk.StringVar(value="---")

                    events_data = {}
                    events_path = os.path.join(device_path, 'events.json')
                    if os.path.exists(events_path):
                        with open(events_path, 'r') as f:
                            events_data = json.load(f)

                    warnings_data = {}
                    warnings_path = os.path.join(device_path, 'warnings.json')
                    if os.path.exists(warnings_path):
                        with open(warnings_path, 'r') as f:
                            warnings_data = json.load(f)

                    self.devices[device_name] = {
                        'gui': gui_module,
                        'parser': parser_module,
                        'script_handlers': None, # No script_handlers for new devices yet
                        'telemetry_data': telemetry_data,
                        'scripting_commands': scripting_commands,
                        'events_data': events_data,
                        'warnings': warnings_data,
                        'config': {},
                        'status_var': tk.StringVar(value=f'{device_name.capitalize()}')
                    }
                    self.device_state[device_name] = {
                        "ip": None,
                        "last_rx": 0,
                        "connection_method": "network",  # 'network' or 'usb'
                        "serial_port": None,
                        "connected": False,
                        "last_discovery_attempt": 0,
                        "simulated": False,
                        "firmware_version": None,
                        "fw_prompt_version": None,
                        "fw_update_in_progress": False,
                        "fw_check_scheduled": False
                    }
                    self.log(f"Successfully loaded new device: {device_name}")
                    newly_loaded.append(device_name)

                except ImportError as e:
                    self.log(f"Failed to load modules for new device '{device_name}': {e}")
                except Exception as e:
                    self.log(f"An unexpected error occurred loading new device '{device_name}': {e}")
        
        if not newly_loaded:
            self.log("No new device modules found.")
            
        return newly_loaded

    def reload_device_modules(self):
        """
        Reloads the JSON configuration files (commands, telemetry, events) for all devices.
        Useful after editing JSON files through the GUI.
        """
        devices_dir = os.path.join(os.path.dirname(__file__), 'devices')
        if not os.path.isdir(devices_dir):
            return

        for device_name in self.devices.keys():
            self.reload_single_device(device_name)

    def reload_single_device(self, device_name):
        """
        Reloads the JSON configuration files for a single device.
        """
        if device_name not in self.devices:
            return
        
        devices_dir = self.devices_path
        device_path = os.path.join(devices_dir, device_name)
        
        # Reload commands.json
        json_path = os.path.join(device_path, 'commands.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                self.devices[device_name]['scripting_commands'] = json.load(f)
                self.log(f"Reloaded commands.json for {device_name}")
        
        # Reload telemetry.json
        schema_path = os.path.join(device_path, 'telemetry.json')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                telemetry_data = json.load(f)
                self.devices[device_name]['telemetry_data'] = telemetry_data
                # Update GUI variables if needed
                for key, details in telemetry_data.items():
                    if 'gui_var' in details and details['gui_var'] not in self.shared_gui_refs:
                        self.shared_gui_refs[details['gui_var']] = tk.StringVar(value="---")
                self.log(f"Reloaded telemetry.json for {device_name}")
        
        # Reload events.json
        events_path = os.path.join(device_path, 'events.json')
        if os.path.exists(events_path):
            with open(events_path, 'r') as f:
                self.devices[device_name]['events_data'] = json.load(f)
                self.log(f"Reloaded events.json for {device_name}")
        
        # Reload warnings.json
        warnings_path = os.path.join(device_path, 'warnings.json')
        if os.path.exists(warnings_path):
            with open(warnings_path, 'r') as f:
                self.devices[device_name]['warnings'] = json.load(f)
                self.log(f"Reloaded warnings.json for {device_name}")
        
        # Refresh syntax highlighter if available
        if 'syntax_highlighter' in self.shared_gui_refs:
            self.shared_gui_refs['syntax_highlighter'].refresh_keywords()
            self.log(f"Refreshed syntax highlighter for {device_name}")
        
        return True

    def log(self, message):
        """Adds a log message to the discovery logs."""
        print(message) # Also print to console for immediate feedback
        self.discovery_logs.append(message)
    
    def start_simulator(self, device_name, connection_type='network'):
        """Start a simulator thread for a specific device.
        
        Args:
            device_name (str): Name of the device to simulate
            connection_type (str): 'network' for local network (127.0.0.1) or 'usb' for virtual USB
        """
        if device_name in self.simulator_threads:
            # Already running
            return
        
        if device_name not in self.devices:
            self.log(f"Cannot start simulator for unknown device: {device_name}")
            return
        
        # Get device port (auto-assigned based on sorted device order)
        device_names = sorted(self.devices.keys())
        base_port = 8888
        device_port = base_port + device_names.index(device_name)
        
        # Load telemetry schema for initial state
        device_path = os.path.join(os.path.dirname(__file__), 'devices', device_name)
        schema_file = os.path.join(device_path, 'telemetry.json')
        initial_state = {}
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_data = json.load(f)
                # Use the telemetry key as-is (not prefixed with device name)
                initial_state = {key: details.get('default', '---') 
                               for key, details in schema_data.items()}
        
        # Create stop flag and socket
        stop_flag = threading.Event()
        sim_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sim_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sim_socket.bind(('127.0.0.1', device_port))
        sim_socket.settimeout(0.01)  # Non-blocking with timeout (10ms for 10Hz telemetry)
        
        # Start simulator thread
        thread = threading.Thread(
            target=self._simulator_worker,
            args=(device_name, sim_socket, initial_state, stop_flag, device_port, connection_type),
            daemon=True
        )
        thread.start()
        
        self.simulator_threads[device_name] = {
            'thread': thread,
            'stop_flag': stop_flag,
            'socket': sim_socket,
            'port': device_port,
            'connection_type': connection_type
        }
        
        # Mark as simulated, but let discovery handle the connection
        self.device_state[device_name]['simulated'] = True
        
        # If USB simulation, set connection method to USB with virtual port
        if connection_type == 'usb':
            virtual_port = "VIRTUAL_COM"
            self.set_connection_method(device_name, 'usb', virtual_port)
            self.log(f"Started USB simulator for {device_name} (virtual port: {virtual_port})")
            
            # Start virtual USB listener
            import comms
            import serial_comms
            # For USB simulation, we'll inject messages directly via handle_serial_message
            # No need for actual serial connection
        else:
            self.log(f"Started network simulator for {device_name} on 127.0.0.1:{device_port}")
            # Trigger a discovery to connect to the newly started simulator
            import comms
            comms.discover_devices(self.shared_gui_refs)
    
    def stop_simulator(self, device_name):
        """Stop the simulator thread for a specific device."""
        if device_name not in self.simulator_threads:
            return
        
        sim_info = self.simulator_threads[device_name]
        sim_info['stop_flag'].set()
        sim_info['socket'].close()
        sim_info['thread'].join(timeout=2.0)
        
        del self.simulator_threads[device_name]
        
        # Update device state - clear simulated flag
        self.device_state[device_name]['simulated'] = False
        # Let the monitor_connections thread handle disconnection
        
        self.log(f"Stopped simulator for {device_name}")
    
    def _simulator_worker(self, device_name, sim_socket, state, stop_flag, port, connection_type='network'):
        """Worker thread for device simulator.
        
        Args:
            connection_type (str): 'network' for UDP or 'usb' for simulated serial
        """
        gui_port = 6272
        telemetry_interval = 0.1  # 10 Hz (100ms)
        last_telemetry = 0
        
        while not stop_flag.is_set():
            # Send telemetry periodically (format: devicename_TELEM:key=value;key=value)
            current_time = time.time()
            if current_time - last_telemetry >= telemetry_interval:
                telemetry_msg = f"{device_name}_TELEM:" + ";".join([f"{k}={v}" for k, v in state.items()])
                
                if connection_type == 'usb':
                    # For USB simulation, send directly via handle_serial_message
                    try:
                        import comms
                        comms.handle_serial_message(device_name, telemetry_msg, self.shared_gui_refs, self)
                    except:
                        pass
                else:
                    # For network simulation, send via UDP
                    try:
                        sim_socket.sendto(telemetry_msg.encode(), ('127.0.0.1', gui_port))
                    except:
                        pass
                last_telemetry = current_time
            
            # Receive commands
            try:
                data, addr = sim_socket.recvfrom(1024)
                message = data.decode().strip()
                
                # Handle discovery messages
                if message.startswith("DISCOVER_DEVICE"):
                    # Send discovery response (format: DISCOVERY_RESPONSE: DEVICE_ID=devicename PORT=port)
                    response = f"DISCOVERY_RESPONSE: DEVICE_ID={device_name} PORT={port} FW=SIM"
                    
                    if connection_type == 'usb':
                        # For USB, inject response directly
                        try:
                            import comms
                            comms.handle_serial_message(device_name, response, self.shared_gui_refs, self)
                        except:
                            pass
                    else:
                        sim_socket.sendto(response.encode(), addr)
                else:
                    # Send acknowledgment for other commands
                    response = f"{device_name.upper()}_DONE: {message}"
                    
                    if connection_type == 'usb':
                        # For USB, inject response directly
                        try:
                            import comms
                            comms.handle_serial_message(device_name, response, self.shared_gui_refs, self)
                        except:
                            pass
                    else:
                        sim_socket.sendto(response.encode(), addr)
                    
                    # Update state based on command (simplified)
                    # You can enhance this with device-specific simulators
                
            except socket.timeout:
                continue
            except:
                break
        
        # Cleanup
        try:
            sim_socket.close()
        except:
            pass

    def get_device_modules(self):
        """Returns the dictionary of loaded device modules."""
        return self.devices

    def get_all_device_names(self):
        """Returns a list of the names of all loaded devices."""
        return list(self.devices.keys())

    def get_discovery_logs(self):
        """Returns the list of discovery log messages."""
        return self.discovery_logs

    def create_all_gui_components(self, parent_container):
        """
        Iterates through all loaded devices and calls their GUI creation functions.
        """
        for device_name, modules in self.devices.items():
            if hasattr(modules['gui'], 'create_gui_components'):
                panel = modules['gui'].create_gui_components(parent_container, self.shared_gui_refs)
                self.shared_gui_refs[f'{device_name}_panel'] = panel
                panel.pack_forget() # Hide by default
                self.log(f"Created GUI panel for {device_name}")

    def get_all_command_functions(self):
        """
        Aggregates command functions from all discovered devices.
        """
        all_commands = {}
        for device_name, device_data in self.devices.items():
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

    def get_all_script_handlers(self):
        """
        Aggregates script handler functions from all loaded device modules.
        """
        all_handlers = {}
        for device_name, modules in self.devices.items():
            if modules.get('script_handlers') and hasattr(modules['script_handlers'], 'HANDLERS'):
                all_handlers.update(modules['script_handlers'].HANDLERS)
        return all_handlers

    def get_device_sender(self, device_name):
        """Returns a lambda function that sends a message to a specific device."""
        import comms # Local import to avoid circular dependency
        return lambda msg: comms.send_to_device(device_name, msg, self.shared_gui_refs)

    def send_global_abort(self):
        """Sends a cancel command to all connected devices."""
        import comms # Local import
        # Pass the entire shared_gui_refs dictionary to the logger
        comms.log_to_terminal("--- GLOBAL CANCEL TRIGGERED ---", self.shared_gui_refs)
        
        for device_name in self.devices.keys():
            # A more robust implementation would check if the device is actually connected
            sender = self.get_device_sender(device_name)
            sender("cancel")

    def get_device_state(self, device_name):
        """Returns the connection state for a specific device."""
        return self.device_state.get(device_name)

    def get_all_device_states(self):
        """Returns the dictionary of all device connection states."""
        return self.device_state

    def update_device_state(self, device_name, new_state):
        """Updates the connection state for a specific device."""
        if device_name in self.device_state:
            self.device_state[device_name].update(new_state)
    
    def set_connection_method(self, device_name, method, serial_port=None):
        """
        Sets the connection method for a device.
        
        Args:
            device_name (str): Name of the device
            method (str): 'network' or 'usb'
            serial_port (str): Serial port name if method is 'usb', None otherwise
        """
        if device_name in self.device_state:
            self.device_state[device_name]['connection_method'] = method
            if method == 'usb':
                self.device_state[device_name]['serial_port'] = serial_port
            else:
                self.device_state[device_name]['serial_port'] = None
            
            # Save to persistent config
            connection_config.save_connection_config(device_name, method, serial_port)
            
            self.log(f"{device_name}: Connection method set to {method}" + 
                    (f" ({serial_port})" if serial_port else ""))
    
    def get_connection_method(self, device_name):
        """Returns the connection method for a device ('network' or 'usb')."""
        if device_name in self.device_state:
            return self.device_state[device_name].get('connection_method', 'network')
        return 'network'
    
    def auto_connect_usb_devices(self):
        """Automatically connects to devices that were last connected via USB."""
        import serial_comms
        import comms
        
        any_usb_connected = False
        
        for device_name, device_state in self.device_state.items():
            if device_state.get('connection_method') == 'usb' and device_state.get('serial_port'):
                port = device_state['serial_port']
                self.log(f"{device_name}: Auto-connecting to USB on {port}")
                
                # Update status variable
                status_text = f"{device_name.capitalize()} ({port})"
                status_var = self.shared_gui_refs.get(f'status_var_{device_name}')
                if status_var:
                    status_var.set(status_text)
                
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
                        comms.log_to_terminal(f"{device_name}: Auto-connected via USB on {port}", self.shared_gui_refs)
                        any_usb_connected = True
                    else:
                        comms.log_to_terminal(f"{device_name}: Failed to auto-connect to {port}", self.shared_gui_refs)
                except Exception as e:
                    comms.log_to_terminal(f"{device_name}: Error auto-connecting to {port}: {e}", self.shared_gui_refs)

    def get_all_scripting_commands(self):
        """
        Aggregates scripting command definitions from all discovered devices.
        Also includes built-in script commands.
        """
        all_commands = {}
        
        # Add built-in script commands
        from script_processor import SCRIPT_COMMANDS
        for cmd_name, cmd_details in SCRIPT_COMMANDS.items():
            all_commands[cmd_name] = cmd_details.copy()
        
        # Add device-specific commands
        for device_name, modules in self.devices.items():
            # Check for commands loaded from JSON
            if modules.get('scripting_commands'):
                device_commands = modules['scripting_commands']
                # Add device information to each command
                for cmd_name, cmd_details in device_commands.items():
                    # Check if command already has device prefix
                    if cmd_name.startswith(f"{device_name}."):
                        # Command already has device prefix, use it as-is
                        full_cmd_key = cmd_name
                    else:
                        # Command doesn't have device prefix, add it
                        full_cmd_key = f"{device_name}.{cmd_name}"
                    
                    # Add device information to command details
                    cmd_details_with_device = cmd_details.copy()
                    cmd_details_with_device['device'] = device_name
                    all_commands[full_cmd_key] = cmd_details_with_device
        return all_commands

    def get_device_scripting_commands(self, device_name):
        """Returns the scripting commands for a specific device."""
        device = self.devices.get(device_name)
        if device:
            return device.get('scripting_commands', {})
        return {}

    def get_all_device_variable_names(self):
        """
        Collects all GUI variable names from all devices and maps them back to their schema keys.
        Returns a dictionary like: {'gantry': {'gantry_x_pos_var': 'x_p', ...}, ...}
        """
        all_vars = {}
        for device_name, modules in self.devices.items():
            device_map = {}
            # Reconstruct the mapping from the stored telemetry_data
            telemetry_data = modules.get('telemetry_data', {})
            for schema_key, details in telemetry_data.items():
                if 'gui_var' in details:
                    device_map[details['gui_var']] = schema_key
            all_vars[device_name] = device_map
        return all_vars

    def get_all_events(self):
        """
        Aggregates event definitions from all discovered devices.
        Returns a dictionary with event names as keys and their details as values.
        """
        all_events = {}
        for device_name, modules in self.devices.items():
            if modules.get('events_data'):
                device_events = modules['events_data']
                for event_name, event_details in device_events.items():
                    # Add device prefix to event name
                    full_event_key = f"{device_name}.{event_name}"
                    # Add device information to event details
                    event_details_with_device = event_details.copy()
                    event_details_with_device['device'] = device_name
                    all_events[full_event_key] = event_details_with_device
        return all_events

    def get_device_events(self, device_name):
        """Returns the events for a specific device."""
        device = self.devices.get(device_name)
        if device:
            return device.get('events_data', {})
        return {}
    
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
