/**
 * @file commands.h
 * @brief Defines the command interface for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-10-22 18:01:10
 * 
 * This header file defines all commands that can be sent TO the Gantry device.
 * For response message formats, see responses.h
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
#define CMD_STR_ENABLE                              "enable                        " ///< No description available.
#define CMD_STR_DISABLE                             "disable                       " ///< No description available.
/** @} */

/**
 * @name Motion Commands
 * @{
 */
#define CMD_STR_HOME_X                              "home_x                        " ///< No description available.
#define CMD_STR_HOME_Y                              "home_y                        " ///< No description available.
#define CMD_STR_HOME_Z                              "home_z                        " ///< No description available.
#define CMD_STR_MOVE_ABS_X                          "move_abs_x                    " ///< No description available.
#define CMD_STR_MOVE_ABS_Y                          "move_abs_y                    " ///< No description available.
#define CMD_STR_MOVE_ABS_Z                          "move_abs_z                    " ///< No description available.
#define CMD_STR_MOVE_INC_X                          "move_inc_x                    " ///< No description available.
#define CMD_STR_MOVE_INC_Y                          "move_inc_y                    " ///< No description available.
#define CMD_STR_MOVE_INC_Z                          "move_inc_z                    " ///< No description available.
/** @} */

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
    CMD_ENABLE                              ///< @see CMD_STR_ENABLE,
    CMD_DISABLE                             ///< @see CMD_STR_DISABLE,

    // Motion Commands
    CMD_HOME_X                              ///< @see CMD_STR_HOME_X,
    CMD_HOME_Y                              ///< @see CMD_STR_HOME_Y,
    CMD_HOME_Z                              ///< @see CMD_STR_HOME_Z,
    CMD_MOVE_ABS_X                          ///< @see CMD_STR_MOVE_ABS_X,
    CMD_MOVE_ABS_Y                          ///< @see CMD_STR_MOVE_ABS_Y,
    CMD_MOVE_ABS_Z                          ///< @see CMD_STR_MOVE_ABS_Z,
    CMD_MOVE_INC_X                          ///< @see CMD_STR_MOVE_INC_X,
    CMD_MOVE_INC_Y                          ///< @see CMD_STR_MOVE_INC_Y,
    CMD_MOVE_INC_Z                          ///< @see CMD_STR_MOVE_INC_Z,
} Command;