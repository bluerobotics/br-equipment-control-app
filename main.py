#!/usr/bin/env python3
"""
BR Equipment Control App - Main Entry Point

This is the main entry point for the Equipment Control Application.
It initializes logging, sets up the window, and launches the main UI.
"""

import tkinter as tk
import platform
import ctypes
import os
import sys

# Add libs directory to path for bundled dependencies (e.g., pyserial)
# This allows the app to work on macOS/Linux when running from source
# Skip this when running as a PyInstaller bundle (sys.frozen is set)
if not getattr(sys, 'frozen', False):
    project_root = os.path.dirname(os.path.abspath(__file__))
    libs_path = os.path.join(project_root, "libs")
    if os.path.exists(libs_path) and libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from src import theme
from src.app import MainApplication


def main():
    """
    Initializes the main application window, creates the primary UI layout,
    and starts the communication threads.
    """
    # Check for command-line arguments (e.g., file association)
    startup_file = None
    if len(sys.argv) > 1:
        startup_file = sys.argv[1]
        if not os.path.exists(startup_file):
            print(f"[SYSTEM WARNING] File not found: {startup_file}")   
            startup_file = None
    
    # Initialize system logger first (before any print statements)
    try:
        from src.logging import initialize_system_logger
        system_logger = initialize_system_logger()
        print(f"[SYSTEM] Session log started: {system_logger.get_log_file_path()}")
    except Exception as e:
        print(f"[SYSTEM ERROR] Failed to initialize system logger: {e}")
        system_logger = None
    
    # --- Make the application DPI-aware on Windows ---
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Could not set DPI awareness: {e}")

    root = tk.Tk()
    
    theme.dark_title_bar(root) # Set dark title bar

    # --- Set Application Icon ---
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set the top-left window icon (uses .png)
        png_path = os.path.join(script_dir, 'assets', 'icon.png')
        if os.path.exists(png_path):
            img = tk.PhotoImage(file=png_path)
            root.tk.call('wm', 'iconphoto', root._w, img)
        else:
             print(f"Could not find icon.png at '{png_path}'.")

        # Set the taskbar icon (requires .ico on Windows)
        if platform.system() == "Windows":
            ico_path = os.path.join(script_dir, 'assets', 'icon.ico')
            if os.path.exists(ico_path):
                # This is the most reliable way to set the taskbar icon
                root.iconbitmap(ico_path)
                
                # Force Windows to associate the icon with the app
                myappid = u'tekbic.st8erboi.st8erboi-controller.1.0' 
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            else:
                print("NOTE: To set the taskbar icon on Windows, 'icon.ico' must exist in the assets folder.")

    except Exception as e:
        print(f"An error occurred while setting the icon: {e}")
        
    app = MainApplication(root, startup_file=startup_file)
    app.run()


if __name__ == "__main__":
    main()
