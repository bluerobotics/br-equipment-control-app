#!/usr/bin/env python3
"""
Download all platform executables from the latest GitHub release.
Places them in the dist/ folder organized by platform.
"""

import os
import sys
import json
import urllib.request
import zipfile
import tarfile
from pathlib import Path

REPO_OWNER = "bluerobotics"
REPO_NAME = "br-equipment-control-app"
DIST_DIR = Path("dist")

def get_latest_release():
    """Get the latest release info from GitHub API."""
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    
    try:
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"Error fetching release info: {e}")
        sys.exit(1)

def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"Downloading {dest_path.name}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"  ✓ Downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error downloading: {e}")
        return False

def extract_archive(archive_path, extract_to):
    """Extract zip or tar.gz archive."""
    print(f"Extracting {archive_path.name}...")
    try:
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        elif archive_path.suffix == ".dmg":
            print(f"  ⓘ DMG file saved at {archive_path} (mount manually on macOS)")
            return True
        else:
            print(f"  ⓘ Unknown archive format: {archive_path.suffix}")
            return False
        
        print(f"  ✓ Extracted to {extract_to}")
        # Remove the archive after extraction
        archive_path.unlink()
        return True
    except Exception as e:
        print(f"  ✗ Error extracting: {e}")
        return False

def main():
    """Download and extract all platform builds from latest release."""
    print(f"Fetching latest release for {REPO_OWNER}/{REPO_NAME}...")
    
    release = get_latest_release()
    version = release['tag_name']
    print(f"\nLatest release: {version}")
    print(f"Published: {release['published_at']}")
    print(f"Release notes: {release['html_url']}\n")
    
    # Create dist directory if it doesn't exist
    DIST_DIR.mkdir(exist_ok=True)
    
    # Define platform directories
    platforms = {
        'windows': DIST_DIR / 'windows',
        'macos': DIST_DIR / 'macos',
        'linux': DIST_DIR / 'linux'
    }
    
    # Create platform subdirectories
    for platform_dir in platforms.values():
        platform_dir.mkdir(exist_ok=True)
    
    # Download and extract each asset
    assets = release.get('assets', [])
    if not assets:
        print("No assets found in release!")
        sys.exit(1)
    
    print(f"Found {len(assets)} assets:\n")
    
    for asset in assets:
        name = asset['name']
        download_url = asset['browser_download_url']
        
        # Determine platform and destination
        if 'windows' in name.lower():
            dest_dir = platforms['windows']
            platform_name = 'Windows'
        elif 'macos' in name.lower() or 'darwin' in name.lower():
            dest_dir = platforms['macos']
            platform_name = 'macOS'
        elif 'linux' in name.lower():
            dest_dir = platforms['linux']
            platform_name = 'Linux'
        else:
            print(f"Skipping unknown platform: {name}")
            continue
        
        print(f"[{platform_name}] {name}")
        dest_path = dest_dir / name
        
        if download_file(download_url, dest_path):
            # Extract if it's an archive (not DMG)
            if dest_path.suffix in ['.zip', '.gz'] or dest_path.name.endswith('.tar.gz'):
                extract_archive(dest_path, dest_dir)
        
        print()
    
    print("=" * 60)
    print("Download complete!")
    print("=" * 60)
    print(f"\nExecutables are in:")
    for platform, path in platforms.items():
        if path.exists() and any(path.iterdir()):
            print(f"  {platform.capitalize()}: {path}")
    print()

if __name__ == "__main__":
    main()

