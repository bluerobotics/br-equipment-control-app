/**
 * @file responses.h
 * @brief Defines all response message formats for the Pressboi controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-22 18:01:10
 * 
 * This header file defines all messages sent FROM the Pressboi device TO the host.
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
#define STATUS_PREFIX_INFO                  "PRESSBOI_INFO: "          ///< Prefix for informational status messages.
#define STATUS_PREFIX_START                 "PRESSBOI_START: "         ///< Prefix for messages indicating the start of an operation.
#define STATUS_PREFIX_DONE                  "PRESSBOI_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.
#define STATUS_PREFIX_ERROR                 "PRESSBOI_ERROR: "         ///< Prefix for messages indicating an error or fault.
#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.
/** @} */

/**
 * @name Telemetry Prefix
 * @brief Prefix for periodic telemetry data messages.
 * @{
 */
#define TELEM_PREFIX                        "PRESSBOI_TELEM: "         ///< Prefix for all telemetry messages.
/** @} */

//==================================================================================================
// Telemetry Field Keys
//==================================================================================================

/**
 * @name Telemetry Field Identifiers
 * @brief String identifiers for telemetry data fields.
 * @details These defines specify the exact field names used in telemetry messages.
 * Format: "PRESSBOI_TELEM: field1:value1,field2:value2,..."
 * @{
 */

#define TELEM_KEY_MAIN_STATE                     "MAIN_STATE               "  ///< Overall press system state
#define TELEM_KEY_FORCE                          "force                    "  ///< Current force being applied by the press
#define TELEM_KEY_FORCE_LIMIT                    "force_limit              "  ///< Maximum force limit for current operation
#define TELEM_KEY_ENABLED0                       "enabled0                 "  ///< Power enable status for motor 1
#define TELEM_KEY_ENABLED1                       "enabled1                 "  ///< Power enable status for motor 2
#define TELEM_KEY_CURRENT_POS                    "current_pos              "  ///< Current position of press axis
#define TELEM_KEY_START_POS                      "start_pos                "  ///< Preset starting position for pressing routine
#define TELEM_KEY_TARGET_POS                     "target_pos               "  ///< Target position for current move operation
#define TELEM_KEY_TORQUE_M1                      "torque_m1                "  ///< Current motor torque percentage for motor 1
#define TELEM_KEY_TORQUE_M2                      "torque_m2                "  ///< Current motor torque percentage for motor 2
#define TELEM_KEY_HOMED                          "homed                    "  ///< Indicates if press has been homed to zero position

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
 *          TELEM_KEY_MAIN_STATE, value1,
 *          TELEM_KEY_FORCE, value2);
 * Serial.println(buffer);
 * @endcode
 */