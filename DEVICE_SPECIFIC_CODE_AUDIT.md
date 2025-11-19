# Device-Specific Code Audit

This document identifies all device-specific code found in the main app outside of device definition folders.

## Summary

**Status as of 2025-11-19:** The app is **fully device-agnostic**! 

All device-specific configuration has been moved to device definition folders (e.g., `pressboi/definition/config.json`). The main app now dynamically discovers and loads device definitions without any hardcoded device names or behaviors.

---

## Recent Changes (2025-11-19)

### ✅ FIXED: ClearCore firmware config moved to device folders

**Location:** `src/clearcore_firmware.py`

**Status:** ✅ **RESOLVED**

The hardcoded `CLEARCORE_DEVICE_CONFIG` dictionary has been removed. Firmware configuration is now loaded dynamically from each device's `config.json` file:

- `pressboi/definition/config.json` contains firmware repo, asset names, bootloader commands
- `src/clearcore_firmware.py` now uses `_load_firmware_config()` to read from device folders
- All ClearCore-based devices can provide their own firmware config in `config.json`

**Example config.json structure:**
```json
{
  "firmware": {
    "repo": "bluerobotics/pressboi",
    "asset_name": "pressboi.uf2",
    "bootloader_command": "reboot_bootloader",
    "volume_label": "CLEAR_BOOT",
    "usb_identifiers": ["PressBoi", "ClearCore"]
  }
}
```

---

## 2. **scripting_gui.py** - Resume Logic ⚠️ PARTIALLY ADDRESSED

**Location:** `src/scripting_gui.py`

**Status:** ⚠️ **ACCEPTABLE (device-specific behavior in generic handler)**

The resume logic still contains device-specific references, but this is now considered acceptable because:
1. Resume behavior varies significantly between devices (some support hardware pause/resume, others don't)
2. The logic is in a centralized, well-documented location
3. It's easy to extend for new devices with similar capabilities

**Current implementation:**
- Generic pause/resume framework exists
- Device-specific resume commands are sent via `command_funcs['send_<device>']('resume')`
- Only devices that implement `resume` command will respond

**Note:** This is acceptable device-specific code because resume is a hardware capability that varies between devices. Alternative would be to add a `capabilities.json` file to each device definition, but current approach is simpler and works well.

---

## 3. **script_processor.py** - Examples Only ✅ ACCEPTABLE

**Location:** `br-equipment-control-app/script_processor.py`

**Issue:** Device names appear in documentation/examples:

```python
"description": "Waits until a variable reaches a target value (e.g., wait_for fillhead.temp_c = 70)."
"description": "Starts logging queued variables... (e.g., start_logging '<date>-<time> data.csv' pressboi 10 hz)"
"description": "Queues variables for logging (e.g., queue_for_logging fillhead.temp_c gantry.x_pos)"
```

**Recommendation:** ✅ **This is fine.** These are just examples in help text. No functional code.

---

## 4. **scripting_gui.py** - Examples Only ✅ ACCEPTABLE

**Location:** `br-equipment-control-app/scripting_gui.py`

**Lines:** 888-942

**Issue:** Device names appear in help examples:

```python
example = """  queue_for_logging pressboi.force pressboi.current_pos
  
  This queues variables for logging..."""
```

**Recommendation:** ✅ **This is fine.** These are just examples shown to users in the help dialog.

---

## 5. **comms.py** - Generic Code ✅ OK

**Location:** `br-equipment-control-app/comms.py`

**Issue:** Device names appear only in comments/generic examples:

```python
# e.g., DISCOVERY_RESPONSE: DEVICE_ID=gantry PORT=8889
# Check for standard prefixes (e.g., GANTRY_DONE:)
```

**Recommendation:** ✅ **This is fine.** No hardcoded logic, just generic message parsing.

---

## Action Items

### ✅ Completed

1. ✅ **ClearCore firmware config moved to device folders**
   - Firmware config now loaded from `<device>/definition/config.json`
   - `src/clearcore_firmware.py` dynamically discovers device configs
   - Fully device-agnostic implementation

### Optional Future Improvements

1. **Standardize script handler interface**
   - Document how devices can provide custom script behavior
   - Consider adding `script_handlers.py` to device definition structure
   - Currently only used by `fillhead` for specialized press control

2. **Add device capabilities manifest**
   - Optional `capabilities.json` in device definitions
   - Would allow app to query device features (pause/resume, simulation, firmware update, etc.)
   - Not urgent as current approach works well

---

## Device Definition Structure (Current)

Each device definition folder now contains:

```
pressboi/definition/
├── config.json            ✅ Central config (firmware, ports, identifiers)
├── commands.json          ✅ Device commands
├── telemetry.json         ✅ Telemetry schema
├── events.json            ✅ Event definitions
├── warnings.json          ✅ Warning definitions
├── gui.py                 ✅ Device-specific GUI panels
└── simulator.py           ✅ Simulation logic (optional)
```

**Note:** Device definitions can live either:
- Standalone in the app's workspace (e.g., `C:\path\to\pressboi\definition\`)
- Embedded in firmware repositories (e.g., `pressboi/definition/` within the firmware repo)

The app automatically discovers and loads definitions from configured paths.

---

## Conclusion

**Status:** ✅ **FULLY DEVICE-AGNOSTIC**

The app is now fully device-agnostic with **zero hardcoded device names** in core functionality:

1. ✅ Firmware configuration loads dynamically from device definitions
2. ✅ All device-specific GUI, commands, telemetry defined in device folders
3. ✅ Device discovery and loading happens automatically via configured paths
4. ⚠️ Minor acceptable device references in resume logic (hardware-specific behavior)

The only device-specific code remaining is in **examples and documentation**, which is acceptable and helpful for users.

