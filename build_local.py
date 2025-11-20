#!/usr/bin/env python3
"""
Build executable for current platform using PyInstaller.
Organizes output in dist/windows, dist/macos, or dist/linux.
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def get_platform_name():
    """Determine the current platform."""
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    else:
        print(f"Unknown platform: {system}")
        sys.exit(1)

def clean_dist():
    """Remove old dist and build folders."""
    print("Cleaning old build artifacts...")
    if Path('dist').exists():
        shutil.rmtree('dist', ignore_errors=True)
    if Path('build').exists():
        shutil.rmtree('build', ignore_errors=True)
    print("  [OK] Cleaned\n")

def get_python_executable():
    """Get the best Python executable for building (prefer Homebrew Python 3.13+ on macOS)."""
    if platform.system() == 'Darwin':  # macOS
        # Try to find Homebrew Python 3.13+ (has modern Tk/Tcl)
        homebrew_pythons = [
            '/opt/homebrew/bin/python3.13',
            '/opt/homebrew/bin/python3',
            '/usr/local/bin/python3.13',
            '/usr/local/bin/python3',
        ]
        for python_path in homebrew_pythons:
            if Path(python_path).exists():
                # Verify it has PyInstaller
                try:
                    result = subprocess.run(
                        [python_path, '-m', 'PyInstaller', '--version'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"  Using: {python_path}")
                        return python_path
                except:
                    pass
        
        print(f"  Warning: Using system Python {sys.executable}")
        print(f"  Recommend: brew install python@3.13 && pip3.13 install pyinstaller")
    
    return sys.executable

def build_executable():
    """Run PyInstaller to build the executable."""
    print("Building executable with PyInstaller...")
    print("This may take a few minutes...\n")
    
    python_exe = get_python_executable()
    
    try:
        result = subprocess.run(
            [python_exe, '-m', 'PyInstaller', '--clean', 'build.spec'],
            check=True,
            capture_output=False
        )
        print("\n  [OK] Build successful\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  [ERROR] Build failed with exit code {e.returncode}\n")
        return False
    except FileNotFoundError:
        print("\n  [ERROR] PyInstaller not found. Install it with: pip install pyinstaller\n")
        return False

def organize_output():
    """Move the built executable to the appropriate platform subfolder."""
    platform_name = get_platform_name()
    
    # Create platform-specific directory
    platform_dir = Path(f'dist/{platform_name}')
    
    print(f"Organizing build for {platform_name}...")
    
    # Clean up old platform directory
    if platform_dir.exists():
        try:
            shutil.rmtree(platform_dir)
        except PermissionError:
            print(f"  [WARNING] Could not delete old build (files in use). Trying to rename...")
            # If we can't delete, try to rename the old build
            import time
            temp_dir = Path(f'dist/{platform_name}.old.{int(time.time())}')
            try:
                platform_dir.rename(temp_dir)
                print(f"  [OK] Moved old build to {temp_dir.name}")
            except:
                print(f"  [ERROR] Could not move old build. Please close any running instances and try again.")
                return False
    platform_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle macOS .app bundle differently
    if platform_name == 'macos':
        # On macOS, PyInstaller creates a .app bundle
        source_app = Path('dist/br-equipment-control-app.app')
        if source_app.exists():
            # Move the .app bundle to the platform directory
            shutil.move(str(source_app), str(platform_dir / 'br-equipment-control-app.app'))
            print(f"  [OK] Organized to dist/{platform_name}/br-equipment-control-app.app\n")
            
            # Clean up the COLLECT output directory if it exists (not needed on macOS)
            collect_dir = Path('dist/br-equipment-control-app')
            if collect_dir.exists():
                shutil.rmtree(collect_dir)
            
            return True
        else:
            print(f"  [ERROR] macOS app bundle not found at {source_app}")
            return False
    else:
        # For Windows/Linux, use the COLLECT directory
        source_dir = Path('dist/br-equipment-control-app')
        if not source_dir.exists():
            print(f"  [ERROR] Build output not found at {source_dir}")
            return False
        
        # Move the entire build to platform directory
        shutil.move(str(source_dir), str(platform_dir / 'br-equipment-control-app'))
        
        print(f"  [OK] Organized to dist/{platform_name}/br-equipment-control-app/\n")
        return True

def create_placeholder_dirs():
    """Create placeholder directories for other platforms."""
    platform_name = get_platform_name()
    all_platforms = ['windows', 'macos', 'linux']
    
    print("Creating placeholder directories for other platforms...")
    for p in all_platforms:
        if p != platform_name:
            placeholder_dir = Path(f'dist/{p}')
            placeholder_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a README in the placeholder
            readme_path = placeholder_dir / 'README.txt'
            readme_path.write_text(
                f"This folder is for {p.capitalize()} builds.\n"
                f"To build for {p.capitalize()}, run this script on a {p.capitalize()} machine.\n"
                f"\nCurrent build is for {platform_name.capitalize()}.\n"
            )
    print(f"  [OK] Created placeholders\n")

def print_summary():
    """Print a summary of what was built."""
    platform_name = get_platform_name()
    
    print("=" * 60)
    print("Build Complete!")
    print("=" * 60)
    
    if platform_name == 'windows':
        exe_path = Path(f'dist/{platform_name}/br-equipment-control-app/br-equipment-control-app.exe')
        print(f"\nWindows executable: {exe_path}")
    elif platform_name == 'macos':
        app_path = Path(f'dist/{platform_name}/br-equipment-control-app.app')
        print(f"\nmacOS app bundle: {app_path}")
    elif platform_name == 'linux':
        exe_path = Path(f'dist/{platform_name}/br-equipment-control-app/br-equipment-control-app')
        print(f"\nLinux executable: {exe_path}")
    
    print(f"\nFull distribution folder structure:")
    print(f"  dist/")
    print(f"    windows/  {'<-- Current build' if platform_name == 'windows' else '(build on Windows)'}")
    print(f"    macos/    {'<-- Current build' if platform_name == 'macos' else '(build on macOS)'}")
    print(f"    linux/    {'<-- Current build' if platform_name == 'linux' else '(build on Linux)'}")
    print()
    print("Note: PyInstaller can only build for the platform it's running on.")
    print("To build for other platforms, run this script on those platforms.")
    print()

def main():
    """Main build process."""
    print("=" * 60)
    print("BR Equipment Control App - Local Build")
    print("=" * 60)
    print()
    
    platform_name = get_platform_name()
    print(f"Building for: {platform_name.capitalize()}\n")
    
    # Check if build.spec exists
    if not Path('build.spec').exists():
        print("  [ERROR] build.spec not found!")
        print("    Make sure you're running this from the project root.")
        sys.exit(1)
    
    # Clean old builds
    clean_dist()
    
    # Build
    if not build_executable():
        sys.exit(1)
    
    # Organize output
    if not organize_output():
        sys.exit(1)
    
    # Create placeholder directories
    create_placeholder_dirs()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()

