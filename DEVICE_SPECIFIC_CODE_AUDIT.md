# Device-Specific Code Audit

This document identifies all device-specific code found in the main app outside of the `devices/` folder.

## Summary

The app is **mostly** device-agnostic, but there are a few areas where device-specific code has leaked into the main codebase. Most are **acceptable** (examples in documentation), but some should be **moved** to device folders.

---

## 1. **clearcore_firmware.py** ⚠️ SHOULD BE MOVED

**Location:** `br-equipment-control-app/clearcore_firmware.py`

**Issue:** This file contains a hardcoded configuration dictionary for ClearCore-based devices:

```python
CLEARCORE_DEVICE_CONFIG = {
    "pressboi": {
        "repo": "bluerobotics/pressboi",
        "asset_name": "pressboi.uf2",
        "label": "Pressboi",
        "bootloader_command": "reboot_bootloader",
        "volume_label": "CLEAR_BOOT",
        "usb_identifiers": ["PressBoi", "ClearCore"]
    }
}
```

**Recommendation:** 
- Move this config to `devices/pressboi/firmware_config.json` (or similar)
- Modify `clearcore_firmware.py` to dynamically load firmware configs from device folders
- Each device that uses ClearCore should provide its own `firmware_config.json`

**Files to create:**
- `devices/pressboi/firmware_config.json`
- Optional: `devices/*/firmware_config.json` for future ClearCore devices

---

## 2. **scripting_gui.py** - Resume Logic ⚠️ NEEDS REFACTOR

**Location:** `br-equipment-control-app/scripting_gui.py`

**Lines:** 1286-1298, 1707-1710

**Issue:** There is hardcoded "pressboi" resume logic:

```python
# If we paused a device (pressboi), send resume command instead of re-executing
if paused_device == 'pressboi':
    print(f"[RESUME] Sending resume to pressboi at line {feed_hold_line}")
    paused_device = None
    feed_hold_line = None
    if 'send_pressboi' in shared_gui_refs['command_funcs']:
        shared_gui_refs['command_funcs']['send_pressboi']('resume')
```

And:

```python
# Track paused devices (for now, focus on pressboi for resume logic)
if 'pressboi' in paused_devices:
    paused_device = 'pressboi'
elif paused_devices:
    paused_device = paused_devices[0]  # Use first paused device
```

**Recommendation:**
- Remove hardcoded "pressboi" reference
- Make resume logic generic for ALL devices that support pause/resume
- Use device capabilities to determine if a device supports resume
- Consider adding a `script_handlers.py` file in each device folder that defines custom script behavior

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

### High Priority (Breaking Device-Agnostic Design)

1. **Move ClearCore firmware config to device folders**
   - Create `devices/pressboi/firmware_config.json`
   - Update `clearcore_firmware.py` to load configs dynamically from device folders
   
2. **Remove hardcoded pressboi resume logic**
   - Make `scripting_gui.py` generic for all devices with pause/resume capability
   - Consider moving special resume behavior to device-specific script handlers

### Low Priority (Acceptable but could be improved)

3. **Standardize script handler interface**
   - Document how devices can provide custom script behavior via `script_handlers.py`
   - Currently only `fillhead` has this file

---

## Device Folder Structure (Recommended)

Each device folder should contain:

```
devices/pressboi/
├── commands.json          ✅ Already exists
├── telemetry.json         ✅ Already exists
├── events.json            ✅ Already exists
├── warnings.json          ✅ Already exists
├── gui.py                 ✅ Already exists
├── simulator.py           ✅ Already exists
├── script_handlers.py     ⚠️ Optional (only fillhead has this)
└── firmware_config.json   ❌ NEEDS TO BE CREATED
```

---

## Conclusion

The app is **mostly device-agnostic**, with only **2 significant violations**:

1. **Hardcoded ClearCore firmware config** (easy to fix)
2. **Hardcoded pressboi resume logic** (requires refactor)

All other references are either examples in documentation or generic parsing logic.

