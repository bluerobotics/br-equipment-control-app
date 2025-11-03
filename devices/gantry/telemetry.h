/**
 * @file telemetry.h
 * @brief Telemetry structure and construction interface for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-11-03 11:25:17
 * 
 * This header defines the complete telemetry data structure for the Gantry.
 * All telemetry fields are assembled in one centralized location.
 * To modify telemetry fields, edit telemetry.json and regenerate this file.
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>

//==================================================================================================
// Telemetry Field Keys
//==================================================================================================

/**
 * @name Telemetry Field Identifiers
 * @brief String keys used in telemetry messages.
 * Format: "GANTRY_TELEM: field1:value1,field2:value2,..."
 * @{
 */
#define TELEM_KEY_MAIN_STATE                     "main_state               "  ///< Overall gantry system state
#define TELEM_KEY_X_STATE                        "x_state                  "  ///< Current operational state of X-axis
#define TELEM_KEY_Y_STATE                        "y_state                  "  ///< Current operational state of Y-axis
#define TELEM_KEY_Z_STATE                        "z_state                  "  ///< Current operational state of Z-axis
#define TELEM_KEY_X_POS                          "x_pos                    "  ///< Current position of X-axis
#define TELEM_KEY_X_TORQUE                       "x_torque                 "  ///< Current motor torque percentage for X-axis
#define TELEM_KEY_X_ENABLED                      "x_enabled                "  ///< Power enable status for X-axis motor
#define TELEM_KEY_X_HOMED                        "x_homed                  "  ///< Indicates if X-axis has been homed
#define TELEM_KEY_Y_POS                          "y_pos                    "  ///< Current position of Y-axis
#define TELEM_KEY_Y_TORQUE                       "y_torque                 "  ///< Current motor torque percentage for Y-axis
#define TELEM_KEY_Y_ENABLED                      "y_enabled                "  ///< Power enable status for Y-axis motor
#define TELEM_KEY_Y_HOMED                        "y_homed                  "  ///< Indicates if Y-axis has been homed
#define TELEM_KEY_Z_POS                          "z_pos                    "  ///< Current position of Z-axis
#define TELEM_KEY_Z_TORQUE                       "z_torque                 "  ///< Current motor torque percentage for Z-axis
#define TELEM_KEY_Z_ENABLED                      "z_enabled                "  ///< Power enable status for Z-axis motor
#define TELEM_KEY_Z_HOMED                        "z_homed                  "  ///< Indicates if Z-axis has been homed
/** @} */

//==================================================================================================
// Telemetry Data Structure
//==================================================================================================

/**
 * @struct TelemetryData
 * @brief Complete telemetry state for the Gantry device.
 * @details This structure contains all telemetry values that are transmitted to the host.
 */
typedef struct {
    int32_t      main_state                    ; ///< Overall gantry system state
    int32_t      x_state                       ; ///< Current operational state of X-axis
    int32_t      y_state                       ; ///< Current operational state of Y-axis
    int32_t      z_state                       ; ///< Current operational state of Z-axis
    float        x_pos                         ; ///< Current position of X-axis
    float        x_torque                      ; ///< Current motor torque percentage for X-axis
    int32_t      x_enabled                     ; ///< Power enable status for X-axis motor
    int32_t      x_homed                       ; ///< Indicates if X-axis has been homed
    float        y_pos                         ; ///< Current position of Y-axis
    float        y_torque                      ; ///< Current motor torque percentage for Y-axis
    int32_t      y_enabled                     ; ///< Power enable status for Y-axis motor
    int32_t      y_homed                       ; ///< Indicates if Y-axis has been homed
    float        z_pos                         ; ///< Current position of Z-axis
    float        z_torque                      ; ///< Current motor torque percentage for Z-axis
    int32_t      z_enabled                     ; ///< Power enable status for Z-axis motor
    int32_t      z_homed                       ; ///< Indicates if Z-axis has been homed
} TelemetryData;

//==================================================================================================
// Telemetry Construction Functions
//==================================================================================================

/**
 * @brief Initialize telemetry data structure with default values.
 * @param data Pointer to TelemetryData structure to initialize
 */
void telemetry_init(TelemetryData* data);

/**
 * @brief Build complete telemetry message string from data structure.
 * @param data Pointer to TelemetryData structure containing current values
 * @param buffer Output buffer to write telemetry message
 * @param buffer_size Size of output buffer
 * @return Number of characters written (excluding null terminator)
 * 
 * @details Constructs a message in the format: "GANTRY_TELEM: field1:value1,field2:value2,..."
 */
int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size);

/**
 * @brief Send telemetry message via Serial.
 * @param data Pointer to TelemetryData structure containing current values
 * 
 * @details Builds and transmits the complete telemetry message.
 */
void telemetry_send(const TelemetryData* data);