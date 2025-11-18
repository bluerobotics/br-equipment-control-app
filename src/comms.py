import socket
import threading
import time
import datetime
import tkinter as tk
import json
from queue import Empty
from . import serial_comms

try:
    from .clearcore_firmware import schedule_version_check
except ImportError:
    schedule_version_check = None

# --- Constants ---
CLEARCORE_PORT = 8888
CLIENT_PORT = 6272
HEARTBEAT_INTERVAL = 0.5
DISCOVERY_INTERVAL = 2.0
TIMEOUT_THRESHOLD = 3.0

# --- Helper ---
def safe_float(s, default_val=0.0):
    try:
        # Strip trailing periods before conversion to handle malformed data like "25."
        return float(s.strip().rstrip('.'))
    except (ValueError, TypeError):
        return default_val

# --- Global State ---
last_fw_main_state_for_gui_update = None
last_fw_feed_state_for_gui_update = None

# --- Communication State ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(('', CLIENT_PORT))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.1)
except OSError as e:
    print(f"ERROR binding socket: {e}. Port {CLIENT_PORT} may be in use by another application.")
    exit()

# MODIFIED: Added a threading lock to prevent race conditions on the socket.
socket_lock = threading.Lock()
devices_lock = threading.Lock() # This can still be useful to protect access to device_manager state


# --- Communication Functions ---

def log_to_terminal(msg, gui_refs):
    """Safely logs a message to the GUI terminal by placing it on the queue."""
    timestr = datetime.datetime.now().strftime("[%H:%M:%S.%f]")[:-3]
    full_msg = f"{timestr} {msg}\n"
    
    # Also log to system logger if available
    # The logger will see the timestamp in full_msg and won't add another one
    try:
        from .system_logger import get_system_logger
        logger = get_system_logger()
        if logger:
            # Pass message with timestamp - logger will detect it and not add another
            logger.log_message(full_msg.rstrip('\n'), is_error=False)
    except Exception:
        pass  # Ignore errors in logging system
    
    terminal_cb = gui_refs.get('terminal_cb')
    gui_queue = gui_refs.get('gui_queue')

    if terminal_cb and gui_queue:
        # The terminal_cb function itself is what needs to run in the main thread.
        gui_queue.put((terminal_cb, (full_msg,), {}))
    else:
        # Fallback for when GUI elements aren't available
        print(full_msg)

def show_recovery_warning(device_name, msg, gui_refs):
    """Shows a critical warning dialog for watchdog recovery."""
    from tkinter import messagebox
    
    # Extract the message after the prefix
    message_text = msg.split(":", 1)[1].strip() if ":" in msg else msg
    
    messagebox.showerror(
        f"{device_name} - WATCHDOG RECOVERY",
        f"⚠️ CRITICAL SYSTEM RECOVERY ⚠️\n\n"
        f"Device: {device_name}\n\n"
        f"{message_text}\n\n"
        f"The device's main loop was blocked for too long,\n"
        f"causing the watchdog timer to trigger a reset.\n\n"
        f"Motors have been disabled for safety.\n"
        f"Send RESET command to clear this state.",
        icon='error'
    )


def discover_devices(gui_refs):
    """Sends a generic discovery message."""
    msg = f"DISCOVER_DEVICE PORT={CLIENT_PORT}"

    log_discovery = gui_refs.get('show_discovery_var', tk.BooleanVar(value=False)).get()
    if log_discovery:
        log_to_terminal(f"[CMD SENT to BROADCAST]: {msg}", gui_refs)

    try:
        # Broadcast to network devices
        sock.sendto(msg.encode(), ('192.168.1.255', CLEARCORE_PORT))
        
        # Also send to localhost simulators on their individual ports
        # They listen on sequential ports starting at CLEARCORE_PORT
        for port_offset in range(4):  # Support up to 4 local simulators
            try:
                sock.sendto(msg.encode(), ('127.0.0.1', CLEARCORE_PORT + port_offset))
            except:
                pass  # Silently ignore if no simulator on that port
    except Exception as e:
        log_to_terminal(f"Discovery error: {e}", gui_refs)


