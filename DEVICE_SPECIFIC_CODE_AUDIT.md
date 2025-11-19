# Device-Specific Code Audit

**Last Updated:** 2025-11-19  
**Status:** ✅ **Fully Device-Agnostic**

---

## Acceptable Device References

### Resume Logic (`src/scripting_gui.py`)

Resume logic contains device-specific checks because resume is a hardware capability that varies between devices. This is centralized, well-documented, and easy to extend.

**Alternative:** Could add a `capabilities.json` manifest to device definitions, but current approach is simpler and works well.

---

## Device Definition Structure

Each device definition folder contains:

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

The app is fully device-agnostic. Adding a new device requires only:
1. Creating a device definition folder with required JSON files
2. Implementing device-specific GUI in `gui.py`
3. Optionally providing `simulator.py` for simulation

No changes to core app code are needed.
