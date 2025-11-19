import os
import json
import string
import shutil
import threading
import time
import tempfile
import urllib.request
from typing import Callable, Optional


# Cache for dynamically loaded firmware configs
_FIRMWARE_CONFIG_CACHE = {}

CACHE_TTL_SECONDS = 15 * 60
RELEASE_CACHE = {}
RELEASE_LIST_CACHE = {}


def clear_firmware_config_cache(device_key=None):
    """
    Clear the firmware config cache for a specific device or all devices.
    
    Args:
        device_key: Device name/key to clear, or None to clear all
    """
    if device_key:
        _FIRMWARE_CONFIG_CACHE.pop(device_key, None)
    else:
        _FIRMWARE_CONFIG_CACHE.clear()


def _load_firmware_config(device_key, device_manager=None):
    """
    Load firmware configuration from device definition folder.
    Returns None if no config exists or if firmware_type is not 'clearcore'.
    
    Args:
        device_key: Device name/key
        device_manager: Optional DeviceManager instance to find device paths
    """
    # Check cache first, but always reload if device_manager is provided (in case paths changed)
    # If no device_manager, we can use cached value
    if device_key in _FIRMWARE_CONFIG_CACHE:
        if device_manager is None:
            # No device_manager provided, use cache
            return _FIRMWARE_CONFIG_CACHE[device_key]
        else:
            # device_manager provided - clear cache for this device to force reload
            # (paths might have changed)
            _FIRMWARE_CONFIG_CACHE.pop(device_key, None)
    
    # Try to find device definition folder
    config_path = None
    
    # First, try to get from device_manager if provided
    # Device paths are root folders (e.g., pressboi/), need to look for definition/ subfolder
    if device_manager:
        for device_root_path in device_manager.device_paths:
            # Normalize paths for comparison
            device_root_path = os.path.normpath(device_root_path)
            
            # Strategy 1: Check if folder name matches device_key, then look for config
            if os.path.basename(device_root_path).lower() == device_key.lower():
                # Try definition subfolder first
                potential_config = os.path.join(device_root_path, 'definition', 'config.json')
                if os.path.exists(potential_config):
                    config_path = potential_config
                    break
                # Try root folder
                potential_config = os.path.join(device_root_path, 'config.json')
                if os.path.exists(potential_config):
                    config_path = potential_config
                    break
            
            # Strategy 2: Check all config files and match by device_name
            # Check definition subfolder first
            definition_path = os.path.join(device_root_path, 'definition')
            test_config_path = os.path.join(definition_path, 'config.json')
            
            if not os.path.exists(test_config_path):
                # Fallback: check root folder (backward compatibility)
                test_config_path = os.path.join(device_root_path, 'config.json')
            
            if os.path.exists(test_config_path):
                try:
                    with open(test_config_path, 'r') as f:
                        test_config = json.load(f)
                        path_device_name = test_config.get('device_name') or test_config.get('name')
                        if path_device_name and path_device_name.lower() == device_key.lower():
                            config_path = test_config_path
                            break
                except Exception:
                    pass
    
    # Fallback: try old devices folder structure
    if not config_path:
        old_config_path = os.path.join(os.path.dirname(__file__), 'devices', device_key, 'firmware_config.json')
        if os.path.exists(old_config_path):
            config_path = old_config_path
    
    # Also try config.json in old structure
    if not config_path:
        old_config_path = os.path.join(os.path.dirname(__file__), 'devices', device_key, 'config.json')
        if os.path.exists(old_config_path):
            config_path = old_config_path
    
    if not config_path or not os.path.exists(config_path):
        if device_manager:
            # Log available paths for debugging
            print(f"[FIRMWARE] No config.json found for '{device_key}'. Searched in:")
            for device_root_path in device_manager.device_paths:
                print(f"  - {os.path.join(device_root_path, 'definition', 'config.json')}")
                print(f"  - {os.path.join(device_root_path, 'config.json')}")
        _FIRMWARE_CONFIG_CACHE[device_key] = None
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Only cache and return if this is a ClearCore device
        firmware_type = config.get('firmware_type')
        if firmware_type == 'clearcore':
            # Validate required fields
            required_fields = ['repo', 'asset_name', 'bootloader_command']
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                print(f"[FIRMWARE] Config for '{device_key}' is missing required fields: {missing_fields}")
                _FIRMWARE_CONFIG_CACHE[device_key] = None
                return None
            _FIRMWARE_CONFIG_CACHE[device_key] = config
            print(f"[FIRMWARE] Loaded firmware config for '{device_key}' from {config_path}")
            return config
        else:
            print(f"[FIRMWARE] Config for '{device_key}' has firmware_type='{firmware_type}', not 'clearcore'")
            _FIRMWARE_CONFIG_CACHE[device_key] = None
            return None
    except Exception as e:
        print(f"[FIRMWARE] Error loading config for {device_key} from {config_path}: {e}")
        import traceback
        traceback.print_exc()
        _FIRMWARE_CONFIG_CACHE[device_key] = None
        return None


