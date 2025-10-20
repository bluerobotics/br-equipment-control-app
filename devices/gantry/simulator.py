"""
Gantry Device Simulator
Handles gantry-specific command simulation and state updates.
"""
import time


def handle_command(device_sim, command, args, gui_address):
    """
    Handle gantry-specific commands.
    
    Args:
        device_sim: Reference to the DeviceSimulator instance
        command: Command string (e.g., "gantry.move.x")
        args: List of command arguments
        gui_address: Tuple of (ip, port) for GUI
    
    Returns:
        True if command was handled, False to use default handler
    """
    # Normalize to lowercase for case-insensitive matching
    cmd_lower = command.lower()
    
    if cmd_lower.startswith("gantry.move_"):
        axis = cmd_lower.split('_')[-1]  # Get last part (x, y, or z)
        if axis in ['x', 'y', 'z']:
            dist = float(args[0])
            duration = max(0.5, abs(dist) / 50.0)
            device_sim.set_state('gantry_state', 'MOVING', f'Moving {axis.upper()}')
            device_sim.command_queue.append((simulate_move, (device_sim, axis, 
                device_sim.state.get(f'{axis}_p', 0) + dist, duration, gui_address, command)))
            return True
    
    elif cmd_lower.startswith("gantry.home_"):
        axis = cmd_lower.split('_')[-1]  # Get last part (x, y, or z)
        if axis in ['x', 'y', 'z']:
            device_sim.set_state('gantry_state', 'HOMING', f'Homing {axis.upper()}')
            device_sim.command_queue.append((simulate_homing, (device_sim, axis, 2.0, gui_address, command)))
            return True
    
    return False


def simulate_move(device_sim, axis, target_pos, duration, gui_address, command):
    """Simulates the process of a gantry move over a duration."""
    start_time = time.time()
    start_pos = device_sim.state[f'{axis}_p']
    
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        progress = elapsed / duration
        device_sim.state[f'{axis}_p'] = start_pos + (target_pos - start_pos) * progress
        time.sleep(0.05)
        if device_sim._stop_event.is_set():
            return

    device_sim.state[f'{axis}_p'] = target_pos
    device_sim.set_state('gantry_state', 'STANDBY', 'Standby')
    device_sim.sock.sendto(f"DONE: {command}".encode(), gui_address)


def simulate_homing(device_sim, axis, duration, gui_address, command):
    """Simulates the homing process."""
    time.sleep(duration)
    if device_sim._stop_event.is_set():
        return
    
    device_sim.state[f'{axis}_p'] = 0.0
    device_sim.state[f'{axis}_h'] = 1
    device_sim.set_state('gantry_state', 'STANDBY', 'Standby')
    device_sim.state[f'{axis}_st'] = 'Standby'
    device_sim.sock.sendto(f"DONE: {command}".encode(), gui_address)


def update_state(device_sim):
    """Update gantry dynamic state (called periodically)."""
    # Add any continuous state updates here if needed
    pass
