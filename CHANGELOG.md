# Changelog

All notable changes to this project will be documented in this file.

## [1.11.0] - 2025-11-19

### Fixed
- **USB hotplug detection**: Implemented automatic USB device reconnection without requiring app restart
- **USB connection reliability**: Fixed multiple issues causing USB connections to fail or require power cycling
- **Connection persistence**: Connection method (USB/Network) now properly persists across app restarts and connection changes
- **Terminal debug filtering**: Added "Show Debug" checkbox to filter debug messages (hidden by default)
- **GUI status panel**: Fixed double `@@` symbols in network connection display (e.g., was `@ @192.168.1.148`, now `@192.168.1.148`)
- **Code generator directory selection**: "Save to Directory" now prompts user for target folder as intended
- **Code generator firmware export**: "Save to Firmware" now automatically saves to device's `inc/` and `src/` folders without user prompts

### Changed
- **USB connection startup**: Improved initial USB connection logic with proper sequencing and retry handling
- **Status panel updates**: Network connections now show `@IP_ADDRESS` format consistently

## [1.10.1] - 2025-11-17

### Changed
- **Device-agnostic firmware system**: Refactored ClearCore firmware configuration to use per-device JSON files instead of hardcoded dictionary

### Fixed
- **Firmware Manager**: Fixed display to show only connected devices with correct COM port and firmware version information
- **Firmware Manager**: Added scrollbar for device list and USB-only flashing note

## [1.10.0] - 2025-11-15

### Added
- **Warning system**: New `throw` command to trigger custom warnings defined in `warnings.json` files
- **Conditional logic**: `if` statements with variable comparisons (e.g., `if pressboi.joules < 1.5 throw pressboi.energy_warning`)
- **Warnings display**: New warnings section in device pane for each device
- **Script error handling**: Warnings now trigger script hold (like errors), require reset to continue

### Changed
- Updated `force_action` parameter documentation

### Fixed
- **Script processor**: Fixed cycle block parsing to correctly detect end of indented cycle blocks, preventing "Unexpected end of file" errors

### Notes
- Compatible with Pressboi firmware v1.6.0+

## [1.9.0] - 2025-11-14

### Added
- **USB serial communication**: Alternative to network communication for all devices
- **Connection method switching**: Right-click devices in Command Reference to switch between Network (UDP) and USB Serial
- **Persistent connection preferences**: Connection method remembered across app restarts (saved per device)
- **USB simulator**: Virtual USB serial simulation option alongside network simulation (`@ VIRTUAL_COM`)
- **Connection status display**: All device panels show `@ IP_ADDRESS` or `@ COM_PORT` inline with device name
- **Firmware Manager**: Automatic USB reconnection after firmware flash (no app restart required)
- **Firmware Manager**: "Flash from File…" button to flash local .uf2 files

### Changed
- **Connection status messages**: Consistent format for network ("Connected via Ethernet on 192.168.x.x") and USB ("Connected via USB on COM10")
- **Firmware Manager UI**: Left-justified button layout, removed LAN connection row and update check text
- **Device status refresh**: Immediate update when switching connection methods (no expand/collapse needed)

### Fixed
- **Script autosave**: No longer adds blank lines over time (Tkinter Text widget trailing newline issue)
- **Device panels**: Connection status correctly displays for all devices (Pressboi, Fillhead, Gantry, Pressurizer)
- **Command Reference**: Refreshes immediately when devices connect
- **USB serial commands**: Use existing connection instead of attempting to reopen port
- **Firmware flash**: Properly closes and reopens USB serial connection during update process
- **Network discovery**: No longer overrides USB connection method when device configured for USB

## [1.8.0] - 2025-11-12


### Added
- **ClearCore**: new ClearCore firmware updater tool
- **Pressboi**: Device definition now includes a new `set_force_zero` command to tare the sensor
- **UI**: Added Settings → UI Scale menu (90%–400%) and default application scaling to 200%
- **UI**: Added “Show Application Paths…” window under Settings listing config, logs, recent files, and executable locations

### Fixed
- **macOS**: Devices folder prompt now saves configuration outside the app bundle to prevent crashes when selecting the folder on first launch
- **Command Reference**: Fixed script pane display bugs
- **macOS**: Log files are now written to Application Support so Finder launches no longer crash on read-only bundles
- **macOS**: Bundled pyserial with the app so Firmware Manager USB detection works without requiring a separate install
- **macOS**: Recent scripts list now saves to Application Support, fixing read-only errors when opening files from Finder launches
- **Windows**: UI scale now honours the system default unless overridden in the menu, fixing shrunken widgets introduced in the first 1.8.0 build
- **UI**: Device/status pane width auto-adjusts to content with a small margin, avoiding OS-specific hard-coded values
- **UI**: Status pane now lives in its own splitter, so you can drag the handle to fine-tune its width

## [1.7.0] - 2025-11-07

### Added
- **Console**: Syntax highlighting for console lines and adjustable console height in the UI
- **Pressboi**: Energy display in the telemetry panel aligns with new firmware Joule reporting
- **Pressboi**: Added `set_force_mode`, `set_force_offset`, `set_force_scale`, and `set_strain_cal` commands to device definition
- **Pressboi**: `set_retract` command documents optional speed argument with device-side defaulting to 25 mm/s
- **Pressboi**: Strain calibration command accepts fifth coefficient for fourth-order machine compliance fits

