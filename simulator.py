import tkinter as tk
from tkinter import ttk
import socket
import threading
import time
import random
from collections import deque
import os
import sys
import importlib.util
import json

# --- Constants ---
BASE_CLEARCORE_PORT = 8888
GUI_APP_PORT = 6272
TELEMETRY_INTERVAL = 1.0  # seconds
SIMULATOR_IP = "127.0.0.1"

def discover_device_schemas():
    """Scans the 'devices' directory and dynamically loads telemetry schemas and simulator modules.
    Returns a dict with device names as keys and dicts containing 'schema', 'port', and 'simulator' as values."""
    schemas = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    devices_path = os.path.join(script_dir, 'devices')

    if not os.path.exists(devices_path):
        print(f"Device directory not found at: {devices_path}")
        return schemas

    # Auto-assign ports starting from BASE_CLEARCORE_PORT
    port_offset = 0

    for device_name in sorted(os.listdir(devices_path)):  # Sort for consistent port assignment
        device_dir = os.path.join(devices_path, device_name)
        schema_file = os.path.join(device_dir, 'telemetry.json')
        if os.path.isdir(device_dir) and os.path.exists(schema_file):
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                    # We need the default values, not the GUI config, for the simulator state
                    initial_state = {key: details.get('default', '---') 
                                     for key, details in schema_data.items()}
                    device_port = BASE_CLEARCORE_PORT + port_offset
                    
                    # Try to load device-specific simulator module
                    simulator_module = None
                    simulator_file = os.path.join(device_dir, 'simulator.py')
                    if os.path.exists(simulator_file):
                        try:
                            spec = importlib.util.spec_from_file_location(f"{device_name}_simulator", simulator_file)
                            simulator_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(simulator_module)
                            print(f"  → Loaded custom simulator for {device_name}")
                        except Exception as e:
                            print(f"  ⚠ Could not load simulator for {device_name}: {e}")
                    
                    schemas[device_name] = {
                        'schema': initial_state,
                        'port': device_port,
                        'simulator': simulator_module
                    }
                    print(f"Loaded schema for device: {device_name} (Port: {device_port})")
                    port_offset += 1
            except Exception as e:
                print(f"Could not load schema for {device_name}: {e}")
    return schemas