def discovery_loop(gui_refs):
    """Continuously sends out discovery messages."""
    while True:
        discover_devices(gui_refs)
        time.sleep(DISCOVERY_INTERVAL)


def send_to_device(device_key, msg, gui_refs):
    """Sends a message to a specific device via network or USB based on connection method."""
    device_manager = gui_refs.get('device_manager')
    if not device_manager: return
    
    with devices_lock:
        device_state = device_manager.get_device_state(device_key)
        if not device_state:
            return
        
        connection_method = device_state.get('connection_method', 'network')
    
    # Route based on connection method
    if connection_method == 'usb':
        # Send via USB serial
        serial_port = device_state.get('serial_port')
        if serial_port:
            try:
                from . import serial_comms
                log_to_terminal(f"[CMD SENT to {device_key.upper()} via USB]: {msg}", gui_refs)
                serial_comms.send_serial_command(serial_port, msg)
            except Exception as e:
                log_to_terminal(f"Error sending to {device_key} via USB: {e}", gui_refs)
        else:
            if msg not in ["cancel", "reset"]:
                log_to_terminal(f"Cannot send to {device_key}: No serial port configured.", gui_refs)
    else:
        # Send via network (original behavior)
        if device_state and device_state.get("ip"):
            device_ip = device_state.get("ip")
            # Use the device's specific port if stored, otherwise use default
            device_port = device_state.get("port", CLEARCORE_PORT)
            # MODIFIED: Added a lock to ensure thread-safe socket access.
            with socket_lock:
                try:
                    log_to_terminal(f"[CMD SENT to {device_key.upper()}]: {msg}", gui_refs)
                    sock.sendto(msg.encode(), (device_ip, device_port))
                except Exception as e:
                    log_to_terminal(f"Error sending to {device_key}: {e}", gui_refs)

        elif "DISCOVER" not in msg:
            # Only log if it's not a cancel or reset command (which are sent to all devices)
            if msg not in ["cancel", "reset"]:
                log_to_terminal(f"Cannot send to {device_key}: IP unknown.", gui_refs)


