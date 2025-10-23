/**
 * @file responses.h
 * @brief Defines all response message formats for the Gantry controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-22 18:01:10
 * 
 * This header file defines all messages sent FROM the Gantry device TO the host.
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
#define STATUS_PREFIX_INFO                  "GANTRY_INFO: "          ///< Prefix for informational status messages.
#define STATUS_PREFIX_START                 "GANTRY_START: "         ///< Prefix for messages indicating the start of an operation.
#define STATUS_PREFIX_DONE                  "GANTRY_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.
#define STATUS_PREFIX_ERROR                 "GANTRY_ERROR: "         ///< Prefix for messages indicating an error or fault.
#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.
/** @} */

/**
 * @name Telemetry Prefix
 * @brief Prefix for periodic telemetry data messages.
 * @{
 */
#define TELEM_PREFIX                        "GANTRY_TELEM: "         ///< Prefix for all telemetry messages.
/** @} */

//==================================================================================================
// Telemetry Field Keys
//==================================================================================================

/**
 * @name Telemetry Field Identifiers
 * @brief String identifiers for telemetry data fields.
 * @details These defines specify the exact field names used in telemetry messages.
 * Format: "GANTRY_TELEM: field1:value1,field2:value2,..."
 * @{
 */

#define TELEM_KEY_GANTRY_STATE                   "gantry_state             "  ///< Overall gantry system state
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
 *          TELEM_KEY_GANTRY_STATE, value1,
 *          TELEM_KEY_X_STATE, value2);
 * Serial.println(buffer);
 * @endcode
 */