class DeviceSimulator(threading.Thread):
    def __init__(self, device_name, ip, port, gui_app_port, schema, simulator_module=None):
        super().__init__()
        self.device_name = device_name
        self.ip = ip
        self.port = port
        self.gui_app_port = gui_app_port
        self.running = False
        self._stop_event = threading.Event()
        self.sock = None
        self.daemon = True
        self.state = schema  # Use the provided schema directly
        self.simulator_module = simulator_module  # Device-specific simulator module
        self.command_queue = deque()  # Queue for async commands

    def stop(self):
        self._stop_event.set()
        if self.sock:
            self.sock.close()

    def run(self):
        self.running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # We don't bind to a specific IP, as we'll send responses to the GUI's address
            self.sock.bind(('', self.port))
            self.sock.settimeout(0.1)
            print(f"[{self.device_name}] Simulator started, listening on port {self.port}")
        except OSError as e:
            print(f"[{self.device_name}] Error binding socket on port {self.port}: {e}")
            self.running = False
            return

        last_telemetry_time = 0
        gui_address = None

        while not self._stop_event.is_set():
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode('utf-8').strip()
                print(f"[{self.device_name}] Received from {addr}: {msg}")
                gui_address = (addr[0], self.gui_app_port)

                if msg.startswith("DISCOVER_DEVICE"):
                    response = f"DISCOVERY_RESPONSE: DEVICE_ID={self.device_name} PORT={self.port}"
                    self.sock.sendto(response.encode(), gui_address)
                    print(f"[{self.device_name}] Sent discovery response to {gui_address}")
                elif msg.startswith("DISCOVER_"):
                    # This is a discovery message for another device, so ignore it.
                    pass
                else:
                    self.handle_command(msg, gui_address)

            except socket.timeout:
                pass
            except Exception as e:
                # Break the loop if the socket is closed, which causes an error.
                if self._stop_event.is_set():
                    break
                print(f"[{self.device_name}] Error in receive loop: {e}")

            # Process any pending commands/state changes
            if self.command_queue:
                cmd_func, cmd_args = self.command_queue.popleft()
                print(f"[{self.device_name}] Processing queued command: {cmd_func.__name__}")
                cmd_func(*cmd_args)
            
            # Simulate dynamic processes like heating
            self.update_state()

            # Check if we should stop before trying to send telemetry
            if self._stop_event.is_set():
                break

            now = time.time()
            if gui_address and (now - last_telemetry_time) > TELEMETRY_INTERVAL:
                telemetry_msg = self.generate_telemetry()
                self.sock.sendto(telemetry_msg.encode(), gui_address)
                # print(f"[{self.device_name}] Sent telemetry to {gui_address}")
                last_telemetry_time = now

        self.running = False
        print(f"[{self.device_name}] Simulator stopped.")

    def handle_command(self, msg, gui_address):
        """Delegates command handling to device-specific simulator module."""
        parts = msg.split()
        command = parts[0]
        args = parts[1:]
        print(f"[{self.device_name}] handle_command called with: {command}, args: {args}")
        
        # Try device-specific handler first
        handled = False
        if self.simulator_module and hasattr(self.simulator_module, 'handle_command'):
            try:
                print(f"[{self.device_name}] Calling device-specific handler")
                handled = self.simulator_module.handle_command(self, command, args, gui_address)
                print(f"[{self.device_name}] Device handler returned: {handled}")
                if handled:
                    print(f"[{self.device_name}] Device handler will send response later")
                    return  # Device module will send response
            except Exception as e:
                print(f"[{self.device_name}] Error in device-specific handler: {e}")
                response = f"ERROR: {str(e)}"
                self.sock.sendto(response.encode(), gui_address)
                return
        
        # Generic response for commands not handled by device module
        if not handled:
            response = f"DONE: {command}"
            self.sock.sendto(response.encode(), gui_address)
            print(f"[{self.device_name}] Responded to {command} with '{response}'")

    def set_state(self, main_state_key, main_state_val, axis_state_val=None):
        """Helper to set device and axis states."""
        self.state[main_state_key] = main_state_val
        if axis_state_val and self.device_name == 'gantry':
            for axis in ['x', 'y', 'z']:
                self.state[f'{axis}_st'] = axis_state_val

    def update_state(self):
        """Delegates state updates to device-specific simulator module."""
        if self.simulator_module and hasattr(self.simulator_module, 'update_state'):
            try:
                self.simulator_module.update_state(self)
            except Exception as e:
                print(f"[{self.device_name}] Error in device update_state: {e}")

    def generate_telemetry(self):
        s = self.state
        # --- Special formats for legacy parsers ---
        if self.device_name == 'gantry':
            s['x_t'] = random.uniform(5, 15) if s.get('gantry_state') != 'STANDBY' else 0.0
            s['y_t'] = random.uniform(5, 15) if s.get('gantry_state') != 'STANDBY' else 0.0
            s['z_t'] = random.uniform(5, 15) if s.get('gantry_state') != 'STANDBY' else 0.0
            
            # The format string is now built dynamically from the state keys
            telem_parts = [f"{key}:{s.get(key, 0)}" for key in s.keys()]
            # Special formatting for floats can be added here if needed, but for now, this is simpler
            return f"GANTRY_TELEM: {','.join(telem_parts)}"

        elif self.device_name == 'fillhead':
            s['inj_t0'] = random.uniform(5, 15) if s.get('MAIN_STATE') != 'STANDBY' else 0.0
            s['inj_t1'] = random.uniform(5, 15) if s.get('MAIN_STATE') != 'STANDBY' else 0.0
            
            telem_parts = [f"{key}:{s.get(key, 0)}" for key in s.keys()]
            return f"FILLHEAD_TELEM: {','.join(telem_parts)}"
        
        # --- Generic Telemetry Format for all other devices ---
        else:
            telem_parts = [f"{key}:{value}" for key, value in s.items()]
            return f"{self.device_name.upper()}_TELEM: {','.join(telem_parts)}"