def handle_serial_message(device_key, message, gui_refs, device_manager):
    """
    Handles incoming messages from USB serial connections.
    Processes them the same way as UDP messages.
    
    Args:
        device_key (str): The device key (e.g. 'pressboi')
        message (str): The message received
        gui_refs (dict): GUI references
        device_manager: The device manager instance
    """
    msg = message.strip()
    if not msg:
        return
    
    # Mark device as connected via USB and update last_rx for ANY message received
    is_new_connection = False
    with devices_lock:
        device_state = device_manager.get_device_state(device_key)
        if device_state:
            was_connected = device_state.get("connected", False)
            if not was_connected:
                is_new_connection = True
            # Always update last_rx when we receive ANY message - this prevents timeout
            device_manager.update_device_state(device_key, {
                "connected": True,
                "last_rx": time.time()
            })
    
    # Update status variable for GUI on first connection
    if is_new_connection:
        serial_port = device_state.get('serial_port', 'USB')
        status_text = f"{device_key.capitalize()} ({serial_port})"
        log_to_terminal(f"{device_key.capitalize()} connected ({serial_port})", gui_refs)
        
        gui_queue = gui_refs.get('gui_queue')
        
        # Queue showing the panel first
        show_panel_fn = gui_refs.get('show_panel')
        if show_panel_fn:
            if gui_queue:
                gui_queue.put((show_panel_fn, (device_key,), {}))
            else:
                show_panel_fn(device_key)
        
        # Then update the status variable
        status_var = gui_refs.get(f'status_var_{device_key}')
        if status_var:
            if gui_queue:
                gui_queue.put((status_var.set, (status_text,), {}))
            else:
                status_var.set(status_text)
        
        # Queue the visibility update for the "searching" panel
        if gui_queue:
            gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
        else:
            update_searching_panel_visibility(gui_refs)
        
        # Refresh the command reference to update the device tree after a small delay
        # This ensures the status variable has been updated before refresh
        command_ref = gui_refs.get('command_reference')
        root = gui_refs.get('root')
        if command_ref and root:
            root.after(100, command_ref.refresh)
    
    # Process the message (same logic as recv_loop, but without IP)
    log_telemetry = gui_refs.get('show_telemetry_var', tk.BooleanVar(value=False)).get()
    log_events = gui_refs.get('show_events_var', tk.BooleanVar(value=False)).get()
    device_modules = device_manager.devices
    
    try:
        # Handle discovery responses - parse firmware version
        if msg.startswith("DISCOVERY_RESPONSE:"):
            try:
                # Parse firmware version from discovery response
                # Format: DISCOVERY_RESPONSE: DEVICE_ID=pressboi PORT=8888 FW=1.6.0
                parts = msg.split()
                for part in parts[1:]:  # Skip "DISCOVERY_RESPONSE:"
                    if "=" in part:
                        key, value = part.split("=", 1)
                        if key in ("FW", "FIRMWARE", "VERSION"):
                            device_manager.update_device_state(device_key, {"firmware_version": value})
                            break
            except Exception as e:
                log_to_terminal(f"Error parsing USB discovery firmware version: {e}", gui_refs)
            return
        
        # Handle telemetry
        if "_TELEM:" in msg:
            try:
                if device_key in device_modules:
                    # Always log that telemetry was received (for debugging)
                    if log_telemetry:
                        log_to_terminal(f"[TELEM via USB]: {msg}", gui_refs)
                    
                    device_info = device_modules[device_key]
                    parser_module = device_info.get('parser')
                    telemetry_data = device_info.get('telemetry_data', {})
                    parsed_data = {}
                    if parser_module and hasattr(parser_module, 'parse_telemetry'):
                        # Use module-level queue_ui_update function
                        parser_module.parse_telemetry(msg, telemetry_data, gui_refs, queue_ui_update, safe_float)
                    else:
                        # Use module-level queue_ui_update function
                        parsed_data = parse_dynamic_telemetry(msg, device_key, telemetry_data, gui_refs, queue_ui_update, safe_float)
                    
                    if parsed_data:
                        device_manager.notify_telemetry_callbacks(device_key, parsed_data)
                else:
                    # Device not configured - log as telemetry (filtered by telemetry checkbox)
                    # but don't parse or process it
                    if log_telemetry:
                        log_to_terminal(f"[TELEM via USB]: {msg}", gui_refs)
            except Exception as e:
                log_to_terminal(f"Error processing USB telemetry: {e}", gui_refs)
        
        # Handle recovery messages
        elif "_RECOVERY:" in msg or msg.startswith("RECOVERY:"):
            log_to_terminal(f"[RECOVERY via USB]: {msg}", gui_refs)
            device_name = device_key.upper()
            gui_queue = gui_refs.get('gui_queue')
            if gui_queue:
                gui_queue.put((show_recovery_warning, (device_name, msg, gui_refs), {}))
        
        # Handle NVM dump messages
        elif msg.startswith("NVMDUMP:"):
            show_cb = gui_refs.get('show_nvm_dump_cb')
            gui_queue = gui_refs.get('gui_queue')
            if show_cb and gui_queue:
                try:
                    _, dev_key, payload = msg.split(":", 2)
                    gui_queue.put((show_cb, (dev_key.lower(), payload), {}))
                except ValueError:
                    pass
            log_to_terminal(f"[STATUS via USB]: {msg}", gui_refs)
        
        # Handle other status messages
        elif is_status_message(msg, device_manager):
            log_to_terminal(f"[STATUS via USB]: {msg}", gui_refs)
        
        else:
            log_to_terminal(f"[UNHANDLED via USB]: {msg}", gui_refs)
            
    except Exception as e:
        log_to_terminal(f"Error processing USB message: {e}", gui_refs)


