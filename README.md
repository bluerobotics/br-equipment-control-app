<div align="center">

<img src="assets/icon.png" alt="Application Icon" width="150">

# BR Equipment Control App

**Multi-Device Manufacturing Equipment Control & Automation**

[![release](https://img.shields.io/github/v/release/bluerobotics/br-equipment-control-app?style=flat-square)](https://github.com/bluerobotics/br-equipment-control-app/releases/latest)
[![build](https://img.shields.io/github/actions/workflow/status/bluerobotics/br-equipment-control-app/build.yml?style=flat-square)](https://github.com/bluerobotics/br-equipment-control-app/actions)
[![downloads](https://img.shields.io/github/downloads/bluerobotics/br-equipment-control-app/total?style=flat-square&color=red)](https://github.com/bluerobotics/br-equipment-control-app/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![scripts](https://img.shields.io/badge/scripts-breq--scripts-darkgreen.svg?style=flat-square)](https://github.com/bluerobotics/breq-scripts)

[View Changelog](CHANGELOG.md) • [Download Latest Release](https://github.com/bluerobotics/br-equipment-control-app/releases/latest)

</div>

---

<div align="center">

## Officially Supported Devices

| Device | Description | Repository |
|:------:|:-----------:|:----------:|
| **Pressboi** | Dual-motor servo press | [bluerobotics/pressboi](https://github.com/bluerobotics/pressboi) |
| **Fillhead** | Automated encapsulation system | [bluerobotics/fillhead](https://github.com/bluerobotics/fillhead) |
| **Gantry** | Three-axis gantry | [bluerobotics/gantry](https://github.com/bluerobotics/gantry) |

</div>

---

## 1. Overview

Open-source desktop application for controlling and automating manufacturing equipment built on ClearCore microcontrollers. Designed for production environments where multiple devices need to work together in coordinated sequences.

<p align="center">
  <img src="assets/app.png" alt="App Screenshot" width="800">
</p>

The application provides a unified interface for scripting, monitoring, and debugging custom manufacturing equipment. Communicate over USB serial or Ethernet, write automation scripts in a simple text format, log telemetry data for analysis, and flash firmware updates without leaving the app. Device definitions are modular - add new equipment types by creating JSON schemas and custom GUI panels.

**Key Capabilities:**
- **Multi-Device Scripting**: Coordinate actions across multiple devices with simple text-based scripts (`.breq` files)
- **Dual Communication**: USB and Ethernet connectivity with automatic discovery and failover
- **Data Logging**: Export telemetry to CSV with millisecond timestamps for analysis in Excel or other tools
- **Firmware Management**: Flash firmware updates over USB or network with version tracking
- **Error Diagnostics**: View device error logs and 24-hour heartbeat history for debugging connectivity issues
- **Simulation Mode**: Test scripts without hardware using built-in device simulators
- **Modular Architecture**: Add new device types by defining JSON schemas - the app auto-generates C++ parsers for firmware

---

## 2. Getting Started

### 2.1. Download the Application

Download the latest release for your platform from the [releases page](https://github.com/bluerobotics/br-equipment-control-app/releases/latest):

- **Windows**: `br-equipment-control-app-windows.zip`
- **macOS**: `br-equipment-control-app-macos.zip`
- **Linux**: `br-equipment-control-app-linux.tar.gz`

Extract the archive and run the executable.

### 2.2. Add a Device

The app needs device definitions to communicate with your equipment.

**Officially Supported Devices:**
- [Pressboi](https://github.com/bluerobotics/pressboi) - Dual-motor servo press
- [Fillhead](https://github.com/bluerobotics/fillhead) - Automated encapsulation system
- [Gantry](https://github.com/bluerobotics/gantry) - Three-axis gantry

#### Option A: Use GitHub Desktop (Recommended)

1. Download and install [GitHub Desktop](https://desktop.github.com/)
2. Open GitHub Desktop and go to **File → Clone Repository**
3. Select the **URL** tab and paste the device repository URL (e.g., `https://github.com/bluerobotics/pressboi`)
4. Choose where to save it and click **Clone**

This is the easiest way to get devices and receive firmware updates via git pull.

#### Option B: Download as ZIP

Download the device repository as a ZIP from GitHub and extract it to a folder on your computer.

### 2.3. Open the Device in the App

On first launch, the app will prompt you to add a device folder.

Otherwise, click the **Add Device** button at the bottom of the **Device Manager** (right side) and navigate to your device repository folder (e.g., `pressboi/`). The device will load and appear in the Device Manager.

### 2.4. Connect to Your Device

The app automatically discovers devices on your network. If your device is connected:
- **Via USB**: Plug in the USB cable - the app will detect it automatically
- **Via Ethernet**: The device will appear in the Device Manager once discovered on UDP port 6272

Right-click the device in the Device Manager to select your connection method (USB or Network).

### 2.5. Start Automating

You're ready to go! Write scripts in the editor, execute commands, log data, and flash firmware. See the sections below for detailed usage.

---

## 3. System Architecture

Multi-threaded Python application with modular device support.

### 3.1. Core Modules

- **Device Manager**: Loads device definitions from `/devices` directory, maintains connection state, routes telemetry
- **Comms**: UDP network and USB serial communication with automatic discovery and reconnection
- **Script Processor**: Executes `.breq` scripts in background thread with validation and error handling
- **Data Logger**: CSV export with variable queueing and timestamp tracking
- **Command Reference**: Interactive tree view of all commands/variables with right-click operations
- **Firmware Manager**: OTA firmware updates with version tracking and GitHub integration

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

## 5. Error Diagnostics

View device error logs and connection history via **Devices → Dump Error Log...**

Devices maintain two circular buffers:
- **Error Log**: 100 entries of system events, warnings, and errors
- **Heartbeat Log**: 2880 entries (24 hours) of USB/network status sampled every 30 seconds

Use this to diagnose intermittent connectivity issues, watchdog timeouts, or firmware errors.

---

## 6. Scripting

Scripts use the `.breq` (BR Equipment) file extension and are plain text files.

### 6.1. Built-In Commands

| Command | Example |
|---------|---------|
| `wait` | `wait 5` |
| `wait_for` | `wait_for gantry.x_pos > 100` |
| `cycle` | `cycle 10` |
| `if` | `if device.temp_c > 100 throw device.overheat` |
| `throw` | `throw device.error_warning` |
| `queue_for_logging` | `queue_for_logging fillhead.temp_c` |
| `unqueue_for_logging` | `unqueue_for_logging fillhead.temp_c` |
| `start_logging` | `start_logging "data.csv" fillhead gantry` |
| `stop_logging` | `stop_logging` |

### 6.2. Syntax

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

## 7. Device Structure

### 7.1. Overview

Each device is a folder under `/devices/` containing:

- **`commands.json`**: Scriptable commands (e.g., `move_x`, `home`, `set_temp`)
- **`telemetry.json`**: Real-time variables (e.g., `x_pos`, `temp_c`, `pressure`)
- **`events.json`**: Asynchronous notifications (e.g., `homed`, `error`)
- **`gui.py`**: Custom status panel for the device

### 7.2. Adding Devices

**Via UI (Recommended):**
1. Right-click Command Reference → "Add Device..."
2. Right-click device → "Add Command..." or "Add Variable..."
3. Use **File → Generate C++ Code** to create firmware headers

**Manual JSON:**
Copy an existing device folder and edit the JSON files directly. Useful for bulk operations.

### 7.3. Using the Command Reference

The Command Reference panel shows all devices, commands, and variables:
- **Click** any command → copies to clipboard for script use
- **Right-click** variable → "Queue for Logging"
- **Right-click** device → "Add Command/Variable" or "Start Logging..."
- **Right-click** item → "Delete" to remove

Changes save immediately to JSON and update the UI.

### 7.4. JSON File Reference

#### `commands.json`
```json
{
  "move_x": {
    "device": "gantry",
    "target": "device",
    "params": [
      { "parameter": "distance", "type": "float", "unit": "mm" }
    ],
    "returns": ["done", "error"],
    "description": "Moves X-axis by relative distance"
  }
}
```
Script usage: `gantry.move_x 100`

#### `telemetry.json`
```json
{
  "x_pos": {
    "type": "float",
    "default": 0.0,
    "unit": "mm",
    "precision": 2
  },
  "main_state": {
    "type": "string",
    "default": "standby",
    "map": { "standby": "Standby", "busy": "Busy" }
  }
}
```

#### `events.json`
```json
{
  "homed": {
    "device": "gantry",
    "description": "Emitted when homing completes"
  }
}
```
Script usage: `wait_for gantry.homed`

#### `gui.py`
Creates the device status panel:
```python
def get_gui_variable_names():
    return ['gantry_x_pos_var', 'gantry_state_var']

def create_gui_components(parent, shared_gui_refs):
    frame = ttk.Frame(parent)
    x_pos_var = shared_gui_refs.get('gantry_x_pos_var')
    ttk.Label(frame, textvariable=x_pos_var).pack()
    return frame
```

### 7.5. C++ Code Generation

Use **File → Generate C++ Code** to auto-generate firmware headers from JSON:
- `commands.json` → `commands.h`, `command_parser.h/cpp`
- `telemetry.json` → `telemetry.h/cpp`
- `events.json` → `events.h/cpp`

This keeps Python app and C++ firmware synchronized.

---

## 8. Network Protocol

UDP on port 6272, ASCII strings.

```
# Discovery
App → Broadcast: DISCOVER_DEVICE
Device → App: DISCOVERY_RESPONSE: DEVICE_ID=gantry PORT=8889

# Commands
App → Device: MOVE_X:100:1000
Device → App: GANTRY_STATUS:MOVE_X:100:1000:DONE

# Telemetry (10Hz)
Device → App: GANTRY_TELEM:x_pos=123.45;y_pos=67.89;x_homed=1

# Events
Device → App: GANTRY_EVENT:HOMED
```

Messages are prefixed with device name in uppercase.

---

## 9. Contributing

For issues, feature requests, or contributions, please open an issue or pull request on GitHub.

---

<div align="center">

⭐ **Star us on GitHub if you found this useful!**

Made with 💙 by the Blue Robotics team and contributors worldwide

---

<img src="assets/logo.png" alt="Blue Robotics" width="300">

**[bluerobotics.com](https://bluerobotics.com)** | Manufacturing Equipment Control

</div>