### Changed
- **Pressboi**: Command defaults updated to reflect the 25 mm/s retract baseline across UI metadata and JSON
- **Pressboi**: Move commands drop inline `force_mode`; use `set_force_mode` for sensor selection
- **Pressboi**: Discovery parser now records firmware version for update comparisons and regenerated command/telemetry C++ so firmware headers match the latest schema

## [1.6.0] - 2025-11-06

### Added
- **Pressboi**: Device watchdog recovery state detection and warning
- **Pressboi**: Added `test_watchdog` command to device definition
- **Pressboi**: Added `force_mode` parameter to move commands (`motor_torque` or `load_cell`)
- **Pressboi**: Force source indicator in GUI with visual badge (`motor_torque` or `load_cell`)
- **Pressboi**: Added telemetry fields `force_load_cell` and `force_motor_torque`

### Changed
- **Pressboi**: GUI displays force based on active mode (`force_source` field)
- **Pressboi**: Torque consolidated to single `torque_avg` field (replaces individual motor values)
- **Scripts**: Auto-removes documentation labels (`action`, `mode`, `limit`, `source`) from command arguments

## [1.5.1] - 2025-11-05

### Added
- Right-click context menu for script functions (logging commands) with detailed help and examples
- Auto-refresh of device connection status in Command Reference panel

### Changed
- Improved syntax highlighting for logging commands

### Fixed
- Fixed "More Info" display for script-only commands (logging functions)
- Fixed device connection status not updating in Command Reference panel until tree expansion

## [1.5.0] - 2025-11-04

### Added
- Script validator now checks that all connected devices support required commands (pause, reset, resume)
- Pause/resume functionality for all connected devices during script execution
- Hold button sends pause command to all connected devices

### Changed
- Script execution now properly waits for resumed moves to complete before advancing
- ScriptRunner remains active during pause/hold, waiting for device DONE messages
- Improved button state management with centralized refresh logic

### Fixed
- Fixed cursor advancement in single block mode - cursor now properly advances after command completion
- Fixed hold button becoming disabled after pause/resume cycles
- Fixed line advancing prematurely during pause/resume operations
- Fixed validation window display for device capability errors
- Implemented complete `advance_to_next_line()` function that was previously a stub

## [1.4.0] - 2025-11-03

### Added
- Right-click "Refresh Device" option to reload device configurations without restarting

### Changed
- Code generator improvements: removed trailing spaces from command strings, fixed enum comma placement
- Refactored command flow: abort → cancel, clear_errors → reset

### Fixed
- Critical fix: Device.command notation now strips device prefix before sending to firmware
- Script DONE waiting now uses stripped command names for reliable matching
- Autogenerated code now compiles without warnings (signed/unsigned, format specifiers)

## [1.3.2] - 2025-11-03

### Added
- Right-click "Refresh Device" option in Command Reference to reload device configurations without restarting

### Changed
- Improved code generator to remove trailing spaces from command strings
- Code generator now uses scoped buffers in events.cpp to eliminate unused variable warnings

### Fixed
- Discovery protocol now working correctly for pressboi (port alignment and command string parsing)
- Firmware build warnings eliminated from autogenerated code (signed/unsigned comparisons, format specifiers)

## [1.3.1] - 2025-11-02

### Added
- **Major:** Added builds for Windows, macOS, and Linux
- User must now select device folder location on first startup
- Added method to change device folder location via Settings menu
- UI fixes and improvements

### Changed
- Standardized executable naming to `br-equipment-control-app` across all platforms
- Device folder can now be customized and stored separately from app installation

### Fixed
- macOS build compatibility issues

## [1.3.0] - 2025-11-02

### Added
- **Major:** Refactored device panel
- **Major:** Added ability to add/edit/delete devices, commands, variables, and events from the app
- **Major:** Added events (messages from the device that can control the script execution)
- **Major:** Added datalogging features
- Integrated device simulation into the main app (now accessible by right clicking device in device pane)
- Added checks to block script execution if devices aren't connected

### Changed
- Improvements to pressboi and gantry device status panels
- Many small bug fixes
- Updated readme

## [1.2.0] - 2025-10-30

### Added
- **Major:** Added variables tab for displaying all available device telemetry variables
- **Major:** Added automatic C++ header code generation from commands.json and telemetry.json
- **Major:** Added wait_for command to wait for conditions (variables, comparisons, timeouts)
- Enhanced commands.json structure with device/host/target specifications
- Added syntax highlighting for device variables (device.variable format)
- Added pressboi `force_action` parameter with options: return, halt, continue
- Added syntax highlighting support for keyword-type parameters

### Changed
- Standardized command response pattern to `done` and `error`

### Fixed
- Fixed tab width in script editor

## [1.1.0] - 2025-10-25

### Added
- **Major:** Refactored command syntax to dot notation (device.do_something) and added syntax highlighting for devices
- **Major:** Refactored device-specific simulator methods to be within device folders
- **Major:** Added file recovery and unsaved file warnings
- Added new "more info" window for commands to display more details about them
- Added support for strings as command parameters

### Changed
- Changed fonts to monospaced and improved tab indenting
- Added basic distance <> force graph to the pressboi device definition

### Fixed
- Fixed simulator device discovery on macOS

## [1.0.1] - 2025-10-20

### Added
- Initial release of the br-equipment-control-app
- Script editor with syntax highlighting
- Multi-device support (fillhead, gantry, pressboi, pressurizer)
- Device simulator
- Command Reference panel
- Real-time device discovery and connection monitoring
- UDP-based communication protocol

