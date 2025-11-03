/**
 * @file telemetry.h
 * @brief Telemetry structure and construction interface for the Fillhead controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-11-03 11:25:17
 * 
 * This header defines the complete telemetry data structure for the Fillhead.
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
 * Format: "FILLHEAD_TELEM: field1:value1,field2:value2,..."
 * @{
 */
#define TELEM_KEY_MAIN_STATE                     "main_state               "  ///< Overall fillhead system state
#define TELEM_KEY_INJECTOR_STATE                 "injector_state           "  ///< Current operational state of the injector motors
#define TELEM_KEY_INJ_VALVE_STATE                "inj_valve_state          "  ///< Current state of the injection pinch valve
#define TELEM_KEY_VAC_VALVE_STATE                "vac_valve_state          "  ///< Current state of the vacuum pinch valve
#define TELEM_KEY_HEATER_STATE                   "heater_state             "  ///< Heater PID control status
#define TELEM_KEY_VACUUM_STATE                   "vacuum_state             "  ///< Current vacuum system operation state
#define TELEM_KEY_INJECTOR_TORQUE                "injector_torque          "  ///< Current motor torque percentage for injector
#define TELEM_KEY_INJECTOR_HOMED                 "injector_homed           "  ///< Indicates if injector has been homed to machine zero
#define TELEM_KEY_INJECTION_CUMULATIVE_ML        "injection_cumulative_ml  "  ///< Total volume dispensed since last cartridge home
#define TELEM_KEY_INJECTION_ACTIVE_ML            "injection_active_ml      "  ///< Volume dispensed in current injection operation
#define TELEM_KEY_INJECTION_TARGET_ML            "injection_target_ml      "  ///< Target volume for current injection operation
#define TELEM_KEY_MOTORS_ENABLED                 "motors_enabled           "  ///< Global motor power enable status
#define TELEM_KEY_INJ_VALVE_POS                  "inj_valve_pos            "  ///< Current position of injection valve actuator
#define TELEM_KEY_INJ_VALVE_TORQUE               "inj_valve_torque         "  ///< Current motor torque percentage for injection valve
#define TELEM_KEY_INJ_VALVE_HOMED                "inj_valve_homed          "  ///< Indicates if injection valve has been homed
#define TELEM_KEY_VAC_VALVE_POS                  "vac_valve_pos            "  ///< Current position of vacuum valve actuator
#define TELEM_KEY_VAC_VALVE_MOTOR_TORQUE         "vac_valve_motor_torque   "  ///< Current motor torque percentage for vacuum valve
#define TELEM_KEY_VAC_VALVE_HOMED                "vac_valve_homed          "  ///< Indicates if vacuum valve has been homed
#define TELEM_KEY_TEMP_C                         "temp_c                   "  ///< Current material temperature from thermocouple
#define TELEM_KEY_HEATER_SETPOINT                "heater_setpoint          "  ///< Target temperature setpoint for PID controller
#define TELEM_KEY_VACUUM_PSIG                    "vacuum_psig              "  ///< Current vacuum pressure reading
/** @} */

//==================================================================================================
// Telemetry Data Structure
//==================================================================================================

/**
 * @struct TelemetryData
 * @brief Complete telemetry state for the Fillhead device.
 * @details This structure contains all telemetry values that are transmitted to the host.
 */
typedef struct {
    int32_t      main_state                    ; ///< Overall fillhead system state
    int32_t      injector_state                ; ///< Current operational state of the injector motors
    int32_t      inj_valve_state               ; ///< Current state of the injection pinch valve
    int32_t      vac_valve_state               ; ///< Current state of the vacuum pinch valve
    int32_t      heater_state                  ; ///< Heater PID control status
    int32_t      vacuum_state                  ; ///< Current vacuum system operation state
    float        injector_torque               ; ///< Current motor torque percentage for injector
    int32_t      injector_homed                ; ///< Indicates if injector has been homed to machine zero
    float        injection_cumulative_ml       ; ///< Total volume dispensed since last cartridge home
    float        injection_active_ml           ; ///< Volume dispensed in current injection operation
    float        injection_target_ml           ; ///< Target volume for current injection operation
    bool         motors_enabled                ; ///< Global motor power enable status
    float        inj_valve_pos                 ; ///< Current position of injection valve actuator
    float        inj_valve_torque              ; ///< Current motor torque percentage for injection valve
    bool         inj_valve_homed               ; ///< Indicates if injection valve has been homed
    float        vac_valve_pos                 ; ///< Current position of vacuum valve actuator
    float        vac_valve_motor_torque        ; ///< Current motor torque percentage for vacuum valve
    bool         vac_valve_homed               ; ///< Indicates if vacuum valve has been homed
    float        temp_c                        ; ///< Current material temperature from thermocouple
    float        heater_setpoint               ; ///< Target temperature setpoint for PID controller
    float        vacuum_psig                   ; ///< Current vacuum pressure reading
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
 * @details Constructs a message in the format: "FILLHEAD_TELEM: field1:value1,field2:value2,..."
 */
int telemetry_build_message(const TelemetryData* data, char* buffer, size_t buffer_size);

/**
 * @brief Send telemetry message via Serial.
 * @param data Pointer to TelemetryData structure containing current values
 * 
 * @details Builds and transmits the complete telemetry message.
 */
void telemetry_send(const TelemetryData* data);