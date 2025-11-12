import os
import json
import string
import shutil
import threading
import time
import tempfile
import urllib.request
from typing import Callable, Optional


# Configuration for ClearCore-based devices
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

CACHE_TTL_SECONDS = 15 * 60
RELEASE_CACHE = {}
RELEASE_LIST_CACHE = {}


def schedule_version_check(device_key, gui_refs, device_manager):
    """Queue a firmware version check on the UI thread for ClearCore devices."""
    if device_key not in CLEARCORE_DEVICE_CONFIG:
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

    config = CLEARCORE_DEVICE_CONFIG.get(device_key)
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
    asset_url = release_info['asset_url']
    success = False

    try:
        _log(gui_refs, f"[{device_key}] Downloading firmware {release_info['version']}...")
        _queue_status_callback(gui_refs, status_callback, f"Downloading {release_info['version']}...")
        temp_path = _download_asset(asset_url)
        if not temp_path:
            raise RuntimeError("Failed to download firmware asset")

        initial_drives = set(_list_available_drives())

        sender = device_manager.get_device_sender(device_key)
        sender(config['bootloader_command'])
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
        success = True

    except Exception as exc:
        _log(gui_refs, f"[{device_key}] Firmware update failed: {exc}")
        _queue_message(gui_refs, _show_error_message, (
            "Firmware Update Failed",
            str(exc)
        ))
        _queue_status_callback(gui_refs, status_callback, f"Update failed: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        update_state = {"fw_update_in_progress": False}
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
        import comms
        comms.log_to_terminal(message, gui_refs)
    except Exception:
        pass


def get_latest_release_info(device_key):
    """Public helper to fetch the latest firmware release info for a ClearCore device."""
    config = CLEARCORE_DEVICE_CONFIG.get(device_key)
    if not config:
        return None
    return _get_latest_release_info(device_key, config)


def compare_versions(current, latest):
    """Compare two semantic version strings. Returns 1 if current>latest, 0 if equal, -1 otherwise."""
    return _compare_versions(current, latest)


def get_release_history(device_key, limit=5, force_refresh=False):
    """Fetch a list of recent releases for the device, including changelog text."""
    config = CLEARCORE_DEVICE_CONFIG.get(device_key)
    if not config:
        return []
    return _get_release_history(device_key, config, per_page=limit, force_refresh=force_refresh)


def start_manual_update(device_key, gui_refs, device_manager, release_info=None, status_callback=None):
    """
    Starts a firmware update without going through the prompt flow.
    Returns the worker thread if the update was started successfully.
    """
    config = CLEARCORE_DEVICE_CONFIG.get(device_key)
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
    cached = RELEASE_LIST_CACHE.get(device_key)
    now = time.time()
    if not force_refresh and cached and (now - cached['fetched'] < CACHE_TTL_SECONDS):
        return cached['releases']

    api_url = f"https://api.github.com/repos/{config['repo']}/releases?per_page={per_page}"
    request = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return cached['releases'] if cached else []

    releases = []
    for entry in data:
        tag_name = entry.get('tag_name') or entry.get('name')
        if not tag_name:
            continue

        asset_url = None
        for asset in entry.get('assets', []):
            if asset.get('name') == config['asset_name']:
                asset_url = asset.get('browser_download_url')
                break

        if not asset_url:
            continue

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