def monitor_connections(gui_refs, device_manager):
    """Monitors device connection status."""
    terminal_cb = gui_refs.get('terminal_cb')
    gui_queue = gui_refs.get('gui_queue')

    while True:
        now = time.time()
        with devices_lock:
            # Create a copy of items to avoid issues with dictionary size changes during iteration
            device_items = list(device_manager.get_all_device_states().items())

        for key, device in device_items:
            with devices_lock:
                # Re-fetch the device's current state inside the lock
                device_state = device_manager.get_device_state(key)
                if not device_state: continue
                prev_conn_status = device_state["connected"]
                fw_update_in_progress = device_state.get("fw_update_in_progress", False)

            # Skip disconnection handling if firmware update is in progress
            # The device will intentionally disconnect when rebooting into bootloader mode
            if fw_update_in_progress:
                # Device is expected to disconnect during firmware update - don't treat as error
                continue

            # Use longer timeout for USB connections (they may take longer to establish communication)
            connection_method = device_state.get("connection_method", "network")
            timeout = TIMEOUT_THRESHOLD * 2 if connection_method == "usb" else TIMEOUT_THRESHOLD
            
            if prev_conn_status and (now - device_state["last_rx"]) > timeout:
                with devices_lock:
                    device_manager.update_device_state(key, {"connected": False, "ip": None})
                
                log_to_terminal(f"{key.capitalize()} Disconnected", gui_refs)
                
                # Queue the panel reset/hide function to run on the main thread
                if gui_queue and 'reset_and_hide_panel' in gui_refs:
                    gui_queue.put((gui_refs['reset_and_hide_panel'], (key,), {}))
                
                # Also queue the visibility update for the "searching" panel
                if gui_queue:
                    gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
                
                # If a script is running, abort it due to device disconnection
                if gui_queue and 'abort_script_on_disconnect' in gui_refs:
                    gui_queue.put((gui_refs['abort_script_on_disconnect'], (key,), {}))

        time.sleep(HEARTBEAT_INTERVAL)


def update_searching_panel_visibility(gui_refs):
    """Shows or hides the 'searching for devices' panel."""
    searching_frame = gui_refs.get('searching_frame')
    status_bar_container = gui_refs.get('status_bar_container')
    device_manager = gui_refs.get('device_manager')
    
    if not searching_frame or not device_manager:
        return
    
    # Check if any devices are connected
    any_connected = False
    with devices_lock:
        device_states = device_manager.get_all_device_states()
        for device_state in device_states.values():
            if device_state.get("connected"):
                any_connected = True
                break
    
    # This function is now executed by the main thread, so it's safe to modify the GUI
    if any_connected:
        # Hide searching panel when devices are connected
        try:
            searching_frame.pack_forget()
        except tk.TclError:
            pass  # Widget might have been destroyed
    else:
        # Show searching panel when no devices are connected
        try:
            # Check if searching_frame is already packed
            try:
                searching_frame.pack_info()
                # Already packed, nothing to do
            except tk.TclError:
                # Not packed, need to pack it
                if status_bar_container:
                    # Try to pack before status_bar_container
                    try:
                        # Ensure status_bar_container is packed first
                        try:
                            status_bar_container.pack_info()
                        except tk.TclError:
                            # Container is not packed, pack it first
                            parent = status_bar_container.master
                            if parent:
                                status_bar_container.pack(side=tk.TOP, fill='x', expand=False)
                        
                        # Pack searching_frame before status_bar_container
                        searching_frame.pack(before=status_bar_container, side=tk.TOP, fill="x", expand=False, pady=(0, 8))
                    except tk.TclError:
                        # Fallback: pack normally if 'before' doesn't work
                        try:
                            searching_frame.pack(side=tk.TOP, fill="x", expand=False, pady=(0, 8))
                        except tk.TclError:
                            pass  # Widget might have been destroyed
                else:
                    # No status_bar_container, just pack normally
                    try:
                        searching_frame.pack(side=tk.TOP, fill="x", expand=False, pady=(0, 8))
                    except tk.TclError:
                        pass  # Widget might have been destroyed
        except tk.TclError:
            pass  # Widget might have been destroyed

