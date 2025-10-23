"""
C++ Code Generator for Device Communication Protocol
Generates commands.h and telemetry.h from JSON schema files.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Dict, Any
import theme


def load_json(filepath: str) -> Dict:
    """Load and parse a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_command_header(commands: Dict[str, Any], device_name: str) -> str:
    """Generate commands.h content from commands.json."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    # Organize commands by category based on common patterns
    categories = {
        'General System Commands': [],
        'Motion Commands': [],
        'Valve Commands': [],
        'Heater Commands': [],
        'Vacuum Commands': [],
        'Script Commands': []
    }
    
    # Categorize commands based on keywords
    for cmd_name, cmd_data in commands.items():
        if 'heater' in cmd_name.lower():
            categories['Heater Commands'].append((cmd_name, cmd_data))
        elif 'vacuum' in cmd_name.lower() and 'valve' not in cmd_name.lower():
            categories['Vacuum Commands'].append((cmd_name, cmd_data))
        elif 'valve' in cmd_name.lower():
            categories['Valve Commands'].append((cmd_name, cmd_data))
        elif any(kw in cmd_name.lower() for kw in ['home', 'jog', 'move', 'inject', 'cartridge', 'machine']):
            categories['Motion Commands'].append((cmd_name, cmd_data))
        elif cmd_data.get('handler') == 'script':
            categories['Script Commands'].append((cmd_name, cmd_data))
        else:
            categories['General System Commands'].append((cmd_name, cmd_data))
    
    # Generate header content
    lines = []
    lines.append("/**")
    lines.append(" * @file commands.h")
    lines.append(f" * @brief Defines the command interface for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from commands.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header file defines all commands that can be sent TO the {device_title} device.")
    lines.append(" * For response message formats, see responses.h")
    lines.append(" * To modify commands, edit commands.json and regenerate this file.")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Command Strings (Host → Device)")
    lines.append("//==================================================================================================")
    lines.append("")
    
    # Generate command string defines for each category
    for category, cmds in categories.items():
        if not cmds:
            continue
            
        lines.append("/**")
        lines.append(f" * @name {category}")
        lines.append(" * @{")
        lines.append(" */")
        
        for cmd_name, cmd_data in cmds:
            # Determine if command has parameters (add trailing space)
            has_params = len(cmd_data.get('params', [])) > 0
            cmd_str = cmd_name + (" " if has_params else "")
            
            help_text = cmd_data.get('help', 'No description available.')
            lines.append(f'#define CMD_STR_{cmd_name.upper():<35} "{cmd_str:<30}" ///< {help_text}')
        
        lines.append("/** @} */")
        lines.append("")
    
    # Generate enum
    lines.append("//==================================================================================================")
    lines.append("// Command Enum")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @enum Command")
    lines.append(f" * @brief Enumerates all possible commands that can be processed by the {device_title}.")
    lines.append(" * @details This enum provides a type-safe way to handle incoming commands.")
    lines.append(" */")
    lines.append("typedef enum {")
    lines.append("    CMD_UNKNOWN,                        ///< Represents an unrecognized or invalid command.")
    lines.append("")
    
    # Add enum entries by category
    for category, cmds in categories.items():
        if not cmds:
            continue
            
        lines.append(f"    // {category}")
        for i, (cmd_name, cmd_data) in enumerate(cmds):
            # Determine if this is the last entry overall
            is_last = (category == list(categories.keys())[-1] and i == len(cmds) - 1)
            comma = "" if is_last else ","
            lines.append(f"    CMD_{cmd_name.upper():<35} ///< @see CMD_STR_{cmd_name.upper()}{comma}")
        lines.append("")
    
    # Remove trailing empty line and add closing brace
    if lines[-1] == "":
        lines.pop()
    lines.append("} Command;")
    
    return '\n'.join(lines)


def generate_command_parser_header(commands: Dict[str, Any], device_name: str) -> str:
    """Generate command_parser.h header file with function declarations."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file command_parser.h")
    lines.append(f" * @brief Command parsing and dispatching declarations for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from commands.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header declares utility functions to parse and dispatch commands for the {device_title}.")
    lines.append(" * @see commands.h for command definitions")
    lines.append(" * @see command_parser.cpp for implementations")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append('#include "commands.h"')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Command Parser Functions")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Parse a command string and return the corresponding Command enum.")
    lines.append(" * @param cmdStr The command string to parse")
    lines.append(" * @return The parsed Command enum value, or CMD_UNKNOWN if not recognized")
    lines.append(" */")
    lines.append("Command parseCommand(const char* cmdStr);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Extract parameter string from a command.")
    lines.append(" * @param cmdStr The full command string")
    lines.append(" * @param cmd The parsed command enum")
    lines.append(" * @return Pointer to the parameter substring, or NULL if no parameters")
    lines.append(" */")
    lines.append("const char* getCommandParams(const char* cmdStr, Command cmd);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Dispatch a parsed command to its handler (template - implement your handlers).")
    lines.append(" * @param cmd The parsed command enum")
    lines.append(" * @param params The parameter string (if any)")
    lines.append(" * @return true if command was handled successfully, false otherwise")
    lines.append(" * ")
    lines.append(" * @note This is a template. Implement your actual command handlers and call them here.")
    lines.append(" */")
    lines.append("bool dispatchCommand(Command cmd, const char* params);")
    
    return '\n'.join(lines)


