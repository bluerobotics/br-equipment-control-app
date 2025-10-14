import time
import tkinter as tk

def _handle_wait_until_vacuum(script_runner, args, line_num):
    try:
        target_psi = float(args[0])
        timeout_s = float(args[1]) if len(args) > 1 else 60.0
    except (ValueError, IndexError):
        script_runner.status_cb(f"Error on L{line_num}: Invalid parameters for WAIT_UNTIL_VACUUM.", line_num)
        return False

    start_time = time.time()
    while True:
        if not script_runner.is_running: return False
        if time.time() - start_time > timeout_s:
            script_runner.status_cb(f"Error on L{line_num}: Timeout waiting for vacuum target.", line_num)
            return False

        try:
            # Note: This relies on a specific gui_var name existing in the shared_gui_refs
            psig_str = script_runner.gui_refs['fillhead_vacuum_psig_var'].get().split()[0]
            current_psi = float(psig_str)
            script_runner.status_cb(f"L{line_num}: Waiting for vacuum <= {target_psi:.2f}, current: {current_psi:.2f}", line_num)
            if current_psi <= target_psi:
                script_runner.status_cb(f"L{line_num}: Vacuum target reached ({current_psi:.2f} PSIG).", line_num)
                return True
        except (ValueError, IndexError, tk.TclError):
            script_runner.status_cb(f"L{line_num}: Waiting for vacuum... (current value invalid)", line_num)
        
        time.sleep(0.2)

def _handle_wait_until_heater_at_temp(script_runner, args, line_num):
    try:
        target_temp = float(args[0])
        timeout_s = float(args[1]) if len(args) > 1 else 100.0
    except (ValueError, IndexError):
        script_runner.status_cb(f"Error on L{line_num}: Invalid or missing parameters for WAIT_UNTIL_HEATER_AT_TEMP.", line_num)
        return False

    start_time = time.time()
    tolerance = target_temp * 0.05
    lower_bound = target_temp - tolerance
    upper_bound = target_temp + tolerance

    while True:
        if not script_runner.is_running: return False
        if time.time() - start_time > timeout_s:
            script_runner.status_cb(f"Error on L{line_num}: Timeout waiting for heater target.", line_num)
            return False

        try:
            # Note: This relies on a specific gui_var name
            temp_str = script_runner.gui_refs['fillhead_temp_c_var'].get().split()[0]
            current_temp = float(temp_str)
            script_runner.status_cb(f"L{line_num}: Waiting for temp [{lower_bound:.1f}..{upper_bound:.1f}], current: {current_temp:.1f}C", line_num)
            if lower_bound <= current_temp <= upper_bound:
                script_runner.status_cb(f"L{line_num}: Heater target reached ({current_temp:.1f} C).", line_num)
                return True
        except (ValueError, IndexError, tk.TclError):
            script_runner.status_cb(f"L{line_num}: Waiting for temp... (current value invalid)", line_num)

        time.sleep(0.2)

# --- Public API ---
# A dictionary mapping command names to their handler functions
HANDLERS = {
    "WAIT_UNTIL_VACUUM": _handle_wait_until_vacuum,
    "WAIT_UNTIL_HEATER_AT_TEMP": _handle_wait_until_heater_at_temp
}
