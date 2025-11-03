/**
 * @file commands.h
 * @brief Defines the command interface for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-03 11:25:17
 * 
 * This header file defines all commands that can be sent TO the Pressurizer device.
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
#define CMD_STR_DISABLE                             "disable                       " ///< No description available.
#define CMD_STR_ENABLE                              "enable                        " ///< No description available.
/** @} */

/**
 * @name Motion Commands
 * @{
 */
#define CMD_STR_HOME                                "home                          " ///< No description available.
#define CMD_STR_MOVE_TO_PRESSURE                    "move_to_pressure              " ///< No description available.
/** @} */

//==================================================================================================
// Command Enum
//==================================================================================================

/**
 * @enum Command
 * @brief Enumerates all possible commands that can be processed by the Pressurizer.
 * @details This enum provides a type-safe way to handle incoming commands.
 */
typedef enum {
    CMD_UNKNOWN,                        ///< Represents an unrecognized or invalid command.

    // General System Commands
    CMD_DISABLE                             ///< @see CMD_STR_DISABLE,
    CMD_ENABLE                              ///< @see CMD_STR_ENABLE,

    // Motion Commands
    CMD_HOME                                ///< @see CMD_STR_HOME,
    CMD_MOVE_TO_PRESSURE                    ///< @see CMD_STR_MOVE_TO_PRESSURE,
} Command;