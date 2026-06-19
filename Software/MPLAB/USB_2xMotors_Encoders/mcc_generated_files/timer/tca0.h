/**
 * TCA0 Generated Driver API Header File
 *
 * @file tca0.h
 *
 * @defgroup tca0_split TCA0 in Split Mode
 *
 * @brief This file contains API prototypes for the TCA0 driver in Split (8-bit) mode.
 *
 * @version TCA0 Driver Version 3.0.1
 *
 * @version Package Version 7.1.0
 */
/*
© [2025] Microchip Technology Inc. and its subsidiaries.

    Subject to your compliance with these terms, you may use Microchip 
    software and any derivatives exclusively with Microchip products. 
    You are responsible for complying with 3rd party license terms  
    applicable to your use of 3rd party software (including open source  
    software) that may accompany Microchip software. SOFTWARE IS ?AS IS.? 
    NO WARRANTIES, WHETHER EXPRESS, IMPLIED OR STATUTORY, APPLY TO THIS 
    SOFTWARE, INCLUDING ANY IMPLIED WARRANTIES OF NON-INFRINGEMENT,  
    MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT 
    WILL MICROCHIP BE LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE, 
    INCIDENTAL OR CONSEQUENTIAL LOSS, DAMAGE, COST OR EXPENSE OF ANY 
    KIND WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER CAUSED, EVEN IF 
    MICROCHIP HAS BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE 
    FORESEEABLE. TO THE FULLEST EXTENT ALLOWED BY LAW, MICROCHIP?S 
    TOTAL LIABILITY ON ALL CLAIMS RELATED TO THE SOFTWARE WILL NOT 
    EXCEED AMOUNT OF FEES, IF ANY, YOU PAID DIRECTLY TO MICROCHIP FOR 
    THIS SOFTWARE.
*/

#ifndef TCA0_H_INCLUDED
#define TCA0_H_INCLUDED

#include <stdint.h>
#include <stdbool.h>
#include "../system/utils/compiler.h"
#include "./tca0_deprecated.h"

/**
 * @misradeviation{@advisory,2.5}
 * MCC Melody drivers provide macros that can be added to an application. 
 * It depends on the application whether a macro is used or not. 
 */

/**
 * @ingroup tca0_split
 * @brief Defines the maximum count of the timer.
 */
#define TCA0_MAX_COUNT (255U)
/**
 * @ingroup tca0_split
 * @brief Defines the timer prescaled clock frequency in hertz.
 */
 /* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_CLOCK_FREQ (24000000UL)

/**
 * @ingroup tca0_split
 * @typedef TCA0_cb_t
 * @brief Function pointer to the callback function called by TCA while operating in Split mode.
 *        The default value is set to NULL, which means that no callback function will be used.
 */
typedef void (*TCA0_cb_t)(void);  

/**
 * @ingroup tca0_split
 * @brief Initializes the TCA0 module.
 * @param None.
 * @return None.
 */ 
void TCA0_Initialize(void);

/**
 * @ingroup tca0_split
 * @brief Deinitializes the TCA0 module.
 * @param None.
 * @return None.
 */
void TCA0_Deinitialize(void);

/**
 * @ingroup tca0_split
 * @brief Starts the TCA0.
 * @param None.
 * @return None.
 */
void TCA0_Start(void);

/**
 * @ingroup tca0_split
 * @brief Stops the TCA0.
 * @param None.
 * @return None.
 */
void TCA0_Stop(void);

/**
 * @ingroup tca0_split
 * @brief Sets the counter value for the Low Byte Timer.
 * @param timerVal - Counter value to be written to the LCNT register
 * @return None.
 */
void TCA0_LowCounterSet(uint8_t timerVal); 

/**
 * @ingroup tca0_split
 * @brief Returns the Low Byte Timer counter value.
 * @param None.
 * @return Counter value from the LCNT register
 */
uint8_t TCA0_LowCounterGet(void);

/**
 * @ingroup tca0_split
 * @brief Returns the High Byte Timer counter value.
 * @param None.
 * @return Counter value from the HCNT register
 */
uint8_t TCA0_HighCounterGet(void);

/**
 * @ingroup tca0_split
 * @brief Sets the counter value for the High Byte Timer.
 * @param timerVal - Counter value to be written to the HCNT register
 * @return None.
 */
void TCA0_HighCounterSet(uint8_t timerVal);

/**
 * @ingroup tca0_split
 * @brief Sets the period count value for the High Byte Timer.
 * @param periodVal - Period count value written to the HPER register
 * @return None.
 */
void TCA0_HighPeriodSet(uint8_t periodVal);

/**
 * @ingroup tca0_split
 * @brief Sets the period count value for the Low Byte Timer.
 * @param periodVal - Period count value written to the LPER register
 * @return None.
 */
void TCA0_LowPeriodSet(uint8_t periodVal);

/**
 * @ingroup tca0_split
 * @brief Returns the period count value of the High Byte Timer.
 * @param None.
 * @return Period count value from the HPER register
 */
uint8_t TCA0_HighPeriodGet(void);

