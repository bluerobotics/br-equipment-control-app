# Device-Specific Code Audit

**Last Updated:** 2025-11-19  
**Status:** ✅ **Fully Device-Agnostic**

---

## Summary

The app is **fully device-agnostic**. All device-specific configuration lives in device definition folders (e.g., `pressboi/definition/`). The main app dynamically discovers and loads device definitions without hardcoded names or behaviors.

---

## What Was Fixed

### ✅ Firmware Configuration
- Removed hardcoded `CLEARCORE_DEVICE_CONFIG` from `src/clearcore_firmware.py`
- Firmware config now loads dynamically from `<device>/definition/config.json`
- Each device provides its own firmware repo, asset names, bootloader commands

### ✅ Documentation Examples
- Replaced device-specific names (e.g., `fillhead.temp_c`, `pressboi.joules`) with generic `device.*` names
- Examples now show `device.temp_c`, `device.energy`, etc.
- Makes documentation clearer and more device-agnostic

---

## Acceptable Device References

### Resume Logic (`src/scripting_gui.py`)
**Status:** ⚠️ Acceptable

Resume logic contains device-specific checks because resume is a hardware capability that varies between devices. This is centralized, well-documented, and easy to extend.

---

## Device Definition Structure

Each device definition folder should contain:

```
<device>/definition/
├── config.json            # Central config (firmware, ports, identifiers)
├── commands.json          # Device commands for scripting
├── telemetry.json         # Telemetry schema
├── events.json            # Event definitions
├── warnings.json          # Warning definitions
├── gui.py                 # Device-specific GUI panels
├── simulator.py           # Simulation logic (optional)
└── script_handlers.py     # Custom script behavior (optional)
```

### Script Handlers (Optional)

Devices can provide custom script behavior by creating a `script_handlers.py` file in their definition folder.

**Purpose:** Handle device-specific script events that require special logic beyond standard command execution.

**Example:** `fillhead/definition/script_handlers.py`

```python
def on_script_start(device_state, shared_gui_refs):
    """Called when a script starts executing."""
    pass

def on_script_stop(device_state, shared_gui_refs):
    """Called when a script stops executing."""
    pass

def on_cycle_start(device_state, shared_gui_refs):
    """Called at the start of each cycle."""
    pass

def on_cycle_end(device_state, shared_gui_refs):
    """Called at the end of each cycle."""
    pass
```

**Current Usage:**
- Only `fillhead` currently implements `script_handlers.py`
- Used for specialized press control and cycle management
- Not required for most devices

**When to Use:**
- Device needs to perform setup/teardown during script execution
- Device requires special handling during cycle operations
- Device has state that needs to be managed across script commands

**How It Works:**
1. App checks for `script_handlers.py` in device definition folder
2. If found, imports the module and calls handler functions at appropriate times
3. Handlers receive `device_state` (current device status) and `shared_gui_refs` (GUI access)
4. Handlers can send commands, update GUI, or modify device state

---

## Conclusion

The app architecture is fully device-agnostic. Adding a new device requires only:
1. Creating a device definition folder with required JSON files
2. Implementing device-specific GUI in `gui.py`
3. Optionally providing `simulator.py` and `script_handlers.py` for advanced features

No changes to core app code are needed.
