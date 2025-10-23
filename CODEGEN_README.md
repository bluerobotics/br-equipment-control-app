# C++ Code Generator - Usage Guide

## Overview

The equipment control app includes a C++ code generator that automatically creates files for embedded device firmware based on JSON schema files. The generator follows proper C++ practices with separate header and implementation files.

## Generated Files

### 1. **`commands.h`** - Command Definitions
Commands sent TO the device (Host → Device)
- Command string definitions (`CMD_STR_*`)
- Command enum for type-safe parsing

### 2. **`responses.h`** - Response Message Definitions
Messages sent FROM the device (Device → Host)
- Status message prefixes (INFO, START, DONE, ERROR, DISCOVERY)
- Telemetry prefix
- Telemetry field identifiers

### 3. **`command_parser.h`** + **`command_parser.cpp`** - Command Parsing & Dispatching
Proper header/implementation separation following C++ best practices
- **`.h`** - Function declarations
- **`.cpp`** - Full implementations including:
  - `parseCommand()` - Parse command strings into enum values
  - `getCommandParams()` - Extract parameter strings from commands
  - `dispatchCommand()` - Template dispatcher with TODO placeholders for your handlers

This organization provides clean, ready-to-use command parsing with minimal boilerplate code.

## How to Generate Headers

### Using the GUI

1. Run the equipment control app
2. Click **Devices → Generate C++ Code...**
3. Select a device from the dropdown
4. Click **Generate Headers**
5. Review the generated code in the tabs
6. Click **Save to Files** to write to the device folder

### Using the Command Line

Run the batch generator to update all devices at once:

```bash
python generate_all_headers.py
```

This will generate headers for all devices in the `devices/` folder.

## Source Files

Each device folder contains:

- **`commands.json`** - Command definitions with parameters and help text
- **`telemetry.json`** - Telemetry field definitions with types, units, and defaults

**Generated files (do not edit manually):**
- **`commands.h`** - Auto-generated from commands.json
- **`responses.h`** - Auto-generated from telemetry.json

## Workflow

1. Edit `commands.json` or `telemetry.json` to add/modify commands or telemetry fields
2. Run the code generator (GUI or command line)
3. Copy the generated `.h` files to your embedded project
4. Include them in your firmware source code

## Example Usage in C++

### 1. Command Parsing (Auto-Generated!)

```cpp
#include "command_parser.h"

void loop() {
    if (Serial.available()) {
        String cmdString = Serial.readStringUntil('\n');
        const char* cmdStr = cmdString.c_str();
        
        // Parse the command (auto-generated function!)
        Command cmd = parseCommand(cmdStr);
        
        // Extract parameters if any
        const char* params = getCommandParams(cmdStr, cmd);
        
        // Dispatch to handler (auto-generated template!)
        if (!dispatchCommand(cmd, params)) {
            sendErrorMessage("Unknown command");
        }
    }
}
```

### 2. Command Dispatching (Fill in TODOs)

```cpp
#include "command_parser.h"

// The dispatchCommand() function is auto-generated with TODOs
// Just implement your handlers:

void handle_heater_on(const char* params) {
    float setpoint = params ? atof(params) : 70.0;
    // Your heater control code here
    sendDoneMessage("heater_on");
}

// Update the generated dispatcher to call your handlers
```

### 3. Using Response Prefixes

```cpp
#include "responses.h"

void publishTelemetry() {
    // Build your telemetry string using the generated field keys
    char buffer[256];
    snprintf(buffer, sizeof(buffer), "%s%s:%d,%s:%.1f,%s:%.1f",
             TELEM_PREFIX,
             TELEM_KEY_HEATER_STATE, heaterState,
             TELEM_KEY_TEMP_C, currentTemp,
             TELEM_KEY_HEATER_SETPOINT, setpoint);
    Serial.println(buffer);
}

void sendStatus(const char* message) {
    Serial.print(STATUS_PREFIX_DONE);
    Serial.println(message);
}
```

## Device-Specific Prefixes

Each device has unique message prefixes:

- **Fillhead**: `FILLHEAD_INFO:`, `FILLHEAD_DONE:`, etc.
- **Gantry**: `GANTRY_INFO:`, `GANTRY_DONE:`, etc.
- **Pressboi**: `PRESSBOI_INFO:`, `PRESSBOI_DONE:`, etc.
- **Pressurizer**: `PRESSURIZER_INFO:`, `PRESSURIZER_DONE:`, etc.

This allows multiple devices to communicate on the same bus without conflicts.

## Key Benefits

✅ **No more boilerplate** - Parsing and formatting functions are generated automatically  
✅ **Type-safe** - Uses enums and const definitions to prevent typos  
✅ **Consistent** - All devices follow the same communication pattern  
✅ **Easy to use** - Just include the headers and fill in your handler functions  
✅ **Maintainable** - Update JSON schemas and regenerate when changes are needed  

## Files

### Generator Scripts
- **`code_generator.py`** - Main generator module with GUI
- **`generate_all_headers.py`** - Batch script to generate all devices

### Input Files (Edit These)
- **`devices/[device_name]/commands.json`** - Command definitions
- **`devices/[device_name]/telemetry.json`** - Telemetry definitions

### Generated Files (Auto-Generated - Don't Edit)
- **`devices/[device_name]/commands.h`** - Command definitions
- **`devices/[device_name]/responses.h`** - Response message definitions
- **`devices/[device_name]/command_parser.h`** - Function declarations
- **`devices/[device_name]/command_parser.cpp`** - Implementation file

