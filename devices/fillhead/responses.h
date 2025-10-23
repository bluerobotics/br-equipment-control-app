/**
 * @file responses.h
 * @brief Defines all response message formats for the Fillhead controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-22 18:01:10
 * 
 * This header file defines all messages sent FROM the Fillhead device TO the host.
 * This includes status messages, telemetry data, and discovery responses.
 * For command definitions (host → device), see commands.h
 * To modify response fields, edit telemetry.json and regenerate this file.
 */
#pragma once

//==================================================================================================
// Response Message Prefixes (Device → Host)
//==================================================================================================

/**
 * @name Status Message Prefixes
 * @brief Prefixes used for different types of status messages from the device.
 * @{
 */
#define STATUS_PREFIX_INFO                  "FILLHEAD_INFO: "          ///< Prefix for informational status messages.
#define STATUS_PREFIX_START                 "FILLHEAD_START: "         ///< Prefix for messages indicating the start of an operation.
#define STATUS_PREFIX_DONE                  "FILLHEAD_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.
#define STATUS_PREFIX_ERROR                 "FILLHEAD_ERROR: "         ///< Prefix for messages indicating an error or fault.
#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.
/** @} */

/**
 * @name Telemetry Prefix
 * @brief Prefix for periodic telemetry data messages.
 * @{
 */
#define TELEM_PREFIX                        "FILLHEAD_TELEM: "         ///< Prefix for all telemetry messages.
/** @} */

//==================================================================================================
// Telemetry Field Keys
//==================================================================================================

/**
 * @name Telemetry Field Identifiers
 * @brief String identifiers for telemetry data fields.
 * @details These defines specify the exact field names used in telemetry messages.
 * Format: "FILLHEAD_TELEM: field1:value1,field2:value2,..."
 * @{
 */

#define TELEM_KEY_FILLHEAD_STATE                 "fillhead_state           "  ///< Overall fillhead system state
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
// Usage Examples
//==================================================================================================

/**
 * @section Status Message Example
 * @code
 * // Send an info message
 * Serial.print(STATUS_PREFIX_INFO);
 * Serial.println("System initialized");
 * 
 * // Send a completion message
 * Serial.print(STATUS_PREFIX_DONE);
 * Serial.println("HEATER_ON");
 * @endcode
 * 
 * @section Telemetry Message Example
 * @code
 * char buffer[256];
 * snprintf(buffer, sizeof(buffer), "%s%s:%d,%s:%.2f",
 *          TELEM_PREFIX,
 *          TELEM_KEY_FILLHEAD_STATE, value1,
 *          TELEM_KEY_INJECTOR_STATE, value2);
 * Serial.println(buffer);
 * @endcode
 */