def queue_ui_update(gui_refs, var_name, value):
    """Safely queues a tkinter variable update."""
    gui_queue = gui_refs.get('gui_queue')
    var = gui_refs.get(var_name)
    if gui_queue and var:
        # Convert value type if necessary for DoubleVar
        if isinstance(var, tk.DoubleVar):
            value = safe_float(value)
        gui_queue.put((var.set, (value,), {}))
    else:
        if not gui_queue:
            pass
        if not var:
            pass

def handle_connection(device_key, source_ip, gui_refs, device_manager):
    """Handles the logic for a new or existing connection."""
    gui_queue = gui_refs.get('gui_queue')
    is_new_connection = False

    with devices_lock:
        device_state = device_manager.get_device_state(device_key)
        if not device_state:
            return
        
        # Don't handle network connection if device is configured for USB AND actually connected via USB
        # If USB connection failed, we should accept network connection instead
        if device_state.get('connection_method') == 'usb' and device_state.get('connected'):
            return
        
        was_connected = device_state.get("connected", False)
        if not was_connected:
            is_new_connection = True
        
        # If we're here and connection_method was 'usb', it means USB failed - switch to network
        updates = {
            "ip": source_ip,
            "last_rx": time.time(),
            "connected": True
        }
        
        # Don't automatically switch to network if USB is the configured method
        # The user must manually switch via the UI if they want to use network instead
        # This prevents network discovery from interrupting USB connections
        
        device_manager.update_device_state(device_key, updates)

    if is_new_connection:
        status_text = f"{device_key.capitalize()} ({source_ip})"
        log_to_terminal(f"{device_key}: Connected via Ethernet on {source_ip}", gui_refs)
        
        status_var = gui_refs.get(f'status_var_{device_key}')
        if status_var:
            if gui_queue:
                # Queue the status variable update
                gui_queue.put((status_var.set, (status_text,), {}))
            else:
                status_var.set(status_text)
        
        # Queue showing the panel
        show_panel_fn = gui_refs.get('show_panel')
        if show_panel_fn:
            if gui_queue:
                gui_queue.put((show_panel_fn, (device_key,), {}))
            else:
                show_panel_fn(device_key)
        
        # Queue the visibility update for the "searching" panel
        if gui_queue:
            gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
        else:
            update_searching_panel_visibility(gui_refs)
        
        # Refresh the command reference to update the device tree after a small delay
        # This ensures the status variable has been updated before refresh
        command_ref = gui_refs.get('command_reference')
        root = gui_refs.get('root')
        if command_ref and root:
            root.after(100, command_ref.refresh)

        if schedule_version_check:
            with devices_lock:
                state = device_manager.get_device_state(device_key)
                already_scheduled = state.get('fw_check_scheduled') if state else True
                if state and not already_scheduled:
                    device_manager.update_device_state(device_key, {"fw_check_scheduled": True})
            if not already_scheduled:
                schedule_version_check(device_key, gui_refs, device_manager)


def is_status_message(msg, device_manager):
    """
    Checks if a message is a known status message, either generic or device-specific.
    This check is dynamic and uses the current state of the device_manager.
    """
    if msg.startswith(("INFO:", "DONE:", "ERROR:", "RECOVERY:")):
        return True
    
    device_modules = device_manager.get_device_modules()
    for key, data in device_modules.items():
        # Check for standard prefixes (e.g., GANTRY_DONE:)
        if msg.startswith(key.upper() + "_"):
            return True
            
    return False


