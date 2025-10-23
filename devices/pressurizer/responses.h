/**
 * @file responses.h
 * @brief Defines all response message formats for the Pressurizer controller.
 * @details AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * Generated from telemetry.json on 2025-10-22 18:01:10
 * 
 * This header file defines all messages sent FROM the Pressurizer device TO the host.
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
#define STATUS_PREFIX_INFO                  "PRESSURIZER_INFO: "          ///< Prefix for informational status messages.
#define STATUS_PREFIX_START                 "PRESSURIZER_START: "         ///< Prefix for messages indicating the start of an operation.
#define STATUS_PREFIX_DONE                  "PRESSURIZER_DONE: "          ///< Prefix for messages indicating the successful completion of an operation.
#define STATUS_PREFIX_ERROR                 "PRESSURIZER_ERROR: "         ///< Prefix for messages indicating an error or fault.
#define STATUS_PREFIX_DISCOVERY             "DISCOVERY_RESPONSE: "     ///< Prefix for the device discovery response.
/** @} */

/**
 * @name Telemetry Prefix
 * @brief Prefix for periodic telemetry data messages.
 * @{
 */
#define TELEM_PREFIX                        "PRESSURIZER_TELEM: "         ///< Prefix for all telemetry messages.
/** @} */

//==================================================================================================
// Telemetry Field Keys
//==================================================================================================

/**
 * @name Telemetry Field Identifiers
 * @brief String identifiers for telemetry data fields.
 * @details These defines specify the exact field names used in telemetry messages.
 * Format: "PRESSURIZER_TELEM: field1:value1,field2:value2,..."
 * @{
 */

#define TELEM_KEY_MAIN_STATE                     "MAIN_STATE               "  ///< Overall pressurizer system state
#define TELEM_KEY_PRESSURE_PSI                   "pressure_psi             "  ///< Current pressure reading converted to meters of seawater
#define TELEM_KEY_ENABLED                        "enabled                  "  ///< Power enable status for pressurizer motor
#define TELEM_KEY_CYCLES_PROGRAMMED              "cycles_programmed        "  ///< Number of pressure cycles programmed for current test
#define TELEM_KEY_CYCLES_COMPLETE                "cycles_complete          "  ///< Number of pressure cycles completed in current test
#define TELEM_KEY_TANK1_TEMP_C                   "tank1_temp_c             "  ///< Temperature reading from tank 1 sensor
#define TELEM_KEY_TANK2_TEMP_C                   "tank2_temp_c             "  ///< Temperature reading from tank 2 sensor

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
 *          TELEM_KEY_PRESSURE_PSI, value2);
 * Serial.println(buffer);
 * @endcode
 */