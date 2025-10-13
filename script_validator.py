# script_validator.py

"""
Contains the command reference with validation rules (min/max) and default values.
Also contains the script validation logic.
"""

import re

# --- Validation Logic ---

def _validate_line(line_content, line_num, commands):
    """Helper function to validate a single, non-empty, non-comment line."""
    errors = []
    sub_commands = line_content.strip().split(',')
    
    command_word_for_line = sub_commands[0].strip().split()[0].upper()
    if (command_word_for_line == "CYCLE" or command_word_for_line == "END_REPEAT") and len(sub_commands) > 1:
        errors.append({"line": line_num, "error": "CYCLE and END_REPEAT commands must be on their own line."})
        return errors # Stop processing this line as it's fundamentally malformed

    for sub_cmd_str in sub_commands:
        sub_cmd_str = sub_cmd_str.strip()
        if not sub_cmd_str:
            continue

        parts = sub_cmd_str.split()
        command_word = parts[0].upper()

        # --- NEW: Extract only numeric parts for arguments ---
        args = []
        for part in parts[1:]:
            # Match a floating point or integer number at the start of the string.
            # This allows for comments/units after the number (e.g., "5 ml", "100_ms")
            match = re.match(r'^-?\d+(\.\d+)?', part)
            if match:
                args.append(match.group(0))

        if command_word not in commands:
            errors.append({"line": line_num, "error": f"In '{sub_cmd_str}': Unknown command '{command_word}'."})
            continue

        command_info = commands[command_word]
        params_def = command_info['params']
        num_required_params = sum(1 for p in params_def if not p.get("optional"))

        if len(args) < num_required_params:
            errors.append({"line": line_num,
                           "error": f"In '{sub_cmd_str}': Not enough numeric parameters for '{command_word}'. Expected at least {num_required_params}, but found {len(args)}."})
            continue

        # Allow more "arguments" than defined, since they are comments, but only validate the ones that map to params.
        args_to_validate = args[:len(params_def)]

        for j, arg in enumerate(args_to_validate):
            param_def = params_def[j]
            param_name = param_def['name']
            try:
                value = float(arg)
            except ValueError:
                errors.append({"line": line_num,
                               "error": f"In '{sub_cmd_str}': Parameter '{param_name}' must be a number, but got '{arg}'."})
                continue

            if 'min' in param_def and value < param_def['min']:
                errors.append({"line": line_num,
                               "error": f"In '{sub_cmd_str}': Parameter '{param_name}' is below minimum of {param_def['min']}. Got {value}."})

            if 'max' in param_def and value > param_def['max']:
                errors.append({"line": line_num,
                               "error": f"In '{sub_cmd_str}': Parameter '{param_name}' is above maximum of {param_def['max']}. Got {value}."})

    return errors


def validate_script(script_content, commands):
    """Validates an entire script against the command reference."""
    errors = []
    lines = script_content.splitlines()
    indent_stack = [0]  # Stack of indentation levels (in spaces)

    for i, line in enumerate(lines):
        line_num = i + 1
        line_content = line.strip()
        if not line_content or line_content.startswith('#'):
            continue

        leading_spaces = len(line) - len(line.lstrip(' '))
        
        # Check indentation rules
        if leading_spaces > indent_stack[-1]:
            # Indent should only happen after a REPEAT command
            prev_line_idx = i - 1
            prev_line_content = ""
            # Find the previous non-empty line
            while prev_line_idx >= 0:
                prev_line_content = lines[prev_line_idx].strip()
                if prev_line_content:
                    break
                prev_line_idx -= 1

            if not prev_line_content.upper().startswith("CYCLE"):
                errors.append({"line": line_num, "error": "Unexpected indent."})
            indent_stack.append(leading_spaces)
        elif leading_spaces < indent_stack[-1]:
            # Dedent must match a previous indentation level
            while indent_stack and leading_spaces < indent_stack[-1]:
                indent_stack.pop()
            if not indent_stack or leading_spaces != indent_stack[-1]:
                errors.append({"line": line_num, "error": "Dedent does not match any outer indentation level."})

        # Validate the command itself
        first_command_word = line_content.split(',')[0].strip().split()[0].upper()
        if first_command_word == "END_REPEAT":
            errors.append({"line": line_num, "error": "END_REPEAT is no longer used. Use indentation to define blocks."})
            continue

        errors.extend(_validate_line(line, line_num, commands))

    if len(indent_stack) > 1:
        errors.append({"line": len(lines), "error": "Unexpected end of file: missing dedent for a CYCLE block."})

    return errors


def validate_single_line(line_content, line_num, commands):
    """Validates a single line of a script."""
    line = line_content.strip()
    if not line or line.startswith('#'):
        return []
    return _validate_line(line, line_num, commands)
