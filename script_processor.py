import time
import threading
import queue
import tkinter as tk  # For TclError and StringVar
import re

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
        "description": "Waits until a variable reaches a target value (e.g., wait_for fillhead.temp_c = 70).",
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
    }
}

class ScriptRunner(threading.Thread):
    """
    Runs a script in a separate thread to avoid blocking the GUI.
    Handles script parsing, command execution, and status reporting.
    """
    def __init__(self, script_content, shared_gui_refs, status_cb, completion_cb, msg_q, scripting_commands, script_handlers, line_offset=0):
        super().__init__(daemon=True)
        self.script_content = script_content
        self.gui_refs = shared_gui_refs
        # Correctly extract command_funcs from the shared_gui_refs
        self.command_funcs = shared_gui_refs.get('command_funcs', {})
        self.status_cb = status_cb
        self.completion_cb = completion_cb
        self.msg_q = msg_q
        self.scripting_commands = scripting_commands
        self.script_handlers = script_handlers # Store the handlers
        self.line_offset = line_offset
        self._stop_event = threading.Event()
        self.is_running = False
        self.runtime_defaults = {}
        # To map expanded lines back to original source lines
        try:
            expanded_content, self.line_map = self._expand_loops(script_content, line_offset)
            self.script_lines = expanded_content
        except Exception as e:
            self.script_lines = [f"Error processing script: {e}"]
            self.line_map = {0: 1 + line_offset}

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
                    
                    line_indent = len(line) - len(line.lstrip(' '))

                    # Find the first non-empty, indented line to start the block
                    body_start_index = -1
                    block_indent = -1
                    for j in range(i + 1, len(block_with_nums)):
                        if block_with_nums[j][0].strip():
                            body_indent = len(block_with_nums[j][0]) - len(block_with_nums[j][0].lstrip(' '))
                            if body_indent > line_indent:
                                body_start_index = j
                                block_indent = body_indent
                            break # Found first non-empty line, stop searching

                    # If no indented block was found, just skip the CYCLE line
                    if body_start_index == -1:
                        i += 1
                        continue

                    # Find the end of the block
                    body_end_index = body_start_index
                    for j in range(body_start_index, len(block_with_nums)):
                        line_content = block_with_nums[j][0]
                        # A non-empty line with less or equal indent ends the block
                        if line_content.strip():
                            current_line_indent = len(line_content) - len(line_content.lstrip(' '))
                            if current_line_indent < block_indent:
                                body_end_index = j - 1 # The block ended on the previous line
                                break
                        # If we haven't broken, this line is part of the block
                        body_end_index = j
                    
                    loop_body_with_nums = block_with_nums[body_start_index : body_end_index + 1]
                    
                    expanded_body = _expand_recursive(loop_body_with_nums)
                    
                    for _ in range(count):
                        expanded_list.extend(expanded_body)
                    
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

    def run(self):
        """The main execution loop for the script thread."""
        print("[DEBUG] ScriptRunner.run() started.")
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
            print(f"[DEBUG] Cleared {cleared_count} stale messages from queue.")

        # Clear the injection target display at the beginning of the script
        if self.gui_refs:
            self.gui_refs['injection_target_ml_var'].set('---')

        for i, line in enumerate(self.script_lines):
            if self._stop_event.is_set():
                self.status_cb("Script stopped by user.", -1)
                print("[DEBUG] ScriptRunner stop event detected.")
                break

            original_line_num = self.line_map.get(i, i + self.line_offset + 1)
            self.status_cb(f"Executing line {original_line_num}...", original_line_num)
            
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            try:
                print(f"[DEBUG] Processing line {original_line_num}: '{line}'")
                # Pass the correct, current line number to the processing method
                if not self._process_line(line, original_line_num):
                    print(f"[DEBUG] _process_line returned False for line {original_line_num}. Halting.")
                    # Stop execution if _process_line returns False
                    break
            except Exception as e:
                error_msg = f"Runtime Error on line {original_line_num}: {e}"
                self.status_cb(error_msg, original_line_num)
                print(f"[DEBUG] Exception during _process_line: {e}")
                # Halt execution on error
                break
        
        self.is_running = False
        print("[DEBUG] ScriptRunner.run() finished.")
        # Always call the completion callback when the loop finishes for any reason.
        if self.completion_cb:
            print("[DEBUG] Calling completion_cb.")
            self.completion_cb()

        # Clear the injection target display at the end of the script
        if self.gui_refs:
            self.gui_refs['injection_target_ml_var'].set('---')
    
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
        
        # Combine value and unit if they are separate words
        combined_args = []
        i = 0
        while i < len(unassigned_args):
            arg = unassigned_args[i]
            # Heuristic: if the current arg is a number and the next is not, they might be value+unit
            is_numeric = self._is_numeric(arg)
            
            if is_numeric and i + 1 < len(unassigned_args) and not self._is_numeric(unassigned_args[i+1]):
                combined_args.append(f"{arg} {unassigned_args[i+1]}")
                i += 2
            else:
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
            
            self.status_cb(f"Waiting for {duration_s} seconds...", line_num)
            
            start_time = time.time()
            while time.time() - start_time < duration_s:
                if self._stop_event.is_set():
                    self.status_cb("Wait cancelled.", line_num)
                    return "stop"
                time.sleep(0.05) # Sleep in small intervals to remain responsive
                
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

    def _process_line(self, line, line_num):
        sub_commands = line.split(',')
        commands_to_wait_for = []

        for sub_cmd_str in sub_commands:
            if not self.is_running: return False
            sub_cmd_str = sub_cmd_str.strip()
            if not sub_cmd_str: continue

            parts = sub_cmd_str.split()
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
            handler = self.script_handlers.get(command_word)
            if handler:
                # Script handlers will need to be updated to expect a dict of params
                # For now, we will adapt by creating a positional list.
                pos_args = []
                for param_def in command_info.get('params', []):
                    if param_def['name'] in resolved_params:
                        pos_args.append(resolved_params[param_def['name']])
                
                if not handler(self, pos_args, line_num): return False
            
            elif device == "script":
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
                    param_name = param_def['name']
                    if param_name in resolved_params:
                        final_args.append(str(resolved_params[param_name]))
                    elif not param_def.get('optional'):
                        # This should have been caught by the parser, but as a safeguard:
                        self.status_cb(f"Error on L{line_num}: Missing required parameter '{param_name}' for {command_word}.", line_num)
                        self.is_running = False
                        return False

                if not self.is_running: return False

                final_command_str = f"{command_word} {' '.join(final_args)}" if final_args else command_word
                send_func = self.command_funcs.get(f"send_{device}")
                if send_func:
                    print(f"[DEBUG] Sending command to {device}: '{final_command_str}'")
                    send_func(final_command_str)
                    if command_info.get("wait_for_done", True): # Assume wait unless specified otherwise
                        commands_to_wait_for.append(command_word)

            time.sleep(0.05)

        if not self.is_running: return False
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

                # Check for failure messages first
                if "FAILED" in msg:
                    for command_to_check in wait_list:
                        is_failure = False
                        if command_to_check == "VACUUM_LEAK_TEST" and "LEAK_TEST" in msg:
                            is_failure = True
                        elif command_to_check in msg:
                            is_failure = True

                        if is_failure:
                            self.status_cb(
                                f"Error on L{line_num}: Received FAILURE for {command_to_check}. Message: {msg}",
                                line_num)
                            return False

                # Check for success messages
                for i in range(len(wait_list) - 1, -1, -1):
                    command_to_check = wait_list[i]
                    is_complete = False

                    # --- FINAL FIX ---
                    # Added specific checks for pinch valve homing commands, as their "DONE"
                    # messages don't contain the original command string.
                    cmd_lower = command_to_check.lower()
                    
                    if "leak" in cmd_lower and "LEAK_TEST" in msg and "PASSED" in msg:
                        is_complete = True
                    elif "inj_valve" in cmd_lower and "home" in cmd_lower and "inj_valve" in msg and "DONE" in msg:
                        is_complete = True
                    elif "vac_valve" in cmd_lower and "home" in cmd_lower and "vac_valve" in msg and "DONE" in msg:
                        is_complete = True
                    # --- FIX for Valve Open/Close ---
                    # These also have unique DONE messages that don't contain the command name.
                    elif "inj_valve" in cmd_lower and ("open" in cmd_lower or "close" in cmd_lower) and "inj_valve" in msg and "DONE" in msg:
                        is_complete = True
                    elif "vac_valve" in cmd_lower and ("open" in cmd_lower or "close" in cmd_lower) and "vac_valve" in msg and "DONE" in msg:
                        is_complete = True
                    # Generic fallback for other commands - case insensitive check
                    elif command_to_check.lower() in msg.lower() and "DONE" in msg:
                        is_complete = True
                    # -----------------

                    if is_complete:
                        wait_list.pop(i)
                        self.status_cb(f"L{line_num}: Received DONE for {command_to_check}", line_num)
                        break

            except queue.Empty:
                continue

        self.status_cb(f"L{line_num}: All operations complete.", line_num)
        return True