# --- Dynamic Telemetry Parser ---
def parse_dynamic_telemetry(msg, device_name, schema, gui_refs, queue_ui_update, safe_float):
    """
    Dynamically parses a telemetry string based on a provided schema.
    Supports enum mapping, numeric formatting with precision and units.
    Returns a dictionary of parsed telemetry values (key -> raw_value).
    """
    parsed_data = {}
    try:
        # Extract the key-value payload from the message
        prefix = f"{device_name.upper()}_TELEM:"
        
        # Case-insensitive check and split
        if prefix.lower() not in msg.lower():
            return parsed_data
        
        payload_start = msg.lower().find(prefix.lower()) + len(prefix)
        payload = msg[payload_start:].strip()
        
        # Support both formats: key:value,key:value and key=value;key=value
        if ';' in payload and '=' in payload:
            # New format: key=value;key=value
            parts = dict(item.split('=', 1) for item in payload.split(';') if '=' in item)
        else:
            # Legacy format: key:value,key:value
            parts = dict(item.split(':', 1) for item in payload.split(',') if ':' in item)

        # Process each key-value pair from the message
        for key, value in parts.items():
            key_match = key.strip()
            if key_match in schema:
                details = schema[key_match]
                # Auto-generate gui_var if not provided: device_key_var
                gui_var_name = details.get('gui_var', f"{device_name}_{key_match}_var")

                if gui_var_name:
                    formatted_value = value.strip()
                    
                    # Store raw value for callbacks
                    parsed_data[key_match] = formatted_value
                    
                    # First, check for enum mapping at top level
                    if 'map' in details:
                        # Map the enum value (int or string) to its display string
                        if formatted_value in details['map']:
                            formatted_value = details['map'][formatted_value]
                    # Then handle numeric formatting with precision and units
                    elif details.get('type') in ['float', 'int']:
                        try:
                            num_value = safe_float(formatted_value)
                            
                            # Apply multiplier if it exists
                            if 'multiplier' in details:
                                num_value *= details['multiplier']

                            precision = details.get('precision')
                            unit = details.get('unit', '')
                            
                            if precision is not None:
                                formatted_value = f"{num_value:.{precision}f}"
                            else:
                                formatted_value = f"{num_value}"
                            
                            # Add unit if present
                            if unit:
                                formatted_value = f"{formatted_value} {unit}"
                        except (ValueError, TypeError):
                            # Keep original value if conversion fails
                            pass
                    
                    # Handle legacy 'format' structure for backward compatibility
                    elif 'format' in details:
                        rules = details['format']
                        if 'map' in rules and formatted_value in rules['map']:
                            formatted_value = rules['map'][formatted_value]
                        else:
                            # Handle numeric formatting for precision and suffix
                            try:
                                num_value = safe_float(formatted_value)
                                
                                # Apply multiplier if it exists
                                if 'multiplier' in rules:
                                    num_value *= rules['multiplier']

                                precision = rules.get('precision')
                                suffix = rules.get('suffix', '')
                                
                                if precision is not None:
                                    formatted_value = f"{num_value:.{precision}f}{suffix}"
                                else:
                                    formatted_value = f"{num_value}{suffix}"
                            except (ValueError, TypeError):
                                formatted_value = formatted_value + rules.get('suffix', '')

                    queue_ui_update(gui_refs, gui_var_name, formatted_value)

    except Exception as e:
        log_func = gui_refs.get('log_func')
        if log_func:
            log_func(f"{device_name.capitalize()} telem parse error: {e}, msg: {msg}")
    
    return parsed_data


# --- Main Receive Loop ---

