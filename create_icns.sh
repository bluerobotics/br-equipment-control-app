#!/bin/bash
# Script to convert icon.png to icon.icns for macOS
# Run this on macOS: bash create_icns.sh

echo "Converting icon.png to icon.icns for macOS..."

# Check if icon.png exists
if [ ! -f "assets/icon.png" ]; then
    echo "Error: assets/icon.png not found!"
    exit 1
fi

# Create iconset directory
mkdir -p assets/icon.iconset

# Generate all required icon sizes
sips -z 16 16     assets/icon.png --out assets/icon.iconset/icon_16x16.png
sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_16x16@2x.png
sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_32x32.png
sips -z 64 64     assets/icon.png --out assets/icon.iconset/icon_32x32@2x.png
sips -z 128 128   assets/icon.png --out assets/icon.iconset/icon_128x128.png
sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_128x128@2x.png
sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_256x256.png
sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_256x256@2x.png
sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_512x512.png
sips -z 1024 1024 assets/icon.png --out assets/icon.iconset/icon_512x512@2x.png

# Convert iconset to icns
iconutil -c icns assets/icon.iconset -o assets/icon.icns

# Clean up iconset directory
rm -rf assets/icon.iconset

echo "Done! Created assets/icon.icns"