def get_clearcore_device_config(device_key, device_manager=None):
    """Get ClearCore firmware configuration for a device. Returns None if not a ClearCore device."""
    return _load_firmware_config(device_key, device_manager)


def get_device_firmware_configs(device_manager=None):
    """
    Get all ClearCore firmware configurations. Returns a dict of {device_key: config}.
    
    Args:
        device_manager: Optional DeviceManager instance to find device paths
    """
    configs = {}
    
    # If device_manager is provided, use its device paths (root folders)
    if device_manager:
        for device_root_path in device_manager.device_paths:
            # Look for config.json in definition subfolder first
            definition_path = os.path.join(device_root_path, 'definition')
            config_path = os.path.join(definition_path, 'config.json')
            
            if not os.path.exists(config_path):
                # Fallback: check root folder (backward compatibility)
                config_path = os.path.join(device_root_path, 'config.json')
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Check if it's a ClearCore device
                    if config.get('firmware_type') == 'clearcore':
                        device_name = config.get('device_name') or config.get('name')
                        if device_name:
                            configs[device_name] = config
                except Exception:
                    pass
    
    # Fallback: try old devices folder structure
    devices_dir = os.path.join(os.path.dirname(__file__), "devices")
    if os.path.exists(devices_dir):
        for device_key in os.listdir(devices_dir):
            device_path = os.path.join(devices_dir, device_key)
            if os.path.isdir(device_path) and device_key not in configs:
                config = _load_firmware_config(device_key, device_manager)
                if config:
                    configs[device_key] = config
    
    return configs


def schedule_version_check(device_key, gui_refs, device_manager):
    """Queue a firmware version check on the UI thread for ClearCore devices."""
    config = _load_firmware_config(device_key, device_manager)
    if not config:
        device_manager.update_device_state(device_key, {"fw_check_scheduled": False})
        return

    gui_queue = gui_refs.get('gui_queue')
    if not gui_queue:
        # Clear the scheduled flag if we can't queue the task
        device_manager.update_device_state(device_key, {"fw_check_scheduled": False})
        return

    gui_queue.put((_check_on_ui_thread, (device_key, gui_refs, device_manager), {}))


def _check_on_ui_thread(device_key, gui_refs, device_manager):
    """Executed on the UI thread to prompt the user for available firmware updates."""
    device_manager.update_device_state(device_key, {"fw_check_scheduled": False})

    config = _load_firmware_config(device_key, device_manager)
    if not config:
        return

    state = device_manager.get_device_state(device_key)
    if not state or state.get('fw_update_in_progress'):
        return

    current_version = state.get('firmware_version')
    if not current_version:
        return

    release_info = _get_latest_release_info(device_key, config)
    if not release_info:
        return

    latest_version = release_info['version']
    if state.get('fw_prompt_version') == latest_version:
        return

    if _compare_versions(current_version, latest_version) >= 0:
        # Device is up to date
        device_manager.update_device_state(device_key, {"fw_prompt_version": latest_version})
        return

    from tkinter import messagebox

    product_name = config.get('label', device_key.capitalize())
    message = (
        f"{product_name} firmware {latest_version} is available (current: {current_version}).\n\n"
        "Would you like to download and install it now?"
    )

    if not messagebox.askyesno("Firmware Update Available", message):
        device_manager.update_device_state(device_key, {"fw_prompt_version": latest_version})
        return

    device_manager.update_device_state(device_key, {
        "fw_update_in_progress": True,
        "fw_prompt_version": latest_version
    })

    worker = threading.Thread(
        target=_perform_update_worker,
        args=(device_key, gui_refs, device_manager, config, release_info),
        daemon=True
    )
    worker.start()


def _queue_status_callback(gui_refs, callback, message):
    """Safely queue a status callback to run on the UI thread."""
    if not callback:
        return

    gui_queue = gui_refs.get('gui_queue')
    if gui_queue:
        gui_queue.put((callback, (message,), {}))
    else:
        try:
            callback(message)
        except Exception:
            pass


