<div align="center">
    <img src="assets/icon.png" alt="Application Icon" width="150">
</div>

# BR Equipment Control App

**Version:** 1.2  
**Author:** Eldin Miller-Stead  
**Release Date:** 2025-10-13

---

## 1. Overview

This application is a desktop program for controlling and scripting multiple pieces of hardware, referred to as "devices". Its main purpose is to provide a single, centralized user interface for running automated scripts that can command several different devices in sequence.

<div align="center">
    <img src="assets/app.png" alt="Application Screenshot">
</div>

The system is designed to be modular. You can add new devices to the application without changing the main codebase. This is done by creating a new folder for the device in the `/devices` directory and adding a set of specific configuration files. The application can even detect and load new device modules while it's running.

---

## 2. Core Features

- **Runtime Device Loading**: You can add new device folders to the `/devices` directory while the application is running. Using the "Scan for New Device Modules" menu option will load the new device, its commands, and its UI without needing a restart.
- **Multi-Threading Model**: The application uses multiple background threads to keep the user interface responsive. Network communication (sending and receiving) and script execution each run on their own threads, so the UI does not freeze during these operations.
- **Text-Based Scripting**: Scripts are simple text files. The application includes a script editor with syntax highlighting for device-specific commands.
- **Script Validation**: Before a script is run, the application validates its syntax against the known commands for all loaded devices. This helps catch typos and errors before they cause problems during execution.
- **Dynamic UI Panels**: Each device has its own status panel in the UI. The content of this panel is defined by the device's own configuration and is created automatically when the device is loaded.
- **Device Simulator**: A separate simulator script is included for development and testing. It can simulate multiple devices on the local network, allowing for script testing without physical hardware.

---

## 3. System Architecture

The application's design separates the core logic from device-specific implementations, so the main application doesn't need to know the details of any particular device.

### 3.1. Threading Model Explained

The application runs on several threads to separate tasks and keep the UI responsive:

