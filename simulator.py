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
CLEARCORE_PORT = 8888
GUI_APP_PORT = 6272
TELEMETRY_INTERVAL = 1.0  # seconds
BASE_IP = "127.0.0.1"

def discover_device_schemas():
    """Scans the 'devices' directory and dynamically loads telemetry schemas from JSON files."""
    schemas = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The 'devices' directory is now at the same level as this script.
    devices_path = os.path.join(script_dir, 'devices')

    if not os.path.exists(devices_path):
        print(f"Device directory not found at: {devices_path}")
        return schemas

    for device_name in os.listdir(devices_path):
        device_dir = os.path.join(devices_path, device_name)
        schema_file = os.path.join(device_dir, 'telemetry.json')
        if os.path.isdir(device_dir) and os.path.exists(schema_file):
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                    # We need the default values, not the GUI config, for the simulator state
                    initial_state = {key: details.get('default', '---') 
                                     for key, details in schema_data.items()}
                    schemas[device_name] = initial_state
                    print(f"Loaded schema for device: {device_name}")
            except Exception as e:
                print(f"Could not load schema for {device_name}: {e}")
    return schemas

class DeviceSimulator(threading.Thread):
    def __init__(self, device_name, ip, port, gui_app_port, schema):
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
        self.command_queue = deque()

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
                    response = f"DISCOVERY_RESPONSE: DEVICE_ID={self.device_name}"
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
        """A more sophisticated command handler that simulates device states."""
        parts = msg.split()
        command = parts[0]
        args = parts[1:]
        
        # Generic response for any command that isn't special-cased
        response = f"DONE: {command}"

        try:
            # --- Device-Specific Command Simulation ---
            # (This section can be expanded with more complex, device-specific logic if needed)
            if self.device_name == 'gantry':
                if command.startswith("MOVE_"):
                    axis = command.split('_')[1].lower()
                    if axis in ['x', 'y', 'z']:
                        dist = float(args[0])
                        duration = max(0.5, abs(dist) / 50.0)
                        self.set_state('gantry_state', 'MOVING', f'Moving {axis.upper()}')
                        self.command_queue.append((self.simulate_move, (axis, self.state.get(f'{axis}_p', 0) + dist, duration, gui_address, command)))
                        return
                elif command.startswith("HOME_"):
                    axis = command.split('_')[1].lower()
                    if axis in ['x', 'y', 'z']:
                        self.set_state('gantry_state', 'HOMING', f'Homing {axis.upper()}')
                        self.command_queue.append((self.simulate_homing, (axis, 2.0, gui_address, command)))
                        return

            elif self.device_name == 'fillhead':
                if command == "JOG_MOVE":
                    self.state['inj_mach_mm'] += float(args[0])
                    self.state['inj_cart_mm'] += float(args[1])
                elif command == "INJECT_MOVE":
                    vol = float(args[0])
                    self.state['inj_tgt_ml'] = vol
                    self.set_state('MAIN_STATE', 'INJECTING')
                    self.command_queue.append((self.simulate_injection, (vol, 2.0, gui_address, command)))
                    return
        
        except (IndexError, ValueError) as e:
            print(f"[{self.device_name}] Error parsing command '{msg}': {e}")
            response = f"ERROR: Invalid arguments for {command}"
        except Exception as e:
            print(f"[{self.device_name}] Unexpected error handling command '{msg}': {e}")
            response = f"ERROR: Internal simulator error on {command}"


        self.sock.sendto(response.encode(), gui_address)
        print(f"[{self.device_name}] Responded to {command} with '{response}'")

    def set_state(self, main_state_key, main_state_val, axis_state_val=None):
        """Helper to set device and axis states."""
        self.state[main_state_key] = main_state_val
        if axis_state_val and self.device_name == 'gantry':
            for axis in ['x', 'y', 'z']:
                self.state[f'{axis}_st'] = axis_state_val

    def simulate_move(self, axis, target_pos, duration, gui_address, command):
        """Simulates the process of a gantry move over a duration."""
        start_time = time.time()
        start_pos = self.state[f'{axis}_p']
        
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            progress = elapsed / duration
            self.state[f'{axis}_p'] = start_pos + (target_pos - start_pos) * progress
            time.sleep(0.05) # Update rate
            if self._stop_event.is_set(): return

        self.state[f'{axis}_p'] = target_pos
        self.set_state('gantry_state', 'STANDBY', 'Standby')
        self.sock.sendto(f"DONE: {command}".encode(), gui_address)

    def simulate_homing(self, axis, duration, gui_address, command):
        """Simulates the homing process."""
        time.sleep(duration)
        if self._stop_event.is_set(): return
        self.state[f'{axis}_p'] = 0.0
        self.state[f'{axis}_h'] = 1
        self.set_state('gantry_state', 'STANDBY', 'Standby')
        self.state[f'{axis}_st'] = 'Standby' # Set specific axis to standby
        self.sock.sendto(f"DONE: {command}".encode(), gui_address)

    def simulate_fillhead_homing(self, component, duration, gui_address, command):
        """Simulates the homing process for various fillhead components."""
        time.sleep(duration)
        if self._stop_event.is_set(): return
        
        if component == 'machine':
            self.state['inj_mach_mm'] = 0.0
            self.state['inj_h_mach'] = 1
            self.state['inj_st'] = 'Standby'
        elif component == 'cartridge':
            self.state['inj_cart_mm'] = 0.0
            self.state['inj_h_cart'] = 1
            # Assuming machine homing implies cartridge is also ready to be used
            self.state['inj_st'] = 'Standby'
        elif component == 'injection_valve':
            self.state['inj_valve_pos'] = 0.0
            self.state['inj_valve_homed'] = 1
            self.state['inj_v_st'] = 'Standby'
        elif component == 'vacuum_valve':
            self.state['vac_valve_pos'] = 0.0
            self.state['vac_valve_homed'] = 1
            self.state['vac_v_st'] = 'Standby'

        self.set_state('MAIN_STATE', 'STANDBY')
        self.sock.sendto(f"DONE: {command}".encode(), gui_address)

    def simulate_injection(self, volume, duration, gui_address, command):
        """Simulates the injection process."""
        start_time = time.time()
        start_vol = self.state['inj_active_ml']
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            progress = elapsed / duration
            self.state['inj_active_ml'] = start_vol + volume * progress
            time.sleep(0.05)
            if self._stop_event.is_set(): return

        self.state['inj_active_ml'] = 0
        self.state['inj_cumulative_ml'] += volume
        self.state['inj_tgt_ml'] = 0
        self.set_state('MAIN_STATE', 'STANDBY')
        self.sock.sendto(f"DONE: {command}".encode(), gui_address)


    def update_state(self):
        """Periodically update dynamic state values like temperature."""
        if self.device_name == 'fillhead':
            # Simulate heater PID loop
            if self.state.get('h_st') == 1:
                error = self.state.get('h_sp', 70) - self.state.get('h_pv', 25)
                self.state['h_op'] = min(100, max(0, error * 10))
                self.state['h_pv'] += self.state.get('h_op', 0) * 0.01 - 0.05
            else:
                self.state['h_op'] = 0
                if self.state.get('h_pv', 0) > 25:
                    self.state['h_pv'] -= 0.1

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
        self.root.title("St8erBoi Device Simulator")
        self.simulators = {}
        self.device_schemas = device_schemas
        self.device_vars = {}

        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Dynamically create checkbuttons for each discovered device
        row = 0
        for device_name in sorted(self.device_schemas.keys()):
            self.device_vars[device_name] = tk.BooleanVar()
            cb = ttk.Checkbutton(
                frame,
                text=f"Simulate {device_name.capitalize()}",
                variable=self.device_vars[device_name],
                command=lambda name=device_name: self.toggle_simulator(name, self.device_vars[name].get())
            )
            cb.grid(row=row, column=0, sticky=tk.W, pady=2)
            
            # Each device listens on the same port for discovery, but on a unique IP.
            # For simulation, we just use localhost.
            ttk.Label(frame, text=f"IP: {BASE_IP} Port: {CLEARCORE_PORT}").grid(row=row, column=1, sticky=tk.W, padx=5)
            row += 1

        if not self.device_schemas:
            ttk.Label(frame, text="No device schemas found. Check paths and telemetry.json files.").grid(row=0, column=0)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_simulator(self, name, start):
        if start:
            if name not in self.simulators or not self.simulators[name].running:
                print(f"Starting {name} simulator...")
                schema = self.device_schemas[name]
                sim = DeviceSimulator(name, BASE_IP, CLEARCORE_PORT, GUI_APP_PORT, schema)
                self.simulators[name] = sim
                sim.start()
        else:
            if name in self.simulators and self.simulators[name].running:
                print(f"Stopping {name} simulator...")
                self.simulators[name].stop()
                self.simulators[name].join()

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
    
    root = tk.Tk()
    app = SimulatorApp(root, discovered_schemas)
    root.mainloop()
