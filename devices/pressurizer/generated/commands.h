/**
 * @file commands.h
 * @brief Defines the command interface for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-03 13:45:47
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
#define CMD_STR_DISCOVER_DEVICE                     "DISCOVER_DEVICE               " ///< Generic command for any device to respond to.
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
// Response Message Prefixes (Device → Host)
//==================================================================================================

/**
 * @name Status Message Prefixes
 * @brief Prefixes used for different types of status messages from the device.
 * @{
 */
#define STATUS_PREFIX_INFO                  "PRESSURIZER_INFO: "          ///< Prefix for informational status messages.
#define STATUS_PREFIX_START                 "PRESSURIZER_START: "         ///< Prefix for messages indicating the start of an operation.
#define STATUS_PREFIX_DONE                  "PRESSURIZER_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.
#define STATUS_PREFIX_ERROR                 "PRESSURIZER_ERROR: "         ///< Prefix for messages indicating an error or fault.
#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.
/** @} */

/**
 * @name Telemetry Prefix
 * @brief Prefix for periodic telemetry data messages.
 * @{
 */
#define TELEM_PREFIX                        "PRESSURIZER_TELEM: "         ///< Prefix for all telemetry messages.
/** @} */

/**
 * @name Event Prefix
 * @brief Prefix for event messages.
 * @{
 */
#define EVENT_PREFIX                        "PRESSURIZER_EVENT: "         ///< Prefix for all event messages.
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
    CMD_DISCOVER_DEVICE                     ///< @see CMD_STR_DISCOVER_DEVICE,
    CMD_DISABLE                             ///< @see CMD_STR_DISABLE,
    CMD_ENABLE                              ///< @see CMD_STR_ENABLE,

    // Motion Commands
    CMD_HOME                                ///< @see CMD_STR_HOME,
    CMD_MOVE_TO_PRESSURE                    ///< @see CMD_STR_MOVE_TO_PRESSURE
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