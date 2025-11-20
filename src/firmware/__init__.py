"""
Firmware Package - Firmware update and management tools.

This package handles firmware updates for ClearCore-based devices including:
- Firmware downloading from GitHub releases
- Firmware flashing via USB
- Firmware version management
- Firmware Manager GUI
"""

from .clearcore import (
    clear_firmware_config_cache,
    schedule_version_check,
    get_release_history,
    start_manual_update
)

from .manager import (
    open_firmware_manager
)

__all__ = [
    'clear_firmware_config_cache',
    'schedule_version_check',
    'get_release_history',
    'start_manual_update',
    'open_firmware_manager'
]