/**
 * @ingroup tca0_split
 * @brief Returns the period count value of the Low Byte Timer.
 * @param None.
 * @return Period count value from the LPER register
 */
uint8_t TCA0_LowPeriodGet(void);

/**
 * @ingroup tca0_split
 * @brief Returns the maximum timer count value.
 * @param None.
 * @return Maximum count value
 */
uint8_t TCA0_MaxCountGet(void);

/**
 * @ingroup tca0_split
 * @brief Clears the High Byte Timer Underflow interrupt flag.
 * @param None.
 * @return None.
 */
void TCA0_HUNFInterruptFlagClear(void);

/**
 * @ingroup tca0_split
 * @brief Returns the status of the High Byte Timer Underflow interrupt flag.
 * @param None.
 * @retval True  - High Byte Underflow interrupt flag is set
 * @retval False - High Byte Underflow interrupt flag is not set
 */
bool TCA0_HUNFInterruptStatusGet(void);

/**
 * @ingroup tca0_split
 * @brief Clears the Low Byte Timer Underflow interrupt flag.
 * @param None.
 * @return None.
 */
void TCA0_LUNFInterruptFlagClear(void);

/**
 * @ingroup tca0_split
 * @brief Returns the status of the Low Byte Timer Underflow interrupt flag.
 * @param None.
 * @retval True  - Low Byte Underflow interrupt flag is set
 * @retval False - Low Byte Underflow interrupt flag is not set
 */
bool TCA0_LUNFInterruptStatusGet(void);

/**
 * @ingroup tca0_split
 * @brief Clears the Low Byte Timer Compare Channel 0 Match interrupt flag.
 * @param None.
 * @return None.
 */
void TCA0_LCMP0InterruptFlagClear(void);

/**
 * @ingroup tca0_split
 * @brief Returns the status of the Low Byte Timer Compare Channel 0 Match interrupt flag.
 * @param None.
 * @retval True  - Low Byte Timer Compare Channel 0 Match interrupt flag is set
 * @retval False - Low Byte Timer Compare Channel 0 Match interrupt flag is not set
 */

bool TCA0_LCMP0InterruptStatusGet(void);
/**
 * @ingroup tca0_split
 * @brief Clears the Low Byte Timer Compare Channel 1 Match interrupt flag.
 * @param None.
 * @return None.
 */
void TCA0_LCMP1InterruptFlagClear(void);

/**
 * @ingroup tca0_split
 * @brief Returns the status of the Low Byte Timer Compare Channel 1 Match interrupt flag.
 * @param None.
 * @retval True  - Low Byte Timer Compare Channel 1 Match interrupt flag is set
 * @retval False - Low Byte Timer Compare Channel 1 Match interrupt flag is not set
 */
bool TCA0_LCMP1InterruptStatusGet(void);

/**
 * @ingroup tca0_split
 * @brief Clears the Low Byte Timer Compare Channel 2 Match interrupt flag.
 * @param None.
 * @return None.
 */
void TCA0_LCMP2InterruptFlagClear(void);

/**
 * @ingroup tca0_split
 * @brief Returns the status of the Low Byte Timer Compare Channel 2 Match interrupt flag.
 * @param None.
 * @retval True  - Low Byte Timer Compare Channel 2 Match interrupt flag is set
 * @retval False - Low Byte Timer Compare Channel 2 Match interrupt flag is not set
 */
bool TCA0_LCMP2InterruptStatusGet(void);
/**
 * @ingroup tca0_split
 * @brief Registers a callback function for the High Byte Timer underflow event.
 * @param CallbackHandler - Address to the custom callback function
 * @return None.
 */ 
void TCA0_HighCountCallbackRegister(TCA0_cb_t CallbackHandler);

/**
 * @ingroup tca0_split
 * @brief Registers a callback function for the Low Byte Timer Compare 0 match event.
 * @param CallbackHandler - Address to the custom callback function
 * @return None.
 */ 
void TCA0_LowCompare0CallbackRegister(TCA0_cb_t CallbackHandler);

/**
 * @ingroup tca0_split
 * @brief Registers a callback function for the Low Byte Timer Compare 1 match event.
 * @param CallbackHandler - Address to the custom callback function
 * @return None.
 */ 
void TCA0_LowCompare1CallbackRegister(TCA0_cb_t CallbackHandler);

/**
 * @ingroup tca0_split
 * @brief Registers a callback function for the Low Byte Timer Compare 2 match event. 
 * @param CallbackHandler - Address to the custom callback function
 * @return None.
 */ 
void TCA0_LowCompare2CallbackRegister(TCA0_cb_t CallbackHandler);

/**
 * @ingroup tca0_split
 * @brief Registers a callback function for the Low Byte Timer underflow event.
 * @param CallbackHandler - Address to the custom callback function
 * @return None.
 */ 
void TCA0_LowCountCallbackRegister(TCA0_cb_t CallbackHandler);
/**
 * @ingroup tca0_split
 * @brief Performs tasks to be executed during the timer interrupt events.
 * @param None.
 * @return None.
 */
void TCA0_Tasks(void);

#endif /* TCA0_H_INCLUDED */