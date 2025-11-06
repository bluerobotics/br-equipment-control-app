/**
 * @file commands.cpp
 * @brief Command parsing implementation for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-05 20:42:41
 * 
 * This file contains the command parser integrated into commands.cpp
 */

#include "commands.h"
#include <string.h>

//==================================================================================================
// Command Parser Implementation
//==================================================================================================

Command parseCommand(const char* cmdStr) {
    if (strncmp(cmdStr, CMD_STR_DISCOVER_DEVICE, strlen(CMD_STR_DISCOVER_DEVICE)) == 0) return CMD_DISCOVER_DEVICE;
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