# Device-Specific Code Audit

## Acceptable Device References

### Resume Logic (`src/scripting_gui.py`)

Resume logic contains device-specific checks because resume is a hardware capability that varies between devices. This is centralized, well-documented, and easy to extend.

**Alternative:** Could add a `capabilities.json` manifest to device definitions, but current approach is simpler and works well.
