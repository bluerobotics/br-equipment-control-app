/**
 * @file commands.cpp
 * @brief Command parsing implementation for the Fillhead controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-12 10:48:49
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
    if (strncmp(cmdStr, CMD_STR_ENABLE, strlen(CMD_STR_ENABLE)) == 0) return CMD_ENABLE;
    if (strncmp(cmdStr, CMD_STR_DISABLE, strlen(CMD_STR_DISABLE)) == 0) return CMD_DISABLE;
    if (strncmp(cmdStr, CMD_STR_DISCOVER_DEVICE, strlen(CMD_STR_DISCOVER_DEVICE)) == 0) return CMD_DISCOVER_DEVICE;
    if (strncmp(cmdStr, CMD_STR_ABORT, strlen(CMD_STR_ABORT)) == 0) return CMD_ABORT;
    if (strncmp(cmdStr, CMD_STR_CLEAR_ERRORS, strlen(CMD_STR_CLEAR_ERRORS)) == 0) return CMD_CLEAR_ERRORS;
    if (strncmp(cmdStr, CMD_STR_INJECT_STATOR, strlen(CMD_STR_INJECT_STATOR)) == 0) return CMD_INJECT_STATOR;
    if (strncmp(cmdStr, CMD_STR_INJECT_ROTOR, strlen(CMD_STR_INJECT_ROTOR)) == 0) return CMD_INJECT_ROTOR;
    if (strncmp(cmdStr, CMD_STR_JOG_MOVE, strlen(CMD_STR_JOG_MOVE)) == 0) return CMD_JOG_MOVE;
    if (strncmp(cmdStr, CMD_STR_MACHINE_HOME, strlen(CMD_STR_MACHINE_HOME)) == 0) return CMD_MACHINE_HOME;
    if (strncmp(cmdStr, CMD_STR_CARTRIDGE_HOME, strlen(CMD_STR_CARTRIDGE_HOME)) == 0) return CMD_CARTRIDGE_HOME;
    if (strncmp(cmdStr, CMD_STR_MOVE_TO_CARTRIDGE_HOME, strlen(CMD_STR_MOVE_TO_CARTRIDGE_HOME)) == 0) return CMD_MOVE_TO_CARTRIDGE_HOME;
    if (strncmp(cmdStr, CMD_STR_MOVE_TO_CARTRIDGE_RETRACT, strlen(CMD_STR_MOVE_TO_CARTRIDGE_RETRACT)) == 0) return CMD_MOVE_TO_CARTRIDGE_RETRACT;
    if (strncmp(cmdStr, CMD_STR_PAUSE_INJECTION, strlen(CMD_STR_PAUSE_INJECTION)) == 0) return CMD_PAUSE_INJECTION;
    if (strncmp(cmdStr, CMD_STR_RESUME_INJECTION, strlen(CMD_STR_RESUME_INJECTION)) == 0) return CMD_RESUME_INJECTION;
    if (strncmp(cmdStr, CMD_STR_CANCEL_INJECTION, strlen(CMD_STR_CANCEL_INJECTION)) == 0) return CMD_CANCEL_INJECTION;
    if (strncmp(cmdStr, CMD_STR_VACUUM_ON, strlen(CMD_STR_VACUUM_ON)) == 0) return CMD_VACUUM_ON;
    if (strncmp(cmdStr, CMD_STR_VACUUM_OFF, strlen(CMD_STR_VACUUM_OFF)) == 0) return CMD_VACUUM_OFF;
    if (strncmp(cmdStr, CMD_STR_VACUUM_LEAK_TEST, strlen(CMD_STR_VACUUM_LEAK_TEST)) == 0) return CMD_VACUUM_LEAK_TEST;
    if (strncmp(cmdStr, CMD_STR_HEATER_ON, strlen(CMD_STR_HEATER_ON)) == 0) return CMD_HEATER_ON;
    if (strncmp(cmdStr, CMD_STR_HEATER_OFF, strlen(CMD_STR_HEATER_OFF)) == 0) return CMD_HEATER_OFF;
    if (strncmp(cmdStr, CMD_STR_INJECTION_VALVE_HOME, strlen(CMD_STR_INJECTION_VALVE_HOME)) == 0) return CMD_INJECTION_VALVE_HOME;
    if (strncmp(cmdStr, CMD_STR_INJECTION_VALVE_OPEN, strlen(CMD_STR_INJECTION_VALVE_OPEN)) == 0) return CMD_INJECTION_VALVE_OPEN;
    if (strncmp(cmdStr, CMD_STR_INJECTION_VALVE_CLOSE, strlen(CMD_STR_INJECTION_VALVE_CLOSE)) == 0) return CMD_INJECTION_VALVE_CLOSE;
    if (strncmp(cmdStr, CMD_STR_INJECTION_VALVE_JOG, strlen(CMD_STR_INJECTION_VALVE_JOG)) == 0) return CMD_INJECTION_VALVE_JOG;
    if (strncmp(cmdStr, CMD_STR_VACUUM_VALVE_HOME, strlen(CMD_STR_VACUUM_VALVE_HOME)) == 0) return CMD_VACUUM_VALVE_HOME;
    if (strncmp(cmdStr, CMD_STR_VACUUM_VALVE_OPEN, strlen(CMD_STR_VACUUM_VALVE_OPEN)) == 0) return CMD_VACUUM_VALVE_OPEN;
    if (strncmp(cmdStr, CMD_STR_VACUUM_VALVE_CLOSE, strlen(CMD_STR_VACUUM_VALVE_CLOSE)) == 0) return CMD_VACUUM_VALVE_CLOSE;
    if (strncmp(cmdStr, CMD_STR_VACUUM_VALVE_JOG, strlen(CMD_STR_VACUUM_VALVE_JOG)) == 0) return CMD_VACUUM_VALVE_JOG;
    if (strncmp(cmdStr, CMD_STR_TEST_COMMAND, strlen(CMD_STR_TEST_COMMAND)) == 0) return CMD_TEST_COMMAND;
    return CMD_UNKNOWN;
}

const char* getCommandParams(const char* cmdStr, Command cmd) {
    switch (cmd) {
        case CMD_INJECT_STATOR:
            return cmdStr + strlen(CMD_STR_INJECT_STATOR);
        case CMD_INJECT_ROTOR:
            return cmdStr + strlen(CMD_STR_INJECT_ROTOR);
        case CMD_JOG_MOVE:
            return cmdStr + strlen(CMD_STR_JOG_MOVE);
        case CMD_MOVE_TO_CARTRIDGE_RETRACT:
            return cmdStr + strlen(CMD_STR_MOVE_TO_CARTRIDGE_RETRACT);
        case CMD_VACUUM_ON:
            return cmdStr + strlen(CMD_STR_VACUUM_ON);
        case CMD_VACUUM_LEAK_TEST:
            return cmdStr + strlen(CMD_STR_VACUUM_LEAK_TEST);
        case CMD_HEATER_ON:
            return cmdStr + strlen(CMD_STR_HEATER_ON);
        case CMD_INJECTION_VALVE_JOG:
            return cmdStr + strlen(CMD_STR_INJECTION_VALVE_JOG);
        case CMD_VACUUM_VALVE_JOG:
            return cmdStr + strlen(CMD_STR_VACUUM_VALVE_JOG);
        case CMD_TEST_COMMAND:
            return cmdStr + strlen(CMD_STR_TEST_COMMAND);
        default:
            return NULL;
    }
}