def _perform_update_worker(device_key, gui_refs, device_manager, config, release_info, status_callback: Optional[Callable[[str], None]] = None):
    """Runs in a background thread to download and flash firmware over USB."""
    temp_path = None
    asset_name = config['asset_name']
    success = False
    
    # Check if we're using a local file or downloading from URL
    local_file = release_info.get('local_file')

    try:
        if local_file:
            # Use local file directly
            _log(gui_refs, f"[{device_key}] Using local firmware file {release_info['version']}...")
            _queue_status_callback(gui_refs, status_callback, f"Preparing {release_info['version']}...")
            temp_path = local_file
        else:
            # Download from GitHub
            asset_url = release_info['asset_url']
            _log(gui_refs, f"[{device_key}] Downloading firmware {release_info['version']}...")
            _queue_status_callback(gui_refs, status_callback, f"Downloading {release_info['version']}...")
            temp_path = _download_asset(asset_url)
            if not temp_path:
                raise RuntimeError("Failed to download firmware asset")

        initial_drives = set(_list_available_drives())

        # Check if device might be in recovery mode - if so, send RESET first
        # Devices in recovery mode (red LED) may not respond to bootloader commands
        sender = device_manager.get_device_sender(device_key)
        
        # Attempt to clear any recovery/error state before flashing
        # This helps if the device is stuck in watchdog recovery mode
        try:
            _log(gui_refs, f"[{device_key}] Clearing any error/recovery states before firmware update...")
            _queue_status_callback(gui_refs, status_callback, "Clearing error states...")
            sender("reset")
            time.sleep(1.0)  # Give device time to process reset and clear recovery state
        except Exception as e:
            _log(gui_refs, f"[{device_key}] Note: Could not send reset command (device may already be in bootloader): {e}")

        # Send reboot command to enter bootloader
        _log(gui_refs, f"[{device_key}] Sending bootloader command: {config['bootloader_command']}")
        _queue_status_callback(gui_refs, status_callback, "Entering bootloader mode...")
        sender(config['bootloader_command'])
        
        # Give the device a moment to process the command before closing connection
        time.sleep(0.2)
        
        # Close serial connection if device is using USB
        device_state = device_manager.get_device_state(device_key)
        if device_state and device_state.get('connection_method') == 'usb':
            serial_port = device_state.get('serial_port')
            if serial_port:
                from . import serial_comms
                _log(gui_refs, f"[{device_key}] Closing serial connection on {serial_port}...")
                serial_comms.disconnect_serial_device(serial_port)
                time.sleep(0.5)  # Give time for device to reboot and port to close

        _log(gui_refs, f"[{device_key}] Waiting for bootloader to appear...")
        _queue_status_callback(gui_refs, status_callback, "Waiting for bootloader...")

        boot_drive = _wait_for_bootloader_drive(initial_drives, config.get('volume_label'))
        if not boot_drive:
            raise RuntimeError("Timed out waiting for ClearCore bootloader drive")

        _log(gui_refs, f"[{device_key}] Copying {asset_name} to {boot_drive}")
        _queue_status_callback(gui_refs, status_callback, f"Copying {asset_name} to device...")
        dest_path = os.path.join(boot_drive, asset_name)
        shutil.copyfile(temp_path, dest_path)
        _log(gui_refs, f"[{device_key}] Firmware copied. Waiting for reboot...")
        _queue_status_callback(gui_refs, status_callback, "Waiting for device to reboot...")

        _wait_for_drive_removal(boot_drive)

        _queue_message(gui_refs, _show_info_message, (
            "Firmware Update Complete",
            f"{config.get('label', device_key.capitalize())} firmware installed. Device will reconnect shortly."
        ))
        _queue_status_callback(gui_refs, status_callback, "Firmware update complete. Waiting for reconnection...")
        
        # Reconnect USB serial if device was using USB before flashing
        if device_state and device_state.get('connection_method') == 'usb' and serial_port:
            _log(gui_refs, f"[{device_key}] Reconnecting USB serial on {serial_port}...")
            time.sleep(2.0)  # Give device time to fully reboot
            
            try:
                from . import serial_comms
                from . import comms
                success_reconnect = serial_comms.connect_serial_device(
                    serial_port,
                    device_key,
                    comms.handle_serial_message,
                    gui_refs,
                    device_manager
                )
                if success_reconnect:
                    _log(gui_refs, f"[{device_key}] USB serial reconnected successfully")
                else:
                    _log(gui_refs, f"[{device_key}] Failed to reconnect USB serial")
            except Exception as e:
                _log(gui_refs, f"[{device_key}] Error reconnecting USB: {e}")
        
        success = True

    except Exception as exc:
        _log(gui_refs, f"[{device_key}] Firmware update failed: {exc}")
        _queue_message(gui_refs, _show_error_message, (
            "Firmware Update Failed",
            str(exc)
        ))
        _queue_status_callback(gui_refs, status_callback, f"Update failed: {exc}")
    finally:
        # Only delete temp file if it was downloaded (not a local file)
        if temp_path and not local_file and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        update_state = {
            "fw_update_in_progress": False,
            "fw_update_cooldown": time.time() + 10  # 10 second cooldown to prevent hotplug spam
        }
        if not success:
            update_state['fw_prompt_version'] = None
        device_manager.update_device_state(device_key, update_state)
        if success:
            _queue_status_callback(gui_refs, status_callback, "Firmware update complete.")


