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

# --- Action Colors for Buttons ---
SUCCESS_GREEN = "#98C379"     # Green for "Run"
ERROR_RED = "#E06C75"         # Red for "Stop/Abort"
WARNING_YELLOW = "#E5C07B"    # Yellow/Orange for "Single Block"
BUSY_BLUE = "#56B6C2"         # A teal/cyan for "Busy/Moving" states

# --- NEW: Hover/Active Colors for Buttons ---
ACTIVE_GREEN = "#6E9454"   # Darker green for hover
PRESSED_GREEN = "#78A359"
ACTIVE_RED = "#A84B52"     # Darker red for hover
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
COMMAND_COLOR = "#61AFEF"     # Blue for commands
PARAMETER_COLOR = "#E5C07B"   # Orange for parameters
COMMENT_COLOR = "#7F848E"     # A lighter grey for comments
SCRIPT_COMMAND_COLOR = "#56B6C2" # A teal/cyan for script-control commands (e.g., REPEAT, WAIT)

# --- Selection Colors ---
SELECTION_BG = "#4B6E9C"      # A subtle blue for selection, with good contrast.
SELECTION_FG = "#FFFFFF"      # Bright white for selected text

# --- Fonts ---
FONT_NORMAL = ("JetBrains Mono", 10)
FONT_BOLD = ("JetBrains Mono", 10, "bold")
FONT_LARGE = ("JetBrains Mono", 12)
FONT_LARGE_BOLD = ("JetBrains Mono", 12, "bold")
