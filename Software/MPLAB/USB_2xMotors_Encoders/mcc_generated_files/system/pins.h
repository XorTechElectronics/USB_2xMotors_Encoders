/**
 * Generated Pins header File
 * 
 * @file pins.h
 * 
 * @defgroup  pinsdriver Pins Driver
 * 
 * @brief This is generated driver header for pins. 
 *        This header file provides APIs for all pins selected in the GUI.
 *
 * @version Driver Version  1.1.0
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

#ifndef PINS_H_INCLUDED
#define PINS_H_INCLUDED

#include <avr/io.h>
#include "./port.h"

//get/set IO_PA1 aliases
#define IO_PA1_SetHigh() do { PORTA_OUTSET = 0x2; } while(0)
#define IO_PA1_SetLow() do { PORTA_OUTCLR = 0x2; } while(0)
#define IO_PA1_Toggle() do { PORTA_OUTTGL = 0x2; } while(0)
#define IO_PA1_GetValue() (VPORTA.IN & (0x1 << 1))
#define IO_PA1_SetDigitalInput() do { PORTA_DIRCLR = 0x2; } while(0)
#define IO_PA1_SetDigitalOutput() do { PORTA_DIRSET = 0x2; } while(0)
#define IO_PA1_SetPullUp() do { PORTA_PIN1CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PA1_ResetPullUp() do { PORTA_PIN1CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PA1_SetInverted() do { PORTA_PIN1CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PA1_ResetInverted() do { PORTA_PIN1CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PA1_DisableInterruptOnChange() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PA1_EnableInterruptForBothEdges() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PA1_EnableInterruptForRisingEdge() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PA1_EnableInterruptForFallingEdge() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PA1_DisableDigitalInputBuffer() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PA1_EnableInterruptForLowLevelSensing() do { PORTA.PIN1CTRL = (PORTA.PIN1CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PA1_SetInterruptHandler IO_PA1_SetInterruptHandler

//get/set IO_PA0 aliases
#define IO_PA0_SetHigh() do { PORTA_OUTSET = 0x1; } while(0)
#define IO_PA0_SetLow() do { PORTA_OUTCLR = 0x1; } while(0)
#define IO_PA0_Toggle() do { PORTA_OUTTGL = 0x1; } while(0)
#define IO_PA0_GetValue() (VPORTA.IN & (0x1 << 0))
#define IO_PA0_SetDigitalInput() do { PORTA_DIRCLR = 0x1; } while(0)
#define IO_PA0_SetDigitalOutput() do { PORTA_DIRSET = 0x1; } while(0)
#define IO_PA0_SetPullUp() do { PORTA_PIN0CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PA0_ResetPullUp() do { PORTA_PIN0CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PA0_SetInverted() do { PORTA_PIN0CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PA0_ResetInverted() do { PORTA_PIN0CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PA0_DisableInterruptOnChange() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PA0_EnableInterruptForBothEdges() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PA0_EnableInterruptForRisingEdge() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PA0_EnableInterruptForFallingEdge() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PA0_DisableDigitalInputBuffer() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PA0_EnableInterruptForLowLevelSensing() do { PORTA.PIN0CTRL = (PORTA.PIN0CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PA0_SetInterruptHandler IO_PA0_SetInterruptHandler

//get/set IO_PF0 aliases
#define IO_PF0_SetHigh() do { PORTF_OUTSET = 0x1; } while(0)
#define IO_PF0_SetLow() do { PORTF_OUTCLR = 0x1; } while(0)
#define IO_PF0_Toggle() do { PORTF_OUTTGL = 0x1; } while(0)
#define IO_PF0_GetValue() (VPORTF.IN & (0x1 << 0))
#define IO_PF0_SetDigitalInput() do { PORTF_DIRCLR = 0x1; } while(0)
#define IO_PF0_SetDigitalOutput() do { PORTF_DIRSET = 0x1; } while(0)
#define IO_PF0_SetPullUp() do { PORTF_PIN0CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PF0_ResetPullUp() do { PORTF_PIN0CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PF0_SetInverted() do { PORTF_PIN0CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PF0_ResetInverted() do { PORTF_PIN0CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PF0_DisableInterruptOnChange() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PF0_EnableInterruptForBothEdges() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PF0_EnableInterruptForRisingEdge() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PF0_EnableInterruptForFallingEdge() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PF0_DisableDigitalInputBuffer() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PF0_EnableInterruptForLowLevelSensing() do { PORTF.PIN0CTRL = (PORTF.PIN0CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF0_SetInterruptHandler IO_PF0_SetInterruptHandler

//get/set IO_PF1 aliases
#define IO_PF1_SetHigh() do { PORTF_OUTSET = 0x2; } while(0)
#define IO_PF1_SetLow() do { PORTF_OUTCLR = 0x2; } while(0)
#define IO_PF1_Toggle() do { PORTF_OUTTGL = 0x2; } while(0)
#define IO_PF1_GetValue() (VPORTF.IN & (0x1 << 1))
#define IO_PF1_SetDigitalInput() do { PORTF_DIRCLR = 0x2; } while(0)
#define IO_PF1_SetDigitalOutput() do { PORTF_DIRSET = 0x2; } while(0)
#define IO_PF1_SetPullUp() do { PORTF_PIN1CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PF1_ResetPullUp() do { PORTF_PIN1CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PF1_SetInverted() do { PORTF_PIN1CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PF1_ResetInverted() do { PORTF_PIN1CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PF1_DisableInterruptOnChange() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PF1_EnableInterruptForBothEdges() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PF1_EnableInterruptForRisingEdge() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PF1_EnableInterruptForFallingEdge() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PF1_DisableDigitalInputBuffer() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PF1_EnableInterruptForLowLevelSensing() do { PORTF.PIN1CTRL = (PORTF.PIN1CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF1_SetInterruptHandler IO_PF1_SetInterruptHandler

//get/set IO_PF2 aliases
#define IO_PF2_SetHigh() do { PORTF_OUTSET = 0x4; } while(0)
#define IO_PF2_SetLow() do { PORTF_OUTCLR = 0x4; } while(0)
#define IO_PF2_Toggle() do { PORTF_OUTTGL = 0x4; } while(0)
#define IO_PF2_GetValue() (VPORTF.IN & (0x1 << 2))
#define IO_PF2_SetDigitalInput() do { PORTF_DIRCLR = 0x4; } while(0)
#define IO_PF2_SetDigitalOutput() do { PORTF_DIRSET = 0x4; } while(0)
#define IO_PF2_SetPullUp() do { PORTF_PIN2CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PF2_ResetPullUp() do { PORTF_PIN2CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PF2_SetInverted() do { PORTF_PIN2CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PF2_ResetInverted() do { PORTF_PIN2CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PF2_DisableInterruptOnChange() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PF2_EnableInterruptForBothEdges() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PF2_EnableInterruptForRisingEdge() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PF2_EnableInterruptForFallingEdge() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PF2_DisableDigitalInputBuffer() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PF2_EnableInterruptForLowLevelSensing() do { PORTF.PIN2CTRL = (PORTF.PIN2CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF2_SetInterruptHandler IO_PF2_SetInterruptHandler

//get/set IO_PF3 aliases
#define IO_PF3_SetHigh() do { PORTF_OUTSET = 0x8; } while(0)
#define IO_PF3_SetLow() do { PORTF_OUTCLR = 0x8; } while(0)
#define IO_PF3_Toggle() do { PORTF_OUTTGL = 0x8; } while(0)
#define IO_PF3_GetValue() (VPORTF.IN & (0x1 << 3))
#define IO_PF3_SetDigitalInput() do { PORTF_DIRCLR = 0x8; } while(0)
#define IO_PF3_SetDigitalOutput() do { PORTF_DIRSET = 0x8; } while(0)
#define IO_PF3_SetPullUp() do { PORTF_PIN3CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define IO_PF3_ResetPullUp() do { PORTF_PIN3CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define IO_PF3_SetInverted() do { PORTF_PIN3CTRL  |= PORT_INVEN_bm; } while(0)
#define IO_PF3_ResetInverted() do { PORTF_PIN3CTRL  &= ~PORT_INVEN_bm; } while(0)
#define IO_PF3_DisableInterruptOnChange() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define IO_PF3_EnableInterruptForBothEdges() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define IO_PF3_EnableInterruptForRisingEdge() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define IO_PF3_EnableInterruptForFallingEdge() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define IO_PF3_DisableDigitalInputBuffer() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define IO_PF3_EnableInterruptForLowLevelSensing() do { PORTF.PIN3CTRL = (PORTF.PIN3CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF3_SetInterruptHandler IO_PF3_SetInterruptHandler

//get/set SS aliases
#define SS_SetHigh() do { PORTA_OUTSET = 0x80; } while(0)
#define SS_SetLow() do { PORTA_OUTCLR = 0x80; } while(0)
#define SS_Toggle() do { PORTA_OUTTGL = 0x80; } while(0)
#define SS_GetValue() (VPORTA.IN & (0x1 << 7))
#define SS_SetDigitalInput() do { PORTA_DIRCLR = 0x80; } while(0)
#define SS_SetDigitalOutput() do { PORTA_DIRSET = 0x80; } while(0)
#define SS_SetPullUp() do { PORTA_PIN7CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define SS_ResetPullUp() do { PORTA_PIN7CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define SS_SetInverted() do { PORTA_PIN7CTRL  |= PORT_INVEN_bm; } while(0)
#define SS_ResetInverted() do { PORTA_PIN7CTRL  &= ~PORT_INVEN_bm; } while(0)
#define SS_DisableInterruptOnChange() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define SS_EnableInterruptForBothEdges() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define SS_EnableInterruptForRisingEdge() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define SS_EnableInterruptForFallingEdge() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define SS_DisableDigitalInputBuffer() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define SS_EnableInterruptForLowLevelSensing() do { PORTA.PIN7CTRL = (PORTA.PIN7CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PA7_SetInterruptHandler SS_SetInterruptHandler

//get/set LED aliases
#define LED_SetHigh() do { PORTC_OUTSET = 0x8; } while(0)
#define LED_SetLow() do { PORTC_OUTCLR = 0x8; } while(0)
#define LED_Toggle() do { PORTC_OUTTGL = 0x8; } while(0)
#define LED_GetValue() (VPORTC.IN & (0x1 << 3))
#define LED_SetDigitalInput() do { PORTC_DIRCLR = 0x8; } while(0)
#define LED_SetDigitalOutput() do { PORTC_DIRSET = 0x8; } while(0)
#define LED_SetPullUp() do { PORTC_PIN3CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define LED_ResetPullUp() do { PORTC_PIN3CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define LED_SetInverted() do { PORTC_PIN3CTRL  |= PORT_INVEN_bm; } while(0)
#define LED_ResetInverted() do { PORTC_PIN3CTRL  &= ~PORT_INVEN_bm; } while(0)
#define LED_DisableInterruptOnChange() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define LED_EnableInterruptForBothEdges() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define LED_EnableInterruptForRisingEdge() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define LED_EnableInterruptForFallingEdge() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define LED_DisableDigitalInputBuffer() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define LED_EnableInterruptForLowLevelSensing() do { PORTC.PIN3CTRL = (PORTC.PIN3CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PC3_SetInterruptHandler LED_SetInterruptHandler

//get/set M1_IN2 aliases
#define M1_IN2_SetHigh() do { PORTD_OUTSET = 0x1; } while(0)
#define M1_IN2_SetLow() do { PORTD_OUTCLR = 0x1; } while(0)
#define M1_IN2_Toggle() do { PORTD_OUTTGL = 0x1; } while(0)
#define M1_IN2_GetValue() (VPORTD.IN & (0x1 << 0))
#define M1_IN2_SetDigitalInput() do { PORTD_DIRCLR = 0x1; } while(0)
#define M1_IN2_SetDigitalOutput() do { PORTD_DIRSET = 0x1; } while(0)
#define M1_IN2_SetPullUp() do { PORTD_PIN0CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M1_IN2_ResetPullUp() do { PORTD_PIN0CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M1_IN2_SetInverted() do { PORTD_PIN0CTRL  |= PORT_INVEN_bm; } while(0)
#define M1_IN2_ResetInverted() do { PORTD_PIN0CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M1_IN2_DisableInterruptOnChange() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M1_IN2_EnableInterruptForBothEdges() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M1_IN2_EnableInterruptForRisingEdge() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M1_IN2_EnableInterruptForFallingEdge() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M1_IN2_DisableDigitalInputBuffer() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M1_IN2_EnableInterruptForLowLevelSensing() do { PORTD.PIN0CTRL = (PORTD.PIN0CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD0_SetInterruptHandler M1_IN2_SetInterruptHandler

//get/set M1_IN1 aliases
#define M1_IN1_SetHigh() do { PORTD_OUTSET = 0x2; } while(0)
#define M1_IN1_SetLow() do { PORTD_OUTCLR = 0x2; } while(0)
#define M1_IN1_Toggle() do { PORTD_OUTTGL = 0x2; } while(0)
#define M1_IN1_GetValue() (VPORTD.IN & (0x1 << 1))
#define M1_IN1_SetDigitalInput() do { PORTD_DIRCLR = 0x2; } while(0)
#define M1_IN1_SetDigitalOutput() do { PORTD_DIRSET = 0x2; } while(0)
#define M1_IN1_SetPullUp() do { PORTD_PIN1CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M1_IN1_ResetPullUp() do { PORTD_PIN1CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M1_IN1_SetInverted() do { PORTD_PIN1CTRL  |= PORT_INVEN_bm; } while(0)
#define M1_IN1_ResetInverted() do { PORTD_PIN1CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M1_IN1_DisableInterruptOnChange() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M1_IN1_EnableInterruptForBothEdges() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M1_IN1_EnableInterruptForRisingEdge() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M1_IN1_EnableInterruptForFallingEdge() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M1_IN1_DisableDigitalInputBuffer() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M1_IN1_EnableInterruptForLowLevelSensing() do { PORTD.PIN1CTRL = (PORTD.PIN1CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD1_SetInterruptHandler M1_IN1_SetInterruptHandler

//get/set M01_STBY aliases
#define M01_STBY_SetHigh() do { PORTD_OUTSET = 0x4; } while(0)
#define M01_STBY_SetLow() do { PORTD_OUTCLR = 0x4; } while(0)
#define M01_STBY_Toggle() do { PORTD_OUTTGL = 0x4; } while(0)
#define M01_STBY_GetValue() (VPORTD.IN & (0x1 << 2))
#define M01_STBY_SetDigitalInput() do { PORTD_DIRCLR = 0x4; } while(0)
#define M01_STBY_SetDigitalOutput() do { PORTD_DIRSET = 0x4; } while(0)
#define M01_STBY_SetPullUp() do { PORTD_PIN2CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M01_STBY_ResetPullUp() do { PORTD_PIN2CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M01_STBY_SetInverted() do { PORTD_PIN2CTRL  |= PORT_INVEN_bm; } while(0)
#define M01_STBY_ResetInverted() do { PORTD_PIN2CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M01_STBY_DisableInterruptOnChange() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M01_STBY_EnableInterruptForBothEdges() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M01_STBY_EnableInterruptForRisingEdge() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M01_STBY_EnableInterruptForFallingEdge() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M01_STBY_DisableDigitalInputBuffer() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M01_STBY_EnableInterruptForLowLevelSensing() do { PORTD.PIN2CTRL = (PORTD.PIN2CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD2_SetInterruptHandler M01_STBY_SetInterruptHandler

//get/set M0_IN1 aliases
#define M0_IN1_SetHigh() do { PORTD_OUTSET = 0x8; } while(0)
#define M0_IN1_SetLow() do { PORTD_OUTCLR = 0x8; } while(0)
#define M0_IN1_Toggle() do { PORTD_OUTTGL = 0x8; } while(0)
#define M0_IN1_GetValue() (VPORTD.IN & (0x1 << 3))
#define M0_IN1_SetDigitalInput() do { PORTD_DIRCLR = 0x8; } while(0)
#define M0_IN1_SetDigitalOutput() do { PORTD_DIRSET = 0x8; } while(0)
#define M0_IN1_SetPullUp() do { PORTD_PIN3CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M0_IN1_ResetPullUp() do { PORTD_PIN3CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M0_IN1_SetInverted() do { PORTD_PIN3CTRL  |= PORT_INVEN_bm; } while(0)
#define M0_IN1_ResetInverted() do { PORTD_PIN3CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M0_IN1_DisableInterruptOnChange() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M0_IN1_EnableInterruptForBothEdges() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M0_IN1_EnableInterruptForRisingEdge() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M0_IN1_EnableInterruptForFallingEdge() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M0_IN1_DisableDigitalInputBuffer() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M0_IN1_EnableInterruptForLowLevelSensing() do { PORTD.PIN3CTRL = (PORTD.PIN3CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD3_SetInterruptHandler M0_IN1_SetInterruptHandler

//get/set M23_STBY aliases
#define M23_STBY_SetHigh() do { PORTD_OUTSET = 0x10; } while(0)
#define M23_STBY_SetLow() do { PORTD_OUTCLR = 0x10; } while(0)
#define M23_STBY_Toggle() do { PORTD_OUTTGL = 0x10; } while(0)
#define M23_STBY_GetValue() (VPORTD.IN & (0x1 << 4))
#define M23_STBY_SetDigitalInput() do { PORTD_DIRCLR = 0x10; } while(0)
#define M23_STBY_SetDigitalOutput() do { PORTD_DIRSET = 0x10; } while(0)
#define M23_STBY_SetPullUp() do { PORTD_PIN4CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M23_STBY_ResetPullUp() do { PORTD_PIN4CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M23_STBY_SetInverted() do { PORTD_PIN4CTRL  |= PORT_INVEN_bm; } while(0)
#define M23_STBY_ResetInverted() do { PORTD_PIN4CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M23_STBY_DisableInterruptOnChange() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M23_STBY_EnableInterruptForBothEdges() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M23_STBY_EnableInterruptForRisingEdge() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M23_STBY_EnableInterruptForFallingEdge() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M23_STBY_DisableDigitalInputBuffer() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M23_STBY_EnableInterruptForLowLevelSensing() do { PORTD.PIN4CTRL = (PORTD.PIN4CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD4_SetInterruptHandler M23_STBY_SetInterruptHandler

//get/set M3_IN2 aliases
#define M3_IN2_SetHigh() do { PORTD_OUTSET = 0x20; } while(0)
#define M3_IN2_SetLow() do { PORTD_OUTCLR = 0x20; } while(0)
#define M3_IN2_Toggle() do { PORTD_OUTTGL = 0x20; } while(0)
#define M3_IN2_GetValue() (VPORTD.IN & (0x1 << 5))
#define M3_IN2_SetDigitalInput() do { PORTD_DIRCLR = 0x20; } while(0)
#define M3_IN2_SetDigitalOutput() do { PORTD_DIRSET = 0x20; } while(0)
#define M3_IN2_SetPullUp() do { PORTD_PIN5CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M3_IN2_ResetPullUp() do { PORTD_PIN5CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M3_IN2_SetInverted() do { PORTD_PIN5CTRL  |= PORT_INVEN_bm; } while(0)
#define M3_IN2_ResetInverted() do { PORTD_PIN5CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M3_IN2_DisableInterruptOnChange() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M3_IN2_EnableInterruptForBothEdges() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M3_IN2_EnableInterruptForRisingEdge() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M3_IN2_EnableInterruptForFallingEdge() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M3_IN2_DisableDigitalInputBuffer() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M3_IN2_EnableInterruptForLowLevelSensing() do { PORTD.PIN5CTRL = (PORTD.PIN5CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD5_SetInterruptHandler M3_IN2_SetInterruptHandler

//get/set M3_IN1 aliases
#define M3_IN1_SetHigh() do { PORTD_OUTSET = 0x40; } while(0)
#define M3_IN1_SetLow() do { PORTD_OUTCLR = 0x40; } while(0)
#define M3_IN1_Toggle() do { PORTD_OUTTGL = 0x40; } while(0)
#define M3_IN1_GetValue() (VPORTD.IN & (0x1 << 6))
#define M3_IN1_SetDigitalInput() do { PORTD_DIRCLR = 0x40; } while(0)
#define M3_IN1_SetDigitalOutput() do { PORTD_DIRSET = 0x40; } while(0)
#define M3_IN1_SetPullUp() do { PORTD_PIN6CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M3_IN1_ResetPullUp() do { PORTD_PIN6CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M3_IN1_SetInverted() do { PORTD_PIN6CTRL  |= PORT_INVEN_bm; } while(0)
#define M3_IN1_ResetInverted() do { PORTD_PIN6CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M3_IN1_DisableInterruptOnChange() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M3_IN1_EnableInterruptForBothEdges() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M3_IN1_EnableInterruptForRisingEdge() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M3_IN1_EnableInterruptForFallingEdge() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M3_IN1_DisableDigitalInputBuffer() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M3_IN1_EnableInterruptForLowLevelSensing() do { PORTD.PIN6CTRL = (PORTD.PIN6CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD6_SetInterruptHandler M3_IN1_SetInterruptHandler

//get/set M0_IN2 aliases
#define M0_IN2_SetHigh() do { PORTD_OUTSET = 0x80; } while(0)
#define M0_IN2_SetLow() do { PORTD_OUTCLR = 0x80; } while(0)
#define M0_IN2_Toggle() do { PORTD_OUTTGL = 0x80; } while(0)
#define M0_IN2_GetValue() (VPORTD.IN & (0x1 << 7))
#define M0_IN2_SetDigitalInput() do { PORTD_DIRCLR = 0x80; } while(0)
#define M0_IN2_SetDigitalOutput() do { PORTD_DIRSET = 0x80; } while(0)
#define M0_IN2_SetPullUp() do { PORTD_PIN7CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M0_IN2_ResetPullUp() do { PORTD_PIN7CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M0_IN2_SetInverted() do { PORTD_PIN7CTRL  |= PORT_INVEN_bm; } while(0)
#define M0_IN2_ResetInverted() do { PORTD_PIN7CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M0_IN2_DisableInterruptOnChange() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M0_IN2_EnableInterruptForBothEdges() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M0_IN2_EnableInterruptForRisingEdge() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M0_IN2_EnableInterruptForFallingEdge() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M0_IN2_DisableDigitalInputBuffer() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M0_IN2_EnableInterruptForLowLevelSensing() do { PORTD.PIN7CTRL = (PORTD.PIN7CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PD7_SetInterruptHandler M0_IN2_SetInterruptHandler

//get/set M2_IN1 aliases
#define M2_IN1_SetHigh() do { PORTF_OUTSET = 0x10; } while(0)
#define M2_IN1_SetLow() do { PORTF_OUTCLR = 0x10; } while(0)
#define M2_IN1_Toggle() do { PORTF_OUTTGL = 0x10; } while(0)
#define M2_IN1_GetValue() (VPORTF.IN & (0x1 << 4))
#define M2_IN1_SetDigitalInput() do { PORTF_DIRCLR = 0x10; } while(0)
#define M2_IN1_SetDigitalOutput() do { PORTF_DIRSET = 0x10; } while(0)
#define M2_IN1_SetPullUp() do { PORTF_PIN4CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M2_IN1_ResetPullUp() do { PORTF_PIN4CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M2_IN1_SetInverted() do { PORTF_PIN4CTRL  |= PORT_INVEN_bm; } while(0)
#define M2_IN1_ResetInverted() do { PORTF_PIN4CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M2_IN1_DisableInterruptOnChange() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M2_IN1_EnableInterruptForBothEdges() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M2_IN1_EnableInterruptForRisingEdge() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M2_IN1_EnableInterruptForFallingEdge() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M2_IN1_DisableDigitalInputBuffer() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M2_IN1_EnableInterruptForLowLevelSensing() do { PORTF.PIN4CTRL = (PORTF.PIN4CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF4_SetInterruptHandler M2_IN1_SetInterruptHandler

//get/set M2_IN2 aliases
#define M2_IN2_SetHigh() do { PORTF_OUTSET = 0x20; } while(0)
#define M2_IN2_SetLow() do { PORTF_OUTCLR = 0x20; } while(0)
#define M2_IN2_Toggle() do { PORTF_OUTTGL = 0x20; } while(0)
#define M2_IN2_GetValue() (VPORTF.IN & (0x1 << 5))
#define M2_IN2_SetDigitalInput() do { PORTF_DIRCLR = 0x20; } while(0)
#define M2_IN2_SetDigitalOutput() do { PORTF_DIRSET = 0x20; } while(0)
#define M2_IN2_SetPullUp() do { PORTF_PIN5CTRL  |= PORT_PULLUPEN_bm; } while(0)
#define M2_IN2_ResetPullUp() do { PORTF_PIN5CTRL  &= ~PORT_PULLUPEN_bm; } while(0)
#define M2_IN2_SetInverted() do { PORTF_PIN5CTRL  |= PORT_INVEN_bm; } while(0)
#define M2_IN2_ResetInverted() do { PORTF_PIN5CTRL  &= ~PORT_INVEN_bm; } while(0)
#define M2_IN2_DisableInterruptOnChange() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x0 ; } while(0)
#define M2_IN2_EnableInterruptForBothEdges() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x1 ; } while(0)
#define M2_IN2_EnableInterruptForRisingEdge() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x2 ; } while(0)
#define M2_IN2_EnableInterruptForFallingEdge() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x3 ; } while(0)
#define M2_IN2_DisableDigitalInputBuffer() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x4 ; } while(0)
#define M2_IN2_EnableInterruptForLowLevelSensing() do { PORTF.PIN5CTRL = (PORTF.PIN5CTRL & ~PORT_ISC_gm) | 0x5 ; } while(0)
#define PF5_SetInterruptHandler M2_IN2_SetInterruptHandler

/**
 * @ingroup  pinsdriver
 * @brief GPIO and peripheral I/O initialization
 * @param none
 * @return none
 */
