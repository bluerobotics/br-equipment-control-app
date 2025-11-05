/**
 * @file variables.cpp
 * @brief Telemetry construction implementation for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-11-04 12:18:51
 */

#include "variables.h"
#include "commands.h"
#include <stdio.h>
#include <string.h>

// Forward declaration - implemented in comms_controller
extern void sendMessage(const char* msg);

//==================================================================================================
// Telemetry Initialization
//==================================================================================================

void telemetry_init(TelemetryData* data) {
    if (data == NULL) return;
    
    data->main_state = "standby";
    data->pressure_psi = 0.0f;
    data->enabled = 1;
    data->cycles_programmed = 10;
    data->cycles_complete = 0;
    data->tank1_temp_c = 25.0f;
    data->tank2_temp_c = 25.1f;
}

//==================================================================================================
// Telemetry Message Construction
//==================================================================================================

int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size) {
    if (data == NULL || buffer == NULL || buffer_size == 0) return 0;
    
    size_t pos = 0;
    
    // Write prefix
    pos += snprintf(buffer + pos, buffer_size - pos, "%s", TELEM_PREFIX);
    
    // main_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%s,", TELEM_KEY_MAIN_STATE, data->main_state);
    }
    
    // pressure_psi
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_PRESSURE_PSI, data->pressure_psi);
    }
    
    // enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%ld,", TELEM_KEY_ENABLED, (long)data->enabled);
    }
    
    // cycles_programmed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%ld,", TELEM_KEY_CYCLES_PROGRAMMED, (long)data->cycles_programmed);
    }
    
    // cycles_complete
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%ld,", TELEM_KEY_CYCLES_COMPLETE, (long)data->cycles_complete);
    }
    
    // tank1_temp_c
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_TANK1_TEMP_C, data->tank1_temp_c);
    }
    
    // tank2_temp_c
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f", TELEM_KEY_TANK2_TEMP_C, data->tank2_temp_c);
    }
    
    return (int)pos;
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