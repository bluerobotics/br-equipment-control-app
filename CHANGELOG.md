# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.20.0] - 2025-11-28

### Added
- **Report System**: New `pressboi.generate_press_report` command for interactive HTML reports
  - Force vs distance graph with pass/fail threshold visualization
  - "Pass zone" box showing acceptable force and endpoint ranges
  - Energy sidebar with visual threshold markers
  - Collapsible machine strain calibration section with polynomial fit
  - Peak, startpoint, and endpoint markers on graph
  - Download raw data as CSV
  - Auto-open report in browser with `open` flag
- **Reports Section**: New "Reports" folder in device panel (cream/off-white color)
- **Reports Directory**: New configurable reports path in Application Paths window
- **Telemetry Parameters**: Device-agnostic telemetry passing to report handlers
- **View Commands**: Script commands to open/close operator views (`pressboi.view_id open/close`)

### Changed
- **Indented Parameter Blocks**: Now supported for ALL commands, not just logging
- **Line Numbers**: Indented lines no longer get line numbers (cleaner display)
- **Device Panel**: Views displayed as `device.view_id` format with double-click to open
- **Syntax Highlighting**: Improved handling of enum values, flags, and keyword parameters

### Fixed
- **Endpoint Pass/Fail**: Now uses telemetry endpoint value instead of CSV last position
- **Report Parameter Parsing**: Correctly handles `value unit keyword` format
- **Single Block Mode**: Fixed validation for commands with indented parameter blocks

## [1.19.0] - 2025-11-26

### Added
- **Cycle Statistics**: Persistent stats tracking (operations, cycle times, yield) with rolling averages
- **Stats Display**: "Show Stats" button in operator view, "Cycle Statistics..." in Settings menu
- **Job Tracking**: Stats tracked per-job with "Last Job" comparison

### Changed
- **Stop Logging**: No longer errors when no active logging sessions
- **Menus**: Removed "Operator Views" from Devices menu (use double-click instead)

## [1.18.0] - 2025-11-26

### Added
- **Operator View Infrastructure**: Support for double-click to open views, shared button state management
- **Script Error Tracking**: Added `had_errors` flag to track warnings/errors for PASS/FAIL logic
- **FONT_FAMILY Export**: Added `theme.FONT_FAMILY` for custom font construction in device modules

### Changed
- **Script Control Sharing**: Run/Hold/Reset handlers now shared with operator views via `shared_gui_refs`
- **Button State Synchronization**: Operator view buttons update simultaneously with main GUI buttons

## [1.17.0] - 2025-11-26

### Added
- **Device Views System**: New "Views" section in device panel for operator UIs
  - JSON-based view definitions in device folders (`views.json`)
  - Right-click context menu: Open View, Display on Startup, Edit, Delete
  - Hover tooltips for view descriptions
  - Support for custom operator views with Run/Hold/Reset controls
  - Persistent startup view settings per device
  
### Changed
- **Device Panel**: Added "Views" folder with lavender/pastel colored headers
- **Device Registry**: Enhanced to load and manage `views.json` definitions
- **JSON Encoding**: All device definition JSON files now use UTF-8 encoding for special character support

## [1.16.1] - 2025-11-26

### Changed
- **Serial Number Panel UI**: Redesigned layout with Op Number moved to top, improved styling and alignment
  - Order: Op Number, Job Number, Serial Number
  - Removed Clear button; fields auto-save on change
  - Right-aligned input boxes and bottom info lines
  - Removed "op" from scanner dropdown (job and serial only)
  - Smaller auto-increment text, improved spacing

## [1.16.0] - 2025-11-24

### Added
- **Lock Editor Button**: Prevents accidental edits to script editor; state persists between restarts
- **NVM Dump Window**: Moved NVM dump functionality to standalone window in Devices menu
- **Firmware Manager Auto-Sizing**: Window automatically scales to fit device content

### Changed
- **Serial Number Panel**: Now visible by default on first launch
- **Serial Number Input**: Redesigned layout with auto-save (removed "Set" button)
- **Device Manager Width**: Changed to percentage-based limits to handle UI scaling better

### Fixed
- **Conditional Statement Warnings**: Fixed warnings being overwritten by "Step complete" message
- **Scanner Input**: Fixed scanner input being typed into script editor when focused there
- **File Wipe Bug**: Fixed autosave wiping file contents during loading
- **Device Manager Width Persistence**: Fixed panel width saving/restoring issues

