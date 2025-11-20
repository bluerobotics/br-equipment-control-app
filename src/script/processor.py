import time
import threading
import queue
import tkinter as tk  # For TclError and StringVar
import re
import shlex
from ..logging import log_to_terminal

# --- Built-in Script Commands ---
# These are commands handled directly by the ScriptRunner, not sent to devices.
SCRIPT_COMMANDS = {
    "wait": {
        "description": "Pauses script execution for a specified duration.",
        "params": [{
            "parameter": "time",
            "unit": "sec",
            "type": "float"
        }],
        "handler": "_handle_wait",
        "device": "script"
    },
    "wait_for": {
        "description": "Waits until a variable reaches a target value (e.g., wait_for device.temp_c = 70).",
        "params": [
            {"parameter": "variable", "type": "string"},
            {"parameter": "operator", "type": "string"},
            {"parameter": "value", "type": "float"},
            {"parameter": "timeout", "unit": "sec", "type": "float", "optional": True}
        ],
        "handler": "_handle_wait_for",
        "device": "script"
    },
    "cycle": {
        "description": "Repeats a block of commands a specified number of times.",
        "params": [{
            "parameter": "count",
            "unit": "times",
            "type": "int"
        }],
        "handler": "_handle_cycle_start",
        "device": "script"
    },
    "start_logging": {
        "description": "Starts logging queued variables from specified devices to a CSV file. Use <date> and <time> tags for timestamps. Optional frequency parameter in Hz (e.g., start_logging '<date>-<time> data.csv' device 10 hz). If frequency not specified, syncs with incoming telemetry.",
        "params": [
            {"parameter": "filename", "type": "string"},
            {"parameter": "devices", "type": "string", "variadic": True},
            {"parameter": "frequency", "unit": "hz", "type": "float", "optional": True}
        ],
        "handler": "_handle_start_logging",
        "device": "script"
    },
    "stop_logging": {
        "description": "Stops logging. Specify filename to stop specific log, or leave empty to stop all.",
        "params": [
            {"parameter": "filename", "type": "string", "optional": True}
        ],
        "handler": "_handle_stop_logging",
        "device": "script"
    },
    "queue_for_logging": {
        "description": "Queues variables for logging (e.g., queue_for_logging device.temp_c device.position).",
        "params": [
            {"parameter": "variables", "type": "string", "variadic": True}
        ],
        "handler": "_handle_queue_for_logging",
        "device": "script"
    },
    "unqueue_for_logging": {
        "description": "Removes variables from the logging queue (e.g., unqueue_for_logging device.temp_c).",
        "params": [
            {"parameter": "variables", "type": "string", "variadic": True}
        ],
        "handler": "_handle_unqueue_for_logging",
        "device": "script"
    },
    "if": {
        "description": "Conditional statement with comparison operators (e.g., if 3 > device.energy < 1.5 throw device.energy_warning).",
        "params": [
            {"parameter": "condition", "type": "string", "variadic": True}
        ],
        "handler": "_handle_if",
        "device": "script"
    },
    "throw": {
        "description": "Throws a warning to halt script execution (e.g., throw device.energy_warning).",
        "params": [
            {"parameter": "warning", "type": "string"}
        ],
        "handler": "_handle_throw",
        "device": "script"
    }
}

