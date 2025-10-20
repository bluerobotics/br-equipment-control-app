"""
Fillhead Device Simulator
Handles fillhead-specific command simulation and state updates.
"""
import time


def handle_command(device_sim, command, args, gui_address):
    """
    Handle fillhead-specific commands.
    
    Args:
        device_sim: Reference to the DeviceSimulator instance
        command: Command string (e.g., "fillhead.machine.home")
        args: List of command arguments
        gui_address: Tuple of (ip, port) for GUI
    
    Returns:
        True if command was handled, False to use default handler
    """
    # Normalize to lowercase for case-insensitive matching
    cmd_lower = command.lower()
    
    if cmd_lower == "jog_move":
        device_sim.state['inj_mach_mm'] += float(args[0])
        device_sim.state['inj_cart_mm'] += float(args[1])
        return False  # Send generic DONE
    
    elif cmd_lower == "inject_move":
        vol = float(args[0])
        device_sim.state['inj_tgt_ml'] = vol
        device_sim.set_state('MAIN_STATE', 'INJECTING')
        device_sim.command_queue.append((simulate_injection, (device_sim, vol, 2.0, gui_address, command)))
        return True
    
    elif cmd_lower == "fillhead.machine_home":
        device_sim.set_state('MAIN_STATE', 'HOMING')
        device_sim.command_queue.append((simulate_homing, (device_sim, 'machine', 2.0, gui_address, command)))
        return True
    
    elif cmd_lower == "fillhead.cartridge_home":
        device_sim.set_state('MAIN_STATE', 'HOMING')
        device_sim.command_queue.append((simulate_homing, (device_sim, 'cartridge', 2.0, gui_address, command)))
        return True
    
    elif cmd_lower.startswith("fillhead.inj_valve_"):
        valve_type = 'inj_valve'
        if 'home' in cmd_lower:
            device_sim.set_state('MAIN_STATE', 'HOMING')
            device_sim.command_queue.append((simulate_valve_homing, (device_sim, valve_type, 1.5, gui_address, command)))
            return True
        elif 'open' in cmd_lower:
            device_sim.state[f'{valve_type}_st'] = 'Open'
        elif 'close' in cmd_lower:
            device_sim.state[f'{valve_type}_st'] = 'Closed'
        return False  # Send generic DONE
    
    elif cmd_lower.startswith("fillhead.vac_valve_"):
        valve_type = 'vac_valve'
        if 'home' in cmd_lower:
            device_sim.set_state('MAIN_STATE', 'HOMING')
            device_sim.command_queue.append((simulate_valve_homing, (device_sim, valve_type, 1.5, gui_address, command)))
            return True
        elif 'open' in cmd_lower:
            device_sim.state[f'{valve_type}_st'] = 'Open'
        elif 'close' in cmd_lower:
            device_sim.state[f'{valve_type}_st'] = 'Closed'
        return False  # Send generic DONE
    
    return False


def simulate_homing(device_sim, component, duration, gui_address, command):
    """Simulates fillhead homing process."""
    time.sleep(duration)
    if device_sim._stop_event.is_set():
        return
    
    if component == 'machine':
        device_sim.state['inj_h_mach'] = 1
        device_sim.state['inj_mach_mm'] = 0.0
    elif component == 'cartridge':
        device_sim.state['inj_h_cart'] = 1
        device_sim.state['inj_cart_mm'] = 0.0
    
    device_sim.state['inj_st'] = 'Standby'
    device_sim.set_state('MAIN_STATE', 'STANDBY')
    device_sim.sock.sendto(f"DONE: {command}".encode(), gui_address)


def simulate_valve_homing(device_sim, valve_type, duration, gui_address, command):
    """Simulates valve homing."""
    time.sleep(duration)
    if device_sim._stop_event.is_set():
        return
    
    device_sim.state[f'{valve_type}_homed'] = 1
    device_sim.state[f'{valve_type}_pos'] = 0.0
    device_sim.state[f'{valve_type}_st'] = 'Homed'
    device_sim.set_state('MAIN_STATE', 'STANDBY')
    device_sim.sock.sendto(f"DONE: {command}".encode(), gui_address)


def simulate_injection(device_sim, volume, duration, gui_address, command):
    """Simulates the injection process."""
    start_time = time.time()
    start_vol = device_sim.state['inj_active_ml']
    
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        progress = elapsed / duration
        device_sim.state['inj_active_ml'] = start_vol + volume * progress
        time.sleep(0.05)
        if device_sim._stop_event.is_set():
            return

    device_sim.state['inj_active_ml'] = 0
    device_sim.state['inj_cumulative_ml'] += volume
    device_sim.state['inj_tgt_ml'] = 0
    device_sim.set_state('MAIN_STATE', 'STANDBY')
    device_sim.sock.sendto(f"DONE: {command}".encode(), gui_address)


def update_state(device_sim):
    """Update fillhead dynamic state (called periodically)."""
    # Simulate heater PID loop
    if device_sim.state.get('h_st') == 1:
        error = device_sim.state.get('h_sp', 70) - device_sim.state.get('h_pv', 25)
        device_sim.state['h_op'] = min(100, max(0, error * 10))
        device_sim.state['h_pv'] += device_sim.state.get('h_op', 0) * 0.01 - 0.05
    else:
        device_sim.state['h_op'] = 0
        if device_sim.state.get('h_pv', 0) > 25:
            device_sim.state['h_pv'] -= 0.1


