# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for BR Equipment Control App

import sys
from pathlib import Path

block_cipher = None

# Collect all device modules and their JSON files
device_datas = []
devices_path = Path('devices')
if devices_path.exists():
    for device_dir in devices_path.iterdir():
        if device_dir.is_dir() and not device_dir.name.startswith('__'):
            # Add all files from device directory
            device_datas.append((str(device_dir), str(Path('devices') / device_dir.name)))

# Collect assets
asset_datas = [
    ('assets', 'assets'),
]

# All Python files that need to be included
python_files = [
    'main.py',
    'comms.py',
    'device_manager.py',
    'device_actions.py',
    'data_logger.py',
    'script_processor.py',
    'script_validator.py',
    'scripting_gui.py',
    'status_panel.py',
    'terminal.py',
    'theme.py',
    'top_menu.py',
    'command_reference.py',
    'code_generator.py',
    '_version.py',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=device_datas + asset_datas,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.font',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        # Device modules
        'devices.fillhead.gui',
        'devices.fillhead.script_handlers',
        'devices.gantry.gui',
        'devices.gantry.script_handlers',
        'devices.pressboi.gui',
        'devices.pressboi.script_handlers',
        'devices.pressurizer.gui',
        'devices.pressurizer.script_handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BR-Equipment-Control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if sys.platform == 'win32' else 'assets/icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BR-Equipment-Control',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BR Equipment Control.app',
        icon='assets/icon.png',
        bundle_identifier='com.bluerobotics.equipment-control',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.3.0',
            'CFBundleVersion': '1.3.0',
        },
    )

