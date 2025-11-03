# script_validator.py

"""
Contains the command reference with validation rules (min/max) and default values.
Also contains the script validation logic.
"""

import re
import shlex

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

        # Use shlex to properly handle quoted strings
        try:
            parts = shlex.split(sub_cmd_str)
        except ValueError:
            # If shlex fails (e.g., unclosed quotes), fall back to simple split
            parts = sub_cmd_str.split()
        
        if not parts:
            continue
            
        command_word = parts[0]

        # --- Case-insensitive command lookup ---
        command_info = None
        canonical_cmd = None
        for cmd_key in commands:
            if cmd_key.lower() == command_word.lower():
                command_info = commands[cmd_key]
                canonical_cmd = cmd_key
                break

        if not command_info:
            errors.append({"line": line_num, "error": f"In '{sub_cmd_str}': Unknown command '{command_word.upper()}'."})
            continue

        params_def = command_info.get('params', [])
        
        # Check if command has string parameters (don't validate these strictly)
        has_string_params = any(p.get('type') == 'string' for p in params_def)
        has_variadic_params = any(p.get('variadic', False) for p in params_def)
        
        # For commands with string/variadic parameters, skip detailed validation
        if has_string_params or has_variadic_params:
            # Count required parameters (non-optional, including variadic which needs at least 1)
            num_required_params = sum(1 for p in params_def if not p.get("optional"))
            if len(parts) - 1 < num_required_params:
                errors.append({"line": line_num,
                               "error": f"In '{sub_cmd_str}': Not enough parameters for '{command_word}'. Expected at least {num_required_params}."})
            continue
        
        # --- Extract only numeric parts for arguments (for numeric-only commands) ---
        args = []
        for part in parts[1:]:
            # Match a floating point or integer number at the start of the string.
            # This allows for comments/units after the number (e.g., "5 ml", "100_ms")
            match = re.match(r'^-?\d+(\.\d+)?', part)
            if match:
                args.append(match.group(0))

        num_required_params = sum(1 for p in params_def if not p.get("optional"))

        if len(args) < num_required_params:
            errors.append({"line": line_num,
                           "error": f"In '{sub_cmd_str}': Not enough numeric parameters for '{command_word}'. Expected at least {num_required_params}, but found {len(args)}."})
            continue

        # Allow more "arguments" than defined, since they are comments, but only validate the ones that map to params.
        args_to_validate = args[:len(params_def)]

        for j, arg in enumerate(args_to_validate):
            param_def = params_def[j]
            # Handle both old ('name') and new ('parameter') structures
            param_name = param_def.get('name') or param_def.get('parameter', f'param{j}')
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


def _get_indent_level(line):
    """Get indentation level, handling both spaces and tabs."""
    # Convert tabs to 4 spaces for consistent indentation handling
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(' '))

def _collapse_logging_blocks(content, line_offset=0):
    """
    Collapses indented blocks for logging commands into single-line commands.
    This allows the validator to properly validate these commands.
    """
    lines = content.splitlines()
    result_lines = []
    i = 0
    
    # Commands that support indented blocks
    block_commands = ['queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
    
    
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Keep comments and empty lines as-is
        if not line_stripped or line_stripped.startswith('#'):
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
            base_indent = _get_indent_level(line)
            
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
                peek_indent = _get_indent_level(peek_line)
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
                    block_line_indent = _get_indent_level(block_line)
                    
                    # Stop if we hit a non-indented line
                    if block_line_indent <= base_indent:
                        break
                    
                    # Add this line's content to args
                    collected_args.append(block_stripped)
                    j += 1
                
                # Create collapsed line
                collapsed_line = f"{' ' * base_indent}{command_word} {' '.join(collected_args)}"
                result_lines.append(collapsed_line)
                
                # Skip the processed block
                i = j
                continue
        
        # Not a block command or no indented block - keep line as-is
        result_lines.append(line)
        i += 1
    
    result = '\n'.join(result_lines)
    # Return tuple for compatibility with script_processor, but validator doesn't use the line map
    return result, {}

def validate_script(script_content, scripting_commands):
    """Validates an entire script against the command reference."""
    errors = []
    
    # First collapse logging blocks so they can be validated properly
    collapsed_content, _ = _collapse_logging_blocks(script_content)
    
    lines = collapsed_content.splitlines()
    indent_stack = [0]  # Stack of indentation levels (in spaces)
    in_logging_block = False
    logging_block_indent = 0

    for i, line in enumerate(lines):
        line_num = i + 1
        line_content = line.strip()
        if not line_content or line_content.startswith('#'):
            continue

        # Handle both tabs and spaces for indentation
        leading_spaces = _get_indent_level(line)
        
        # Check if we're exiting a logging block
        if in_logging_block and leading_spaces <= logging_block_indent:
            in_logging_block = False
        
        # Check if we're in a logging block and should skip validation
        if in_logging_block and leading_spaces > logging_block_indent:
            # This is an indented line in a logging block - skip validation
            # But still track indentation
            if leading_spaces > indent_stack[-1]:
                indent_stack.append(leading_spaces)
            elif leading_spaces < indent_stack[-1]:
                while indent_stack and leading_spaces < indent_stack[-1]:
                    indent_stack.pop()
            continue
        
        # Check indentation rules
        if leading_spaces > indent_stack[-1]:
            # Indent should only happen after CYCLE or logging commands
            prev_line_idx = i - 1
            prev_line_content = ""
            # Find the previous non-empty line
            while prev_line_idx >= 0:
                prev_line_content = lines[prev_line_idx].strip()
                if prev_line_content:
                    break
                prev_line_idx -= 1

            # Commands that allow indented blocks
            allowed_block_commands = ['cycle', 'queue_for_logging', 'unqueue_for_logging', 
                                     'start_logging', 'stop_logging']
            
            try:
                prev_parts = shlex.split(prev_line_content) if prev_line_content else []
            except ValueError:
                prev_parts = prev_line_content.split()
            prev_cmd = prev_parts[0].lower() if prev_parts else ''
            
            if prev_cmd not in allowed_block_commands:
                errors.append({"line": line_num, "error": "Unexpected indent."})
                indent_stack.append(leading_spaces)
            elif prev_cmd in ['queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']:
                # Entering a logging block - skip validation for this and subsequent indented lines
                in_logging_block = True
                logging_block_indent = indent_stack[-1]
                indent_stack.append(leading_spaces)
                # Skip validation for this line since it's part of a logging block
                continue
            else:
                # CYCLE or other allowed block command
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

        errors.extend(_validate_line(line, line_num, scripting_commands))

    if len(indent_stack) > 1:
        errors.append({"line": len(lines), "error": "Unexpected end of file: missing dedent for a CYCLE block."})

    return errors


def validate_single_line(line_content, line_num, commands):
    """Validates a single line of a script."""
    line = line_content.strip()
    if not line or line.startswith('#'):
        return []
    
    # Check if this is a logging command with indented block
    # For single block mode, we skip validation since the indented lines will be handled
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = line.split()
    
    command_word = parts[0].lower() if parts else ''
    logging_commands = ['queue_for_logging', 'unqueue_for_logging', 'start_logging', 'stop_logging']
    
    if command_word in logging_commands and len(parts) == 1:
        # This is a logging command with no args on the same line
        # Assume it has an indented block that will be collected in single block mode
        # Skip validation for now (the script processor will handle it)
        return []
    
    return _validate_line(line, line_num, commands)