def generate_command_parser_cpp(commands: Dict[str, Any], device_name: str) -> str:
    """Generate command_parser.cpp implementation file."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file command_parser.cpp")
    lines.append(f" * @brief Command parsing and dispatching implementations for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from commands.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" */")
    lines.append("")
    lines.append('#include "command_parser.h"')
    lines.append('#include <string.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Command Parser Implementation")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("Command parseCommand(const char* cmdStr) {")
    
    # Generate parsing logic for each command
    for cmd_name in commands.keys():
        lines.append(f"    if (strncmp(cmdStr, CMD_STR_{cmd_name.upper()}, strlen(CMD_STR_{cmd_name.upper()})) == 0) return CMD_{cmd_name.upper()};")
    
    lines.append("    return CMD_UNKNOWN;")
    lines.append("}")
    lines.append("")
    lines.append("const char* getCommandParams(const char* cmdStr, Command cmd) {")
    lines.append("    switch (cmd) {")
    
    # Add cases for commands with parameters
    for cmd_name, cmd_data in commands.items():
        if len(cmd_data.get('params', [])) > 0:
            lines.append(f"        case CMD_{cmd_name.upper()}:")
            lines.append(f"            return cmdStr + strlen(CMD_STR_{cmd_name.upper()});")
    
    lines.append("        default:")
    lines.append("            return NULL;")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Command Dispatcher Template")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("bool dispatchCommand(Command cmd, const char* params) {")
    lines.append("    switch (cmd) {")
    
    # Generate dispatch cases
    for cmd_name, cmd_data in commands.items():
        has_params = len(cmd_data.get('params', [])) > 0
        lines.append(f"        case CMD_{cmd_name.upper()}:")
        if has_params:
            lines.append(f"            // TODO: Implement handler with parameters")
            lines.append(f"            // handle_{cmd_name}(params);")
        else:
            lines.append(f"            // TODO: Implement handler")
            lines.append(f"            // handle_{cmd_name}();")
        lines.append("            return true;")
        lines.append("")
    
    lines.append("        case CMD_UNKNOWN:")
    lines.append("        default:")
    lines.append("            return false;")
    lines.append("    }")
    lines.append("}")
    
    return '\n'.join(lines)


def generate_telemetry_formatter(telemetry: Dict[str, Any], device_name: str) -> str:
    """Generate telemetry_formatter.h content with formatting functions."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file telemetry_formatter.h")
    lines.append(f" * @brief Telemetry formatting utilities for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from telemetry.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header provides utility functions to format telemetry messages for the {device_title}.")
    lines.append(" * @see responses.h for response message definitions")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append('#include "responses.h"')
    lines.append('#include <stdio.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Status Message Helpers")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an info status message.")
    lines.append(" * @param message The message to send")
    lines.append(" */")
    lines.append("void sendInfoMessage(const char* message) {")
    lines.append("    Serial.print(STATUS_PREFIX_INFO);")
    lines.append("    Serial.println(message);")
    lines.append("}")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send a start status message.")
    lines.append(" * @param commandName The name of the command that is starting")
    lines.append(" */")
    lines.append("void sendStartMessage(const char* commandName) {")
    lines.append("    Serial.print(STATUS_PREFIX_START);")
    lines.append("    Serial.println(commandName);")
    lines.append("}")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send a done status message.")
    lines.append(" * @param commandName The name of the command that completed")
    lines.append(" */")
    lines.append("void sendDoneMessage(const char* commandName) {")
    lines.append("    Serial.print(STATUS_PREFIX_DONE);")
    lines.append("    Serial.println(commandName);")
    lines.append("}")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an error status message.")
    lines.append(" * @param errorMessage The error message to send")
    lines.append(" */")
    lines.append("void sendErrorMessage(const char* errorMessage) {")
    lines.append("    Serial.print(STATUS_PREFIX_ERROR);")
    lines.append("    Serial.println(errorMessage);")
    lines.append("}")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Builder")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @class TelemetryBuilder")
    lines.append(" * @brief Helper class to build telemetry messages.")
    lines.append(" */")
    lines.append("class TelemetryBuilder {")
    lines.append("private:")
    lines.append("    char buffer[512];")
    lines.append("    size_t position;")
    lines.append("    bool firstField;")
    lines.append("")
    lines.append("public:")
    lines.append("    TelemetryBuilder() {")
    lines.append("        position = snprintf(buffer, sizeof(buffer), \"%s\", TELEM_PREFIX);")
    lines.append("        firstField = true;")
    lines.append("    }")
    lines.append("")
    lines.append("    void addInt(const char* key, int value) {")
    lines.append("        if (!firstField && position < sizeof(buffer)) {")
    lines.append("            buffer[position++] = ',';")
    lines.append("        }")
    lines.append("        position += snprintf(buffer + position, sizeof(buffer) - position, \"%s:%d\", key, value);")
    lines.append("        firstField = false;")
    lines.append("    }")
    lines.append("")
    lines.append("    void addFloat(const char* key, float value, int precision = 2) {")
    lines.append("        if (!firstField && position < sizeof(buffer)) {")
    lines.append("            buffer[position++] = ',';")
    lines.append("        }")
    lines.append("        char format[16];")
    lines.append("        snprintf(format, sizeof(format), \"%%s:%%.%df\", precision);")
    lines.append("        position += snprintf(buffer + position, sizeof(buffer) - position, format, key, value);")
    lines.append("        firstField = false;")
    lines.append("    }")
    lines.append("")
    lines.append("    void addString(const char* key, const char* value) {")
    lines.append("        if (!firstField && position < sizeof(buffer)) {")
    lines.append("            buffer[position++] = ',';")
    lines.append("        }")
    lines.append("        position += snprintf(buffer + position, sizeof(buffer) - position, \"%s:%s\", key, value);")
    lines.append("        firstField = false;")
    lines.append("    }")
    lines.append("")
    lines.append("    void send() {")
    lines.append("        Serial.println(buffer);")
    lines.append("    }")
    lines.append("")
    lines.append("    const char* getString() {")
    lines.append("        return buffer;")
    lines.append("    }")
    lines.append("};")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Field Helpers")
    lines.append("//==================================================================================================")
    lines.append("")
    
    # Generate type-safe helper functions for each telemetry field
    lines.append("/**")
    lines.append(" * @brief Example function to send a complete telemetry packet.")
    lines.append(" * @note Modify this template to match your actual telemetry structure.")
    lines.append(" */")
    lines.append("void sendTelemetry() {")
    lines.append("    TelemetryBuilder telem;")
    lines.append("    ")
    lines.append("    // TODO: Add your telemetry fields here")
    
    # Add a few example fields based on the telemetry schema
    field_count = 0
    for field, field_data in telemetry.items():
        if field_count >= 3:  # Just show a few examples
            break
        field_type = field_data.get('type', 'unknown')
        if field_type == 'int':
            lines.append(f"    // telem.addInt(TELEM_KEY_{field.upper()}, your_{field}_value);")
        elif field_type == 'float':
            precision = field_data.get('precision', 2)
            lines.append(f"    // telem.addFloat(TELEM_KEY_{field.upper()}, your_{field}_value, {precision});")
        elif field_type == 'bool':
            lines.append(f"    // telem.addInt(TELEM_KEY_{field.upper()}, your_{field}_value ? 1 : 0);")
        field_count += 1
    
    lines.append("    ")
    lines.append("    telem.send();")
    lines.append("}")
    
    return '\n'.join(lines)


