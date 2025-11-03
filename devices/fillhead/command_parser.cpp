/**
 * @file command_parser.cpp
 * @brief Command parsing and dispatching implementations for the Fillhead controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from commands.json on 2025-11-03 11:25:17
 */

#include "command_parser.h"
#include <string.h>

//==================================================================================================
// Command Parser Implementation
//==================================================================================================

Command parseCommand(const char* cmdStr) {
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

//==================================================================================================
// Command Dispatcher Template
//==================================================================================================

bool dispatchCommand(Command cmd, const char* params) {
    switch (cmd) {
        case CMD_ENABLE:
            // TODO: Implement handler
            // handle_enable();
            return true;

        case CMD_DISABLE:
            // TODO: Implement handler
            // handle_disable();
            return true;

        case CMD_DISCOVER_DEVICE:
            // TODO: Implement handler
            // handle_discover_device();
            return true;

        case CMD_ABORT:
            // TODO: Implement handler
            // handle_abort();
            return true;

        case CMD_CLEAR_ERRORS:
            // TODO: Implement handler
            // handle_clear_errors();
            return true;

        case CMD_INJECT_STATOR:
            // TODO: Implement handler with parameters
            // handle_inject_stator(params);
            return true;

        case CMD_INJECT_ROTOR:
            // TODO: Implement handler with parameters
            // handle_inject_rotor(params);
            return true;

        case CMD_JOG_MOVE:
            // TODO: Implement handler with parameters
            // handle_jog_move(params);
            return true;

        case CMD_MACHINE_HOME:
            // TODO: Implement handler
            // handle_machine_home();
            return true;

        case CMD_CARTRIDGE_HOME:
            // TODO: Implement handler
            // handle_cartridge_home();
            return true;

        case CMD_MOVE_TO_CARTRIDGE_HOME:
            // TODO: Implement handler
            // handle_move_to_cartridge_home();
            return true;

        case CMD_MOVE_TO_CARTRIDGE_RETRACT:
            // TODO: Implement handler with parameters
            // handle_move_to_cartridge_retract(params);
            return true;

        case CMD_PAUSE_INJECTION:
            // TODO: Implement handler
            // handle_pause_injection();
            return true;

        case CMD_RESUME_INJECTION:
            // TODO: Implement handler
            // handle_resume_injection();
            return true;

        case CMD_CANCEL_INJECTION:
            // TODO: Implement handler
            // handle_cancel_injection();
            return true;

        case CMD_VACUUM_ON:
            // TODO: Implement handler with parameters
            // handle_vacuum_on(params);
            return true;

        case CMD_VACUUM_OFF:
            // TODO: Implement handler
            // handle_vacuum_off();
            return true;

        case CMD_VACUUM_LEAK_TEST:
            // TODO: Implement handler with parameters
            // handle_vacuum_leak_test(params);
            return true;

        case CMD_HEATER_ON:
            // TODO: Implement handler with parameters
            // handle_heater_on(params);
            return true;

        case CMD_HEATER_OFF:
            // TODO: Implement handler
            // handle_heater_off();
            return true;

        case CMD_INJECTION_VALVE_HOME:
            // TODO: Implement handler
            // handle_injection_valve_home();
            return true;

        case CMD_INJECTION_VALVE_OPEN:
            // TODO: Implement handler
            // handle_injection_valve_open();
            return true;

        case CMD_INJECTION_VALVE_CLOSE:
            // TODO: Implement handler
            // handle_injection_valve_close();
            return true;

        case CMD_INJECTION_VALVE_JOG:
            // TODO: Implement handler with parameters
            // handle_injection_valve_jog(params);
            return true;

        case CMD_VACUUM_VALVE_HOME:
            // TODO: Implement handler
            // handle_vacuum_valve_home();
            return true;

        case CMD_VACUUM_VALVE_OPEN:
            // TODO: Implement handler
            // handle_vacuum_valve_open();
            return true;

        case CMD_VACUUM_VALVE_CLOSE:
            // TODO: Implement handler
            // handle_vacuum_valve_close();
            return true;

        case CMD_VACUUM_VALVE_JOG:
            // TODO: Implement handler with parameters
            // handle_vacuum_valve_jog(params);
            return true;

        case CMD_TEST_COMMAND:
            // TODO: Implement handler with parameters
            // handle_test_command(params);
            return true;

        case CMD_UNKNOWN:
        default:
            return false;
    }
}