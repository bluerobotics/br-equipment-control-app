## v1.2.0 - 2025-10-27
- **Major:** Added variables tab for displaying all available device telemetry variables
- **Major:** Added automatic C++ header code generation from commands.json and telemetry.json
- **Major:** Added WAIT_FOR command to wait for conditions (variables, comparisons, timeouts)
- Enhanced commands.json structure with device/host/target specifications
- Added syntax highlighting for device variables (device.variable format)
- Added pressboi `force_action` parameter with options: return, halt, continue
- Standardized command response pattern to `done` and `error`
- Fixed tab width in script editor
- Added syntax highlighting support for keyword-type parameters

## v1.1.0 - 2025-10-20
- **Major:** Refactored command syntax to dot notation (device.do_something) and added syntax highlighting for devices
- **Major:** Refactored device-specific simulator methods to be within device folders
- **Major:** Added file recovery and unsaved file warnings
- Fixed simulator device discovery on macOS
- Added new "more info" window for commands to display more details about them
- Added support for strings as command parameters
- Changed fonts to monospaced and improved tab indenting
- Added basic distance <> force graph to the pressboi device definition

## v1.0.1  - 2025-10-13
- **Major:** Initial release of the BR Equipment Control App.
