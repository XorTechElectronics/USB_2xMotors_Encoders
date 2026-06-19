/**
 * TCA0 Generated Driver File
 *
 * @file tca0.c
 *
 * @ingroup tca0_split
 *
 * @brief This file contains the API implementations for TCA0 module in Split (8-bit) mode.
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

#include "../tca0.h"

static void (*TCA0_HCNT_Callback)(void) = NULL;
static void (*TCA0_LCMP0_Callback)(void) = NULL;
static void (*TCA0_LCMP1_Callback)(void) = NULL;
static void (*TCA0_LCMP2_Callback)(void) = NULL;
static void (*TCA0_LCNT_Callback)(void) = NULL;

void TCA0_Initialize(void)  
{
    TCA0.SPLIT.CTRLD = (1 << TCA_SPLIT_SPLITM_bp);  // SPLITM enabled

    TCA0.SPLIT.CTRLB = (1 << TCA_SPLIT_HCMP0EN_bp)   // HCMP0EN enabled
        | (0 << TCA_SPLIT_HCMP1EN_bp)   // HCMP1EN disabled
        | (0 << TCA_SPLIT_HCMP2EN_bp)   // HCMP2EN disabled
        | (1 << TCA_SPLIT_LCMP0EN_bp)   // LCMP0EN enabled
        | (1 << TCA_SPLIT_LCMP1EN_bp)   // LCMP1EN enabled
        | (1 << TCA_SPLIT_LCMP2EN_bp);  // LCMP2EN enabled

    TCA0.SPLIT.CTRLC = (0 << TCA_SPLIT_HCMP0OV_bp)   // HCMP0OV disabled
        | (0 << TCA_SPLIT_HCMP1OV_bp)   // HCMP1OV disabled
        | (0 << TCA_SPLIT_HCMP2OV_bp)   // HCMP2OV disabled
        | (0 << TCA_SPLIT_LCMP0OV_bp)   // LCMP0OV disabled
        | (0 << TCA_SPLIT_LCMP1OV_bp)   // LCMP1OV disabled
        | (0 << TCA_SPLIT_LCMP2OV_bp);  // LCMP2OV disabled

    TCA0.SPLIT.CTRLECLR = (TCA_SPLIT_CMD_NONE_gc)   // CMD NONE
        | (TCA_SPLIT_CMDEN_NONE_gc);  // CMDEN NONE

    TCA0.SPLIT.CTRLESET = (TCA_SPLIT_CMD_NONE_gc)   // CMD NONE
        | (TCA_SPLIT_CMDEN_NONE_gc);  // CMDEN NONE

    TCA0.SPLIT.DBGCTRL = (0 << TCA_SPLIT_DBGRUN_bp);  // DBGRUN disabled

    TCA0.SPLIT.HCMP0 = 0x0;  // HCMP0 0x0

    TCA0.SPLIT.HCMP1 = 0x0;  // HCMP1 0x0

    TCA0.SPLIT.HCMP2 = 0x0;  // HCMP2 0x0

    TCA0.SPLIT.HCNT = 0x0;  // HCNT 0x0

    TCA0.SPLIT.HPER = 0xFFU;  // HPER 0xFF

    TCA0.SPLIT.INTCTRL = (0 << TCA_SPLIT_HUNF_bp)   // HUNF disabled
        | (0 << TCA_SPLIT_LCMP0_bp)   // LCMP0 disabled
        | (0 << TCA_SPLIT_LCMP1_bp)   // LCMP1 disabled
        | (0 << TCA_SPLIT_LCMP2_bp)   // LCMP2 disabled
        | (0 << TCA_SPLIT_LUNF_bp);  // LUNF disabled

    TCA0.SPLIT.INTFLAGS = (0 << TCA_SPLIT_HUNF_bp)   // HUNF disabled
        | (0 << TCA_SPLIT_LCMP0_bp)   // LCMP0 disabled
        | (0 << TCA_SPLIT_LCMP1_bp)   // LCMP1 disabled
        | (0 << TCA_SPLIT_LCMP2_bp)   // LCMP2 disabled
        | (0 << TCA_SPLIT_LUNF_bp);  // LUNF disabled

    TCA0.SPLIT.LCMP0 = 0x0;  // LCMP0 0x0

    TCA0.SPLIT.LCMP1 = 0x0;  // LCMP1 0x0

    TCA0.SPLIT.LCMP2 = 0x0;  // LCMP2 0x0

    TCA0.SPLIT.LCNT = 0x0;  // LCNT 0x0

    TCA0.SPLIT.LPER = 0xFFU;  // LPER 0xFF

    TCA0.SPLIT.CTRLA = (TCA_SPLIT_CLKSEL_DIV1_gc)   // CLKSEL DIV1
        | (1 << TCA_SPLIT_ENABLE_bp)   // ENABLE enabled
        | (0 << TCA_SPLIT_RUNSTDBY_bp);  // RUNSTDBY disabled
}

void TCA0_Deinitialize(void)
{
    TCA0.SPLIT.CTRLA &= ~TCA_SPLIT_ENABLE_bm;

    TCA0.SPLIT.CTRLA = 0x0;
    TCA0.SPLIT.CTRLB = 0x0;
    TCA0.SPLIT.CTRLC = 0x0;
    TCA0.SPLIT.CTRLD = 0x0;

    TCA0.SPLIT.CTRLESET = 0x0;
    TCA0.SPLIT.CTRLECLR = 0x0;    
    
    TCA0.SPLIT.LCNT = 0x0;
    TCA0.SPLIT.LPER = 0xFFU;
    TCA0.SPLIT.HCNT = 0x0;
    TCA0.SPLIT.HPER = 0xFFU;
    TCA0.SPLIT.LCMP0 = 0x0;
    TCA0.SPLIT.LCMP1 = 0x0;
    TCA0.SPLIT.LCMP2 = 0x0;
    TCA0.SPLIT.HCMP0 = 0x0;
    TCA0.SPLIT.HCMP1 = 0x0;
    TCA0.SPLIT.HCMP2 = 0x0;

    TCA0.SPLIT.INTCTRL = 0x0;
    TCA0.SPLIT.INTFLAGS = ~0x0;
}

void TCA0_Start(void)
{
    TCA0.SPLIT.CTRLA |= TCA_SPLIT_ENABLE_bm;
}

void TCA0_Stop(void)
{
    TCA0.SPLIT.CTRLA &= ~TCA_SPLIT_ENABLE_bm;
}

void TCA0_LowCounterSet(uint8_t timerVal)
{
    TCA0.SPLIT.LCNT = timerVal;
}

uint8_t TCA0_LowCounterGet(void)
{
    return TCA0.SPLIT.LCNT;
}

void TCA0_HighCounterSet(uint8_t timerVal)
{
    TCA0.SPLIT.HCNT = timerVal;
}

uint8_t TCA0_HighCounterGet(void)
{
    return TCA0.SPLIT.HCNT;
}

void TCA0_HighPeriodSet(uint8_t periodVal)
{
    TCA0.SPLIT.HPER = periodVal;
}

void TCA0_LowPeriodSet(uint8_t periodVal)
{
    TCA0.SPLIT.LPER = periodVal;
}

uint8_t TCA0_HighPeriodGet(void)
{
    return TCA0.SPLIT.HPER;
}

uint8_t TCA0_LowPeriodGet(void)
{
    return TCA0.SPLIT.LPER;
}

uint8_t TCA0_MaxCountGet(void)
{
    return TCA0_MAX_COUNT;
}

void TCA0_HUNFInterruptFlagClear(void)
{
    TCA0.SPLIT.INTFLAGS = TCA_SPLIT_HUNF_bm; /* Clear High-Byte Underflow Interrupt Flag */
}

