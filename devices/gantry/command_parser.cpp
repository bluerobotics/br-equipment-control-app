/**
 * @file command_parser.cpp
 * @brief Command parsing and dispatching implementations for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-10-22 18:01:10
 */

#include "command_parser.h"
#include <string.h>

//==================================================================================================
// Command Parser Implementation
//==================================================================================================

Command parseCommand(const char* cmdStr) {
    if (strncmp(cmdStr, CMD_STR_HOME_X, strlen(CMD_STR_HOME_X)) == 0) return CMD_HOME_X;
    if (strncmp(cmdStr, CMD_STR_HOME_Y, strlen(CMD_STR_HOME_Y)) == 0) return CMD_HOME_Y;
    if (strncmp(cmdStr, CMD_STR_HOME_Z, strlen(CMD_STR_HOME_Z)) == 0) return CMD_HOME_Z;
    if (strncmp(cmdStr, CMD_STR_MOVE_ABS_X, strlen(CMD_STR_MOVE_ABS_X)) == 0) return CMD_MOVE_ABS_X;
    if (strncmp(cmdStr, CMD_STR_MOVE_ABS_Y, strlen(CMD_STR_MOVE_ABS_Y)) == 0) return CMD_MOVE_ABS_Y;
    if (strncmp(cmdStr, CMD_STR_MOVE_ABS_Z, strlen(CMD_STR_MOVE_ABS_Z)) == 0) return CMD_MOVE_ABS_Z;
    if (strncmp(cmdStr, CMD_STR_MOVE_INC_X, strlen(CMD_STR_MOVE_INC_X)) == 0) return CMD_MOVE_INC_X;
    if (strncmp(cmdStr, CMD_STR_MOVE_INC_Y, strlen(CMD_STR_MOVE_INC_Y)) == 0) return CMD_MOVE_INC_Y;
    if (strncmp(cmdStr, CMD_STR_MOVE_INC_Z, strlen(CMD_STR_MOVE_INC_Z)) == 0) return CMD_MOVE_INC_Z;
    if (strncmp(cmdStr, CMD_STR_ENABLE, strlen(CMD_STR_ENABLE)) == 0) return CMD_ENABLE;
    if (strncmp(cmdStr, CMD_STR_DISABLE, strlen(CMD_STR_DISABLE)) == 0) return CMD_DISABLE;
    return CMD_UNKNOWN;
}

const char* getCommandParams(const char* cmdStr, Command cmd) {
    switch (cmd) {
        case CMD_MOVE_ABS_X:
            return cmdStr + strlen(CMD_STR_MOVE_ABS_X);
        case CMD_MOVE_ABS_Y:
            return cmdStr + strlen(CMD_STR_MOVE_ABS_Y);
        case CMD_MOVE_ABS_Z:
            return cmdStr + strlen(CMD_STR_MOVE_ABS_Z);
        case CMD_MOVE_INC_X:
            return cmdStr + strlen(CMD_STR_MOVE_INC_X);
        case CMD_MOVE_INC_Y:
            return cmdStr + strlen(CMD_STR_MOVE_INC_Y);
        case CMD_MOVE_INC_Z:
            return cmdStr + strlen(CMD_STR_MOVE_INC_Z);
        default:
            return NULL;
    }
}

//==================================================================================================
// Command Dispatcher Template
//==================================================================================================

bool dispatchCommand(Command cmd, const char* params) {
    switch (cmd) {
        case CMD_HOME_X:
            // TODO: Implement handler
            // handle_home_x();
            return true;

        case CMD_HOME_Y:
            // TODO: Implement handler
            // handle_home_y();
            return true;

        case CMD_HOME_Z:
            // TODO: Implement handler
            // handle_home_z();
            return true;

        case CMD_MOVE_ABS_X:
            // TODO: Implement handler with parameters
            // handle_move_abs_x(params);
            return true;

        case CMD_MOVE_ABS_Y:
            // TODO: Implement handler with parameters
            // handle_move_abs_y(params);
            return true;

        case CMD_MOVE_ABS_Z:
            // TODO: Implement handler with parameters
            // handle_move_abs_z(params);
            return true;

        case CMD_MOVE_INC_X:
            // TODO: Implement handler with parameters
            // handle_move_inc_x(params);
            return true;

        case CMD_MOVE_INC_Y:
            // TODO: Implement handler with parameters
            // handle_move_inc_y(params);
            return true;

        case CMD_MOVE_INC_Z:
            // TODO: Implement handler with parameters
            // handle_move_inc_z(params);
            return true;

        case CMD_ENABLE:
            // TODO: Implement handler
            // handle_enable();
            return true;

        case CMD_DISABLE:
            // TODO: Implement handler
            // handle_disable();
            return true;

        case CMD_UNKNOWN:
        default:
            return false;
    }
}