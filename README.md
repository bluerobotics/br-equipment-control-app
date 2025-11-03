<div align="center">
    <img src="assets/icon.png" alt="Application Icon" width="150">
</div>

# BR Equipment Control App

[View Changelog](CHANGELOG.md)

---

## 1. Overview

This application is a desktop program for controlling and scripting multiple pieces of hardware, referred to as "devices". Its main purpose is to provide a single, centralized user interface for running automated scripts that can command several different devices in sequence, with built-in data logging capabilities.

<p align="center">
  <img src="assets/app.png" alt="App Screenshot" width="800">
</p>

The system is designed to be modular. You can add new devices to the application without changing the main codebase. This is done by creating a new folder for the device in the `/devices` directory and adding a set of specific configuration files. The application can even detect and load new device modules while it's running.

---

## 2. Features

- Text-based scripting with syntax highlighting and validation
- Step-through execution mode for debugging
- CSV data logging with millisecond timestamps
- Queue variables for logging via UI or script commands
- Built-in device simulator for testing without hardware
- Runtime device module loading without application restart
- C++ code generation for embedded command parsers
- Auto-recovery of unsaved scripts

---

## 3. System Architecture

The application separates core logic from device-specific implementations.

### 3.1. Threading Model

1.  **Main Thread**: Tkinter UI event loop. Background threads queue UI updates for processing on this thread.

2.  **Communication Threads**:
    - `recv_loop`: Receives and routes UDP packets
    - `discovery_loop`: Broadcasts device discovery messages
    - `monitor_connections`: Marks devices as disconnected on timeout

3.  **Script Thread**: Executes scripts in the background

4.  **Simulator Threads**: One per simulated device

### 3.2. Core Modules

#### `main.py`
Application entry point. Creates the main window, initializes `DeviceManager` and `DataLogger`, scans `/devices` directory, and starts communication threads.

#### `device_manager.py`
Loads device modules from `/devices` directory. Maintains registry of commands, telemetry schemas, and connection status. Manages telemetry callbacks for data logger.

#### `data_logger.py`
Handles CSV logging. Tracks queued variables, manages log files, and writes telemetry data with timestamps.

#### `comms.py`
UDP network communication. Sends/receives device messages, performs device discovery, monitors connection timeouts.

#### `script_processor.py`
Executes scripts in a background thread. Parses commands, validates device connectivity, handles built-in commands (`wait`, `cycle`, logging commands).

#### `scripting_gui.py`
Script editor UI with syntax highlighting, line numbers, find/replace, and execution controls.

#### `command_reference.py`
Interactive panel showing available commands and variables with context menus for logging operations.

#### `script_validator.py`
Pre-execution validation of script syntax and device availability.

---

## 4. Data Logging

### 4.1. Using the UI

1. Right-click variables in the Command Reference and select "Queue for Logging"
2. Right-click the device and select "Start Logging..."
3. Stop logging via device context menu or global abort

Variables show `[queued]` (blue) and `[logging]` (yellow) indicators.

### 4.2. Using Scripts

```
# Queue variables for logging
queue_for_logging
    fillhead.temp_c
    fillhead.heater_setpoint
    fillhead.vacuum_psig

queue_for_logging
    gantry.x_pos
    gantry.y_pos
    gantry.z_pos

# Start logging queued variables from both devices to one file
start_logging "<date>-<time> test_data.csv" fillhead gantry

# Run your test
wait 60

# Stop all logging
stop_logging
```

### 4.3. CSV Format

Files are saved to `logs/` with columns: `date`, `time_ms`, `elapsed_s`, followed by logged variables.

Each device writes values to its columns when it sends telemetry. Other columns remain blank for that row.

Use `<date>` and `<time>` in filenames for automatic timestamps:
```
start_logging "<date>-<time> data.csv" fillhead
```

Collisions are resolved by appending `_1`, `_2`, etc.

---

## 5. Scripting

### 5.1. Built-In Commands

| Command | Example |
|---------|---------|
| `wait` | `wait 5` |
| `wait_for` | `wait_for gantry.x_pos > 100` |
| `cycle` | `cycle 10` |
| `queue_for_logging` | `queue_for_logging fillhead.temp_c` |
| `unqueue_for_logging` | `unqueue_for_logging fillhead.temp_c` |
| `start_logging` | `start_logging "data.csv" fillhead gantry` |
| `stop_logging` | `stop_logging` |

### 5.2. Syntax

