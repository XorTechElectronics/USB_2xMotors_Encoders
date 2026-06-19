/**
 * TCA0 Generated Driver API Header File
 * 
 * @file tca0.h
 * 
 * @ingroup tca0_split
 * 
 * @brief This file contains the deprecated macros or APIs for the TCA0 driver.
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

#ifndef TCA0_DEPRECATED_H
#define TCA0_DEPRECATED_H

#warning "The tca0_deprecated.h file contains the deprecated macros or functions. Replace the deprecated macro or functions with the recommended alternative."

/**
 * @misradeviation{@advisory,2.5}
 * MCC Melody drivers provide macros that can be added to an application. 
 * It depends on the application whether a macro is used or not. 
 */
 
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ReadHighCount will be deprecated in the future release. Use TCA0_HighCounterGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ReadHighCount TCA0_HighCounterGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_WriteHighCount will be deprecated in the future release. Use TCA0_HighCounterSet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_WriteHighCount TCA0_HighCounterSet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ReadLowCount will be deprecated in the future release. Use TCA0_LowCounterGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ReadLowCount TCA0_LowCounterGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_WriteLowCount will be deprecated in the future release. Use TCA0_LowCounterSet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_WriteLowCount TCA0_LowCounterSet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ClearHUNFInterruptFlag will be deprecated in the future release. Use TCA0_HUNFInterruptFlagClear instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ClearHUNFInterruptFlag TCA0_HUNFInterruptFlagClear
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_IsHUNFInterruptFlagSet will be deprecated in the future release. Use TCA0_HUNFInterruptStatusGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_IsHUNFInterruptFlagSet TCA0_HUNFInterruptStatusGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ClearLUNFInterruptFlag will be deprecated in the future release. Use TCA0_LUNFInterruptFlagClear instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ClearLUNFInterruptFlag TCA0_LUNFInterruptFlagClear
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_IsLUNFInterruptFlagSet will be deprecated in the future release. Use TCA0_LUNFInterruptStatusGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_IsLUNFInterruptFlagSet TCA0_LUNFInterruptStatusGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ClearLCMP0InterruptFlag will be deprecated in the future release. Use TCA0_LCMP0InterruptFlagClear instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ClearLCMP0InterruptFlag TCA0_LCMP0InterruptFlagClear
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_IsLCMP0InterruptFlagSet will be deprecated in the future release. Use TCA0_LCMP0InterruptStatusGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_IsLCMP0InterruptFlagSet TCA0_LCMP0InterruptStatusGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ClearLCMP1InterruptFlag will be deprecated in the future release. Use TCA0_LCMP1InterruptFlagClear instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ClearLCMP1InterruptFlag TCA0_LCMP1InterruptFlagClear
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_IsLCMP1InterruptFlagSet will be deprecated in the future release. Use TCA0_LCMP1InterruptStatusGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_IsLCMP1InterruptFlagSet TCA0_LCMP1InterruptStatusGet
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_ClearHUNFInterruptFlag will be deprecated in the future release. Use TCA0_LCMP2InterruptFlagClear instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_ClearLCMP2InterruptFlag TCA0_LCMP2InterruptFlagClear
/**
 * @ingroup tca0_split
 * @brief Defines the Custom Name for the \ref TCA0_CounterGet API. 
 *        The TCA0_IsLCMP2InterruptFlagSet will be deprecated in the future release. Use TCA0_LCMP2InterruptStatusGet instead.
 */
/* cppcheck-suppress misra-c2012-2.5 */  
#define TCA0_IsLCMP2InterruptFlagSet TCA0_LCMP2InterruptStatusGet

#endif //TCA0_DEPRECATED_H