void PIN_MANAGER_Initialize();

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PA1 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PA1_SetInterruptHandler() method.
 *        This handler is called every time the IO_PA1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PA1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PA1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PA1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PA1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PA0 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PA0_SetInterruptHandler() method.
 *        This handler is called every time the IO_PA0 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PA0_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PA0 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PA0 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PA0_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PF0 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PF0_SetInterruptHandler() method.
 *        This handler is called every time the IO_PF0 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PF0_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PF0 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PF0 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PF0_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PF1 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PF1_SetInterruptHandler() method.
 *        This handler is called every time the IO_PF1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PF1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PF1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PF1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PF1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PF2 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PF2_SetInterruptHandler() method.
 *        This handler is called every time the IO_PF2 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PF2_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PF2 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PF2 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PF2_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for IO_PF3 pin. 
 *        This is a predefined interrupt handler to be used together with the IO_PF3_SetInterruptHandler() method.
 *        This handler is called every time the IO_PF3 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void IO_PF3_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for IO_PF3 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for IO_PF3 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void IO_PF3_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for SS pin. 
 *        This is a predefined interrupt handler to be used together with the SS_SetInterruptHandler() method.
 *        This handler is called every time the SS ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void SS_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for SS pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for SS at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void SS_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for LED pin. 
 *        This is a predefined interrupt handler to be used together with the LED_SetInterruptHandler() method.
 *        This handler is called every time the LED ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void LED_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for LED pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for LED at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void LED_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M1_IN2 pin. 
 *        This is a predefined interrupt handler to be used together with the M1_IN2_SetInterruptHandler() method.
 *        This handler is called every time the M1_IN2 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M1_IN2_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M1_IN2 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M1_IN2 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M1_IN2_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M1_IN1 pin. 
 *        This is a predefined interrupt handler to be used together with the M1_IN1_SetInterruptHandler() method.
 *        This handler is called every time the M1_IN1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M1_IN1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M1_IN1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M1_IN1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M1_IN1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M01_STBY pin. 
 *        This is a predefined interrupt handler to be used together with the M01_STBY_SetInterruptHandler() method.
 *        This handler is called every time the M01_STBY ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M01_STBY_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M01_STBY pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M01_STBY at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M01_STBY_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M0_IN1 pin. 
 *        This is a predefined interrupt handler to be used together with the M0_IN1_SetInterruptHandler() method.
 *        This handler is called every time the M0_IN1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M0_IN1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M0_IN1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M0_IN1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M0_IN1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M23_STBY pin. 
 *        This is a predefined interrupt handler to be used together with the M23_STBY_SetInterruptHandler() method.
 *        This handler is called every time the M23_STBY ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M23_STBY_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M23_STBY pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M23_STBY at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M23_STBY_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M3_IN2 pin. 
 *        This is a predefined interrupt handler to be used together with the M3_IN2_SetInterruptHandler() method.
 *        This handler is called every time the M3_IN2 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M3_IN2_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M3_IN2 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M3_IN2 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M3_IN2_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M3_IN1 pin. 
 *        This is a predefined interrupt handler to be used together with the M3_IN1_SetInterruptHandler() method.
 *        This handler is called every time the M3_IN1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M3_IN1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M3_IN1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M3_IN1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M3_IN1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M0_IN2 pin. 
 *        This is a predefined interrupt handler to be used together with the M0_IN2_SetInterruptHandler() method.
 *        This handler is called every time the M0_IN2 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M0_IN2_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M0_IN2 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M0_IN2 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M0_IN2_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M2_IN1 pin. 
 *        This is a predefined interrupt handler to be used together with the M2_IN1_SetInterruptHandler() method.
 *        This handler is called every time the M2_IN1 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M2_IN1_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M2_IN1 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M2_IN1 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M2_IN1_SetInterruptHandler(void (* interruptHandler)(void)) ; 

/**
 * @ingroup  pinsdriver
 * @brief Default Interrupt Handler for M2_IN2 pin. 
 *        This is a predefined interrupt handler to be used together with the M2_IN2_SetInterruptHandler() method.
 *        This handler is called every time the M2_IN2 ISR is executed. 
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param none
 * @return none
 */
void M2_IN2_DefaultInterruptHandler(void);

/**
 * @ingroup  pinsdriver
 * @brief Interrupt Handler Setter for M2_IN2 pin input-sense-config functionality.
 *        Allows selecting an interrupt handler for M2_IN2 at application runtime
 * @pre PIN_MANAGER_Initialize() has been called at least once
 * @param InterruptHandler function pointer.
 * @return none
 */
void M2_IN2_SetInterruptHandler(void (* interruptHandler)(void)) ; 
#endif /* PINS_H_INCLUDED */