def recv_loop(gui_refs, device_manager):
    """Main network receive loop. Routes packets to the correct local parser."""
    # Don't cache device_modules - get it fresh each iteration to pick up newly added devices
    # device_modules = device_manager.get_device_modules()  # Removed - get fresh each time

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8', errors='replace').strip()
            source_ip = addr[0]
            log_telemetry = gui_refs.get('show_telemetry_var', tk.BooleanVar(value=False)).get()

            if msg.startswith("DISCOVERY_RESPONSE:"):
                try:
                    # e.g., DISCOVERY_RESPONSE: DEVICE_ID=gantry PORT=8889
                    parts = msg.split()
                    device_key = None
                    device_port = None
                    device_fw = None
                    
                    for part in parts[1:]:  # Skip "DISCOVERY_RESPONSE:"
                        if "=" in part:
                            key, value = part.split("=", 1)
                            if key == "DEVICE_ID":
                                device_key = value.lower()
                            elif key == "PORT":
                                device_port = int(value)
                            elif key in ("FW", "FIRMWARE", "VERSION"):
                                device_fw = value
                    
                    # Get fresh device_modules to pick up newly added devices
                    device_modules = device_manager.get_device_modules()
                    if device_key and device_key in device_modules:
                        # Check if device is configured for USB - if so, ignore network discovery
                        with devices_lock:
                            device_state = device_manager.get_device_state(device_key)
                            if device_state and device_state.get('connection_method') == 'usb':
                                continue  # Ignore network discovery for USB devices
                        
                        # Store the port if provided, otherwise use default
                        if device_port:
                            with devices_lock:
                                device_state = device_manager.get_device_state(device_key)
                                if device_state:
                                    device_state['port'] = device_port
                        if device_fw:
                            with devices_lock:
                                device_state = device_manager.get_device_state(device_key)
                                if device_state:
                                    device_state['firmware_version'] = device_fw
                        
                        handle_connection(device_key, source_ip, gui_refs, device_manager)
                except (IndexError, ValueError) as e:
                    log_to_terminal(f"Malformed discovery response: {msg} - {e}", gui_refs)
            
            # --- DYNAMIC TELEMETRY PARSING ---
            elif "_TELEM:" in msg:
                try:
                    device_key = msg.split("_TELEM:")[0].lower()
                    # Get fresh device_modules to pick up newly added devices
                    device_modules = device_manager.get_device_modules()
                    
                    if device_key in device_modules:
                        # Update connection state based on telemetry
                        # BUT: Don't mark as connected if device is configured for USB - let USB handle that
                        is_new_connection = False
                        with devices_lock:
                            device_state = device_manager.get_device_state(device_key)
                            if device_state:
                                connection_method = device_state.get('connection_method', 'network')
                                was_connected = device_state.get('connected', False)
                                
                                # Only update connection state if device is using network connection
                                # If using USB, completely ignore network telemetry
                                if connection_method == 'network':
                                    if not was_connected:
                                        is_new_connection = True
                                    device_manager.update_device_state(device_key, {
                                        "connected": True,
                                        "last_rx": time.time(),
                                        "ip": source_ip
                                    })
                                # If USB is configured, ignore network telemetry entirely
                                # Don't even update the IP
                        
                        # Update status variable if this is a new network connection
                        if is_new_connection:
                            status_text = f"{device_key.capitalize()} ({source_ip})"
                            log_to_terminal(f"{device_key}: Connected via Ethernet on {source_ip}", gui_refs)
                            
                            status_var = gui_refs.get(f'status_var_{device_key}')
                            if status_var:
                                gui_queue = gui_refs.get('gui_queue')
                                if gui_queue:
                                    gui_queue.put((status_var.set, (status_text,), {}))
                                else:
                                    status_var.set(status_text)
                            
                            # Show the panel if it was hidden
                            show_panel_fn = gui_refs.get('show_panel')
                            if show_panel_fn:
                                gui_queue = gui_refs.get('gui_queue')
                                if gui_queue:
                                    gui_queue.put((show_panel_fn, (device_key,), {}))
                                else:
                                    show_panel_fn(device_key)
                            
                            # Update searching panel visibility
                            gui_queue = gui_refs.get('gui_queue')
                            if gui_queue:
                                gui_queue.put((update_searching_panel_visibility, (gui_refs,), {}))
                        
                        if log_telemetry:
                            log_to_terminal(f"[TELEM @{source_ip}]: {msg}", gui_refs)
                        
                        # Call the dynamically loaded parser
                        device_info = device_modules[device_key]
                        parser_module = device_info.get('parser')
                        telemetry_data = device_info.get('telemetry_data', {})
                        
                        parsed_data = {}
                        if parser_module and hasattr(parser_module, 'parse_telemetry'):
                            # The schema is now passed to the parser
                            parser_module.parse_telemetry(msg, telemetry_data, gui_refs, queue_ui_update, safe_float)
                            # Note: Custom parsers don't return parsed_data, so callbacks won't be notified
                        else:
                            # Fallback to dynamic parsing if no specific parser
                            parsed_data = parse_dynamic_telemetry(msg, device_key, telemetry_data, gui_refs, queue_ui_update, safe_float)
                        
                        # Notify telemetry callbacks (e.g., for data logging)
                        if parsed_data:
                            device_manager.notify_telemetry_callbacks(device_key, parsed_data)
                    else:
                        # Device not configured - log as telemetry (filtered by telemetry checkbox)
                        # but don't parse or process it
                        if log_telemetry:
                            log_to_terminal(f"[TELEM @{source_ip}]: {msg}", gui_refs)
                except Exception as e:
                    log_to_terminal(f"Error processing telemetry for {msg}: {e}", gui_refs)

            elif "_RECOVERY:" in msg or msg.startswith("RECOVERY:"):
                # Special handler for watchdog recovery messages
                log_to_terminal(f"[RECOVERY @{source_ip}]: {msg}", gui_refs)
                with devices_lock:
                    for key, device_state in device_manager.get_all_device_states().items():
                        if device_state["ip"] == source_ip:
                            # Ignore if device is configured for USB
                            if device_state.get('connection_method') == 'usb':
                                continue
                            device_manager.update_device_state(key, {"last_rx": time.time()})
                            # Queue a warning dialog to show on the main GUI thread
                            device_name = key.upper()
                            if gui_queue := gui_refs.get('gui_queue'):
                                gui_queue.put((show_recovery_warning, (device_name, msg, gui_refs), {}))
                            break
            elif msg.startswith("NVMDUMP:"):
                try:
                    _, device_key, payload = msg.split(":", 2)
                except ValueError:
                    log_to_terminal(f"[STATUS @{source_ip}]: {msg}", gui_refs)
                    continue

                # Check if device is configured for USB - if so, ignore network messages
                with devices_lock:
                    device_state = device_manager.get_device_state(device_key.lower())
                    if device_state and device_state.get('connection_method') == 'usb':
                        continue

                show_cb = gui_refs.get('show_nvm_dump_cb')
                if show_cb:
                    if gui_queue := gui_refs.get('gui_queue'):
                        gui_queue.put((show_cb, (device_key.lower(), payload), {}))
                log_to_terminal(f"[STATUS @{source_ip}]: {msg}", gui_refs)
            elif is_status_message(msg, device_manager):
                # Check which device this message is from
                device_key_for_msg = None
                with devices_lock:
                    for key, device_state in device_manager.get_all_device_states().items():
                        if device_state["ip"] == source_ip:
                            device_key_for_msg = key
                            # Ignore if device is configured for USB
                            if device_state.get('connection_method') == 'usb':
                                continue
                            device_manager.update_device_state(key, {"last_rx": time.time()})
                            break
                
                # Only log if device is not configured for USB
                if device_key_for_msg:
                    with devices_lock:
                        device_state = device_manager.get_device_state(device_key_for_msg)
                        if device_state and device_state.get('connection_method') != 'usb':
                            log_to_terminal(f"[STATUS @{source_ip}]: {msg}", gui_refs)
            else:
                log_to_terminal(f"[UNHANDLED @{source_ip}]: {msg}", gui_refs)

        except socket.timeout:
            continue
        except Exception as e:
            # Check if the socket was closed intentionally.
            if isinstance(e, socket.error) and e.errno == 10004: # WSAEINTR on Windows
                break # Exit loop if socket is closed.
            
            # Suppress common connection errors that occur when devices are not available
            if isinstance(e, socket.error):
                if e.errno == 10054:  # WSAECONNRESET - Connection reset by peer
                    continue  # Silently continue, this is normal when devices are offline
                elif e.errno == 10053:  # WSAECONNABORTED - Software caused connection abort
                    continue  # Silently continue, this is normal when devices are offline
                elif e.errno == 10057:  # WSAENOTCONN - Socket is not connected
                    continue  # Silently continue, this is normal when devices are offline
            
            # Only log other types of errors
            log_to_terminal(f"Recv_loop error: {e}\n", gui_refs)
