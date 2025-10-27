/**
 * @file telemetry.cpp
 * @brief Telemetry construction implementation for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-24 16:49:57
 */

#include "telemetry.h"
#include <stdio.h>
#include <string.h>
#include "ClearCore.h"

#define TELEM_PREFIX "GANTRY_TELEM: "

//==================================================================================================
// Telemetry Initialization
//==================================================================================================

void telemetry_init(TelemetryData* data) {
    if (data == NULL) return;
    
    data->gantry_state = STANDBY;
    data->x_state = Standby;
    data->y_state = Standby;
    data->z_state = Standby;
    data->x_pos = 0.0f;
    data->x_torque = 0.0f;
    data->x_enabled = 1;
    data->x_homed = 0;
    data->y_pos = 0.0f;
    data->y_torque = 0.0f;
    data->y_enabled = 1;
    data->y_homed = 0;
    data->z_pos = 0.0f;
    data->z_torque = 0.0f;
    data->z_enabled = 1;
    data->z_homed = 0;
}

//==================================================================================================
// Telemetry Message Construction
//==================================================================================================

int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size) {
    if (data == NULL || buffer == NULL || buffer_size == 0) return 0;
    
    int pos = 0;
    
    // Write prefix
    pos += snprintf(buffer + pos, buffer_size - pos, "%s", TELEM_PREFIX);
    
    // gantry_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_GANTRY_STATE, data->gantry_state);
    }
    
    // x_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_X_STATE, data->x_state);
    }
    
    // y_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_Y_STATE, data->y_state);
    }
    
    // z_state
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_Z_STATE, data->z_state);
    }
    
    // x_pos
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_X_POS, data->x_pos);
    }
    
    // x_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_X_TORQUE, data->x_torque);
    }
    
    // x_enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_X_ENABLED, data->x_enabled);
    }
    
    // x_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_X_HOMED, data->x_homed);
    }
    
    // y_pos
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_Y_POS, data->y_pos);
    }
    
    // y_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_Y_TORQUE, data->y_torque);
    }
    
    // y_enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_Y_ENABLED, data->y_enabled);
    }
    
    // y_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_Y_HOMED, data->y_homed);
    }
    
    // z_pos
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.2f,", TELEM_KEY_Z_POS, data->z_pos);
    }
    
    // z_torque
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%.1f,", TELEM_KEY_Z_TORQUE, data->z_torque);
    }
    
    // z_enabled
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d,", TELEM_KEY_Z_ENABLED, data->z_enabled);
    }
    
    // z_homed
    if (pos < buffer_size) {
        pos += snprintf(buffer + pos, buffer_size - pos, "%s:%d", TELEM_KEY_Z_HOMED, data->z_homed);
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