/**
 * @file commands.h
 * @brief Defines the command interface for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-12 10:48:49
 * 
 * This header file defines all commands that can be sent TO the Gantry device.
 * For message prefixes and events, see events.h
 * To modify commands, edit commands.json and regenerate this file.
 */
#pragma once

//==================================================================================================
// Command Strings (Host → Device)
//==================================================================================================

/**
 * @name General System Commands
 * @{
 */
#define CMD_STR_DISCOVER_DEVICE                     "DISCOVER_DEVICE" ///< Generic command for any device to respond to.
#define CMD_STR_ENABLE                              "enable" ///< No description available.
#define CMD_STR_DISABLE                             "disable" ///< No description available.
/** @} */

/**
 * @name Motion Commands
 * @{
 */
#define CMD_STR_HOME_X                              "home_x" ///< No description available.
#define CMD_STR_HOME_Y                              "home_y" ///< No description available.
#define CMD_STR_HOME_Z                              "home_z" ///< No description available.
#define CMD_STR_MOVE_ABS_X                          "move_abs_x " ///< No description available.
#define CMD_STR_MOVE_ABS_Y                          "move_abs_y " ///< No description available.
#define CMD_STR_MOVE_ABS_Z                          "move_abs_z " ///< No description available.
#define CMD_STR_MOVE_INC_X                          "move_inc_x " ///< No description available.
#define CMD_STR_MOVE_INC_Y                          "move_inc_y " ///< No description available.
#define CMD_STR_MOVE_INC_Z                          "move_inc_z " ///< No description available.
/** @} */

//==================================================================================================
// Response Message Prefixes (Device → Host)
//==================================================================================================

//==================================================================================================
// Command Enum
//==================================================================================================

/**
 * @enum Command
 * @brief Enumerates all possible commands that can be processed by the Gantry.
 * @details This enum provides a type-safe way to handle incoming commands.
 */
typedef enum {
    CMD_UNKNOWN,                        ///< Represents an unrecognized or invalid command.

    // General System Commands
    CMD_DISCOVER_DEVICE,                                    ///< @see CMD_STR_DISCOVER_DEVICE
    CMD_ENABLE,                                    ///< @see CMD_STR_ENABLE
    CMD_DISABLE,                                    ///< @see CMD_STR_DISABLE

    // Motion Commands
    CMD_HOME_X,                                    ///< @see CMD_STR_HOME_X
    CMD_HOME_Y,                                    ///< @see CMD_STR_HOME_Y
    CMD_HOME_Z,                                    ///< @see CMD_STR_HOME_Z
    CMD_MOVE_ABS_X,                                    ///< @see CMD_STR_MOVE_ABS_X
    CMD_MOVE_ABS_Y,                                    ///< @see CMD_STR_MOVE_ABS_Y
    CMD_MOVE_ABS_Z,                                    ///< @see CMD_STR_MOVE_ABS_Z
    CMD_MOVE_INC_X,                                    ///< @see CMD_STR_MOVE_INC_X
    CMD_MOVE_INC_Y,                                    ///< @see CMD_STR_MOVE_INC_Y
    CMD_MOVE_INC_Z                                     ///< @see CMD_STR_MOVE_INC_Z
} Command;

//==================================================================================================
// Command Parser Functions
//==================================================================================================

/**
 * @brief Parse a command string and return the corresponding Command enum.
 * @param cmdStr The command string to parse
 * @return The parsed Command enum value, or CMD_UNKNOWN if not recognized
 */
Command parseCommand(const char* cmdStr);

/**
 * @brief Extract parameter string from a command.
 * @param cmdStr The full command string
 * @param cmd The parsed command enum
 * @return Pointer to the parameter substring, or NULL if no parameters
 */
const char* getCommandParams(const char* cmdStr, Command cmd);