```
# Comments start with #

# Device commands
gantry.home_x
gantry.move_x 100 1000
fillhead.set_temp 25.5

# Loops with indented blocks
cycle 5
    gantry.move_x 10
    wait 1

# Logging with indented blocks
queue_for_logging
    fillhead.temp_c
    fillhead.heater_setpoint

start_logging "test.csv" fillhead
wait 10
stop_logging
```

Scripts are validated before execution. Devices must be connected to run.

---

## 6. Device Structure

### 6.1. Overview

Each device lives in its own folder under `/devices`. The folder name becomes the device identifier (e.g., `gantry`, `fillhead`). A device consists of:

- **Commands**: Actions the device can perform (e.g., `move_x`, `home`, `set_temp`)
- **Variables**: Telemetry data the device reports (e.g., `x_pos`, `temp_c`, `pressure`)
- **Events**: Asynchronous notifications the device emits (e.g., `homed`, `error`)
- **GUI**: Custom status panel for displaying device state

### 6.2. Working with Commands, Variables, and Events

**The standard workflow is through the app itself, not by editing JSON files directly.**

The Command Reference panel (right side of the app) displays all commands, variables, and events for each device in a hierarchical tree:

```
▼ gantry [connected]
  ▼ commands (15)
    home_x
    move_x (distance, speed)
    enable_x
    ...
  ▼ variables (15)
    x_pos (float) mm [queued]
    x_homed (int) [enum]
    main_state (string) [enum]
    ...
  ▼ events (2)
    homed
    error
```

**To use commands in scripts:**
- Click any command to copy it to clipboard
- Paste into script editor
- The app shows parameter hints and validates syntax

**To log variables:**
- Right-click a variable → "Queue for Logging"
- Right-click the device → "Start Logging (N queued vars)..."
- The app handles CSV creation and column headers automatically

**To view the JSON structure:**
- Look at existing devices in `/devices` as examples
- The JSON files define what appears in the Command Reference

### 6.3. Device Files

Each device folder must contain:

#### `commands.json`
Defines scriptable commands. Each command has:

- `device`: Device identifier (must match folder name)
- `target`: `"device"` (sent to hardware) or `"host"` (executed by app)
- `params`: Array of parameter definitions
  - `parameter`: Parameter name
  - `type`: `"float"`, `"int"`, `"string"`, etc.
  - `unit`: Optional unit text (e.g., `"mm"`, `"deg"`)
- `returns`: Array of possible return values (e.g., `["done", "error"]`)
- `description`: What the command does

Example:
```json
{
  "move_x": {
    "device": "gantry",
    "target": "device",
    "params": [
      { "parameter": "distance", "type": "float", "unit": "mm" },
      { "parameter": "speed", "type": "int", "unit": "mm/s" }
    ],
    "returns": ["done", "error"],
    "description": "Moves X-axis by relative distance"
  }
}
```

In scripts, this appears as: `gantry.move_x 100 1000`

#### `telemetry.json`
Defines telemetry variables. Each variable has:

- `type`: Data type (`"float"`, `"int"`, `"string"`)
- `gui_var`: (Optional) Name of the tkinter variable for GUI binding
- `default`: Initial value when disconnected
- `unit`: (Optional) Unit text displayed in Command Reference
- `precision`: (Optional) Decimal places for floats
- `map`: (Optional) Dictionary mapping raw values to display strings

Example:
```json
{
  "x_pos": {
    "type": "float",
    "default": 0.0,
    "unit": "mm",
    "precision": 2
  },
  "x_homed": {
    "type": "int",
    "default": 0,
    "map": {
      "0": "Not Homed",
      "1": "Homed"
    }
  },
  "main_state": {
    "type": "string",
    "default": "standby",
    "map": {
      "standby": "Standby",
      "busy": "Busy",
      "error": "Error"
    }
  }
}
```

Variables with `map` are shown as `[enum]` in the Command Reference.

#### `events.json` (Optional)
Defines events that can be referenced in scripts with `wait_for`:

```json
{
  "homed": {
    "device": "gantry",
    "description": "Emitted when homing completes"
  }
}
```

Usage in scripts: `wait_for gantry.homed`

#### `gui.py`
Python module that creates the device's status panel. Must export:

- `create_gui_components(parent, shared_gui_refs)`: Returns a tkinter Frame
- `get_gui_variable_names()`: Returns list of required StringVar/DoubleVar names

The function receives `shared_gui_refs`, a dictionary containing all tkinter variables defined in `telemetry.json`. Access them by the `gui_var` name.

