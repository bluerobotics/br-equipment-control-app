import time
import threading
import queue
import tkinter as tk  # For TclError and StringVar
import re

# --- Script-Specific Command Definitions ---
SCRIPT_COMMANDS = {
    "WAIT": {
        "device": "script",
        "params": [{"name": "time_ms", "type": "int"}],
        "help": "Pauses script execution for a specified duration."
    },
    "CYCLE": {
        "device": "script",
        "params": [],
        "help": "Marks a point for the script to loop back to."
    },
    "REPEAT": {
        "device": "script",
        "params": [{"name": "count", "type": "int"}],
        "help": "Repeats the script from the last CYCLE point."
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

    def _get_default(self, command_name, param_index):
        # This function is no longer needed with the new keyword parser.
        pass
    
    def _parse_keyword_args(self, parts, command_info):
        """
        Parses a list of command parts for keyword arguments.
        Returns a dictionary of resolved arguments and an error string if applicable.
        """
        resolved_args = {}
        error = None
        
        # --- Create a map of keyword -> param_name ---
        keyword_map = {}
        for param in command_info.get('params', []):
            for keyword in param.get('keywords', []):
                keyword_map[keyword.lower()] = param['name']

        # --- Identify values and their potential keywords ---
        # A value is a number, a keyword is a non-number.
        # Example: "HEATER_ON", "70", "C", "20", "P"
        # We pair the value with the keywords that follow it.
        
        i = 1 # Start after the command word
        while i < len(parts):
            # Check if the current part is a number
            current_part = parts[i]
            is_numeric = False
            try:
                float(current_part)
                is_numeric = True
            except ValueError:
                pass
            
            if is_numeric:
                value = current_part
                # The next parts are potential keywords until we hit another number or the end
                potential_keywords = []
                j = i + 1
                while j < len(parts):
                    next_part = parts[j]
                    is_next_numeric = False
                    try:
                        float(next_part)
                        is_next_numeric = True
                    except ValueError:
                        pass
                    
                    if is_next_numeric:
                        break # Stop at the next number
                    
                    potential_keywords.append(next_part.lower())
                    j += 1
                
                # --- Find the first matching keyword ---
                found_keyword = False
                for p_keyword in potential_keywords:
                    if p_keyword in keyword_map:
                        param_name = keyword_map[p_keyword]
                        if param_name not in resolved_args:
                            resolved_args[param_name] = value
                            found_keyword = True
                            break # Found a match, consume the value
                
                # If no keyword was found for this value, it could be a positional argument
                if not found_keyword:
                    # For now, we only support keyword arguments for this new parser
                    # This could be extended to support positional args as well
                    pass
                
                i = j # Move the main index to the start of the next value/keyword group
            else:
                i += 1 # Not a number, just skip to the next part
        
        # --- Fill in defaults for any missing optional parameters ---
        for param in command_info.get('params', []):
            param_name = param['name']
            if param_name not in resolved_args:
                if param.get('optional'):
                    if 'default' in param:
                        resolved_args[param_name] = param['default']
                else:
                    # This is a required parameter that was not found.
                    error = f"Missing required parameter '{param_name}'"
                    break
        
        return resolved_args, error

    def _handle_wait(self, args, line_num, is_seconds=False):
        if not args:
            self.status_cb(f"Error on L{line_num}: WAIT command requires a duration.", line_num)
            self.is_running = False
            return False
        try:
            duration = float(args[0])
            duration_ms = duration * 1000 if is_seconds else duration
            unit = "s" if is_seconds else "ms"
            self.status_cb(f"L{line_num}: Waiting for {duration} {unit}...", line_num)

            start_time = time.time()
            end_time = start_time + (duration_ms / 1000.0)
            while time.time() < end_time:
                if not self.is_running: return False
                remaining_time = end_time - time.time()
                self.status_cb(f"L{line_num}: Waiting... {remaining_time:.1f}s remaining", line_num)
                time.sleep(0.1) # Update GUI 10 times per second
            return True
        except ValueError:
            self.status_cb(f"Error on L{line_num}: Invalid duration for WAIT command.", line_num)
            self.is_running = False
            return False

    def _process_line(self, line, line_num):
        sub_commands = line.split(',')
        commands_to_wait_for = []

        for sub_cmd_str in sub_commands:
            if not self.is_running: return False
            sub_cmd_str = sub_cmd_str.strip()
            if not sub_cmd_str: continue

            parts = sub_cmd_str.split()
            command_word = parts[0].upper()
            
            command_info = self.scripting_commands.get(command_word)

            if not command_info:
                self.status_cb(f"Error on L{line_num}: Unknown command '{command_word}'.", line_num)
                self.is_running = False
                return False

            device = command_info['device']
            
            # --- New Keyword Argument Parsing ---
            resolved_params, error = self._parse_keyword_args(parts, command_info)
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
                # Handle built-in script commands
                if command_word == "WAIT":
                    if not self._handle_wait([resolved_params.get('time_ms', 0)], line_num, is_seconds=True): return False
                elif command_word in ["CYCLE", "REPEAT"]:
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
                    if command_to_check == "VACUUM_LEAK_TEST" and "LEAK_TEST" in msg and "PASSED" in msg:
                        is_complete = True
                    elif (command_to_check == "INJECTION_VALVE_HOME_UNTUBED" or command_to_check == "INJECTION_VALVE_HOME_TUBED") and "inj_valve" in msg and "DONE" in msg:
                        is_complete = True
                    elif (command_to_check == "VACUUM_VALVE_HOME_UNTUBED" or command_to_check == "VACUUM_VALVE_HOME_TUBED") and "vac_valve" in msg and "DONE" in msg:
                        is_complete = True
                    # --- FIX for Valve Open/Close ---
                    # These also have unique DONE messages that don't contain the command name.
                    elif (command_to_check == "INJECTION_VALVE_OPEN" or command_to_check == "INJECTION_VALVE_CLOSE") and "inj_valve" in msg and "DONE" in msg:
                        is_complete = True
                    elif (command_to_check == "VACUUM_VALVE_OPEN" or command_to_check == "VACUUM_VALVE_CLOSE") and "vac_valve" in msg and "DONE" in msg:
                        is_complete = True
                    # Generic fallback for other commands like MOVE_X, HOME_Y, etc.
                    elif command_to_check in msg and "DONE" in msg:
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