class SimulatorApp:
    def __init__(self, root, device_schemas):
        self.root = root
        self.root.title("Device Simulator")

        # --- Dark Mode ---
        BG_COLOR = "#282c34"
        FG_COLOR = "#abb2bf"
        self.root.configure(bg=BG_COLOR)

        # Let window auto-size to fit contents
        self.root.lift()  # Bring window to front
        self.root.attributes('-topmost', True)  # Make window appear on top
        self.root.after(100, lambda: self.root.attributes('-topmost', False))  # Release topmost after showing
        
        self.simulators = {}
        self.device_schemas = device_schemas
        self.device_vars = {}

        style = ttk.Style()
        style.configure('TFrame', background=BG_COLOR)
        style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR, font=('JetBrains Mono', 9))
        style.configure('TCheckbutton', background=BG_COLOR, foreground=FG_COLOR, font=('JetBrains Mono', 9))
        style.map('TCheckbutton',
                  foreground=[('active', FG_COLOR)],
                  background=[('active', BG_COLOR)],
                  indicatorcolor=[('selected', '#61afef'), ('!selected', FG_COLOR)])

        frame = ttk.Frame(self.root, padding="10", style='TFrame')
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Dynamically create checkbuttons for each discovered device
        row = 0
        for device_name in sorted(self.device_schemas.keys()):
            self.device_vars[device_name] = tk.BooleanVar()
            
            # Create a proper closure for the callback
            def make_callback(name):
                def callback():
                    state = self.device_vars[name].get()
                    print(f"DEBUG: Checkbox for {name} clicked, state={state}")
                    self.toggle_simulator(name, state)
                return callback
            
            cb = ttk.Checkbutton(
                frame,
                text=f"Simulate {device_name.capitalize()}",
                variable=self.device_vars[device_name],
                command=make_callback(device_name),
                style='TCheckbutton'
            )
            cb.grid(row=row, column=0, sticky=tk.W, pady=2)
            
            # Each device gets its own port on localhost
            device_port = self.device_schemas[device_name]['port']
            ttk.Label(frame, text=f"IP: {SIMULATOR_IP} Port: {device_port}", style='TLabel').grid(row=row, column=1, sticky=tk.W, padx=5)
            row += 1

        if not self.device_schemas:
            ttk.Label(frame, text="No device schemas found. Check paths and telemetry.json files.", style='TLabel').grid(row=0, column=0)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_simulator(self, name, start):
        print(f"DEBUG: toggle_simulator called with name={name}, start={start}")
        try:
            if start:
                if name not in self.simulators or not self.simulators[name].running:
                    print(f"Starting {name} simulator...")
                    device_info = self.device_schemas[name]
                    schema = device_info['schema'].copy()  # Copy the schema to avoid sharing state
                    device_port = device_info['port']
                    simulator_module = device_info.get('simulator')
                    print(f"DEBUG: Creating DeviceSimulator for {name} on port {device_port}")
                    sim = DeviceSimulator(name, SIMULATOR_IP, device_port, GUI_APP_PORT, schema, simulator_module)
                    self.simulators[name] = sim
                    print(f"DEBUG: Starting thread for {name}...")
                    sim.start()
                    print(f"DEBUG: Thread started for {name}, running={sim.running}")
                else:
                    print(f"DEBUG: {name} simulator already running or exists")
            else:
                print(f"DEBUG: Attempting to stop {name}")
                if name in self.simulators and self.simulators[name].running:
                    print(f"Stopping {name} simulator...")
                    self.simulators[name].stop()
                    self.simulators[name].join()
                else:
                    print(f"DEBUG: {name} not in simulators or not running")
        except Exception as e:
            print(f"ERROR in toggle_simulator for {name}: {e}")
            import traceback
            traceback.print_exc()

    def on_closing(self):
        print("Closing simulator...")
        for name in self.simulators:
            if self.simulators[name].running:
                self.simulators[name].stop()
                self.simulators[name].join()
        self.root.destroy()


if __name__ == "__main__":
    # Discover schemas before initializing the app
    discovered_schemas = discover_device_schemas()
    print(f"DEBUG: Discovered {len(discovered_schemas)} device(s): {list(discovered_schemas.keys())}")
    
    root = tk.Tk()
    app = SimulatorApp(root, discovered_schemas)
    print("DEBUG: Simulator GUI window created and displayed")
    root.mainloop()
