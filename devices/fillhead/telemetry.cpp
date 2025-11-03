/**
 * @file telemetry.cpp
 * @brief Telemetry construction implementation for the Fillhead controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-11-03 11:25:17
 */

#include "telemetry.h"
#include <stdio.h>
#include <string.h>
// #include "ClearCore.h"  // Include if using ClearCore hardware

#define TELEM_PREFIX "FILLHEAD_TELEM: "

//==================================================================================================
// Telemetry Initialization
//==================================================================================================

void telemetry_init(TelemetryData* data) {
    if (data == NULL) return;
    
    data->main_state = 0;
    data->injector_state = 0;
    data->inj_valve_state = 0;
    data->vac_valve_state = 0;
    data->heater_state = 0;
    data->vacuum_state = 0;
    data->injector_torque = 0.0f;
    data->injector_homed = 0;
    data->injection_cumulative_ml = 0.0f;
    data->injection_active_ml = 0.0f;
    data->injection_target_ml = 0.0f;
    data->motors_enabled = true;
    data->inj_valve_pos = 0.0f;
    data->inj_valve_torque = 0.0f;
    data->inj_valve_homed = false;
    data->vac_valve_pos = 0.0f;
    data->vac_valve_motor_torque = 0.0f;
    data->vac_valve_homed = false;
    data->temp_c = 25.0f;
    data->heater_setpoint = 70.0f;
    data->vacuum_psig = 0.5f;
}

//==================================================================================================
// Telemetry Message Construction
//==================================================================================================

int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size) {
    if (data == NULL || buffer == NULL || buffer_size == 0) return 0;
    
    int pos = 0;
    
    // Write prefix
    pos += snprintf(buffer + pos, buffer_size - pos, "%s", TELEM_PREFIX);
    
    // main_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_MAIN_STATE, data->main_state);
    }
    
    // injector_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_INJECTOR_STATE, data->injector_state);
    }
    
    // inj_valve_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_INJ_VALVE_STATE, data->inj_valve_state);
    }
    
    // vac_valve_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_VAC_VALVE_STATE, data->vac_valve_state);
    }
    
    // heater_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_HEATER_STATE, data->heater_state);
    }
    
    // vacuum_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_VACUUM_STATE, data->vacuum_state);
    }
    
    // injector_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_INJECTOR_TORQUE, data->injector_torque);
    }
    
    // injector_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_INJECTOR_HOMED, data->injector_homed);
    }
    
    // injection_cumulative_ml
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_INJECTION_CUMULATIVE_ML, data->injection_cumulative_ml);
    }
    
    // injection_active_ml
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_INJECTION_ACTIVE_ML, data->injection_active_ml);
    }
    
    // injection_target_ml
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_INJECTION_TARGET_ML, data->injection_target_ml);
    }
    
    // motors_enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_MOTORS_ENABLED, data->motors_enabled ? 1 : 0);
    }
    
    // inj_valve_pos
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_INJ_VALVE_POS, data->inj_valve_pos);
    }
    
    // inj_valve_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_INJ_VALVE_TORQUE, data->inj_valve_torque);
    }
    
    // inj_valve_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_INJ_VALVE_HOMED, data->inj_valve_homed ? 1 : 0);
    }
    
    // vac_valve_pos
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_VAC_VALVE_POS, data->vac_valve_pos);
    }
    
    // vac_valve_motor_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_VAC_VALVE_MOTOR_TORQUE, data->vac_valve_motor_torque);
    }
    
    // vac_valve_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_VAC_VALVE_HOMED, data->vac_valve_homed ? 1 : 0);
    }
    
    // temp_c
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_TEMP_C, data->temp_c);
    }
    
    // heater_setpoint
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_HEATER_SETPOINT, data->heater_setpoint);
    }
    
    // vacuum_psig
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f", TELEM_KEY_VACUUM_PSIG, data->vacuum_psig);
    }
    
    return pos;
}

//==================================================================================================
// Telemetry Transmission
//==================================================================================================

// NOTE: You need to provide a sendMessage() implementation based on your comms setup
// For example:
// extern CommsController comms;
// #define sendMessage(msg) comms.enqueueTx(msg, comms.m_guiIp, comms.m_guiPort)

void telemetry_send(const TelemetryData* data) {
    char buffer[512];
    int len = telemetry_build_message(data, buffer, sizeof(buffer));
    
    if (len > 0) {
        sendMessage(buffer);
    }
}