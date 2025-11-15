"""
@file theme.py
@author Gemini
@date September 12, 2025
@brief Centralized theme definitions for the Tkinter GUI.

This file contains all color and font definitions to ensure a consistent
look and feel across the entire application, inspired by the
Cursor/VS Code dark theme.
"""

# --- Base Colors (User-Specified Warmer Dark Theme) ---
BG_COLOR = "#141414"          # Main window background
WIDGET_BG = "#191919"         # Script editor and other widget backgrounds
CARD_BG = "#1E1E1E"           # A slightly lighter gray for cards to stand out
FG_COLOR = "#ABB2BF"          # A soft off-white for text
PRIMARY_ACCENT = "#61AFEF"    # A nice, clear blue for highlights
SECONDARY_ACCENT = "#3E4452"  # A medium gray for inactive elements
WIDGET_BORDER = "#181A1F"     # A very dark border for widgets

# --- Terminal Colors ---
TERMINAL_FG_COLOR = "#F0F0F0"   # A bright, clean white for terminal text

# --- Action Colors for Buttons ---
SUCCESS_GREEN = "#98C379"     # Green for "Run"
ERROR_RED = "#E06C75"         # Red for "Stop/Abort"
WARNING_YELLOW = "#E5C07B"    # Yellow/Orange for "Single Block"
BUSY_BLUE = "#56B6C2"         # A teal/cyan for "Busy/Moving" states

# --- NEW: Hover/Active Colors for Buttons ---
ACTIVE_GREEN = "#6E9454"   # Darker green for hover
PRESSED_GREEN = "#78A359"
ACTIVE_RED = "#F08090"     # Lighter red for hover (more visible)
PRESSED_RED = "#C04C55"
ACTIVE_BLUE = "#418BC7"    # Darker blue for hover
PRESSED_BLUE = "#4198D1"   # Even darker for pressed
ACTIVE_ORANGE = "#F0CD8C"
PRESSED_ORANGE = "#D9B26B"
PRESSED_GRAY = "#4A505E"
RUNNING_GREEN = "#4A6A34"  # A deeper green for when a script is running
HOLDING_RED = "#8B2B32"    # A deeper red for when a script is held
ACTIVE_HOLDING_RED = "#5D1D22" # Darker hover for the holding state
PRESSED_HOLDING_RED = "#692026" # Even darker pressed for the holding state

# --- Syntax Highlighting Colors ---
DEVICE_COLOR = "#C678DD"         # Purple/magenta for device namespace (before the dot)
COMMAND_COLOR = "#61AFEF"        # Blue for commands (after the dot)
PARAMETER_COLOR = "#E5C07B"      # Orange for parameters
COMMENT_COLOR = "#7F848E"        # A lighter grey for comments
SCRIPT_COMMAND_COLOR = "#56B6C2" # A teal/cyan for script-control commands (e.g., REPEAT, WAIT)
VARIABLE_COLOR = "#E89448"       # Orange for variables (device.variable format) - distinct from parameters

# --- Selection Colors ---
SELECTION_BG = "#4B6E9C"      # A subtle blue for selection, with good contrast.
SELECTION_FG = "#FFFFFF"      # Bright white for selected text

# --- Fonts ---
import platform
import ctypes

def dark_title_bar(window):
    """
    Sets the title bar to dark mode on Windows 10/11.
    """
    if platform.system() == "Windows":
        try:
            window.update()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(window.winfo_id())
            rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
            value = 2
            value = ctypes.c_int(value)
            set_window_attribute(hwnd, rendering_policy, ctypes.byref(value), ctypes.sizeof(value))
        except Exception as e:
            print(f"Failed to set dark title bar: {e}")

def _get_monospace_font():
    """Returns a monospace font appropriate for the platform (matches VS Code defaults)."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "Menlo"
    elif system == "Windows":
        return "Consolas"
    else:  # Linux and others
        # Try VS Code's preference first, then fallback
        return "Droid Sans Mono"  # VS Code default on Linux

MONOSPACE_FONT = _get_monospace_font()

# Base font sizes (will be scaled by UI scaling factor)
_BASE_FONT_SMALL = 9
_BASE_FONT_NORMAL = 11
_BASE_FONT_LARGE = 13

# Default fonts (these will be updated by set_font_scale)
FONT_SMALL = (MONOSPACE_FONT, 9)
FONT_NORMAL = (MONOSPACE_FONT, 11)
FONT_BOLD = (MONOSPACE_FONT, 11, "bold")
FONT_LARGE = (MONOSPACE_FONT, 13)
FONT_LARGE_BOLD = (MONOSPACE_FONT, 13, "bold")

def set_font_scale(scale_factor=1.0):
    """
    Update font sizes based on UI scale factor.
    Should be called when UI scaling changes.
    """
    global FONT_SMALL, FONT_NORMAL, FONT_BOLD, FONT_LARGE, FONT_LARGE_BOLD
    
    # Calculate scaled font sizes
    small_size = max(8, int(_BASE_FONT_SMALL * scale_factor))
    normal_size = max(9, int(_BASE_FONT_NORMAL * scale_factor))
    large_size = max(11, int(_BASE_FONT_LARGE * scale_factor))
    
    # Update font tuples
    FONT_SMALL = (MONOSPACE_FONT, small_size)
    FONT_NORMAL = (MONOSPACE_FONT, normal_size)
    FONT_BOLD = (MONOSPACE_FONT, normal_size, "bold")
    FONT_LARGE = (MONOSPACE_FONT, large_size)
    FONT_LARGE_BOLD = (MONOSPACE_FONT, large_size, "bold")
    
    return {
        'FONT_SMALL': FONT_SMALL,
        'FONT_NORMAL': FONT_NORMAL,
        'FONT_BOLD': FONT_BOLD,
        'FONT_LARGE': FONT_LARGE,
        'FONT_LARGE_BOLD': FONT_LARGE_BOLD
    }
