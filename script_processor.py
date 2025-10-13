import time
import threading
import queue
import tkinter as tk  # For TclError and StringVar
import re

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
        param_def = self.scripting_commands[command_name]['params'][param_index]
        param_name = param_def['name']

        if command_name.startswith("MOVE"):
            if "Speed" in param_name: return self.runtime_defaults.get("MOVE_VEL") or param_def.get("default")
            if "Accel" in param_name: return self.runtime_defaults.get("MOVE_ACC") or param_def.get("default")
            if "Torque" in param_name: return self.runtime_defaults.get("MOVE_TORQUE") or param_def.get("default")

        if command_name == "WAIT_UNTIL_VACUUM":
            if "Target-PSI" in param_name: return self.runtime_defaults.get("VACUUM_TARGET") or param_def.get("default")
            if "Timeout" in param_name: return self.runtime_defaults.get("VACUUM_TIMEOUT") or param_def.get("default")

        if command_name == "WAIT_UNTIL_HEATER_AT_TEMP":
            if "Target-Temp" in param_name: return self.runtime_defaults.get("HEATER_TARGET") or param_def.get(
                "default")
            if "Timeout" in param_name: return self.runtime_defaults.get("HEATER_TIMEOUT") or param_def.get("default")

        return param_def.get("default")

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

    def _handle_wait_until_vacuum(self, args, line_num):
        try:
            # New logic: Use the GUI's target var as the source of truth
            target_psi_str = args[0] if len(args) > 0 else self.gui_refs['vac_target_var'].get()
            target_psi = float(target_psi_str)
            timeout_s = float(args[1]) if len(args) > 1 else float(self.runtime_defaults.get("VACUUM_TIMEOUT", 60))
        except (ValueError, IndexError, tk.TclError):
            self.status_cb(f"Error on L{line_num}: Invalid parameters for WAIT_UNTIL_VACUUM.", line_num)
            self.is_running = False
            return False

        start_time = time.time()
        while True:
            if not self.is_running: return False
            if time.time() - start_time > timeout_s:
                self.status_cb(f"Error on L{line_num}: Timeout waiting for vacuum target.", line_num)
                self.is_running = False
                return False

            try:
                psig_str = self.gui_refs['vacuum_psig_var'].get().split()[0]
                current_psi = float(psig_str)
                self.status_cb(f"L{line_num}: Waiting for vacuum <= {target_psi:.2f}, current: {current_psi:.2f}",
                                     line_num)
                if current_psi <= target_psi:
                    self.status_cb(f"L{line_num}: Vacuum target reached ({current_psi:.2f} PSIG).", line_num)
                    return True
            except (ValueError, IndexError, tk.TclError):
                self.status_cb(f"L{line_num}: Waiting for vacuum... (current value invalid)", line_num)

            time.sleep(0.2)

    def _handle_wait_until_heater_at_temp(self, args, line_num):
        try:
            # The temperature is now a required parameter.
            target_temp = float(args[0])
            timeout_s = float(args[1]) if len(args) > 1 else float(self.runtime_defaults.get("HEATER_TIMEOUT", 100))
        except (ValueError, IndexError):
            self.status_cb(f"Error on L{line_num}: Invalid or missing parameters for WAIT_UNTIL_HEATER_AT_TEMP.", line_num)
            self.is_running = False
            return False

        start_time = time.time()
        # Calculate the 5% tolerance band
        tolerance = target_temp * 0.05
        lower_bound = target_temp - tolerance
        upper_bound = target_temp + tolerance

        while True:
            if not self.is_running: return False
            if time.time() - start_time > timeout_s:
                self.status_cb(f"Error on L{line_num}: Timeout waiting for heater target.", line_num)
                self.is_running = False
                return False

            try:
                temp_str = self.gui_refs['temp_c_var'].get().split()[0]
                current_temp = float(temp_str)
                self.status_cb(f"L{line_num}: Waiting for temp in range [{lower_bound:.1f}..{upper_bound:.1f}]C, current: {current_temp:.1f}C",
                                     line_num)
                if lower_bound <= current_temp <= upper_bound:
                    self.status_cb(f"L{line_num}: Heater target reached ({current_temp:.1f} C).", line_num)
                    return True
            except (ValueError, IndexError, tk.TclError):
                self.status_cb(f"L{line_num}: Waiting for temp... (current value invalid)", line_num)

            time.sleep(0.2)

    def _process_line(self, line, line_num):
        sub_commands = line.split(',')
        commands_to_wait_for = []

        for sub_cmd_str in sub_commands:
            if not self.is_running: return False
            sub_cmd_str = sub_cmd_str.strip()
            if not sub_cmd_str: continue

            parts = sub_cmd_str.split()
            command_word = parts[0].upper()
            
            # --- NEW: Extract only numeric parts for arguments ---
            args = []
            for part in parts[1:]:
                match = re.match(r'^-?\d+(\.\d+)?', part)
                if match:
                    args.append(match.group(0))

            command_info = self.scripting_commands.get(command_word)

            if not command_info:
                self.status_cb(f"Error on L{line_num}: Unknown command '{command_word}'.", line_num)
                self.is_running = False
                return False

            device = command_info['device']
            
            # --- Special Handling for Script-Aware Commands ---
            # Update the GUI's own variables to keep them in sync with the script
            if command_word == "SET_HEATER_SETPOINT" and len(args) > 0:
                # CORRECTED: Uses the real command and the correct GUI variable.
                self.gui_refs['pid_setpoint_var'].set(args[0])
            if command_word == "SET_VACUUM_TARGET" and len(args) > 0:
                self.gui_refs['vac_target_var'].set(args[0])

            if device == "script":
                if command_word == "WAIT_MS":
                    if not self._handle_wait(args, line_num, is_seconds=False): return False
                elif command_word == "WAIT":
                    if not self._handle_wait(args, line_num, is_seconds=True): return False
                elif command_word == "WAIT_UNTIL_VACUUM":
                    if not self._handle_wait_until_vacuum(args, line_num): return False
                elif command_word == "WAIT_UNTIL_HEATER_AT_TEMP":
                    if not self._handle_wait_until_heater_at_temp(args, line_num): return False
                elif command_word.startswith("SET_DEFAULT_"):
                    key = command_word.replace("SET_DEFAULT_", "")
                    if len(args) == 1: self.runtime_defaults[key] = args[0]
            # --- NEW: Special handling for 'both' device commands like ABORT ---
            elif device == "both":
                # The validator ensures this is a known command, so we can call it directly.
                # Currently, only "ABORT" uses device "both".
                func = self.command_funcs.get(command_word.lower())
                if func:
                    print(f"[DEBUG] Calling global command: '{command_word}'")
                    func()
                else:
                    self.status_cb(f"Error on L{line_num}: No handler for global command '{command_word}'.", line_num)
                    self.is_running = False
                    return False
            else:
                params_def = command_info['params']
                full_args = list(args)

                if len(args) < len(params_def):
                    for j in range(len(args), len(params_def)):
                        param_def = params_def[j]
                        default_val = self._get_default(command_word, j)

                        if default_val is not None:
                            full_args.append(str(default_val))
                        elif not param_def.get("optional"):
                            self.status_cb(f"Error on L{line_num}: Missing required parameter '{param_def['name']}' for {command_word}.", line_num)
                            self.is_running = False
                            return False

                if not self.is_running: return False

                final_command_str = f"{command_word} {' '.join(full_args)}" if full_args else command_word
                send_func = self.command_funcs.get(f"send_{device}")
                if send_func:
                    print(f"[DEBUG] Sending command to {device}: '{final_command_str}'")
                    send_func(final_command_str)
                    # Add any command that elicits a "_DONE" response to this list.
                    if "MOVE" in command_word or \
                       "HOME" in command_word or \
                       "OPEN" in command_word or \
                       "CLOSE" in command_word or \
                       "VACUUM_LEAK_TEST" in command_word or \
                       "INJECT_STATOR" in command_word or \
                       "INJECT_ROTOR" in command_word:
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