## [1.15.0] - 2025-11-22

### Added
- **Serial Number System**: Comprehensive serial number tracking with auto-increment functionality
  - Manual entry via GUI panel (located in Device Manager, hidden by default)
  - Barcode/QR code scanner support (USB and Bluetooth)
  - Automatic integration with data logging filenames
  - Smart auto-increment for various serial formats (numeric, prefix+numeric, mixed)
  - Persistent storage of serial numbers and settings
  - Template variables: `<serial>`, `<date>`, `<time>` for flexible filename formatting
  - Serial number settings dialog accessible via Settings menu
  - Toggle panel visibility via Settings → "Show Serial Number Panel" (off by default)
  - Real-time feedback on scanner activity (no misleading "ready" status)
  - Comprehensive documentation (SERIAL_NUMBER_SYSTEM.md, SERIAL_NUMBER_QUICKSTART.md)
  - Example scripts demonstrating serial number usage
  - Test suite for serial number functionality (test_serial_system.py)

### Fixed
- **Firmware Manager mousewheel crash**: Fixed `TclError: invalid command name` exception that occurred when scrolling mouse wheel after closing the Firmware Manager window. Added proper event binding cleanup in window close handler.

## [1.14.6] - 2025-11-21

### Fixed
- **Syntax highlighting diagnostics**: Added error handling and diagnostic logging to identify syntax highlighting failures on certain Windows machines
- **Syntax error fix**: Corrected indentation issue in error handling code that prevented app from launching

## [1.14.5] - 2025-11-21

### Changed
- **Device Manager default width**: Changed from 25% to 30% of window width for better visibility on first launch

### Fixed
- **USB simulation**: Fixed USB simulator not working on Windows (and all platforms) by properly passing device_manager reference to message handler
- **Network simulation**: Fixed network simulator incorrectly displaying "VIRTUAL_COM" instead of "@127.0.0.1" connection address
- **Device Manager width**: Fixed default panel width being too wide on macOS by reducing from previous auto-calculated size to 30% of window width

## [1.14.4] - 2025-11-20

### Changed
- **Device pane renamed to Device Manager**: Right panel now labeled "Device Manager" for clearer UI nomenclature
- **README improvements**: Comprehensive Getting Started guide with step-by-step instructions, GitHub Desktop recommended for device setup, colored section headers for better readability, removed redundant sections (Keyboard Shortcuts, Troubleshooting, Related Projects)

## [1.14.3] - 2025-11-20

### Added
- **Sash position persistence**: Splitter positions (device pane width, terminal height) are now saved and restored across sessions
- **Auto-save sash positions**: Splitter positions are automatically saved when manually resized by the user

### Changed
- **Terminal height on macOS**: Reduced default terminal height from 220px to 180px for better screen space utilization
- **Default font size**: Changed from 11pt to 12pt for improved readability on all platforms
- **Terminal font size**: Terminal text is now 2pt smaller than the main font size for more compact display (e.g., 10pt terminal when main font is 12pt)
- **Device pane default width**: Set to 25% of window width on first launch; subsequent launches use the saved width from last manual resize
- **Scrollbars**: Hidden scrollbars on script editor and terminal for cleaner UI (mouse wheel/touchpad scrolling still works)

### Removed
- **Device pane collapse trigger bar**: Removed collapsible panel trigger bar - users can now hide the device pane by simply resizing it to zero width (position is saved)

### Fixed
- **Device pane width persistence**: Panel width now properly updates and saves when manually resized via splitter
- **Device pane zero-width persistence**: Resizing device pane to zero width (hidden) now correctly saves and restores on app reboot
- **Device pane initial render**: Device pane now renders at correct width immediately on startup with no visible resize
- **Status panel interference**: Status panel width adjustments no longer affect device pane width (independent sash handling)
- **Terminal font size**: Terminal text now uses the configured font size instead of hardcoded 9pt

**Note**: Font size changes require an application restart to rebuild all UI components with the new font. This is expected behavior.

## [1.14.2] - 2025-11-20

### Added
- **Configurable log directories**: System logs and data logs now use separate directories that can be configured via Settings → Show Application Paths
- **Application Paths dialog**: Updated to allow editing system and data log directories with Browse buttons and Save/Cancel actions
- **USB disconnect detection**: Serial listener now detects physical USB disconnections via port status checks and data timeout monitoring

