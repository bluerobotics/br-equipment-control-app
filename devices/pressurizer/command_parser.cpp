/**
 * @file command_parser.cpp
 * @brief Command parsing and dispatching implementations for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-03 11:25:17
 */

#include "command_parser.h"
#include <string.h>

//==================================================================================================
// Command Parser Implementation
//==================================================================================================

Command parseCommand(const char* cmdStr) {
    if (strncmp(cmdStr, CMD_STR_HOME, strlen(CMD_STR_HOME)) == 0) return CMD_HOME;
    if (strncmp(cmdStr, CMD_STR_DISABLE, strlen(CMD_STR_DISABLE)) == 0) return CMD_DISABLE;
    if (strncmp(cmdStr, CMD_STR_ENABLE, strlen(CMD_STR_ENABLE)) == 0) return CMD_ENABLE;
    if (strncmp(cmdStr, CMD_STR_MOVE_TO_PRESSURE, strlen(CMD_STR_MOVE_TO_PRESSURE)) == 0) return CMD_MOVE_TO_PRESSURE;
    return CMD_UNKNOWN;
}

const char* getCommandParams(const char* cmdStr, Command cmd) {
    switch (cmd) {
        case CMD_MOVE_TO_PRESSURE:
            return cmdStr + strlen(CMD_STR_MOVE_TO_PRESSURE);
        default:
            return NULL;
    }
}

//==================================================================================================
// Command Dispatcher Template
//==================================================================================================

bool dispatchCommand(Command cmd, const char* params) {
    switch (cmd) {
        case CMD_HOME:
            // TODO: Implement handler
            // handle_home();
            return true;

        case CMD_DISABLE:
            // TODO: Implement handler
            // handle_disable();
            return true;

        case CMD_ENABLE:
            // TODO: Implement handler
            // handle_enable();
            return true;

        case CMD_MOVE_TO_PRESSURE:
            // TODO: Implement handler with parameters
            // handle_move_to_pressure(params);
            return true;

        case CMD_UNKNOWN:
        default:
            return false;
    }
}