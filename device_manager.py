import os
import importlib
import tkinter as tk
import json
import threading
import socket
import time

class DeviceManager:
    def __init__(self, shared_gui_refs):
        self.devices = {}
        self.device_state = {} # New dictionary for connection state
        self.discovery_logs = []
        self.shared_gui_refs = shared_gui_refs
        self.simulator_threads = {}  # device_name -> {'thread': thread, 'stop_flag': Event, 'socket': socket}
        self.telemetry_callbacks = {}  # device_name -> list of callback functions
        self.discover_devices()

    def discover_devices(self):
        """
        Dynamically discovers and loads device modules from the 'devices' directory.
        """
        self.log("Starting device discovery...")
        
        # Clear existing devices to pick up deletions/renames
        self.devices.clear()
        self.device_state.clear()
        
        devices_dir = os.path.join(os.path.dirname(__file__), 'devices')
        if not os.path.isdir(devices_dir):
            self.log(f"Devices directory not found at '{devices_dir}'")
            return

        for device_name in os.listdir(devices_dir):
            device_path = os.path.join(devices_dir, device_name)
            if os.path.isdir(device_path) and not device_name.startswith('__'):
                try:
                    gui_module = importlib.import_module(f'devices.{device_name}.gui')
                    
                    # --- NEW: Optional Script Handlers ---
                    script_handlers_module = None
                    try:
                        script_handlers_module = importlib.import_module(f'devices.{device_name}.script_handlers')
                    except ImportError:
                        pass # It's okay if a device doesn't have script handlers

                    # The parser module is now optional.
                    parser_module = None
                    try:
                        parser_module = importlib.import_module(f'devices.{device_name}.parser')
                    except ImportError:
                        # This is now the standard behavior, so no log message is needed.
                        pass

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

                    self.devices[device_name] = {
                        'gui': gui_module,
                        'parser': parser_module,
                        'script_handlers': script_handlers_module, # Store the module
                        'telemetry_data': telemetry_data, # Store the schema
                        'scripting_commands': scripting_commands, # Store loaded JSON data
                        'events_data': events_data, # Store events data
                        'config': {}, # Keep the key for consistent structure, but it's now unused
                        'status_var': tk.StringVar(value=f'{device_name.capitalize()}')
                    }
                    # Initialize the state for this device
                    self.device_state[device_name] = {
                        "ip": None, 
                        "last_rx": 0, 
                        "connected": False, 
                        "last_discovery_attempt": 0,
                        "simulated": False
                    }
                    self.log(f"Successfully loaded device module: {device_name}")

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
        devices_dir = os.path.join(os.path.dirname(__file__), 'devices')
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
                    gui_module = importlib.import_module(f'devices.{device_name}.gui')
                    parser_module = None
                    try:
                        parser_module = importlib.import_module(f'devices.{device_name}.parser')
                    except ImportError:
                        pass

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

                    self.devices[device_name] = {
                        'gui': gui_module,
                        'parser': parser_module,
                        'script_handlers': None, # No script_handlers for new devices yet
                        'telemetry_data': telemetry_data,
                        'scripting_commands': scripting_commands,
                        'events_data': events_data,
                        'config': {},
                        'status_var': tk.StringVar(value=f'{device_name.capitalize()}')
                    }
                    self.device_state[device_name] = {
                        "ip": None, "last_rx": 0, "connected": False, "last_discovery_attempt": 0
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
            device_path = os.path.join(devices_dir, device_name)
            
            # Reload commands.json
            json_path = os.path.join(device_path, 'commands.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    self.devices[device_name]['scripting_commands'] = json.load(f)
            
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
            
            # Reload events.json
            events_path = os.path.join(device_path, 'events.json')
            if os.path.exists(events_path):
                with open(events_path, 'r') as f:
                    self.devices[device_name]['events_data'] = json.load(f)

    def log(self, message):
        """Adds a log message to the discovery logs."""
        print(message) # Also print to console for immediate feedback
        self.discovery_logs.append(message)
    
    def start_simulator(self, device_name):
        """Start a simulator thread for a specific device."""
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
            args=(device_name, sim_socket, initial_state, stop_flag, device_port),
            daemon=True
        )
        thread.start()
        
        self.simulator_threads[device_name] = {
            'thread': thread,
            'stop_flag': stop_flag,
            'socket': sim_socket,
            'port': device_port
        }
        
        # Mark as simulated, but let discovery handle the connection
        self.device_state[device_name]['simulated'] = True
        
        self.log(f"Started simulator for {device_name} on port {device_port}")
        
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
    
    def _simulator_worker(self, device_name, sim_socket, state, stop_flag, port):
        """Worker thread for device simulator."""
        gui_port = 6272
        telemetry_interval = 0.1  # 10 Hz (100ms)
        last_telemetry = 0
        
        while not stop_flag.is_set():
            # Send telemetry periodically (format: devicename_TELEM:key=value;key=value)
            current_time = time.time()
            if current_time - last_telemetry >= telemetry_interval:
                telemetry_msg = f"{device_name}_TELEM:" + ";".join([f"{k}={v}" for k, v in state.items()])
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
                    response = f"DISCOVERY_RESPONSE: DEVICE_ID={device_name} PORT={port}"
                    sim_socket.sendto(response.encode(), addr)
                else:
                    # Send acknowledgment for other commands
                    response = f"{device_name.upper()}_STATUS:{message}:DONE"
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
        """Sends an ABORT command to all connected devices."""
        import comms # Local import
        # Pass the entire shared_gui_refs dictionary to the logger
        comms.log_to_terminal("--- GLOBAL ABORT TRIGGERED ---", self.shared_gui_refs)
        
        for device_name in self.devices.keys():
            # A more robust implementation would check if the device is actually connected
            sender = self.get_device_sender(device_name)
            sender("ABORT")

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