class ScriptRunner(threading.Thread):
    """
    Runs a script in a separate thread to avoid blocking the GUI.
    Handles script parsing, command execution, and status reporting.
    """
    def __init__(self, script_content, shared_gui_refs, status_cb, completion_cb, msg_q, scripting_commands, line_offset=0):
        super().__init__(daemon=True)
        self.script_content = script_content
        self.gui_refs = shared_gui_refs
        # Correctly extract command_funcs from the shared_gui_refs
        self.command_funcs = shared_gui_refs.get('command_funcs', {})
        self.status_cb = status_cb
        self.completion_cb = completion_cb
        self.msg_q = msg_q
        self.scripting_commands = scripting_commands
        self.line_offset = line_offset
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self.is_running = False
        self.is_held = False
        self.runtime_defaults = {}
        # To map expanded lines back to original source lines
        try:
            # First collapse logging blocks, then expand loops
            collapsed_content, collapse_line_map = self._collapse_logging_blocks(script_content, line_offset)
            expanded_content, expand_line_map = self._expand_loops(collapsed_content, 0)  # Use 0 offset since collapse_line_map already has it
            
            # Combine the two maps: expanded line -> collapsed line -> original line
            self.line_map = {}
            for exp_idx, collapsed_line_num in expand_line_map.items():
                # collapsed_line_num is 1-based in the collapsed content
                # collapse_line_map maps 0-based collapsed indices to original line numbers
                collapsed_idx = collapsed_line_num - 1
                original_line = collapse_line_map.get(collapsed_idx, collapsed_line_num + line_offset)
                self.line_map[exp_idx] = original_line
            
            self.script_lines = expanded_content
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.script_lines = [f"Error processing script: {e}"]
            self.line_map = {0: 1 + line_offset}

    def _get_indent_level(self, line):
        """Get indentation level, handling both spaces and tabs."""
        # Convert tabs to 4 spaces for consistent indentation handling
        expanded = line.expandtabs(4)
        return len(expanded) - len(expanded.lstrip(' '))
    
    def _collapse_logging_blocks(self, content, line_offset=0):
        """
        Collapses indented blocks for logging commands into single-line commands.
        Returns (collapsed_content, line_map) where line_map maps collapsed line index to original line number.
        
        For example:
            queue_for_logging
                device.temp_c
                device.heater_setpoint
        
        Becomes:
            queue_for_logging device.temp_c device.heater_setpoint
        """
        lines = content.splitlines()
        result_lines = []
        line_map = {}  # Maps collapsed line index (0-based) to original line number (1-based with offset)
        i = 0
        
        # Commands that support indented blocks
        block_commands = ['queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
        
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # Keep comments and empty lines as-is
            if not line_stripped or line_stripped.startswith('#'):
                line_map[len(result_lines)] = i + 1 + line_offset  # Map collapsed index to original line number
                result_lines.append(line)
                i += 1
                continue
            
            # Check if this is a block command
            try:
                parts = shlex.split(line_stripped)
            except ValueError:
                parts = line_stripped.split()
            
            command_word = parts[0].lower() if parts else ''
            
            if command_word in block_commands:
                # Get base indentation of the command line (handle tabs and spaces)
                base_indent = self._get_indent_level(line)
                
                # Look ahead to see if next non-empty, non-comment line is indented
                j = i + 1
                has_block = False
                
                while j < len(lines):
                    peek_line = lines[j]
                    peek_stripped = peek_line.strip()
                    
                    # Skip empty lines and comments
                    if not peek_stripped or peek_stripped.startswith('#'):
                        j += 1
                        continue
                    
                    # Check if this line is indented (handle tabs and spaces)
                    peek_indent = self._get_indent_level(peek_line)
                    if peek_indent > base_indent:
                        has_block = True
                    break
                
                if has_block:
                    # Collect all indented lines
                    collected_args = []
                    
                    # Add any args from the command line itself (e.g., filename in start_logging)
                    if len(parts) > 1:
                        collected_args.extend(parts[1:])
                    
                    # Collect indented block
                    j = i + 1
                    
                    while j < len(lines):
                        block_line = lines[j]
                        block_stripped = block_line.strip()
                        
                        # Skip empty lines and comments
                        if not block_stripped or block_stripped.startswith('#'):
                            j += 1
                            continue
                        
                        # Handle tabs and spaces for indentation
                        block_line_indent = self._get_indent_level(block_line)
                        
                        # Stop if we hit a non-indented line
                        if block_line_indent <= base_indent:
                            break
                        
                        # Add this line's content to args
                        collected_args.append(block_stripped)
                        j += 1
                    
                    # Create collapsed line
                    collapsed_line = f"{' ' * base_indent}{command_word} {' '.join(collected_args)}"
                    line_map[len(result_lines)] = i + 1 + line_offset  # Map to the command line (start of block)
                    result_lines.append(collapsed_line)
                    
                    # Skip the processed block
                    i = j
                    continue
            
            # Not a block command or no indented block - keep line as-is
            line_map[len(result_lines)] = i + 1 + line_offset  # Map collapsed index to original line number
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines), line_map
    
    def _expand_loops(self, content, start_offset):
        lines_with_nums = [(line, i + 1 + start_offset) for i, line in enumerate(content.splitlines())]

        def _expand_recursive(block_with_nums):
            expanded_list = []
            i = 0
            while i < len(block_with_nums):
                line, line_num = block_with_nums[i]
                
                if line.strip().upper().startswith("CYCLE"):
                    parts = line.strip().split()
                    
                    # Allow for an optional colon and comments, e.g., "CYCLE 100:"
                    count = 0
                    # Find the first numeric argument for the count
                    for part in parts[1:]:
                        match = re.match(r'^-?\d+(\.\d+)?', part)
                        if match:
                            count = int(float(match.group(0))) # float then int to handle "100.0"
                            break
                    
                    print(f"[DEBUG] CYCLE found: line='{line.strip()}', parts={parts}, count={count}")
                    
                    # Use _get_indent_level helper to handle both tabs and spaces
                    line_indent = self._get_indent_level(line)
                    print(f"[DEBUG] CYCLE line_indent={line_indent}, total lines in block={len(block_with_nums)}, current i={i}")

                    # Find the first non-empty, indented line to start the block
                    body_start_index = -1
                    block_indent = -1
                    for j in range(i + 1, len(block_with_nums)):
                        peek_line = block_with_nums[j][0]
                        print(f"[DEBUG] CYCLE scanning j={j}: '{peek_line}' (stripped: '{peek_line.strip()}')")
                        if peek_line.strip():
                            body_indent = self._get_indent_level(peek_line)
                            print(f"[DEBUG] CYCLE found non-empty line at j={j}, body_indent={body_indent}, line_indent={line_indent}")
                            if body_indent > line_indent:
                                body_start_index = j
                                block_indent = body_indent
                                print(f"[DEBUG] CYCLE body starts at j={j}, block_indent={block_indent}")
                            break # Found first non-empty line, stop searching

                    # If no indented block was found, just skip the CYCLE line
                    if body_start_index == -1:
                        print(f"[DEBUG] CYCLE: No indented block found, skipping")
                        i += 1
                        continue

                    # Find the end of the block
                    body_end_index = body_start_index
                    for j in range(body_start_index, len(block_with_nums)):
                        line_content = block_with_nums[j][0]
                        # A non-empty line with less or equal indent ends the block
                        if line_content.strip():
                            current_line_indent = self._get_indent_level(line_content)
                            if current_line_indent < block_indent:
                                body_end_index = j - 1 # The block ended on the previous line
                                break
                        # If we haven't broken, this line is part of the block
                        body_end_index = j
                    
                    loop_body_with_nums = block_with_nums[body_start_index : body_end_index + 1]
                    
                    print(f"[DEBUG] CYCLE body extraction: body_start_index={body_start_index}, body_end_index={body_end_index}, block_indent={block_indent}")
                    print(f"[DEBUG] CYCLE body lines (raw slice):")
                    for idx, (line, lnum) in enumerate(loop_body_with_nums):
                        print(f"[DEBUG]   [{idx}] line {lnum}: '{line}'")
                    
                    expanded_body = _expand_recursive(loop_body_with_nums)
                    
                    print(f"[DEBUG] Expanding cycle {count} times, body has {len(expanded_body)} lines")
                    for iteration in range(1, count + 1):
                        # Add iteration marker comment at the start of each iteration
                        marker_line = f"# CYCLE ITERATION {iteration}/{count}"
                        expanded_list.append((marker_line, line_num))  # Use the cycle line number
                        expanded_list.extend(expanded_body)
                        # Add end marker comment at the end of each iteration
                        end_marker_line = f"# CYCLE END {iteration}/{count}"
                        expanded_list.append((end_marker_line, line_num))
                    print(f"[DEBUG] After expansion, expanded_list has {len(expanded_list)} lines total")
                    
                    i = body_end_index + 1
                else:
                    expanded_list.append((line, line_num))
                    i += 1
            return expanded_list
            
        processed_lines_with_nums = _expand_recursive(lines_with_nums)
        
        final_lines = [line for line, num in processed_lines_with_nums]
        final_map = {i: num for i, (line, num) in enumerate(processed_lines_with_nums)}
        
        return final_lines, final_map

    def stop(self):
        """Signals the script execution thread to stop."""
        self._stop_event.set()
        self.is_running = False
    
    def resume_after_error(self):
        """Signals the script to resume after an error hold."""
        self._resume_event.set()
        self.is_held = False
    
    def _get_required_devices(self):
        """
        Scans the script to identify which devices are referenced.
        Returns a set of device names that need to be connected.
        """
        required_devices = set()
        
        # Get list of all known devices from device_manager
        device_manager = self.gui_refs.get('device_manager')
        known_devices = set()
        if device_manager:
            known_devices = set(device_manager.device_state.keys())
        
        for line in self.script_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Use shlex to properly parse the line
            try:
                parts = shlex.split(line)
            except ValueError:
                parts = line.split()
            
            if not parts:
                continue
            
            command_word = parts[0].lower()
            
            # Check all parts for device.variable or device.event patterns
            for part in parts:
                if '.' in part:
                    # This might be a device.variable or device.event reference
                    device_name = part.split('.')[0].lower()
                    # Only add if it's a known device
                    if device_name in known_devices:
                        required_devices.add(device_name)
            
            # Check if command is device-specific
            command_info = self.scripting_commands.get(command_word)
            if not command_info:
                # Try case-insensitive lookup
                for cmd_key in self.scripting_commands:
                    if cmd_key.lower() == command_word.lower():
                        command_info = self.scripting_commands[cmd_key]
                        break
            
            if command_info:
                device = command_info.get('device')
                # If device is not 'script' or 'both', it's a device-specific command
                if device and device not in ['script', 'both']:
                    required_devices.add(device)
        
        return required_devices

    def run(self):
        """The main execution loop for the script thread."""
        self.is_running = True
        
        # Clear any stale messages from the queue before starting
        cleared_count = 0
        while not self.msg_q.empty():
            try:
                self.msg_q.get_nowait()
                cleared_count += 1
            except queue.Empty:
                break
        if cleared_count > 0:
            pass  # Cleared stale messages

        # Clear the injection target display at the beginning of the script
        if self.gui_refs and 'injection_target_ml_var' in self.gui_refs:
            self.gui_refs['injection_target_ml_var'].set('---')
        
        # Pre-flight check: verify required devices are connected
        required_devices = self._get_required_devices()
        if required_devices:
            device_manager = self.gui_refs.get('device_manager')
            if device_manager:
                disconnected = []
                for device_name in required_devices:
                    device_state = device_manager.get_device_state(device_name)
                    if not device_state or not device_state.get('connected'):
                        disconnected.append(device_name)
                
                if disconnected:
                    error_msg = f"Cannot run script: The following devices are not connected: {', '.join(disconnected)}"
                    self.status_cb(error_msg, -1)
                    
                    # Show error dialog to user
                    import tkinter.messagebox as messagebox
                    root = self.gui_refs.get('root')
                    if root:
                        root.after(0, lambda: messagebox.showerror(
                            "Devices Not Connected",
                            f"Cannot run script.\n\nThe following devices are not connected:\n\n{', '.join(disconnected)}\n\nPlease connect the devices or start their simulators before running the script."
                        ))
                    
                    self.is_running = False
                    if self.completion_cb:
                        try:
                            self.completion_cb()
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                    return

        for i, line in enumerate(self.script_lines):
            if self._stop_event.is_set():
                self.status_cb("Script stopped by user.", -1)
                break

            original_line_num = self.line_map.get(i, i + self.line_offset + 1)
            
            line = line.strip()
            
            # Check for cycle iteration markers and log them
            if line.startswith('# CYCLE ITERATION '):
                iteration_info = line.replace('# CYCLE ITERATION ', '')
                iteration_num = iteration_info.split('/')[0]  # Extract just the iteration number
                
                # Log to both status line and terminal
                self.status_cb(f"Cycle {iteration_num}", original_line_num)
                
                # Also log to terminal as a system message
                try:
                    from . import comms
                    log_to_terminal(f"[SYSTEM] Cycle {iteration_num}", self.gui_refs)
                except Exception:
                    pass  # Ignore if logging fails
                
                continue
            
            # Check for cycle end markers (skip them silently)
            if line.startswith('# CYCLE END '):
                continue
            
            if not line or line.startswith('#'):
                continue
            
            self.status_cb(f"Executing line {original_line_num}...", original_line_num)

            try:
                # Pass the correct, current line number to the processing method
                if not self._process_line(line, original_line_num):
                    # Stop execution if _process_line returns False
                    break
                else:
                    pass  # Line executed successfully, continue
            except Exception as e:
                error_msg = f"Runtime Error on line {original_line_num}: {e}"
                self.status_cb(error_msg, original_line_num)
                import traceback
                traceback.print_exc()
                # Halt execution on error
                break
        
        self.is_running = False
        
        # Always call the completion callback when the loop finishes for any reason.
        if self.completion_cb:
            self.completion_cb()

        # Clear the injection target display at the end of the script
        if self.gui_refs and 'injection_target_ml_var' in self.gui_refs:
            self.gui_refs['injection_target_ml_var'].set('---')
    
    def _parse_positional_args(self, parts, command_info):
        """
        Parses command arguments from parts list.
        Returns (resolved_params_dict, error_message).
        """
        try:
            param_words = parts[1:]  # Skip command word
            params_def = command_info.get('params', [])
            resolved_params = {}
            
            # Handle variadic parameters
            has_variadic = any(p.get('variadic', False) for p in params_def)
            
            if has_variadic:
                # For variadic commands, collect all remaining args
                param_index = 0
                for param_def in params_def:
                    param_name = param_def.get('parameter', param_def.get('name', f'param{param_index}'))
                    
                    if param_def.get('variadic', False):
                        # Collect all remaining words as a space-separated string
                        if param_index < len(param_words):
                            resolved_params[param_name] = ' '.join(param_words[param_index:])
                        else:
                            resolved_params[param_name] = ''
                        break
                    else:
                        # Regular parameter
                        if param_index < len(param_words):
                            resolved_params[param_name] = param_words[param_index]
                        elif not param_def.get('optional', False):
                            return {}, f"Missing required parameter '{param_name}'"
                        param_index += 1
            else:
                # Non-variadic: use the old resolution logic
                resolved_params = self._resolve_params(param_words, command_info)
            
            return resolved_params, None
            
        except Exception as e:
            return {}, str(e)
    
    def _is_numeric(self, value):
        """Check if a value is numeric."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _resolve_params(self, param_words, command_info):
        """
        Resolves script parameter words into a dictionary of named parameters.
        Handles both positional and keyword arguments.
        """
        resolved_params = {}
        unassigned_args = list(param_words)
        param_defs = command_info.get('params', [])
        # Use the 'parameter' key from the new JSON structure
        param_names = [p.get('parameter', f'arg{i}') for i, p in enumerate(param_defs)]

        # First pass: find keyword arguments (e.g., "return")
        for i, word in enumerate(unassigned_args):
            if word in param_names:
                # This is a keyword, like 'return'. Assume it's a flag.
                resolved_params[word] = True
                unassigned_args[i] = None # Mark for removal

        # Remove used keywords
        unassigned_args = [arg for arg in unassigned_args if arg is not None]

        # Second pass: assign remaining positional arguments
        positional_param_defs = [p for p in param_defs if p.get('parameter') not in resolved_params]
        
        # Combine value and unit if they are separate words, and strip label words
        combined_args = []
        # Label words to skip (like "action", "mode", "limit", etc.)
        label_words = {'action', 'mode', 'limit', 'source', 'value', 'parameter'}
        
        i = 0
        while i < len(unassigned_args):
            arg = unassigned_args[i]
            # Heuristic: if the current arg is a number and the next is not, they might be value+unit
            is_numeric = self._is_numeric(arg)
            
            if is_numeric and i + 1 < len(unassigned_args) and not self._is_numeric(unassigned_args[i+1]):
                # Skip the unit word if it's a label word
                next_word = unassigned_args[i+1].lower()
                if next_word not in label_words:
                    combined_args.append(f"{arg} {unassigned_args[i+1]}")
                else:
                    # Just the numeric value, skip the label
                    combined_args.append(arg)
                i += 2
            else:
                # Skip standalone label words
                if arg.lower() not in label_words:
                    combined_args.append(arg)
                i += 1
        
        for i, param_def in enumerate(positional_param_defs):
            if i < len(combined_args):
                # Use the 'parameter' key here as well
                param_name = param_def.get('parameter', f'arg{i}')
                resolved_params[param_name] = combined_args[i]

        return resolved_params

    def _handle_wait(self, command_info, resolved_params, line_num=0):
        """Handler for the built-in 'wait' command."""
        try:
            # Use the new parameter name 'time'
            duration_str = resolved_params.get('time', '0')
            duration_s = float(duration_str.split()[0]) # Handle cases like "1 sec"
            
            start_time = time.time()
            last_update = 0
            
            while time.time() - start_time < duration_s:
                if self._stop_event.is_set():
                    self.status_cb("Wait cancelled.", line_num)
                    return "stop"
                
                # Update countdown display every 0.1 seconds
                elapsed = time.time() - start_time
                remaining = duration_s - elapsed
                if elapsed - last_update >= 0.1 or remaining <= 0:
                    self.status_cb(f"Waiting... {remaining:.1f}s remaining", line_num)
                    last_update = elapsed
                
                time.sleep(0.05) # Sleep in small intervals to remain responsive
            
            self.status_cb(f"Wait complete ({duration_s}s)", line_num)
            return "continue"
        except (ValueError, IndexError) as e:
            self.status_cb(f"Error in wait command: Invalid time value '{resolved_params.get('time', '')}'. {e}", line_num)
            return "error"
    
    def _handle_wait_for(self, command_info, resolved_params, line_num):
        """Handler for the 'wait_for' command - waits for a variable to reach a target value."""
        try:
            variable = resolved_params.get('variable', '')
            operator = resolved_params.get('operator', '=')
            target_value_str = resolved_params.get('value', '0')
            timeout_str = resolved_params.get('timeout', '60')
            
            # Parse target value and timeout
            target_value = float(target_value_str.split()[0])
            timeout = float(timeout_str.split()[0]) if timeout_str else 60.0
            
            # Parse device.variable
            if '.' not in variable:
                self.status_cb(f"Error: Variable must be in format 'device.variable', got '{variable}'", line_num)
                return "error"
            
            device_name, param_name = variable.split('.', 1)
            
            # Get the device manager
            device_manager = self.gui_refs.get('device_manager')
            if not device_manager:
                self.status_cb(f"Error: Device manager not available", line_num)
                return "error"
            
            # Get the device data
            device_data = None
            for dev_name in device_manager.get_all_device_names():
                if dev_name.lower() == device_name.lower():
                    device_data = device_manager.devices.get(dev_name)
                    device_name = dev_name
                    break
            
            if not device_data:
                self.status_cb(f"Error: Unknown device '{device_name}'", line_num)
                return "error"
            
            # Get telemetry info for this parameter
            telemetry_data = device_data.get('telemetry_data', {})
            param_info = telemetry_data.get(param_name)
            
            if not param_info:
                self.status_cb(f"Error: Unknown parameter '{param_name}' for device '{device_name}'", line_num)
                return "error"
            
            # Get the GUI variable that stores this value
            gui_var_name = param_info.get('gui_var')
            if not gui_var_name:
                self.status_cb(f"Error: Parameter '{param_name}' has no GUI variable mapping", line_num)
                return "error"
            
            gui_var = self.gui_refs.get(gui_var_name)
            if not gui_var:
                self.status_cb(f"Error: GUI variable '{gui_var_name}' not found", line_num)
                return "error"
            
            # Determine comparison function
            compare_funcs = {
                '=': lambda a, b: abs(a - b) < 0.01,  # Approximate equality for floats
                '==': lambda a, b: abs(a - b) < 0.01,
                '>': lambda a, b: a > b,
                '<': lambda a, b: a < b,
                '>=': lambda a, b: a >= b,
                '<=': lambda a, b: a <= b
            }
            
            compare_func = compare_funcs.get(operator)
            if not compare_func:
                self.status_cb(f"Error: Invalid operator '{operator}'. Use =, >, <, >=, or <=", line_num)
                return "error"
            
            self.status_cb(f"Waiting for {variable} {operator} {target_value} (timeout: {timeout}s)...", line_num)
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._stop_event.is_set():
                    self.status_cb("Wait cancelled.", line_num)
                    return "stop"
                
                # Get current value from GUI variable
                try:
                    current_value_str = gui_var.get()
                    # Try to extract numeric value (handle formats like "70.0 °C" or "70.0")
                    current_value = float(re.search(r'-?\d+\.?\d*', current_value_str).group())
                    
                    # Check if condition is met
                    if compare_func(current_value, target_value):
                        self.status_cb(f"Condition met: {variable} = {current_value}", line_num)
                        return "continue"
                        
                except (ValueError, AttributeError):
                    # Can't parse value, keep waiting
                    pass
                
                time.sleep(0.1) # Check every 100ms
            
            # Timeout
            self.status_cb(f"Timeout: {variable} did not reach {operator} {target_value} within {timeout}s", line_num)
            return "error"
            
        except Exception as e:
            self.status_cb(f"Error in wait_for command: {e}", line_num)
            return "error"
    
    def _handle_start_logging(self, command_info, resolved_params, line_num):
        """Handler for the 'start_logging' command - starts logging queued variables from devices to a CSV file."""
        try:
            # Get the data logger from shared_gui_refs
            data_logger = self.gui_refs.get('data_logger')
            if not data_logger:
                self.status_cb(f"Error: Data logger not available", line_num)
                return "error"
            
            filename = resolved_params.get('filename')
            devices_str = resolved_params.get('devices', '')
            frequency = resolved_params.get('frequency', None)  # Optional frequency in Hz
            
            # Parse device names (filter out frequency if it was included in devices)
            if isinstance(devices_str, str):
                device_names = devices_str.split()
            elif isinstance(devices_str, list):
                device_names = devices_str
            else:
                device_names = []
            
            if not filename:
                self.status_cb(f"Error: Filename is required for start_logging", line_num)
                return "error"
            
            if not device_names:
                self.status_cb(f"Error: No devices specified for logging", line_num)
                return "error"
            
            # Collect all queued variables from specified devices
            all_variables = []
            for device_name in device_names:
                queued_vars = data_logger.get_queued_variables(device_name)
                if queued_vars:
                    # Add full variable names (device.variable)
                    all_variables.extend([f"{device_name}.{var}" for var in queued_vars])
            
            if not all_variables:
                self.status_cb(f"Error: No queued variables found for specified devices: {', '.join(device_names)}", line_num)
                return "error"
            
            # Start logging all collected variables with optional frequency
            success, message, actual_filename = data_logger.start_logging(filename, all_variables, frequency)
            
            if success:
                freq_info = f" at {frequency} Hz" if frequency else " (synced with telemetry)"
                self.status_cb(f"Started logging {len(all_variables)} variable(s){freq_info}: {message}", line_num)
                return "continue"
            else:
                self.status_cb(f"Error starting logging: {message}", line_num)
                return "error"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_cb(f"Error in start_logging command: {e}", line_num)
            return "error"
    
    def _handle_stop_logging(self, command_info, resolved_params, line_num):
        """Handler for the 'stop_logging' command - stops logging to specified file or all files."""
        try:
            # Get the data logger from shared_gui_refs
            data_logger = self.gui_refs.get('data_logger')
            if not data_logger:
                self.status_cb(f"Error: Data logger not available", line_num)
                return "error"
            
            filename = resolved_params.get('filename')
            
            # Stop logging
            success, message = data_logger.stop_logging(filename)
            
            if success:
                self.status_cb(f"Stopped logging: {message}", line_num)
                return "continue"
            else:
                self.status_cb(f"Error stopping logging: {message}", line_num)
                return "error"
                
        except Exception as e:
            self.status_cb(f"Error in stop_logging command: {e}", line_num)
            return "error"
    
    def _handle_queue_for_logging(self, command_info, resolved_params, line_num):
        """Handler for the 'queue_for_logging' command - queues variables for logging."""
        try:
            # Get the data logger from shared_gui_refs
            data_logger = self.gui_refs.get('data_logger')
            if not data_logger:
                self.status_cb(f"Error: Data logger not available", line_num)
                return "error"
            
            variables_str = resolved_params.get('variables', '')
            
            # Parse variables
            if isinstance(variables_str, str):
                variables = variables_str.split()
            elif isinstance(variables_str, list):
                variables = variables_str
            else:
                variables = []
            
            
            if not variables:
                self.status_cb(f"Error: No variables specified for queueing", line_num)
                return "error"
            
            # Queue each variable
            queued_count = 0
            for var in variables:
                if '.' not in var:
                    self.status_cb(f"Error: Invalid variable format '{var}'. Use device.variable", line_num)
                    continue
                
                device_name, var_name = var.split('.', 1)
                data_logger.queue_variable(device_name, var_name)
                queued_count += 1
            
            if queued_count > 0:
                self.status_cb(f"Queued {queued_count} variable(s) for logging", line_num)
                
                # Refresh command reference to show [queued] badges (schedule on main thread)
                refresh_func = self.gui_refs.get('refresh_commands_ref')
                if refresh_func:
                    # Use after_idle to schedule the refresh on the main thread
                    root = self.gui_refs.get('root')
                    if root:
                        root.after_idle(refresh_func)
                
                return "continue"
            else:
                self.status_cb(f"Error: No valid variables queued", line_num)
                return "error"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_cb(f"Error in queue_for_logging command: {e}", line_num)
            return "error"
    
    def _handle_unqueue_for_logging(self, command_info, resolved_params, line_num):
        """Handler for the 'unqueue_for_logging' command - removes variables from logging queue."""
        try:
            # Get the data logger from shared_gui_refs
            data_logger = self.gui_refs.get('data_logger')
            if not data_logger:
                self.status_cb(f"Error: Data logger not available", line_num)
                return "error"
            
            variables_str = resolved_params.get('variables', '')
            
            # Parse variables
            if isinstance(variables_str, str):
                variables = variables_str.split()
            elif isinstance(variables_str, list):
                variables = variables_str
            else:
                variables = []
            
            if not variables:
                self.status_cb(f"Error: No variables specified for unqueueing", line_num)
                return "error"
            
            # Unqueue each variable
            unqueued_count = 0
            for var in variables:
                if '.' not in var:
                    self.status_cb(f"Error: Invalid variable format '{var}'. Use device.variable", line_num)
                    continue
                
                device_name, var_name = var.split('.', 1)
                data_logger.unqueue_variable(device_name, var_name)
                unqueued_count += 1
            
            if unqueued_count > 0:
                self.status_cb(f"Unqueued {unqueued_count} variable(s)", line_num)
                
                # Refresh command reference to hide [queued] badges (schedule on main thread)
                refresh_func = self.gui_refs.get('refresh_commands_ref')
                if refresh_func:
                    # Use after_idle to schedule the refresh on the main thread
                    root = self.gui_refs.get('root')
                    if root:
                        root.after_idle(refresh_func)
                
                return "continue"
            else:
                self.status_cb(f"Error: No valid variables unqueued", line_num)
                return "error"
                
        except Exception as e:
            self.status_cb(f"Error in unqueue_for_logging command: {e}", line_num)
            return "error"

    def _handle_if(self, command_info, resolved_params, line_num):
        """Handler for the 'if' conditional command."""
        try:
            # Get the full condition string (all args after 'if')
            condition_str = resolved_params.get('condition', '')
            print(f"[DEBUG] _handle_if condition_str: '{condition_str}'")
            print(f"[DEBUG] _handle_if resolved_params: {resolved_params}")
            
            # Parse the condition: supports "value1 > var < value2" or similar
            # Split on comparison operators while preserving them
            import re
            
            # Find all tokens (numbers, variables, operators, commands)
            tokens = re.split(r'\s+', condition_str)
            print(f"[DEBUG] _handle_if tokens: {tokens}")
            
            # Evaluate the comparison chain
            result = self._evaluate_condition(tokens, line_num)
            
            if result is None:
                self.status_cb(f"Error: Invalid condition syntax", line_num)
                return "error"
            
            # If condition is true, continue processing remaining tokens
            if result:
                # Find 'throw' command in tokens
                if 'throw' in tokens:
                    throw_index = tokens.index('throw')
                    if throw_index + 1 < len(tokens):
                        warning_name = tokens[throw_index + 1]
                        return self._trigger_warning(warning_name, line_num)
                # If no action specified, just continue
                return "continue"
            else:
                # Condition false - skip any action and continue
                self.status_cb(f"Condition false - skipping", line_num)
                return "continue"
                
        except Exception as e:
            self.status_cb(f"Error in if command: {e}", line_num)
            return "error"

    def _evaluate_condition(self, tokens, line_num):
        """Evaluate a chained comparison like '3 > device.energy < 1.5' or 'device.energy > 3'"""
        try:
            # Resolve variables to their values
            resolved = []
            for token in tokens:
                if token in ['>', '<', '>=', '<=', '==', '!=']:
                    resolved.append(token)
                elif token == 'throw':
                    # Stop processing at 'throw' - that's the action
                    break
                else:
                    # Try to parse as a number first
                    try:
                        resolved.append(float(token))
                        continue
                    except ValueError:
                        pass
                    
                    # If it's not a number, check if it's a variable (device.variable format)
                    if '.' in token:
                        # It's a variable - resolve it
                        value = self._get_variable_value(token)
                        if value is None:
                            self.status_cb(f"Error: Variable {token} not found or has no value", line_num)
                            return None
                        resolved.append(float(value))
                    else:
                        # Skip unknown tokens (like 'action', etc.)
                        continue
            
            # Debug output
            print(f"[DEBUG] _evaluate_condition resolved tokens: {resolved}")
            
            # Now evaluate the chain: e.g., [3.0, '>', 1.5, '<', 1.5]
            # becomes: (3.0 > 1.5) and (1.5 < 1.5)
            # Or simple: [18.02, '<', 1.5] becomes: (18.02 < 1.5)
            if len(resolved) < 3:
                self.status_cb(f"Error: Invalid condition - need at least 3 tokens (value operator value), got {len(resolved)}", line_num)
                return None
            
            # Process comparison chain
            # Pattern is: value1 op1 value2 [op2 value3 ...]
            result = True
            i = 0
            while i < len(resolved) - 2:
                left = resolved[i]
                op = resolved[i + 1]
                right = resolved[i + 2]
                
                print(f"[DEBUG] Evaluating: {left} {op} {right}")
                
                if op == '>':
                    comparison_result = (left > right)
                elif op == '<':
                    comparison_result = (left < right)
                elif op == '>=':
                    comparison_result = (left >= right)
                elif op == '<=':
                    comparison_result = (left <= right)
                elif op == '==':
                    comparison_result = (left == right)
                elif op == '!=':
                    comparison_result = (left != right)
                else:
                    self.status_cb(f"Error: Unknown operator '{op}'", line_num)
                    return None
                
                print(f"[DEBUG] Result: {comparison_result}")
                result = result and comparison_result
                
                if not result:
                    break
                
                # For chained comparisons, move by 2 (reuse the right value as the next left)
                i += 2
            
            print(f"[DEBUG] Final condition result: {result}")
            return result
            
        except Exception as e:
            self.status_cb(f"Error evaluating condition: {e}", line_num)
            print(f"[DEBUG] Exception in _evaluate_condition: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_variable_value(self, var_name):
        """Get the current value of a variable like device.energy"""
        try:
            print(f"[DEBUG] _get_variable_value: looking up '{var_name}'")
            device_name, field_name = var_name.split('.', 1)
            print(f"[DEBUG] device_name='{device_name}', field_name='{field_name}'")
            
            device_manager = self.gui_refs.get('device_manager')
            if not device_manager:
                print(f"[DEBUG] device_manager not found in gui_refs")
                return None
            
            device_data = device_manager.devices.get(device_name)
            if not device_data:
                print(f"[DEBUG] device '{device_name}' not found in devices")
                return None
            
            telemetry_data = device_data.get('telemetry_data', {})
            print(f"[DEBUG] telemetry_data keys: {list(telemetry_data.keys())}")
            
            field_info = telemetry_data.get(field_name)
            if not field_info:
                print(f"[DEBUG] field '{field_name}' not found in telemetry_data")
                return None
            
            gui_var_name = field_info.get('gui_var')
            if not gui_var_name:
                print(f"[DEBUG] gui_var not found in field_info")
                return None
            
            print(f"[DEBUG] gui_var_name: '{gui_var_name}'")
            gui_var = self.gui_refs.get(gui_var_name)
            if not gui_var:
                print(f"[DEBUG] gui_var '{gui_var_name}' not found in gui_refs")
                return None
            
            value_str = gui_var.get()
            print(f"[DEBUG] value_str: '{value_str}'")
            
            # Strip units and convert to float
            try:
                value = float(value_str.split()[0])
                print(f"[DEBUG] returning value: {value}")
                return value
            except (ValueError, IndexError) as e:
                print(f"[DEBUG] failed to parse value: {e}")
                return None
                
        except Exception as e:
            print(f"[DEBUG] Exception in _get_variable_value: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _handle_throw(self, command_info, resolved_params, line_num):
        """Handler for the 'throw' command to trigger warnings."""
        try:
            warning_name = resolved_params.get('warning', '')
            return self._trigger_warning(warning_name, line_num)
                
        except Exception as e:
            self.status_cb(f"Error in throw command: {e}", line_num)
            return "error"

    def _trigger_warning(self, warning_name, line_num):
        """Trigger a warning and halt script execution."""
        try:
            # Parse device.warning format
            if '.' not in warning_name:
                self.status_cb(f"Error: Invalid warning format '{warning_name}'. Use device.warning_name", line_num)
                return "error"
            
            device_name, warning_key = warning_name.split('.', 1)
            
            # Load warnings for this device
            device_manager = self.gui_refs.get('device_manager')
            if not device_manager:
                self.status_cb(f"Error: Device manager not available", line_num)
                return "error"
            
            device_data = device_manager.devices.get(device_name)
            if not device_data:
                self.status_cb(f"Error: Device '{device_name}' not found", line_num)
                return "error"
            
            warnings_data = device_data.get('warnings', {})
            warning_info = warnings_data.get(warning_key)
            
            if not warning_info:
                self.status_cb(f"Error: Warning '{warning_key}' not defined for {device_name}", line_num)
                return "error"
            
            # Get warning description
            description = warning_info.get('description', warning_key)
            
            # Send a warning message (format: DEVICE_WARNING: message)
            warning_msg = f"{device_name.upper()}_WARNING: {description}"
            self.status_cb(warning_msg, line_num)
            
            # Put script in error hold state
            self.is_held = True
            
            # Return error to stop execution
            return "error"
                
        except Exception as e:
            self.status_cb(f"Error triggering warning: {e}", line_num)
            return "error"

    def _process_line(self, line, line_num):
        sub_commands = line.split(',')
        commands_to_wait_for = []

        for sub_cmd_str in sub_commands:
            if not self.is_running: return False
            sub_cmd_str = sub_cmd_str.strip()
            if not sub_cmd_str: continue

            # Use shlex to properly handle quoted strings
            try:
                parts = shlex.split(sub_cmd_str)
            except ValueError:
                # If shlex fails (e.g., unclosed quotes), fall back to simple split
                parts = sub_cmd_str.split()
            
            if not parts: continue
            command_word = parts[0]
            
            # Try exact match first, then case-insensitive
            command_info = self.scripting_commands.get(command_word)
            if not command_info:
                # Try case-insensitive lookup
                for cmd_key in self.scripting_commands:
                    if cmd_key.lower() == command_word.lower():
                        command_info = self.scripting_commands[cmd_key]
                        command_word = cmd_key  # Use the canonical form
                        break

            if not command_info:
                self.status_cb(f"Error on L{line_num}: Unknown command '{command_word}'.", line_num)
                self.is_running = False
                return False

            device = command_info['device']
            
            # --- New Keyword Argument Parsing ---
            resolved_params, error = self._parse_positional_args(parts, command_info)
            if error:
                self.status_cb(f"Error on L{line_num}: {error} for command '{command_word}'.", line_num)
                self.is_running = False
                return False

            # --- Handler Dispatch (for script-level commands) ---
            if device == "script":
                # Handle built-in script commands (case-insensitive)
                cmd_lower = command_word.lower()
                if cmd_lower == "wait":
                    result = self._handle_wait(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "wait_for":
                    result = self._handle_wait_for(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "start_logging":
                    result = self._handle_start_logging(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "stop_logging":
                    result = self._handle_stop_logging(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "queue_for_logging":
                    result = self._handle_queue_for_logging(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "unqueue_for_logging":
                    result = self._handle_unqueue_for_logging(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "if":
                    result = self._handle_if(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "throw":
                    result = self._handle_throw(command_info, resolved_params, line_num)
                    if result == "error" or result == "stop":
                        self.is_running = False
                        return False
                elif cmd_lower == "cycle":
                    # Cycle is handled by the loop expander, not here
                    pass

            elif device == "both":
                func = self.command_funcs.get(command_word.lower())
                if func:
                    func()
                else:
                    self.status_cb(f"Error on L{line_num}: No handler for global command '{command_word}'.", line_num)
                    self.is_running = False
                    return False
            else:
                # --- Construct Final Command for Firmware ---
                final_args = []
                for param_def in command_info.get('params', []):
                    param_name = param_def.get('parameter', param_def.get('name', ''))
                    if param_name in resolved_params:
                        # Strip units from the value before sending to firmware
                        param_value = str(resolved_params[param_name])
                        # Extract just the numeric part (first word)
                        numeric_value = param_value.split()[0] if param_value else param_value
                        final_args.append(numeric_value)
                    elif not param_def.get('optional'):
                        # This should have been caught by the parser, but as a safeguard:
                        self.status_cb(f"Error on L{line_num}: Missing required parameter '{param_name}' for {command_word}.", line_num)
                        self.is_running = False
                        return False

                if not self.is_running: return False

                # Strip device prefix if present (e.g., "device.disable" -> "disable")
                cmd_to_send = command_word.split('.', 1)[1] if '.' in command_word else command_word
                final_command_str = f"{cmd_to_send} {' '.join(final_args)}" if final_args else cmd_to_send
                send_func = self.command_funcs.get(f"send_{device}")
                if send_func:
                    send_func(final_command_str)
                    if command_info.get("wait_for_done", True): # Assume wait unless specified otherwise
                        # Store the stripped command for DONE matching
                        commands_to_wait_for.append(cmd_to_send)

            time.sleep(0.05)

        if not self.is_running: 
            return False
        if commands_to_wait_for:
            if not self._wait_for_done_messages(commands_to_wait_for, line_num):
                self.is_running = False
                return False

        return True

    def _wait_for_done_messages(self, commands, line_num, timeout_s=600):
        start_time = time.time()

        wait_list = list(commands)
        self.status_cb(f"L{line_num}: Waiting for DONE: {', '.join(wait_list)}", line_num)

        while wait_list:
            if not self.is_running:
                self.status_cb("Stopped", -1)
                return False

            if time.time() - start_time > timeout_s:
                self.status_cb(f"Error on L{line_num}: Timeout waiting for DONE: {', '.join(wait_list)}",
                                     line_num)
                return False

            try:
                msg = self.msg_q.get(timeout=0.1)
                print(f"[DEBUG] script_processor received: {msg}")
                print(f"[DEBUG] waiting for: {wait_list}")

                # Check for ERROR messages - put script in permanent hold state (requires reset)
                if "_ERROR:" in msg or "_WARNING:" in msg:
                    self.is_held = True
                    error_type = "ERROR" if "_ERROR:" in msg else "WARNING"
                    self.status_cb(f"{error_type}: {msg} - Script held. Click Reset to clear.", line_num)
                    
                    # Check if an automatic safety action was triggered (e.g., retract, home, etc.)
                    # Continue processing messages to see if a START message appears right after ERROR
                    safety_action_in_progress = False
                    safety_action_name = None
                    error_wait_start = time.time()
                    while time.time() - error_wait_start < 2.0:  # Wait up to 2 seconds for START message
                        try:
                            next_msg = self.msg_q.get(timeout=0.1)
                            print(f"[DEBUG] During error hold, received: {next_msg}")
                            # Look for any START message (generic safety action)
                            if "START" in next_msg and ":" in next_msg:
                                # Extract the command name after the colon (e.g., "START: retract" -> "retract")
                                parts = next_msg.split(":", 1)
                                if len(parts) == 2:
                                    safety_action_name = parts[1].strip()
                                    safety_action_in_progress = True
                                    self.status_cb(f"Safety action '{safety_action_name}' triggered. Waiting for completion...", line_num)
                                    break
                        except queue.Empty:
                            continue
                    
                    # If safety action is in progress, wait for its DONE message
                    if safety_action_in_progress and safety_action_name:
                        safety_timeout = time.time() + 60  # 60 second timeout
                        while self.is_running and time.time() < safety_timeout:
                            try:
                                safety_msg = self.msg_q.get(timeout=0.1)
                                print(f"[DEBUG] Waiting for safety action completion: {safety_msg}")
                                # Check if DONE message contains the safety action name
                                if "DONE" in safety_msg and safety_action_name.lower() in safety_msg.lower():
                                    self.status_cb(f"Safety action '{safety_action_name}' complete. Click Reset to clear error.", line_num)
                                    break
                            except queue.Empty:
                                continue
                    
                    # Enter permanent hold state - only reset or stop can exit
                    # Do NOT allow resume with Run button
                    while self.is_running and not self._stop_event.is_set():
                        time.sleep(0.1)
                        # Ignore resume events - errors require reset, not resume
                        if self._resume_event.is_set():
                            self._resume_event.clear()  # Clear the event but don't resume
                    
                    # User clicked Stop (or script was stopped externally)
                    self.is_held = False
                    return False

                # Check for failure messages first
                if "FAILED" in msg:
                    for command_to_check in wait_list:
                        # Generic check: command name should appear in failure message
                        if command_to_check in msg:
                            self.status_cb(
                                f"Error on L{line_num}: Received FAILURE for {command_to_check}. Message: {msg}",
                                line_num)
                            return False

                # Check for success messages
                for i in range(len(wait_list) - 1, -1, -1):
                    command_to_check = wait_list[i]
                    
                    # Generic check: command name should appear in DONE message (case insensitive)
                    if command_to_check.lower() in msg.lower() and "DONE" in msg:
                        wait_list.pop(i)
                        self.status_cb(f"L{line_num}: Received DONE for {command_to_check}", line_num)
                        break

            except queue.Empty:
                continue

        self.status_cb(f"L{line_num}: All operations complete.", line_num)
        return True
