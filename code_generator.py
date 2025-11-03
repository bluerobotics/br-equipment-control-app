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
        'General System Commands': [('DISCOVER_DEVICE', {'help': 'Generic command for any device to respond to.'})],
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
            # Don't pad the string with spaces - just use it as-is
            lines.append(f'#define CMD_STR_{cmd_name.upper():<35} "{cmd_str}" ///< {help_text}')
        
        lines.append("/** @} */")
        lines.append("")
    
    # Generate enum
    # Add response/status prefixes
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
    lines.append("/**")
    lines.append(" * @name Event Prefix")
    lines.append(" * @brief Prefix for event messages.")
    lines.append(" * @{")
    lines.append(" */")
    lines.append(f'#define EVENT_PREFIX                        "{device_upper}_EVENT: "         ///< Prefix for all event messages.')
    lines.append("/** @} */")
    lines.append("")
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
    all_cmds_list = []
    for category, cmds in categories.items():
        if cmds:
            all_cmds_list.extend(cmds)
    
    for category, cmds in categories.items():
        if not cmds:
            continue
            
        lines.append(f"    // {category}")
        for i, (cmd_name, cmd_data) in enumerate(cmds):
            # Check if this is the very last command across all categories
            is_last_overall = (cmd_name, cmd_data) == all_cmds_list[-1]
            comma = "" if is_last_overall else ","
            lines.append(f"    CMD_{cmd_name.upper()}{comma:<36} ///< @see CMD_STR_{cmd_name.upper()}")
        lines.append("")
    
    # Remove trailing empty line and add closing brace
    if lines[-1] == "":
        lines.pop()
    lines.append("} Command;")
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


def generate_commands_cpp(commands: Dict[str, Any], device_name: str) -> str:
    """Generate commands.cpp with integrated command parser."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file commands.cpp")
    lines.append(f" * @brief Command parsing implementation for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from commands.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(" * This file contains the command parser integrated into commands.cpp")
    lines.append(" */")
    lines.append("")
    lines.append('#include "commands.h"')
    lines.append('#include <string.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Command Parser Implementation")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("Command parseCommand(const char* cmdStr) {")
    
    # Always add DISCOVER_DEVICE first
    lines.append(f"    if (strncmp(cmdStr, CMD_STR_DISCOVER_DEVICE, strlen(CMD_STR_DISCOVER_DEVICE)) == 0) return CMD_DISCOVER_DEVICE;")
    
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


def generate_variables_header(telemetry: Dict[str, Any], device_name: str) -> str:
    """Generate variables.h content from telemetry.json with struct and function declarations."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file variables.h")
    lines.append(f" * @brief Telemetry structure and construction interface for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from telemetry.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header defines the complete telemetry data structure for the {device_title}.")
    lines.append(" * All telemetry fields are assembled in one centralized location.")
    lines.append(" * To modify telemetry fields, edit telemetry.json and regenerate this file.")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append('#include <stdint.h>')
    lines.append('#include <stdbool.h>')
    lines.append('#include <stddef.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Field Keys")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @name Telemetry Field Identifiers")
    lines.append(" * @brief String keys used in telemetry messages.")
    lines.append(f' * Format: "{device_upper}_TELEM: field1:value1,field2:value2,..."')
    lines.append(" * @{")
    lines.append(" */")
    
    for field, field_data in telemetry.items():
        field_help = field_data.get('help', 'No description available.')
        lines.append(f'#define TELEM_KEY_{field.upper():<30} "{field:<25}"  ///< {field_help}')
    
    lines.append("/** @} */")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Data Structure")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @struct TelemetryData")
    lines.append(f" * @brief Complete telemetry state for the {device_title} device.")
    lines.append(" * @details This structure contains all telemetry values that are transmitted to the host.")
    lines.append(" */")
    lines.append("typedef struct {")
    
    # Generate struct fields based on telemetry types
    for field, field_data in telemetry.items():
        field_type = field_data.get('type', 'int')
        default = field_data.get('default', 0)
        field_help = field_data.get('help', '')
        
        # Map JSON types to C types
        if field_type == 'int':
            c_type = 'int32_t'
        elif field_type == 'float':
            c_type = 'float'
        elif field_type == 'bool':
            c_type = 'bool'
        elif field_type == 'string':
            c_type = 'const char*'
        else:
            c_type = 'int32_t'
        
        lines.append(f"    {c_type:<12} {field:<30}; ///< {field_help}")
    
    lines.append("} TelemetryData;")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Construction Functions")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Initialize telemetry data structure with default values.")
    lines.append(" * @param data Pointer to TelemetryData structure to initialize")
    lines.append(" */")
    lines.append("void telemetry_init(TelemetryData* data);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Build complete telemetry message string from data structure.")
    lines.append(" * @param data Pointer to TelemetryData structure containing current values")
    lines.append(" * @param buffer Output buffer to write telemetry message")
    lines.append(" * @param buffer_size Size of output buffer")
    lines.append(" * @return Number of characters written (excluding null terminator)")
    lines.append(" * ")
    lines.append(f" * @details Constructs a message in the format: \"{device_upper}_TELEM: field1:value1,field2:value2,...\"")
    lines.append(" */")
    lines.append("int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send telemetry message via comms controller.")
    lines.append(" * @param data Pointer to TelemetryData structure containing current values")
    lines.append(" * ")
    lines.append(" * @details Builds and transmits the complete telemetry message.")
    lines.append(" */")
    lines.append("void telemetry_send(const TelemetryData* data);")
    
    return '\n'.join(lines)