1.  **Main UI Thread**: This is the primary thread that runs the Tkinter event loop. It handles all window drawing, user input, and button clicks. Any change to the UI (like updating a label's text) must happen on this thread. To achieve this, background threads place UI update tasks onto a central `queue.Queue`, which the main thread processes periodically.
2.  **Communication Threads**: These are background "daemon" threads that handle all network traffic.
    - **`recv_loop`**: This thread's only job is to listen for incoming UDP packets. When a packet arrives, it identifies the message type (telemetry, status, discovery response) and the source device. It then passes the message to the appropriate handler.
    - **`discovery_loop`**: This thread sends a broadcast UDP message (`DISCOVER_DEVICE`) over the network every few seconds. Devices on the network are expected to reply to this message, which is how the application finds their IP addresses.
    - **`monitor_connections`**: This thread acts as a watchdog. It periodically checks the timestamp of the last message received from each device. If a device has been silent for too long, this thread marks it as "Disconnected" and updates the UI accordingly.
3.  **Script Execution Thread**: When you click the "Run" button, the `ScriptRunner` class starts a new background thread to execute the script. This allows the UI to remain fully interactive while the script is running, which is especially important for long `WAIT` commands.

### 3.2. How the Core Modules Work Together

#### `main.py` - The Orchestrator
This is the starting point of the application. The `MainApplication` class is responsible for:
- Creating the main window and setting up the overall layout.
- Creating an instance of the `DeviceManager`.
- Telling the `DeviceManager` to perform its initial scan of the `/devices` directory.
- Creating the main UI components like the menu bar, the scripting panel, and the terminal.
- Starting the background threads defined in `comms.py`.
- Providing functions that can be called later to add new UI panels (`add_new_device_panels`) and refresh the command lists (`refresh_command_components`) when a new device is loaded at runtime.

#### `device_manager.py` - The Device Database
This module's `DeviceManager` class is the central authority on all things related to devices.

- **On Startup**: It scans the `/devices` folder and loads all the configuration files and `gui.py` modules it finds. It builds an internal dictionary of all known devices and their properties.
- **At Runtime**: When the user clicks "Scan for New Device Modules", its `scan_and_load_new_devices()` method is called. This method re-scans the `/devices` folder, identifies any new subdirectories, and loads them in the same way it did at startup.
- **Source of Truth**: It holds the complete, up-to-date list of all loaded devices, their command definitions, their telemetry schemas, their UI modules, and their current connection status (IP address, etc.). Other parts of the application query the `DeviceManager` to get this information.

#### `comms.py` - The Network Handler
This module handles all sending and receiving of UDP packets over the network. The protocol is lightweight and designed for use on a local Ethernet network.

- It does not contain any hardcoded device names. When a message like `GANTRY_TELEM:...` arrives, the `recv_loop` function extracts the `gantry` part of the message. It then asks the `DeviceManager`, "Do you know about a device named 'gantry'?" If the `DeviceManager` says yes, `comms.py` proceeds to handle the message. If no, the message is marked as "[UNHANDLED]".
- This design means that when a new device is loaded by the `DeviceManager`, the `comms.py` module will start recognizing its messages automatically, without needing to be restarted or reconfigured.

#### `scripting_gui.py` & `script_processor.py` - The Scripting Engine
- The UI for the scripting engine is created in `scripting_gui.py`. When it is created, it asks the `DeviceManager` for a list of all commands from all known devices. It uses this list to configure the syntax highlighter and the command reference panel. It also includes `refresh` methods so these components can be updated when new devices are loaded.
- `script_processor.py` contains the `ScriptRunner` class, which is responsible for executing the script text. It runs in a background thread and sends commands to devices one by one, waiting for a `DONE:` reply before moving to the next line to provide synchronous execution of commands.

---

## 4. How to Add a New Device

To add a new device, you create a folder inside the `/devices` directory. The name of the folder becomes the device's unique ID (e.g., `test_device`). Inside this folder, you must create the following files:

### 4.1. `commands.json`
This file defines all the commands the device accepts in a script.

- **Structure**: A JSON object. Each key in the object is a command name (e.g., `"MOVE_X"`).
- **Properties for each command**:
    - `device`: The device's ID (e.g., `"test_device"`). Must match the folder name.
    - `params`: A list of parameters the command takes. Each parameter is an object with a `name` and `type` (e.g., `{"name": "distance", "type": "float"}`).
    - `help`: A short description of what the command does.
    - `gui_action` (Optional): The name of a function to be called when a UI button is pressed. This links a button in the device's GUI panel to a script command.

**Example `commands.json`:**
```json
{
  "MOVE_X": {
    "device": "gantry",
    "params": [
      { "name": "distance", "type": "float" },
      { "name": "speed", "type": "int" }
    ],
    "help": "Moves the gantry X-axis by a relative distance at a specified speed."
  },
  "HOME_X": {
    "device": "gantry",
    "params": [],
    "help": "Homes the gantry X-axis."
  },
  "ENABLE_X": {
    "device": "gantry",
    "gui_action": "enable_x",
    "params": [],
    "help": "Enables the gantry X-axis motor."
  }
}
```

### 4.2. `telemetry.json`
This file tells the application how to interpret telemetry data sent by the device.

- **Structure**: A JSON object. Each key is the name of a variable in the telemetry message (e.g., `"pressure_psi"`).
- **Properties for each variable**:
    - `gui_var`: The name of the `tk.StringVar` or `tk.DoubleVar` that this value will update in the UI. You will use this same name in your `gui.py` file.
    - `default`: The value the UI variable should have when the application starts and what it should be reset to if the device disconnects. This is important for a clean user experience.
    - `format` (Optional): An object that defines how to format the raw value before displaying it.
        - `map`: Converts a raw value to a string (e.g., `{"0": "Off", "1": "On"}`).
        - `suffix`: Text to add after the value (e.g., `" mm"`).
        - `precision`: For numbers, the number of decimal places to show.
        - `multiplier`: A number to multiply the incoming value by.

**Example `telemetry.json`:**
```json
{
  "gantry_state": {
    "gui_var": "gantry_main_state_var", 
    "default": "STANDBY"
  },
  "x_p": {
    "gui_var": "gantry_x_pos_var", 
    "default": 0.0,
    "format": { "precision": 2, "suffix": " mm" }
  },
  "x_h": {
    "gui_var": "gantry_x_homed_var", 
    "default": 0,
    "format": { "map": { "0": "Not Homed", "1": "Homed" } }
  }
}
```

### 4.3. `gui.py`
This Python file contains the code to build the device's UI panel.

- It must contain a function with the exact signature: `create_gui_components(parent, shared_gui_refs)`.
- `parent`: This is the Tkinter frame inside the main application where your UI panel will be placed.
- `shared_gui_refs`: This is a dictionary that your function will use to get access to the `tk.StringVar`s you defined in `telem_schema.json`.
- Your function should create a `tk.Frame` that contains all the labels, buttons, etc., for your device, and then return that frame.

**Example `gui.py`:**
```python
import tkinter as tk
from tkinter import ttk

def create_gui_components(parent, shared_gui_refs):
    # Create the main container frame for this device
    device_panel = ttk.Frame(parent, padding=5)

    # Get the specific StringVar for the pressure reading
    pressure_var = shared_gui_refs.get("my_device_pressure_var")

    # Create and arrange the widgets
    ttk.Label(device_panel, text="Pressure:").pack(side=tk.LEFT)
    ttk.Label(device_panel, textvariable=pressure_var).pack(side=tk.LEFT)

    return device_panel
```

---

## 5. Project Setup

1.  **Python Version**: Python 3.10 or newer is recommended.
2.  **Dependencies**: This project does not have any external dependencies and uses only Python's built-in libraries. A `requirements.txt` file is included to make it easier to add and manage dependencies in the future.
3.  **To Run**:
    ```bash
    python main.py
    ```