bool TCA0_HUNFInterruptStatusGet(void)
{
    return ((TCA0.SPLIT.INTFLAGS & TCA_SPLIT_HUNF_bm) > 0);
}

void TCA0_LUNFInterruptFlagClear(void)
{
    TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LUNF_bm; /* Clear Low-Byte Underflow Interrupt Flag */
}

bool TCA0_LUNFInterruptStatusGet(void)
{
    return ((TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LUNF_bm) > 0);
}

void TCA0_LCMP0InterruptFlagClear(void)
{
    TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP0_bm; /* Clear Low-Byte Compare Channel-0 Interrupt Flag */
}

bool TCA0_LCMP0InterruptStatusGet(void)
{
    return ((TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP0_bm) > 0);
}

void TCA0_LCMP1InterruptFlagClear(void)
{
    TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP1_bm; /* Clear Low-Byte Compare Channel-1 Interrupt Flag */
}

bool TCA0_LCMP1InterruptStatusGet(void)
{
    return ((TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP1_bm) > 0);
}

void TCA0_LCMP2InterruptFlagClear(void)
{
    TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP2_bm; /* Clear Low-Byte Compare Channel-2 Interrupt Flag */
}

bool TCA0_LCMP2InterruptStatusGet(void)
{
    return ((TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP2_bm) > 0);
}

void TCA0_Tasks(void)
{
    if(0 != (TCA0.SPLIT.INTFLAGS & TCA_SPLIT_HUNF_bm))
    {
        if(NULL != TCA0_HCNT_Callback)
        {
            (*TCA0_HCNT_Callback)();
        }
        TCA0.SPLIT.INTFLAGS = TCA_SPLIT_HUNF_bm;
    }
    
    if(0 != (TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP0_bm))
    {
        if(NULL != TCA0_LCMP0_Callback)
        {
            (*TCA0_LCMP0_Callback)();
        }
        TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP0_bm;
    }
    
    if(0 != (TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP1_bm))
    {
        if(NULL != TCA0_LCMP1_Callback)
        {
            (*TCA0_LCMP1_Callback)();
        }
        TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP1_bm;
    }
    
    if(0 != (TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LCMP2_bm))
    {
        if(NULL != TCA0_LCMP2_Callback)
        {
            (*TCA0_LCMP2_Callback)();
        }
        TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LCMP2_bm;
    }
    
    if(0 != (TCA0.SPLIT.INTFLAGS & TCA_SPLIT_LUNF_bm))
    {
         if(NULL != TCA0_LCNT_Callback)
        {
            (*TCA0_LCNT_Callback)();
        }
        TCA0.SPLIT.INTFLAGS = TCA_SPLIT_LUNF_bm;
    }
}

void TCA0_HighCountCallbackRegister(TCA0_cb_t CallbackHandler)
{
    TCA0_HCNT_Callback = CallbackHandler;
}

void TCA0_LowCompare0CallbackRegister(TCA0_cb_t CallbackHandler)
{
    TCA0_LCMP0_Callback = CallbackHandler;
}

void TCA0_LowCompare1CallbackRegister(TCA0_cb_t CallbackHandler)
{
    TCA0_LCMP1_Callback = CallbackHandler;
}

void TCA0_LowCompare2CallbackRegister(TCA0_cb_t CallbackHandler)
{
    TCA0_LCMP2_Callback = CallbackHandler;
}

void TCA0_LowCountCallbackRegister(TCA0_cb_t CallbackHandler)
{
    TCA0_LCNT_Callback = CallbackHandler;
}