# Alias for backwards compatibility
generate_telemetry_header = generate_variables_header


def generate_variables_cpp(telemetry: Dict[str, Any], device_name: str) -> str:
    """Generate variables.cpp implementation file."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file variables.cpp")
    lines.append(f" * @brief Telemetry construction implementation for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from telemetry.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" */")
    lines.append("")
    lines.append('#include "variables.h"')
    lines.append('#include "commands.h"')
    lines.append('#include <stdio.h>')
    lines.append('#include <string.h>')
    lines.append("")
    lines.append("// Forward declaration - implemented in comms_controller")
    lines.append("extern void sendMessage(const char* msg);")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Initialization")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("void telemetry_init(TelemetryData* data) {")
    lines.append("    if (data == NULL) return;")
    lines.append("    ")
    
    # Initialize all fields with defaults
    for field, field_data in telemetry.items():
        default = field_data.get('default', 0)
        field_type = field_data.get('type', 'int')
        
        if field_type == 'float':
            lines.append(f"    data->{field} = {default}f;")
        elif field_type == 'bool':
            lines.append(f"    data->{field} = {'true' if default else 'false'};")
        elif field_type == 'string':
            lines.append(f"    data->{field} = \"{default}\";")
        else:
            lines.append(f"    data->{field} = {default};")
    
    lines.append("}")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Message Construction")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size) {")
    lines.append("    if (data == NULL || buffer == NULL || buffer_size == 0) return 0;")
    lines.append("    ")
    lines.append("    size_t pos = 0;")
    lines.append("    ")
    lines.append("    // Write prefix")
    lines.append("    pos += snprintf(buffer + pos, buffer_size - pos, \"%s\", TELEM_PREFIX);")
    lines.append("    ")
    
    # Build telemetry fields
    field_items = list(telemetry.items())
    for i, (field, field_data) in enumerate(field_items):
        field_type = field_data.get('type', 'int')
        precision = field_data.get('precision', 2)
        is_last = (i == len(field_items) - 1)
        separator = "" if is_last else ","
        
        lines.append(f"    // {field}")
        lines.append("    if (pos < buffer_size) {")
        
        if field_type == 'float':
            lines.append(f"        pos += snprintf(buffer + pos, buffer_size - pos, \"%s:%.{precision}f{separator}\", TELEM_KEY_{field.upper()}, data->{field});")
        elif field_type == 'bool':
            lines.append(f"        pos += snprintf(buffer + pos, buffer_size - pos, \"%s:%d{separator}\", TELEM_KEY_{field.upper()}, data->{field} ? 1 : 0);")
        elif field_type == 'string':
            lines.append(f"        pos += snprintf(buffer + pos, buffer_size - pos, \"%s:%s{separator}\", TELEM_KEY_{field.upper()}, data->{field});")
        else:  # int/int32_t
            lines.append(f"        pos += snprintf(buffer + pos, buffer_size - pos, \"%s:%ld{separator}\", TELEM_KEY_{field.upper()}, (long)data->{field});")
        
        lines.append("    }")
        lines.append("    ")
    
    lines.append("    return (int)pos;")
    lines.append("}")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Telemetry Transmission")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("// NOTE: You need to provide a sendMessage() implementation based on your comms setup")
    lines.append("// For example:")
    lines.append("// extern CommsController comms;")
    lines.append("// #define sendMessage(msg) comms.enqueueTx(msg, comms.m_guiIp, comms.m_guiPort)")
    lines.append("")
    lines.append("void telemetry_send(const TelemetryData* data) {")
    lines.append("    char buffer[512];")
    lines.append("    int len = telemetry_build_message(data, buffer, sizeof(buffer));")
    lines.append("    ")
    lines.append("    if (len > 0) {")
    lines.append("        sendMessage(buffer);")
    lines.append("    }")
    lines.append("}")
    
    return '\n'.join(lines)

# Alias for backwards compatibility
generate_telemetry_cpp = generate_variables_cpp


def generate_events_header(events: Dict[str, Any], device_name: str) -> str:
    """Generate events.h content from events.json."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file events.h")
    lines.append(f" * @brief Defines all event types that can be sent from the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from events.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" * ")
    lines.append(f" * This header file defines all events sent FROM the {device_title} device TO the host.")
    lines.append(" * Events are asynchronous notifications that can trigger host-side actions.")
    lines.append(" * For command definitions (host → device), see commands.h")
    lines.append(" * For response definitions, see responses.h")
    lines.append(" * To modify events, edit events.json and regenerate this file.")
    lines.append(" */")
    lines.append("#pragma once")
    lines.append("")
    lines.append('#include <stdint.h>')
    lines.append('#include <stdbool.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Event String Definitions")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @name Event String Identifiers")
    lines.append(" * @brief String identifiers used in event messages.")
    lines.append(f' * Format: "{device_upper}_EVENT: event_name [param1] [param2] ..."')
    lines.append(" * @{")
    lines.append(" */")
    
    for event_name, event_data in events.items():
        event_help = event_data.get('description', 'No description available.')
        # Don't pad the string with spaces - just use it as-is
        lines.append(f'#define EVENT_STR_{event_name.upper():<35} "{event_name}"  ///< {event_help}')
    
    lines.append("/** @} */")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Event Enum")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @enum Event")
    lines.append(f" * @brief Enumerates all possible events that can be sent by the {device_title}.")
    lines.append(" * @details This enum provides a type-safe way to handle outgoing events.")
    lines.append(" */")
    lines.append("typedef enum {")
    lines.append("    EVENT_UNKNOWN,                        ///< Represents an unrecognized or invalid event.")
    lines.append("")
    
    # Add enum entries
    event_items = list(events.items())
    for i, (event_name, event_data) in enumerate(event_items):
        is_last = (i == len(event_items) - 1)
        comma = "" if is_last else ","
        lines.append(f"    EVENT_{event_name.upper()}{comma:<35} ///< @see EVENT_STR_{event_name.upper()}")
    
    lines.append("} Event;")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Event Sending Functions")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an event message with no parameters.")
    lines.append(" * @param event The event enum to send")
    lines.append(" */")
    lines.append("void sendEvent(Event event);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an event message with a single integer parameter.")
    lines.append(" * @param event The event enum to send")
    lines.append(" * @param param The integer parameter")
    lines.append(" */")
    lines.append("void sendEventInt(Event event, int32_t param);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an event message with a single string parameter.")
    lines.append(" * @param event The event enum to send")
    lines.append(" * @param param The string parameter")
    lines.append(" */")
    lines.append("void sendEventString(Event event, const char* param);")
    lines.append("")
    lines.append("/**")
    lines.append(" * @brief Send an event message with multiple parameters.")
    lines.append(" * @param event The event enum to send")
    lines.append(" * @param param1 First parameter (integer)")
    lines.append(" * @param param2 Second parameter (integer)")
    lines.append(" */")
    lines.append("void sendEventMulti(Event event, int32_t param1, int32_t param2);")
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Usage Examples")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("/**")
    lines.append(" * @section Event Sending Example")
    lines.append(" * @code")
    lines.append(" * // Send a simple event")
    lines.append(" * sendEvent(EVENT_SCRIPT_RUN);")
    lines.append(" * ")
    lines.append(" * // Send an event with a reason")
    lines.append(" * sendEventString(EVENT_SCRIPT_HOLD, \"Light curtain triggered\");")
    lines.append(" * ")
    lines.append(" * // Send an event with numeric data")
    lines.append(" * sendEventInt(EVENT_SCRIPT_RESET, 1); // zone 1")
    lines.append(" * @endcode")
    lines.append(" */")
    
    return '\n'.join(lines)


