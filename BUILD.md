# Building Executables

This guide explains how to build standalone executables for Windows, macOS, and Linux.

## Quick Start

### Automated Builds (Recommended)

Executables are automatically built when you push a git tag:

```bash
git tag v1.8.0
git push origin v1.8.0
```

GitHub Actions will build executables for all three platforms and create a release with downloadable files.

---

## Manual Builds

### Prerequisites

1. **Install Python 3.10+**
2. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

### Windows

```bash
# Build the executable
pyinstaller build.spec

# The executable will be in: dist/br-equipment-control-app/
# To create a zip for distribution:
cd dist
powershell Compress-Archive -Path "br-equipment-control-app" -DestinationPath "br-equipment-control-app-windows.zip"
```

The Windows build will:
- Create a `.exe` file with no console window
- Include the icon from `assets/icon.ico`
- Bundle all dependencies in the `dist/br-equipment-control-app/` folder

**Distribution:** Share the entire `br-equipment-control-app` folder or the zip file. Users can run `br-equipment-control-app.exe` directly.

---

### macOS

```bash
# Build the app bundle
pyinstaller build.spec

# The app will be in: dist/br-equipment-control-app.app/
# To create a DMG (requires create-dmg):
brew install create-dmg
cd dist
create-dmg \
  --volname "br-equipment-control-app" \
  --volicon "../assets/icon.png" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "br-equipment-control-app.app" 200 190 \
  --hide-extension "br-equipment-control-app.app" \
  --app-drop-link 600 185 \
  "br-equipment-control-app-macos.dmg" \
  "br-equipment-control-app.app"
```

The macOS build will:
- Create a `.app` bundle
- Set app name and icon
- Use the proper Info.plist for macOS apps

**Distribution:** Share the `.dmg` file or zip the `.app` bundle. Users can drag it to their Applications folder.

---

### Linux

```bash
# Install tkinter if needed
sudo apt-get install python3-tk  # Ubuntu/Debian
# or
sudo yum install python3-tkinter  # RHEL/CentOS

# Build the executable
pyinstaller build.spec

# The executable will be in: dist/br-equipment-control-app/
# To create a tarball:
cd dist
tar -czf br-equipment-control-app-linux.tar.gz br-equipment-control-app/
```

The Linux build will:
- Create an executable binary
- Bundle all dependencies
- Include all device modules and assets

**Distribution:** Share the `.tar.gz` file. Users extract it and run `./br-equipment-control-app` from the terminal.

---

## Build Configuration

The build is controlled by `build.spec`. Key settings:

### Console Window
```python
console=False  # No console window (GUI only)
```

Set to `True` for debugging or to see print statements.

### Icon
```python
icon='assets/icon.ico'  # Windows
icon='assets/icon.png'   # macOS/Linux
```

### Including Files
The spec file automatically includes:
- All device modules from `devices/`
- Assets from `assets/`
- All Python source files

To add more files, edit the `datas` list in `build.spec`.

### Hidden Imports
If you add new device modules or dependencies, add them to `hiddenimports`:
```python
hiddenimports=[
    'devices.mydevice.gui',
    'devices.mydevice.script_handlers',
]
```

---

## Troubleshooting

### "Module not found" errors
Add the missing module to `hiddenimports` in `build.spec`.

### "Icon file not found"
Ensure `assets/icon.ico` (Windows) or `assets/icon.png` (macOS/Linux) exists.

### Large executable size
This is normal for PyInstaller. It bundles the Python interpreter and all dependencies. Typical sizes:
- Windows: 20-30 MB
- macOS: 30-40 MB  
- Linux: 25-35 MB

### macOS "App is damaged" warning
After downloading, users may need to run:
```bash
xattr -cr "/Applications/BR Equipment Control.app"
```

Or right-click the app and select "Open" the first time.

### Linux missing libraries
Users may need to install tkinter:
```bash
sudo apt-get install python3-tk
```

---

## Device Folder Configuration

The app prompts users to select a devices folder on first run. This allows:

- **Developers** can point to their git repo's `devices/` folder
- **End users** can maintain configs separately from the app
- **Device configs** remain editable even when using the executable

The choice is saved in `app_config.json` (created in the app's directory). To reset, delete this file.

### For Bundled Devices

The `build.spec` includes the devices folder in the executable bundle. However, users can:
1. Choose the bundled devices folder (inside the extracted directory)
2. Point to any other devices folder (like their git repo)
3. Create a new folder with their own device configs

This design solves the macOS .app bundle issue where files are hidden from users.

---

## Testing Builds

Always test builds on a clean machine (or VM) without Python installed to ensure all dependencies are bundled.

**Quick VM Testing:**
- Windows: Use Windows Sandbox
- macOS: Test on another Mac without dev tools
- Linux: Use a Docker container or fresh Ubuntu VM

**Test the devices folder prompt:**
1. Run the executable on a fresh machine
2. Verify the first-run prompt appears
3. Test selecting different folder locations
4. Verify `app_config.json` is created
5. Restart and verify it uses the saved path

---

## Updating Version Numbers

When releasing a new version:

1. **Update `_version.py`:**
   ```python
   __version__ = "1.8.0"
   ```

2. **Update `build.spec` (macOS section):**
   ```python
   'CFBundleShortVersionString': '1.8.0',
   'CFBundleVersion': '1.8.0',
   ```

3. **Tag the release:**
   ```bash
   git tag v1.8.0
   git push origin v1.8.0
   ```

GitHub Actions will automatically build and create a release.

---

## Advanced: Code Signing (Optional)

### Windows
Use `signtool.exe` after building:
```bash
signtool sign /f certificate.pfx /p password dist/BR-Equipment-Control/BR-Equipment-Control.exe
```

### macOS
```bash
codesign --force --sign "Developer ID Application: Your Name" "dist/BR Equipment Control.app"
```

Then notarize with Apple:
```bash
xcrun notarytool submit "BR-Equipment-Control-macOS.zip" --keychain-profile "notary-profile" --wait
xcrun stapler staple "dist/BR Equipment Control.app"
```

### Linux
Not typically required, but you can sign with GPG if desired.

---

## Distribution Checklist

Before releasing:
- [ ] Version number updated in `_version.py`
- [ ] Changelog updated with new features
- [ ] Tested build on clean machine
- [ ] All device modules included
- [ ] Icon displays correctly
- [ ] No console window appears (Windows/macOS)
- [ ] All assets load correctly
- [ ] Network discovery works
- [ ] File dialogs work

---

## GitHub Actions Setup

The `.github/workflows/build.yml` workflow automatically:
1. Builds on all three platforms
2. Creates archives (zip/dmg/tar.gz)
3. Uploads artifacts
4. Creates a GitHub Release with all files

To trigger manually: Go to Actions → Build Executables → Run workflow

To trigger on tag push:
```bash
git tag v1.8.0
git push origin v1.8.0
```

The workflow runs on:
- `windows-latest` (Windows Server 2022)
- `macos-latest` (macOS 13)
- `ubuntu-latest` (Ubuntu 22.04)

