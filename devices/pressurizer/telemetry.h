/**
 * @file telemetry.h
 * @brief Telemetry structure and construction interface for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-11-03 11:25:17
 * 
 * This header defines the complete telemetry data structure for the Pressurizer.
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
 * Format: "PRESSURIZER_TELEM: field1:value1,field2:value2,..."
 * @{
 */
#define TELEM_KEY_MAIN_STATE                     "main_state               "  ///< Overall pressurizer system state
#define TELEM_KEY_PRESSURE_PSI                   "pressure_psi             "  ///< Current pressure reading converted to meters of seawater
#define TELEM_KEY_ENABLED                        "enabled                  "  ///< Power enable status for pressurizer motor
#define TELEM_KEY_CYCLES_PROGRAMMED              "cycles_programmed        "  ///< Number of pressure cycles programmed for current test
#define TELEM_KEY_CYCLES_COMPLETE                "cycles_complete          "  ///< Number of pressure cycles completed in current test
#define TELEM_KEY_TANK1_TEMP_C                   "tank1_temp_c             "  ///< Temperature reading from tank 1 sensor
#define TELEM_KEY_TANK2_TEMP_C                   "tank2_temp_c             "  ///< Temperature reading from tank 2 sensor
/** @} */

//==================================================================================================
// Telemetry Data Structure
//==================================================================================================

/**
 * @struct TelemetryData
 * @brief Complete telemetry state for the Pressurizer device.
 * @details This structure contains all telemetry values that are transmitted to the host.
 */
typedef struct {
    int32_t      main_state                    ; ///< Overall pressurizer system state
    float        pressure_psi                  ; ///< Current pressure reading converted to meters of seawater
    int32_t      enabled                       ; ///< Power enable status for pressurizer motor
    int32_t      cycles_programmed             ; ///< Number of pressure cycles programmed for current test
    int32_t      cycles_complete               ; ///< Number of pressure cycles completed in current test
    float        tank1_temp_c                  ; ///< Temperature reading from tank 1 sensor
    float        tank2_temp_c                  ; ///< Temperature reading from tank 2 sensor
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
 * @details Constructs a message in the format: "PRESSURIZER_TELEM: field1:value1,field2:value2,..."
 */
int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size);

/**
 * @brief Send telemetry message via Serial.
 * @param data Pointer to TelemetryData structure containing current values
 * 
 * @details Builds and transmits the complete telemetry message.
 */
void telemetry_send(const TelemetryData* data);