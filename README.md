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

## 6. Adding Devices

Create a folder in `/devices` with the device name. Add these files:

### 6.1. `commands.json`
Command definitions.

**Example:**
```json
{
  "MOVE_X": {
    "device": "gantry",
    "target": "device",
    "params": [
      { "parameter": "distance", "type": "float", "unit": "mm" },
      { "parameter": "speed", "type": "int", "unit": "mm/s" }
    ],
    "returns": ["done", "error"],
    "description": "Moves the X-axis by a relative distance at specified speed."
  },
  "HOME_X": {
    "device": "gantry",
    "target": "device",
    "params": [],
    "returns": ["done", "error"],
    "description": "Homes the X-axis to the limit switch."
  }
}
```

### 6.2. `telemetry.json`
Telemetry variable definitions.

**Example:**
```json
{
  "x_pos": {
    "type": "float",
    "gui_var": "gantry_x_pos_var", 
    "default": 0.0,
    "format": {
      "precision": 2,
      "suffix": " mm"
    }
  },
  "x_homed": {
    "type": "int",
    "gui_var": "gantry_x_homed_var", 
    "default": 0,
    "format": {
      "map": { "0": "Not Homed", "1": "Homed" }
    }
  },
  "main_state": {
    "type": "string",
    "gui_var": "gantry_state_var",
    "default": "standby",
    "format": {
      "map": {
        "standby": "Standby",
        "busy": "Busy",
        "error": "Error"
      }
    }
  }
}
```

Format options: `precision`, `suffix`, `map`, `multiplier`.

### 6.3. `events.json` (Optional)
Event definitions (emitted by device asynchronously).

### 6.4. `gui.py`
UI panel creation.

```python
import tkinter as tk
from tkinter import ttk

def create_gui_components(parent, shared_gui_refs):
    frame = ttk.Frame(parent)
    
    x_pos_var = shared_gui_refs.get('gantry_x_pos_var')
    ttk.Label(frame, text="X Position:").grid(row=0, column=0)
    ttk.Label(frame, textvariable=x_pos_var).grid(row=0, column=1)
    
    return frame
```

### 6.5. `script_handlers.py` (Optional)
Host-side command handlers.

```python
def my_handler(script_runner, args, line_num):
    # Execute logic here
    script_runner.status_cb(f"Result: {args}", line_num)
    return True  # True to continue, False to halt

HANDLERS = {
    "my_command": my_handler
}
```

In `commands.json`, set `"target": "host"` and `"handler": "my_handler"`.

---

## 7. Setup

**Requirements:** Python 3.10+, no external dependencies

**Run:**
    ```bash
    python main.py
    ```

The app creates a `logs/` directory on first run.

---

## 8. Keyboard Shortcuts

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

## 9. Troubleshooting

**Devices not discovered:** Check network, verify UDP port 6272 is accessible, restart simulators

**Script errors:** Use File → Validate Script. Check devices exist in `/devices` and are connected.

**Logging not working:** Queue variables first, ensure devices are connected

**Timeouts:** Devices timeout after 3 seconds without telemetry

---

## 10. License & Contact

Developed by Blue Robotics for internal equipment control.

Repository: https://github.com/bluerobotics/br-equipment-control-app