def generate_responses_header(telemetry: Dict[str, Any], device_name: str) -> str:
    """Generate responses.h content from telemetry.json."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file responses.h")
    lines.append(f" * @brief Defines all response message formats for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from telemetry.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header file defines all messages sent FROM the {device_title} device TO the host.")
    lines.append(" * This includes status messages, telemetry data, and discovery responses.")
    lines.append(" * For command definitions (host → device), see commands.h")
    lines.append(" * To modify response fields, edit telemetry.json and regenerate this file.")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Response Message Prefixes (Device → Host)")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @name Status Message Prefixes")
    lines.append(" * @brief Prefixes used for different types of status messages from the device.")
    lines.append(" * @{")
    lines.append(" */")
    lines.append(f'#define STATUS_PREFIX_INFO                  "{device_upper}_INFO: "          ///< Prefix for informational status messages.')
    lines.append(f'#define STATUS_PREFIX_START                 "{device_upper}_START: "         ///< Prefix for messages indicating the start of an operation.')
    lines.append(f'#define STATUS_PREFIX_DONE                  "{device_upper}_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.')
    lines.append(f'#define STATUS_PREFIX_ERROR                 "{device_upper}_ERROR: "         ///< Prefix for messages indicating an error or fault.')
    lines.append(f'#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.')
    lines.append("/** @} */")
    lines.append("")
    lines.append("/**")
    lines.append(" * @name Telemetry Prefix")
    lines.append(" * @brief Prefix for periodic telemetry data messages.")
    lines.append(" * @{")
    lines.append(" */")
    lines.append(f'#define TELEM_PREFIX                        "{device_upper}_TELEM: "         ///< Prefix for all telemetry messages.')
    lines.append("/** @} */")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Field Keys")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @name Telemetry Field Identifiers")
    lines.append(" * @brief String identifiers for telemetry data fields.")
    lines.append(" * @details These defines specify the exact field names used in telemetry messages.")
    lines.append(f' * Format: "{device_upper}_TELEM: field1:value1,field2:value2,..."')
    lines.append(" * @{")
    lines.append(" */")
    lines.append("")
    
    # Group telemetry fields for better organization
    for field, field_data in telemetry.items():
        gui_var = field_data.get('gui_var', 'N/A')
        default = field_data.get('default', 'N/A')
        field_help = field_data.get('help', 'No description available.')
        lines.append(f'#define TELEM_KEY_{field.upper():<30} "{field:<25}"  ///< {field_help}')
    
    lines.append("")
    lines.append("/** @} */")
    lines.append("")
    
    # Add a comment about usage
    lines.append("//==================================================================================================")
    lines.append("// Usage Examples")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @section Status Message Example")
    lines.append(" * @code")
    lines.append(" * // Send an info message")
    lines.append(' * Serial.print(STATUS_PREFIX_INFO);')
    lines.append(' * Serial.println("System initialized");')
    lines.append(" * ")
    lines.append(" * // Send a completion message")
    lines.append(' * Serial.print(STATUS_PREFIX_DONE);')
    lines.append(' * Serial.println("HEATER_ON");')
    lines.append(" * @endcode")
    lines.append(" * ")
    lines.append(" * @section Telemetry Message Example")
    lines.append(" * @code")
    lines.append(" * char buffer[256];")
    lines.append(' * snprintf(buffer, sizeof(buffer), "%s%s:%d,%s:%.2f",')
    lines.append(" *          TELEM_PREFIX,")
    
    # Add example with first two telemetry fields if available
    telem_keys = list(telemetry.keys())
    if len(telem_keys) >= 1:
        lines.append(f" *          TELEM_KEY_{telem_keys[0].upper()}, value1,")
    if len(telem_keys) >= 2:
        lines.append(f" *          TELEM_KEY_{telem_keys[1].upper()}, value2);")
    else:
        lines.append(" *          TELEM_KEY_FIELD, value);")
    lines.append(' * Serial.println(buffer);')
    lines.append(" * @endcode")
    lines.append(" */")
    
    return '\n'.join(lines)


class CodeGeneratorDialog(tk.Toplevel):
    """Dialog window for generating C++ headers from device JSON files."""
    
    def __init__(self, parent, shared_gui_refs):
        super().__init__(parent)
        
        self.shared_gui_refs = shared_gui_refs
        self.device_manager = shared_gui_refs.get('device_manager')
        
        self.title("C++ Code Generator")
        self.geometry("900x750")
        self.configure(bg=theme.BG_COLOR)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Center the dialog on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        
        # Main container with padding
        main_frame = tk.Frame(self, bg=theme.BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Device C++ Code Generator",
            bg=theme.BG_COLOR,
            fg=theme.FG_COLOR,
            font=theme.FONT_BOLD
        )
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = tk.Label(
            main_frame,
            text="Generate C++ files from device JSON schemas.\nIncludes: commands.h, responses.h, command_parser.h, command_parser.cpp",
            bg=theme.BG_COLOR,
            fg=theme.COMMENT_COLOR,
            font=theme.FONT_NORMAL,
            justify=tk.LEFT
        )
        desc_label.pack(pady=(0, 20))
        
        # Device selection frame
        select_frame = tk.Frame(main_frame, bg=theme.CARD_BG)
        select_frame.pack(fill=tk.X, pady=(0, 20))
        
        select_inner = tk.Frame(select_frame, bg=theme.CARD_BG, padx=15, pady=15)
        select_inner.pack(fill=tk.X)
        
        device_label = tk.Label(
            select_inner,
            text="Select Device:",
            bg=theme.CARD_BG,
            fg=theme.FG_COLOR,
            font=theme.FONT_BOLD
        )
        device_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Get available devices
        devices = self.device_manager.get_device_modules()
        device_names = list(devices.keys())
        
        self.device_var = tk.StringVar()
        if device_names:
            self.device_var.set(device_names[0])
        
        device_dropdown = ttk.Combobox(
            select_inner,
            textvariable=self.device_var,
            values=device_names,
            state='readonly',
            width=30
        )
        device_dropdown.pack(side=tk.LEFT, padx=(0, 20))
        
        # Generate button
        generate_btn = tk.Button(
            select_inner,
            text="Generate Headers",
            command=self.generate_code,
            bg=theme.PRIMARY_ACCENT,
            fg='black',
            font=theme.FONT_BOLD,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        generate_btn.pack(side=tk.LEFT)
        
        # Output console frame
        console_frame = tk.Frame(main_frame, bg=theme.BG_COLOR)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        console_label = tk.Label(
            console_frame,
            text="Generated Code:",
            bg=theme.BG_COLOR,
            fg=theme.FG_COLOR,
            font=theme.FONT_BOLD
        )
        console_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Tabbed output for all generated files
        self.notebook = ttk.Notebook(console_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Commands.h tab
        commands_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.commands_text = scrolledtext.ScrolledText(
            commands_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.commands_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(commands_frame, text="commands.h")
        
        # Responses.h tab
        responses_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.responses_text = scrolledtext.ScrolledText(
            responses_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.responses_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(responses_frame, text="responses.h")
        
        # Command Parser tab
        parser_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.parser_text = scrolledtext.ScrolledText(
            parser_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.parser_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(parser_frame, text="command_parser.h")
        
        # Command Parser CPP tab
        parser_cpp_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.parser_cpp_text = scrolledtext.ScrolledText(
            parser_cpp_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.parser_cpp_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(parser_cpp_frame, text="command_parser.cpp")
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg=theme.BG_COLOR)
        buttons_frame.pack(fill=tk.X)
        
        # Copy button
        copy_btn = tk.Button(
            buttons_frame,
            text="Copy Current Tab",
            command=self.copy_current_tab,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            font=theme.FONT_NORMAL,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Save to file button
        save_btn = tk.Button(
            buttons_frame,
            text="Save to Files",
            command=self.save_to_files,
            bg=theme.SUCCESS_GREEN,
            fg='black',
            font=theme.FONT_BOLD,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_btn = tk.Button(
            buttons_frame,
            text="Close",
            command=self.destroy,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            font=theme.FONT_NORMAL,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Initial message
        initial_msg = "Select a device and click 'Generate Headers' to begin..."
        self.commands_text.insert('1.0', initial_msg)
        self.responses_text.insert('1.0', initial_msg)
        self.parser_text.insert('1.0', initial_msg)
        self.parser_cpp_text.insert('1.0', initial_msg)
    
    def generate_code(self):
        """Generate C++ headers from selected device's JSON files."""
        try:
            device_name = self.device_var.get()
            if not device_name:
                messagebox.showerror("Error", "Please select a device.")
                return
            
            # Get device path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            device_dir = os.path.join(script_dir, 'devices', device_name)
            
            commands_json_path = os.path.join(device_dir, 'commands.json')
            telemetry_json_path = os.path.join(device_dir, 'telemetry.json')
            
            # Check if files exist
            if not os.path.exists(commands_json_path):
                messagebox.showerror("Error", f"commands.json not found for device '{device_name}'")
                return
            
            if not os.path.exists(telemetry_json_path):
                messagebox.showerror("Error", f"telemetry.json not found for device '{device_name}'")
                return
            
            # Load JSON files
            commands = load_json(commands_json_path)
            telemetry = load_json(telemetry_json_path)
            
            # Generate all files
            commands_h = generate_command_header(commands, device_name)
            responses_h = generate_responses_header(telemetry, device_name)
            parser_h = generate_command_parser_header(commands, device_name)
            parser_cpp = generate_command_parser_cpp(commands, device_name)
            
            # Display in text widgets
            self.commands_text.delete('1.0', tk.END)
            self.commands_text.insert('1.0', commands_h)
            
            self.responses_text.delete('1.0', tk.END)
            self.responses_text.insert('1.0', responses_h)
            
            self.parser_text.delete('1.0', tk.END)
            self.parser_text.insert('1.0', parser_h)
            
            self.parser_cpp_text.delete('1.0', tk.END)
            self.parser_cpp_text.insert('1.0', parser_cpp)
            
            # Store generated content for saving
            self.generated_commands = commands_h
            self.generated_responses = responses_h
            self.generated_parser = parser_h
            self.generated_parser_cpp = parser_cpp
            self.current_device = device_name
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate code:\n{str(e)}")
    
    def copy_current_tab(self):
        """Copy the content of the current tab to clipboard."""
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # commands.h
            content = self.commands_text.get('1.0', tk.END)
        elif current_tab == 1:  # responses.h
            content = self.responses_text.get('1.0', tk.END)
        elif current_tab == 2:  # command_parser.h
            content = self.parser_text.get('1.0', tk.END)
        else:  # command_parser.cpp
            content = self.parser_cpp_text.get('1.0', tk.END)
        
        self.clipboard_clear()
        self.clipboard_append(content)
        
        messagebox.showinfo("Success", "Content copied to clipboard!")
    
    def save_to_files(self):
        """Save generated files to the device directory."""
        if not hasattr(self, 'generated_commands') or not hasattr(self, 'generated_responses'):
            messagebox.showerror("Error", "Please generate the files first.")
            return
        
        try:
            # Determine save paths
            script_dir = os.path.dirname(os.path.abspath(__file__))
            device_dir = os.path.join(script_dir, 'devices', self.current_device)
            
            commands_h_path = os.path.join(device_dir, 'commands.h')
            responses_h_path = os.path.join(device_dir, 'responses.h')
            parser_h_path = os.path.join(device_dir, 'command_parser.h')
            parser_cpp_path = os.path.join(device_dir, 'command_parser.cpp')
            
            # Save all files
            with open(commands_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_commands)
            
            with open(responses_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_responses)
            
            with open(parser_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_parser)
            
            with open(parser_cpp_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_parser_cpp)
            
            messagebox.showinfo(
                "Success",
                f"All files saved successfully!\n\n"
                f"commands.h\n"
                f"responses.h\n"
                f"command_parser.h\n"
                f"command_parser.cpp\n\n"
                f"Location: {device_dir}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files:\n{str(e)}")


def show_code_generator(parent, shared_gui_refs):
    """Show the code generator dialog."""
    dialog = CodeGeneratorDialog(parent, shared_gui_refs)
    dialog.wait_window()

