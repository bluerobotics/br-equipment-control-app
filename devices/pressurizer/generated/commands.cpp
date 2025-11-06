/**
 * @file commands.cpp
 * @brief Command parsing implementation for the Pressurizer controller.
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