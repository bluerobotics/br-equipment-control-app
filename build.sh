#!/bin/bash
# Build script for macOS and Linux

echo "Building BR Equipment Control App..."
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    echo "Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller is not installed."
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
    echo ""
fi

# Build the executable
echo "Running PyInstaller..."
pyinstaller build.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Build failed! Check the error messages above."
    exit 1
fi

echo ""
echo "Build complete!"

# Create distribution archives
cd dist

if [[ "$OS" == "macOS" ]]; then
    echo "Executable location: dist/br-equipment-control-app.app"
    echo ""
    
    # Try to create DMG if create-dmg is available
    if command -v create-dmg &> /dev/null; then
        echo "Creating DMG..."
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
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "Done! Distributable DMG file created at:"
            echo "  dist/br-equipment-control-app-macos.dmg"
        else
            echo "DMG creation failed, creating zip instead..."
            zip -r "br-equipment-control-app-macos.zip" "br-equipment-control-app.app"
            echo ""
            echo "Done! Distributable zip file created at:"
            echo "  dist/br-equipment-control-app-macos.zip"
        fi
    else
        echo "create-dmg not found, creating zip..."
        echo "Tip: Install with: brew install create-dmg"
        zip -r "br-equipment-control-app-macos.zip" "br-equipment-control-app.app"
        echo ""
        echo "Done! Distributable zip file created at:"
        echo "  dist/br-equipment-control-app-macos.zip"
    fi
    
elif [[ "$OS" == "Linux" ]]; then
    echo "Executable location: dist/br-equipment-control-app/br-equipment-control-app"
    echo ""
    echo "Creating tarball..."
    tar -czf br-equipment-control-app-linux.tar.gz br-equipment-control-app/
    echo ""
    echo "Done! Distributable tarball created at:"
        echo "  dist/br-equipment-control-app-linux.tar.gz"
fi

cd ..
echo ""

