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
    echo "Executable location: dist/BR Equipment Control.app"
    echo ""
    
    # Try to create DMG if create-dmg is available
    if command -v create-dmg &> /dev/null; then
        echo "Creating DMG..."
        create-dmg \
            --volname "BR Equipment Control" \
            --volicon "../assets/icon.png" \
            --window-pos 200 120 \
            --window-size 800 400 \
            --icon-size 100 \
            --icon "BR Equipment Control.app" 200 190 \
            --hide-extension "BR Equipment Control.app" \
            --app-drop-link 600 185 \
            "BR-Equipment-Control-macOS.dmg" \
            "BR Equipment Control.app"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "Done! Distributable DMG file created at:"
            echo "  dist/BR-Equipment-Control-macOS.dmg"
        else
            echo "DMG creation failed, creating zip instead..."
            zip -r "BR-Equipment-Control-macOS.zip" "BR Equipment Control.app"
            echo ""
            echo "Done! Distributable zip file created at:"
            echo "  dist/BR-Equipment-Control-macOS.zip"
        fi
    else
        echo "create-dmg not found, creating zip..."
        echo "Tip: Install with: brew install create-dmg"
        zip -r "BR-Equipment-Control-macOS.zip" "BR Equipment Control.app"
        echo ""
        echo "Done! Distributable zip file created at:"
        echo "  dist/BR-Equipment-Control-macOS.zip"
    fi
    
elif [[ "$OS" == "Linux" ]]; then
    echo "Executable location: dist/BR-Equipment-Control/BR-Equipment-Control"
    echo ""
    echo "Creating tarball..."
    tar -czf BR-Equipment-Control-Linux.tar.gz BR-Equipment-Control/
    echo ""
    echo "Done! Distributable tarball created at:"
    echo "  dist/BR-Equipment-Control-Linux.tar.gz"
fi

cd ..
echo ""

