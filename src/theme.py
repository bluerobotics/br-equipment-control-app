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

# Font options available to the user
AVAILABLE_FONTS = [
    ("Consolas", "Consolas"),  # Windows default (clean, professional)
    ("SF Mono", "SF Mono"),     # macOS system font
    ("Menlo", "Menlo"),         # macOS traditional
    ("Cascadia Code", "Cascadia Code"),  # Modern Microsoft font
    ("Monaco", "Monaco"),       # macOS classic
    ("Courier New", "Courier New"),  # Cross-platform fallback
]

def _get_default_monospace_font():
    """
    Returns the default monospace font (Cascadia Code for consistency).
    """
    # Use Cascadia Code by default for all platforms for consistent look
    return "Cascadia Code"

def _get_monospace_font():
    """
    Returns the currently configured monospace font.
    Checks user preference first, then falls back to platform default.
    """
    # Check if user has set a font preference
    try:
        from .config import get_font_family
        user_font = get_font_family()
        if user_font:
            return user_font
    except:
        pass
    
    return _get_default_monospace_font()

MONOSPACE_FONT = _get_monospace_font()

# Initialize font size from config on startup
try:
    from .config import get_font_size
    _FONT_SIZE = get_font_size()
    set_font_size(_FONT_SIZE)  # Apply the saved size
except:
    pass  # Use default if config not available

def get_available_fonts():
    """Returns list of (display_name, font_family) tuples for font selection."""
    return AVAILABLE_FONTS

def set_monospace_font(font_family):
    """
    Sets the monospace font for the application.
    Updates the global variable and saves to config.
    """
    global MONOSPACE_FONT
    MONOSPACE_FONT = font_family
    
    # Save to config
    try:
        from .config import set_font_family
        set_font_family(font_family)
    except Exception as e:
        print(f"Error saving font preference: {e}")

# Base font size (user-configurable, independent of UI scaling)
_FONT_SIZE = 11  # Default font size in points

# Default fonts (these will be updated by set_font_size)
FONT_SMALL = (MONOSPACE_FONT, 9)
FONT_NORMAL = (MONOSPACE_FONT, 11)
FONT_BOLD = (MONOSPACE_FONT, 11, "bold")
FONT_LARGE = (MONOSPACE_FONT, 13)
FONT_LARGE_BOLD = (MONOSPACE_FONT, 13, "bold")

def get_font_size():
    """Get the current base font size."""
    return _FONT_SIZE

def set_font_size(size):
    """
    Update font sizes based on user's font size preference.
    Independent of UI scaling.
    """
    global _FONT_SIZE, FONT_SMALL, FONT_NORMAL, FONT_BOLD, FONT_LARGE, FONT_LARGE_BOLD
    
    _FONT_SIZE = size
    
    # Calculate related sizes (small is -2, large is +2)
    small_size = max(8, size - 2)
    normal_size = size
    large_size = size + 2
    
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