### Changed
- **Log directory defaults**: System logs now go to OS-specific system log locations (e.g., `~/Library/Logs` on macOS), data logs go to `data_logs` subdirectory
- **Log directory separation**: System logs (stdout/stderr) and data logs (CSV telemetry) now stored in different configurable directories

### Fixed
- **Panel visibility on reconnection**: Added robust error handling in GUI queue processing to prevent silent failures
- **Device panel desync**: Implemented automatic monitoring and recovery when connected devices don't have visible panels
- **Connection resilience**: Added safeguards to ensure device panels show correctly after USB reconnection, especially during watchdog recovery states
- **GUI queue errors**: Individual task failures no longer break the entire queue; errors are logged and processing continues
- **USB disconnect logging**: USB disconnections now consistently logged to GUI terminal with proper device state cleanup and panel hiding
- **Zombie serial threads**: Fixed serial listener threads not terminating on USB disconnect, causing thread accumulation on replug
- **Inconsistent disconnect messages**: USB disconnect detection now works reliably via `is_open` checks and 3-second data timeout

## [1.14.1] - 2025-11-20

### Changed
- **Script file extension**: Changed from `.brs` to `.breq` (BR Equipment) to avoid conflict with BrightScript
- **Import system**: Converted all relative imports to absolute imports (`from src.*`) for reliable operation in both source and executable contexts

### Fixed
- **Device add/remove errors**: Fixed "attempted relative import beyond top-level package" errors when adding or removing devices

## [1.14.0] - 2025-11-20

### Added
- **Error log viewer**: Dedicated window (Devices → Dump Error Log...) with syntax highlighting, device selector, and copy-to-clipboard support
- **USB connection robustness**: DTR/RTS toggling and 2-second buffer draining eliminates "ghost data" from previous sessions

### Changed
- **Script file extension**: Changed from `.txt` to `.breq` (BR Equipment) for clearer file association and branding
- **Terminal capture**: Error log window tracks position to show only new messages, preventing duplicate entries from previous dumps
- **UI structure**: Moved `app.py` from `src/ui/` to `src/` and removed unused UI files

### Fixed
- **TTK theme contamination**: Error log window uses custom style name instead of global theme reset
- **Import errors**: Corrected relative imports in firmware modules (`from .comms` → `from ..comms`)
- **Error log timeout**: Fixed message parsing for USB and network formats, case-insensitive device matching
- **Watchdog recovery handling**: Script processor now auto-clears error hold when device sends `DONE: reset`
- **Recovery message display**: Status bar immediately shows RECOVERY messages (not just ERROR), even when no script running
- **Double recovery popups**: Deduplication prevents same warning from appearing twice when received over USB + network
- **Status bar persistence**: `DONE: reset` automatically clears red error state in GUI

## [1.13.0] - 2025-11-19

### Changed
- **Codebase cleanup**: Removed unused `download_release.py` and `device_actions.py` utility files
- **Device-agnostic documentation**: All comments and examples now use generic device names instead of specific device references
- **Code organization**: Moved device menu commands into `top_menu.py` for better separation of concerns
- **Script processor**: Removed device-specific workarounds for fillhead/injector valve commands (will be fixed in firmware)
- **Script processor**: Replaced hardcoded "retract" safety action with generic START/DONE detection for any safety action

### Fixed
- **Firmware v1.9.0 compatibility**: App now expects single DONE message per command (firmware handles multi-step commands internally)

## [1.12.0] - 2025-11-19

### Fixed
- **Device removal/re-addition flow**: Fixed status panel not appearing after removing and re-adding a device without app restart
- **Device removal/re-addition flow**: Fixed `UnboundLocalError` and `_tkinter.TclError` exceptions when removing and re-adding devices
- **Syntax highlighting refresh**: Fixed syntax highlighting not updating after removing device, closing app, and re-adding device
- **Script validator refresh**: Fixed script validator not recognizing device commands after device removal and re-addition
- **Add device flow**: Simplified device addition to go directly to folder browser without intermediate dialog
- **Connection cycling**: Fixed unnecessary disconnect/reconnect cycle on app startup when device is already connected
- **GUI status panel resilience**: Hardened Tkinter callbacks to gracefully handle widget destruction during device removal

### Changed
- **Add device dialog**: Removed intermediate dialog, now goes directly to folder browser when adding devices
- **Device removal notifications**: Removed "Device has been removed" confirmation messagebox for cleaner UX

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