Minimal example:
```python
import tkinter as tk
from tkinter import ttk

def get_gui_variable_names():
    return ['gantry_x_pos_var', 'gantry_state_var']

def create_gui_components(parent, shared_gui_refs):
    frame = ttk.Frame(parent)
    
    x_pos_var = shared_gui_refs.get('gantry_x_pos_var')
    state_var = shared_gui_refs.get('gantry_state_var')
    
    ttk.Label(frame, text="X Position:").grid(row=0, column=0)
    ttk.Label(frame, textvariable=x_pos_var).grid(row=0, column=1)
    
    ttk.Label(frame, text="State:").grid(row=1, column=0)
    ttk.Label(frame, textvariable=state_var).grid(row=1, column=1)
    
    return frame
```

The variables automatically update when telemetry arrives. The `device_manager` parses incoming telemetry and sets the corresponding StringVar values based on the `telemetry.json` definitions.

#### `script_handlers.py` (Optional)
For commands with `"target": "host"`, define custom Python handlers:

```python
def my_handler(script_runner, args, line_num):
    """
    Args:
        script_runner: ScriptRunner instance with access to gui_refs
        args: List of command arguments (already parsed)
        line_num: Current line number for status messages
    
    Returns:
        True to continue script execution, False to halt
    """
    # Access shared GUI refs
    device_manager = script_runner.gui_refs.get('device_manager')
    
    # Execute custom logic
    result = do_something(args)
    
    # Report status
    script_runner.status_cb(f"Command result: {result}", line_num)
    return True

HANDLERS = {
    "my_command": my_handler
}
```

Reference the handler in `commands.json`:
```json
{
  "my_command": {
    "device": "my_device",
    "target": "host",
    "handler": "my_handler",
    "params": [...],
    "description": "..."
  }
}
```

### 6.4. How Data Flows

When a device sends telemetry (UDP packet format: `GANTRY_TELEM:x_pos=123.45;x_homed=1`):

1. `comms.py` receives the packet and extracts device name (`gantry`)
2. `device_manager.py` parses values using `telemetry.json` schema
3. For each key in the packet:
   - Looks up the variable definition in `telemetry.json`
   - Applies formatting (`precision`, `map`, `suffix`, `multiplier`)
   - Updates the corresponding tkinter variable (`gui_var`)
4. GUI labels bound to those variables update automatically
5. If logging is active, `data_logger.py` writes the raw values to CSV

This separation means:
- Your `gui.py` doesn't need to parse telemetry
- The Command Reference doesn't need device-specific code
- Adding a new variable only requires updating `telemetry.json`

### 6.5. C++ Code Generation

The app includes a code generator (**File → Generate C++ Code**) that creates embedded firmware code from your JSON definitions. This ensures the Python app and C++ firmware stay synchronized.

From `commands.json`, it generates:
- `commands.h`: Command parser with parameter extraction
- Command handler stubs with correct function signatures

From `telemetry.json`, it generates:
- `telemetry.h`: Telemetry formatting and transmission functions
- State variable declarations

This eliminates manual synchronization between the app and firmware.

---

## 7. Network Protocol

Communication uses UDP on port 6272. Messages are ASCII strings.

**Device Discovery:**
```
App → Broadcast: DISCOVER_DEVICE
Device → App: DISCOVERY_RESPONSE: DEVICE_ID=gantry PORT=8889
```

**Commands:**
```
App → Device: MOVE_X:100:1000
Device → App: GANTRY_STATUS:MOVE_X:100:1000:DONE
```

**Telemetry (sent at 10Hz):**
```
Device → App: GANTRY_TELEM:x_pos=123.45;y_pos=67.89;x_homed=1;main_state=standby
```

**Events:**
```
Device → App: GANTRY_EVENT:HOMED
```

All messages are prefixed with the device name in uppercase. The app extracts the device identifier and routes the message accordingly.

---

## 8. Setup

**Requirements:** Python 3.10+, no external dependencies

**Run:**
    ```bash
    python main.py
    ```

The app creates a `logs/` directory on first run.

---

## 9. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New Script |
| `Ctrl+O` | Open Script |
| `Ctrl+S` | Save Script |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+X` | Cut |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+F` | Find |
| `Ctrl+H` | Replace |
| `Ctrl+Shift+V` | Validate Script |

---

## 10. Troubleshooting

**Devices not discovered:** Check network, verify UDP port 6272 is accessible, restart simulators

**Script errors:** Use File → Validate Script. Check devices exist in `/devices` and are connected.

**Logging not working:** Queue variables first, ensure devices are connected

**Timeouts:** Devices timeout after 3 seconds without telemetry

---

## 11. License & Contact

Developed by Blue Robotics for internal equipment control.

Repository: https://github.com/bluerobotics/br-equipment-control-app
