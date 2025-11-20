"""
Device Simulator - Manages device simulators for testing without hardware.

This module handles:
- Starting/stopping device simulators
- Simulated network and USB connections
- Telemetry generation and command handling
- Simulator thread management
"""

import os
import json
import threading
import socket
import time


class DeviceSimulatorManager:
    """Manages simulators for devices."""
    
    def __init__(self, device_registry, device_state, shared_gui_refs):
        """
        Initialize DeviceSimulatorManager.
        
        Args:
            device_registry: DeviceRegistry instance
            device_state: DeviceState instance
            shared_gui_refs: Dictionary of shared GUI references
        """
        self.device_registry = device_registry
        self.device_state = device_state
        self.shared_gui_refs = shared_gui_refs
        self.simulator_threads = {}  # device_name -> sim_info dict
    
    def log(self, message):
        """Log a simulator message."""
        print(f"[python] {message}")
    
    def start_simulator(self, device_name, connection_type='network'):
        """
        Start a simulator thread for a specific device.
        
        Args:
            device_name: Name of the device to simulate
            connection_type: 'network' for local network (127.0.0.1) or 'usb' for virtual USB
        """
        if device_name in self.simulator_threads:
            # Already running
            return
        
        devices = self.device_registry.get_device_modules()
        if device_name not in devices:
            self.log(f"Cannot start simulator for unknown device: {device_name}")
            return
        
        # Get device port (auto-assigned based on sorted device order)
        device_names = sorted(devices.keys())
        base_port = 8888
        device_port = base_port + device_names.index(device_name)
        
        # Get device path
        device_data = devices[device_name]
        device_path = device_data['path']
        
        # Load telemetry schema for initial state
        telemetry_data = device_data.get('telemetry_data', {})
        initial_state = {key: details.get('default', '---') 
                        for key, details in telemetry_data.items()}
        
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
        
        # Mark as simulated
        self.device_state.update_state(device_name, {'simulated': True})
        
        # If USB simulation, set connection method to USB with virtual port
        if connection_type == 'usb':
            virtual_port = "VIRTUAL_COM"
            self.device_state.set_connection_method(device_name, 'usb', virtual_port)
            self.log(f"Started USB simulator for {device_name} (virtual port: {virtual_port})")
        else:
            self.log(f"Started network simulator for {device_name} on 127.0.0.1:{device_port}")
            # Trigger a discovery to connect to the newly started simulator
            from .. import comms
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
        self.device_state.update_state(device_name, {'simulated': False})
        
        self.log(f"Stopped simulator for {device_name}")
    
    def _simulator_worker(self, device_name, sim_socket, state, stop_flag, port, connection_type='network'):
        """
        Worker thread for device simulator.
        
        Args:
            device_name: Name of the device
            sim_socket: Socket for communication
            state: Dictionary of simulated state
            stop_flag: Threading event to signal stop
            port: Port number
            connection_type: 'network' for UDP or 'usb' for simulated serial
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
                        from .. import comms
                        # Need to pass device_manager, but we don't have direct access
                        # This will be handled when integrating back into DeviceManager
                        comms.handle_serial_message(device_name, telemetry_msg, self.shared_gui_refs, None)
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
                            from .. import comms
                            comms.handle_serial_message(device_name, response, self.shared_gui_refs, None)
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
                            from .. import comms
                            comms.handle_serial_message(device_name, response, self.shared_gui_refs, None)
                        except:
                            pass
                    else:
                        sim_socket.sendto(response.encode(), addr)
                
            except socket.timeout:
                continue
            except:
                break
        
        # Cleanup
        try:
            sim_socket.close()
        except:
            pass
    
    def is_simulator_running(self, device_name):
        """Check if a simulator is currently running for a device."""
        return device_name in self.simulator_threads
    
    def stop_all_simulators(self):
        """Stop all running simulators."""
        for device_name in list(self.simulator_threads.keys()):
            self.stop_simulator(device_name)

