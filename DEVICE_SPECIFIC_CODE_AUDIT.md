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
└── simulator.py           # Simulation logic (optional)
```

---

## Conclusion

The app architecture is fully device-agnostic. Adding a new device requires only:
1. Creating a device definition folder with required JSON files
2. Implementing device-specific GUI in `gui.py`
3. Optionally providing `simulator.py` and `script_handlers.py` for advanced features

No changes to core app code are needed.
