/**
 * @file telemetry.cpp
 * @brief Telemetry construction implementation for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-24 16:49:57
 */

#include "telemetry.h"
#include <stdio.h>
#include <string.h>
#include "ClearCore.h"

#define TELEM_PREFIX "PRESSURIZER_TELEM: "

//==================================================================================================
// Telemetry Initialization
//==================================================================================================

void telemetry_init(TelemetryData* data) {
    if (data == NULL) return;
    
    data->MAIN_STATE = STANDBY;
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
    
    int pos = 0;
    
    // Write prefix
    pos += snprintf(buffer + pos, buffer_size - pos, "%s", TELEM_PREFIX);
    
    // MAIN_STATE
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_MAIN_STATE, data->MAIN_STATE);
    }
    
    // pressure_psi
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_PRESSURE_PSI, data->pressure_psi);
    }
    
    // enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_ENABLED, data->enabled);
    }
    
    // cycles_programmed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_CYCLES_PROGRAMMED, data->cycles_programmed);
    }
    
    // cycles_complete
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_CYCLES_COMPLETE, data->cycles_complete);
    }
    
    // tank1_temp_c
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_TANK1_TEMP_C, data->tank1_temp_c);
    }
    
    // tank2_temp_c
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f", TELEM_KEY_TANK2_TEMP_C, data->tank2_temp_c);
    }
    
    return pos;
}

//==================================================================================================
// Telemetry Transmission
//==================================================================================================

void telemetry_send(const TelemetryData* data) {
    char buffer[512];
    int len = telemetry_build_message(data, buffer, sizeof(buffer));
    
    if (len > 0) {
        ConnectorUsb.SendLine(buffer);
    }
}