def generate_events_cpp(events: Dict[str, Any], device_name: str) -> str:
    """Generate events.cpp implementation file."""
    
    device_upper = device_name.upper()
    device_title = device_name.capitalize()
    
    lines = []
    lines.append("/**")
    lines.append(" * @file events.cpp")
    lines.append(f" * @brief Event sending implementation for the {device_title} controller.")
    lines.append(" * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY")
    lines.append(f" * Generated from events.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" */")
    lines.append("")
    lines.append('#include "events.h"')
    lines.append('#include "commands.h"')
    lines.append('#include <stdio.h>')
    lines.append('#include <string.h>')
    lines.append("")
    lines.append("//==================================================================================================")
    lines.append("// Event Sending Implementation")
    lines.append("//==================================================================================================")
    lines.append("")
    lines.append("// Forward declaration - implemented in comms_controller")
    lines.append("extern void sendMessage(const char* msg);")
    lines.append("")
    lines.append("void sendEvent(Event event) {")
    if events:  # Only create buffer if there are events
        lines.append("    char buffer[256];")
    lines.append("    switch (event) {")
    
    # Generate cases for each event
    for event_name, event_data in events.items():
        lines.append(f"        case EVENT_{event_name.upper()}:")
        lines.append(f"            {{")
        lines.append(f"                char buffer[256];")
        lines.append(f"                snprintf(buffer, sizeof(buffer), \"%s%s\", EVENT_PREFIX, EVENT_STR_{event_name.upper()});")
        lines.append(f"                sendMessage(buffer);")
        lines.append(f"            }}")
        lines.append("            break;")
        lines.append("")
    
    lines.append("        case EVENT_UNKNOWN:")
    lines.append("        default:")
    lines.append("            // Do nothing for unknown events")
    lines.append("            break;")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("void sendEventInt(Event event, int32_t param) {")
    lines.append("    switch (event) {")
    
    # Generate cases for events that might have integer parameters
    has_int_events = False
    for event_name, event_data in events.items():
        params = event_data.get('params', [])
        has_int_param = any(p.get('type') == 'int' for p in params)
        if has_int_param:
            has_int_events = True
            lines.append(f"        case EVENT_{event_name.upper()}:")
            lines.append(f"            {{")
            lines.append(f"                char buffer[256];")
            lines.append(f"                snprintf(buffer, sizeof(buffer), \"%s%s %d\", EVENT_PREFIX, EVENT_STR_{event_name.upper()}, param);")
            lines.append(f"                sendMessage(buffer);")
            lines.append(f"            }}")
            lines.append("            break;")
            lines.append("")
    
    lines.append("        default:")
    lines.append("            // Fall back to simple event for events without int params")
    lines.append("            sendEvent(event);")
    lines.append("            break;")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("void sendEventString(Event event, const char* param) {")
    lines.append("    switch (event) {")
    
    # Generate cases for events that might have string parameters
    has_string_events = False
    for event_name, event_data in events.items():
        params = event_data.get('params', [])
        has_string_param = any(p.get('type') == 'string' for p in params)
        if has_string_param:
            has_string_events = True
            lines.append(f"        case EVENT_{event_name.upper()}:")
            lines.append(f"            {{")
            lines.append(f"                char buffer[256];")
            lines.append(f"                snprintf(buffer, sizeof(buffer), \"%s%s %s\", EVENT_PREFIX, EVENT_STR_{event_name.upper()}, param);")
            lines.append(f"                sendMessage(buffer);")
            lines.append(f"            }}")
            lines.append("            break;")
            lines.append("")
    
    lines.append("        default:")
    lines.append("            // Fall back to simple event for events without string params")
    lines.append("            sendEvent(event);")
    lines.append("            break;")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("void sendEventMulti(Event event, int32_t param1, int32_t param2) {")
    lines.append("    switch (event) {")
    lines.append("        // Add specific cases for events that need multiple parameters")
    lines.append("        default:")
    lines.append("            // Fall back to single int parameter")
    lines.append("            sendEventInt(event, param1);")
    lines.append("            break;")
    lines.append("    }")
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
    lines.append(" * For telemetry structure, see telemetry.h")
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
    lines.append(" * // Use the telemetry.h interface for sending telemetry")
    lines.append(" * #include \"telemetry.h\"")
    lines.append(" * ")
    lines.append(" * TelemetryData telem;")
    lines.append(" * telemetry_init(&telem);")
    lines.append(" * // ... update telem fields ...")
    lines.append(" * telemetry_send(&telem);")
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
            text="Generate C++ files from device JSON schemas.\nFiles saved to: devices/{device}/generated/\nIncludes: commands.h, responses.h, commands.cpp, variables.h/cpp, events.h/cpp",
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
        
        # Commands.cpp tab
        commands_cpp_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.commands_cpp_text = scrolledtext.ScrolledText(
            commands_cpp_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.commands_cpp_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(commands_cpp_frame, text="commands.cpp")
        
        # Variables.h tab
        variables_h_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.variables_h_text = scrolledtext.ScrolledText(
            variables_h_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.variables_h_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(variables_h_frame, text="variables.h")
        
        # Variables.cpp tab
        variables_cpp_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.variables_cpp_text = scrolledtext.ScrolledText(
            variables_cpp_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.variables_cpp_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(variables_cpp_frame, text="variables.cpp")
        
        # Events.h tab
        events_h_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.events_h_text = scrolledtext.ScrolledText(
            events_h_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.events_h_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(events_h_frame, text="events.h")
        
        # Events.cpp tab
        events_cpp_frame = tk.Frame(self.notebook, bg=theme.WIDGET_BG)
        self.events_cpp_text = scrolledtext.ScrolledText(
            events_cpp_frame,
            bg=theme.WIDGET_BG,
            fg=theme.FG_COLOR,
            insertbackground=theme.FG_COLOR,
            font=('Courier', 9),
            wrap=tk.NONE
        )
        self.events_cpp_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(events_cpp_frame, text="events.cpp")
        
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
        self.commands_cpp_text.insert('1.0', initial_msg)
        self.variables_h_text.insert('1.0', initial_msg)
        self.variables_cpp_text.insert('1.0', initial_msg)
        self.events_h_text.insert('1.0', initial_msg)
        self.events_cpp_text.insert('1.0', initial_msg)
    
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
            events_json_path = os.path.join(device_dir, 'events.json')
            
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
            
            # Load events.json if it exists (optional)
            events = {}
            if os.path.exists(events_json_path):
                events = load_json(events_json_path)
            
            # Generate all files
            commands_h = generate_command_header(commands, device_name)
            responses_h = generate_responses_header(telemetry, device_name)
            commands_cpp = generate_commands_cpp(commands, device_name)
            variables_h = generate_variables_header(telemetry, device_name)
            variables_cpp = generate_variables_cpp(telemetry, device_name)
            events_h = generate_events_header(events, device_name)
            events_cpp = generate_events_cpp(events, device_name)
            
            # Display in text widgets
            self.commands_text.delete('1.0', tk.END)
            self.commands_text.insert('1.0', commands_h)
            
            self.responses_text.delete('1.0', tk.END)
            self.responses_text.insert('1.0', responses_h)
            
            self.commands_cpp_text.delete('1.0', tk.END)
            self.commands_cpp_text.insert('1.0', commands_cpp)
            
            self.variables_h_text.delete('1.0', tk.END)
            self.variables_h_text.insert('1.0', variables_h)
            
            self.variables_cpp_text.delete('1.0', tk.END)
            self.variables_cpp_text.insert('1.0', variables_cpp)
            
            self.events_h_text.delete('1.0', tk.END)
            self.events_h_text.insert('1.0', events_h)
            
            self.events_cpp_text.delete('1.0', tk.END)
            self.events_cpp_text.insert('1.0', events_cpp)
            
            # Store generated content for saving
            self.generated_commands = commands_h
            self.generated_responses = responses_h
            self.generated_commands_cpp = commands_cpp
            self.generated_variables_h = variables_h
            self.generated_variables_cpp = variables_cpp
            self.generated_events_h = events_h
            self.generated_events_cpp = events_cpp
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
        elif current_tab == 2:  # commands.cpp
            content = self.commands_cpp_text.get('1.0', tk.END)
        elif current_tab == 3:  # variables.h
            content = self.variables_h_text.get('1.0', tk.END)
        elif current_tab == 4:  # variables.cpp
            content = self.variables_cpp_text.get('1.0', tk.END)
        elif current_tab == 5:  # events.h
            content = self.events_h_text.get('1.0', tk.END)
        else:  # events.cpp
            content = self.events_cpp_text.get('1.0', tk.END)
        
        self.clipboard_clear()
        self.clipboard_append(content)
        
        messagebox.showinfo("Success", "Content copied to clipboard!")
    
    def save_to_files(self):
        """Save generated files to the device directory."""
        if not hasattr(self, 'generated_commands') or not hasattr(self, 'generated_responses'):
            messagebox.showerror("Error", "Please generate the files first.")
            return
        
        try:
            # Determine save paths (save to generated/ subfolder)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            device_dir = os.path.join(script_dir, 'devices', self.current_device)
            gen_dir = os.path.join(device_dir, 'generated')
            
            # Create generated/ folder if it doesn't exist
            os.makedirs(gen_dir, exist_ok=True)
            
            commands_h_path = os.path.join(gen_dir, 'commands.h')
            responses_h_path = os.path.join(gen_dir, 'responses.h')
            commands_cpp_path = os.path.join(gen_dir, 'commands.cpp')
            variables_h_path = os.path.join(gen_dir, 'variables.h')
            variables_cpp_path = os.path.join(gen_dir, 'variables.cpp')
            events_h_path = os.path.join(gen_dir, 'events.h')
            events_cpp_path = os.path.join(gen_dir, 'events.cpp')
            
            # Save all files
            with open(commands_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_commands)
            
            with open(responses_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_responses)
            
            with open(commands_cpp_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_commands_cpp)
            
            with open(variables_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_variables_h)
            
            with open(variables_cpp_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_variables_cpp)
            
            with open(events_h_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_events_h)
            
            with open(events_cpp_path, 'w', encoding='utf-8') as f:
                f.write(self.generated_events_cpp)
            
            messagebox.showinfo(
                "Success",
                f"All files saved successfully to generated/ folder!\n\n"
                f"generated/commands.h\n"
                f"generated/responses.h\n"
                f"generated/commands.cpp\n"
                f"generated/variables.h\n"
                f"generated/variables.cpp\n"
                f"generated/events.h\n"
                f"generated/events.cpp\n\n"
                f"Location: {gen_dir}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files:\n{str(e)}")


def show_code_generator(parent, shared_gui_refs):
    """Show the code generator dialog."""
    dialog = CodeGeneratorDialog(parent, shared_gui_refs)
    dialog.wait_window()

