# Distribution Quick Start

## For End Users (No Python Required!)

Download the pre-built executable for your platform from the [Releases page](https://github.com/bluerobotics/br-equipment-control-app/releases):

### Windows
1. Download `BR-Equipment-Control-Windows.zip`
2. Extract the zip file
3. Run `BR-Equipment-Control.exe`
4. On first run, you'll be prompted to select your `devices` folder location
   - **For development:** Point to your local git repo's devices folder
   - **For general use:** Use the bundled devices folder in the extracted directory

### macOS
1. Download `BR-Equipment-Control-macOS.dmg`
2. Open the DMG file
3. Drag `BR Equipment Control.app` to your Applications folder
4. If you get a security warning, right-click the app and select "Open"
5. On first run, you'll be prompted to select your `devices` folder location
   - **For development:** Point to your local git repo's devices folder
   - **For general use:** Create/select a folder with your device configs

### Linux
1. Download `BR-Equipment-Control-Linux.tar.gz`
2. Extract: `tar -xzf BR-Equipment-Control-Linux.tar.gz`
3. Run: `cd BR-Equipment-Control && ./BR-Equipment-Control`
4. If you get a "tkinter not found" error, install it:
   - Ubuntu/Debian: `sudo apt-get install python3-tk`
   - Fedora/RHEL: `sudo dnf install python3-tkinter`
5. On first run, you'll be prompted to select your `devices` folder location
   - **For development:** Point to your local git repo's devices folder
   - **For general use:** Use the bundled devices folder in the extracted directory

### About the Devices Folder

The app prompts you to choose where device configurations are stored. This design allows:

- **Developers:** Point to your git repo's `devices/` folder to edit configs directly while using the executable
- **Users:** Choose any folder with device configurations, keeping configs separate from the app
- **Flexibility:** Easily switch between different device configuration sets

Your choice is saved in `app_config.json` (next to the executable). To change it later, delete this file and restart the app.

---

## For Developers

### Quick Build

**Windows:**
```bash
build.bat
```

**macOS/Linux:**
```bash
chmod +x build.sh
./build.sh
```

### Automated Release Process

1. Update version in `_version.py` and `build.spec`
2. Commit changes: `git commit -am "Bump version to v1.3.1"`
3. Create and push tag: `git tag v1.3.1 && git push origin v1.3.1`
4. GitHub Actions automatically builds for all platforms
5. Check the [Actions tab](https://github.com/bluerobotics/br-equipment-control-app/actions) for build status
6. Release appears automatically with all executables

### Manual Build (if needed)

See [BUILD.md](BUILD.md) for detailed build instructions.

---

## What's Included

All executables include:
- ✅ Full GUI application
- ✅ All device modules (fillhead, gantry, pressboi, pressurizer)
- ✅ Script editor with syntax highlighting
- ✅ Data logging
- ✅ Device simulator
- ✅ All assets and icons
- ✅ No Python installation required!

---

## Troubleshooting

### Windows: "Windows protected your PC" warning
Click "More info" → "Run anyway". This is because the app is not code-signed.

### macOS: "App is damaged" or "from unidentified developer"
Right-click the app → Select "Open" → Click "Open" in the dialog.

Or run in Terminal:
```bash
xattr -cr "/Applications/BR Equipment Control.app"
```

### Linux: "Permission denied"
Make it executable:
```bash
chmod +x BR-Equipment-Control
```

### Linux: "tkinter not found"
Install tkinter:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL  
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

---

## File Sizes (Approximate)

- Windows: 20-30 MB (zip)
- macOS: 30-40 MB (dmg)
- Linux: 25-35 MB (tar.gz)

These sizes are normal for PyInstaller - it bundles the entire Python interpreter.

---

## Need Help?

- 📖 [User Guide](README.md)
- 🔧 [Build Instructions](BUILD.md)
- 📋 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/bluerobotics/br-equipment-control-app/issues)