def _get_latest_release_info(device_key, config):
    """Fetch release info from GitHub, caching for a short period."""
    cached = RELEASE_CACHE.get(device_key)
    now = time.time()
    if cached and (now - cached['fetched'] < CACHE_TTL_SECONDS):
        return cached

    releases = _get_release_history(device_key, config, per_page=1)
    if not releases:
        return None

    info = releases[0].copy()
    info['fetched'] = now
    RELEASE_CACHE[device_key] = info
    return info


def _normalize_version(version_str):
    if not version_str:
        return "0.0.0"
    version_str = version_str.strip()
    if version_str.lower().startswith('v'):
        version_str = version_str[1:]
    return version_str


def _compare_versions(current, latest):
    cur = _version_tuple(current)
    lat = _version_tuple(latest)
    if cur == lat:
        return 0
    return 1 if cur > lat else -1


def _version_tuple(version_str):
    clean = _normalize_version(version_str)
    parts = []
    for token in clean.split('.'):
        try:
            parts.append(int(''.join(ch for ch in token if ch.isdigit())))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _download_asset(url):
    temp_fd, temp_path = tempfile.mkstemp(suffix=".uf2")
    os.close(temp_fd)

    with urllib.request.urlopen(url, timeout=30) as response, open(temp_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

    return temp_path


def _list_available_drives():
    drives = []
    if os.name == 'nt':
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if os.path.exists(path):
                drives.append(path)
    else:
        for mount_root in ('/media', '/mnt', '/Volumes'):
            if os.path.isdir(mount_root):
                for entry in os.listdir(mount_root):
                    drives.append(os.path.join(mount_root, entry))
    return drives


def _wait_for_bootloader_drive(initial_drives, volume_label, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for drive in _list_available_drives():
            if drive in initial_drives:
                continue
            if _is_clearcore_drive(drive, volume_label):
                return drive
        time.sleep(1.0)
    return None


def _is_clearcore_drive(drive, volume_label):
    info_path = os.path.join(drive, "INFO_UF2.TXT")
    if os.path.isfile(info_path):
        try:
            with open(info_path, 'r', encoding='utf-8', errors='ignore') as info_file:
                content = info_file.read()
            if 'ClearCore' in content or 'UF2' in content:
                return True
        except OSError:
            pass

    if volume_label and os.name == 'nt':
        # On Windows, attempt to check the volume label via os.statvfs is not available.
        # As a fallback, compare uppercase path ending with volume label.
        if drive.rstrip('\\/').upper().endswith(volume_label.upper()):
            return True

    return False


def _wait_for_drive_removal(drive, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not os.path.exists(drive):
            return True
        time.sleep(1.0)
    return False


def _queue_message(gui_refs, func, args):
    gui_queue = gui_refs.get('gui_queue')
    if gui_queue:
        gui_queue.put((func, args, {}))


def _show_info_message(title, message):
    from tkinter import messagebox
    messagebox.showinfo(title, message)


def _show_error_message(title, message):
    from tkinter import messagebox
    messagebox.showerror(title, message)


def _log(gui_refs, message):
    try:
        from . import comms
        comms.log_to_terminal(message, gui_refs)
    except Exception:
        pass


def get_latest_release_info(device_key, device_manager=None):
    """Public helper to fetch the latest firmware release info for a ClearCore device."""
    config = _load_firmware_config(device_key, device_manager)
    if not config:
        return None
    return _get_latest_release_info(device_key, config)


def compare_versions(current, latest):
    """Compare two semantic version strings. Returns 1 if current>latest, 0 if equal, -1 otherwise."""
    return _compare_versions(current, latest)


def get_release_history(device_key, limit=5, force_refresh=False, device_manager=None):
    """Fetch a list of recent releases for the device, including changelog text."""
    import sys
    print(f"[FW DEBUG] get_release_history: loading config for {device_key}", file=sys.stderr, flush=True)
    config = _load_firmware_config(device_key, device_manager)
    if not config:
        print(f"[FW DEBUG] get_release_history: NO CONFIG FOUND for {device_key}!", file=sys.stderr, flush=True)
        return []
    print(f"[FW DEBUG] get_release_history: config loaded, calling _get_release_history", file=sys.stderr, flush=True)
    return _get_release_history(device_key, config, per_page=limit, force_refresh=force_refresh)


def start_manual_update(device_key, gui_refs, device_manager, release_info=None, status_callback=None):
    """
    Starts a firmware update without going through the prompt flow.
    Returns the worker thread if the update was started successfully.
    """
    config = _load_firmware_config(device_key, device_manager)
    if not config:
        raise ValueError(f"No ClearCore firmware configuration found for '{device_key}'.")

    if not device_manager:
        raise ValueError("Device manager is required to start a firmware update.")

    state = device_manager.get_device_state(device_key)
    if not state:
        raise ValueError(f"No device state available for '{device_key}'.")

    if not state.get('connected'):
        raise RuntimeError(f"{config.get('label', device_key.capitalize())} is not connected.")

    if state.get('fw_update_in_progress'):
        raise RuntimeError("A firmware update is already in progress for this device.")

    if release_info is None:
        release_info = _get_latest_release_info(device_key, config)
        if not release_info:
            raise RuntimeError("Unable to retrieve firmware release information.")

    device_manager.update_device_state(device_key, {
        "fw_update_in_progress": True,
        "fw_prompt_version": release_info['version']
    })

    worker = threading.Thread(
        target=_perform_update_worker,
        args=(device_key, gui_refs, device_manager, config, release_info),
        kwargs={"status_callback": status_callback},
        daemon=True
    )
    worker.start()
    return worker


def _get_release_history(device_key, config, per_page=5, force_refresh=False):
    import sys
    print(f"[FW DEBUG] _get_release_history called for {device_key}, repo={config['repo']}, asset_name={config['asset_name']}", file=sys.stderr, flush=True)
    cached = RELEASE_LIST_CACHE.get(device_key)
    now = time.time()
    if not force_refresh and cached and (now - cached['fetched'] < CACHE_TTL_SECONDS):
        print(f"[FW DEBUG] Using cached releases for {device_key}", file=sys.stderr, flush=True)
        return cached['releases']

    api_url = f"https://api.github.com/repos/{config['repo']}/releases?per_page={per_page}"
    print(f"[FW DEBUG] Fetching from GitHub API: {api_url}", file=sys.stderr, flush=True)
    request = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[FW DEBUG] GitHub API returned {len(data)} releases", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[FW DEBUG] GitHub API error: {e}", file=sys.stderr, flush=True)
        return cached['releases'] if cached else []

    releases = []
    import sys
    for entry in data:
        tag_name = entry.get('tag_name') or entry.get('name')
        if not tag_name:
            continue

        asset_url = None
        assets_found = [a.get('name') for a in entry.get('assets', [])]
        print(f"[FW DEBUG] Release {tag_name}: looking for '{config['asset_name']}', found assets: {assets_found}", file=sys.stderr, flush=True)
        
        for asset in entry.get('assets', []):
            if asset.get('name') == config['asset_name']:
                asset_url = asset.get('browser_download_url')
                break

        if not asset_url:
            print(f"[FW DEBUG] Release {tag_name}: No matching asset found, skipping", file=sys.stderr, flush=True)
            continue
        
        print(f"[FW DEBUG] Release {tag_name}: Found matching asset at {asset_url}", file=sys.stderr, flush=True)

        releases.append({
            "version": _normalize_version(tag_name),
            "raw_version": tag_name,
            "asset_url": asset_url,
            "body": entry.get('body', '') or '',
            "published_at": entry.get('published_at'),
            "html_url": entry.get('html_url')
        })

    RELEASE_LIST_CACHE[device_key] = {
        "fetched": now,
        "releases": releases
    }
    return releases
