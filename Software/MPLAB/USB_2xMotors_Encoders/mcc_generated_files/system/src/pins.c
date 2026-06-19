/**
 * Generated Driver File
 * 
 * @file pins.c
 * 
 * @ingroup  pinsdriver
 * 
 * @brief This is generated driver implementation for pins. 
 *        This file provides implementations for pin APIs for all pins selected in the GUI.
 *
 * @version Driver Version 1.1.0
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

#include "../pins.h"

static void (*IO_PA1_InterruptHandler)(void);
static void (*IO_PA0_InterruptHandler)(void);
static void (*IO_PF0_InterruptHandler)(void);
static void (*IO_PF1_InterruptHandler)(void);
static void (*IO_PF2_InterruptHandler)(void);
static void (*IO_PF3_InterruptHandler)(void);
static void (*SS_InterruptHandler)(void);
static void (*LED_InterruptHandler)(void);
static void (*M1_IN2_InterruptHandler)(void);
static void (*M1_IN1_InterruptHandler)(void);
static void (*M01_STBY_InterruptHandler)(void);
static void (*M0_IN1_InterruptHandler)(void);
static void (*M23_STBY_InterruptHandler)(void);
static void (*M3_IN2_InterruptHandler)(void);
static void (*M3_IN1_InterruptHandler)(void);
static void (*M0_IN2_InterruptHandler)(void);
static void (*M2_IN1_InterruptHandler)(void);
static void (*M2_IN2_InterruptHandler)(void);

void PIN_MANAGER_Initialize()
{

  /* OUT Registers Initialization */
    PORTA.OUT = 0x1;
    PORTC.OUT = 0x0;
    PORTD.OUT = 0x0;
    PORTF.OUT = 0x0;

  /* DIR Registers Initialization */
    PORTA.DIR = 0x81;
    PORTC.DIR = 0x8;
    PORTD.DIR = 0xFF;
    PORTF.DIR = 0x3F;

  /* PINxCTRL registers Initialization */
    PORTA.PIN0CTRL = 0x0;
    PORTA.PIN1CTRL = 0x0;
    PORTA.PIN2CTRL = 0x0;
    PORTA.PIN3CTRL = 0x0;
    PORTA.PIN4CTRL = 0x0;
    PORTA.PIN5CTRL = 0x0;
    PORTA.PIN6CTRL = 0x0;
    PORTA.PIN7CTRL = 0x0;
    PORTC.PIN0CTRL = 0x0;
    PORTC.PIN1CTRL = 0x0;
    PORTC.PIN2CTRL = 0x0;
    PORTC.PIN3CTRL = 0x0;
    PORTC.PIN4CTRL = 0x0;
    PORTC.PIN5CTRL = 0x0;
    PORTC.PIN6CTRL = 0x0;
    PORTC.PIN7CTRL = 0x0;
    PORTD.PIN0CTRL = 0x0;
    PORTD.PIN1CTRL = 0x0;
    PORTD.PIN2CTRL = 0x0;
    PORTD.PIN3CTRL = 0x0;
    PORTD.PIN4CTRL = 0x0;
    PORTD.PIN5CTRL = 0x0;
    PORTD.PIN6CTRL = 0x0;
    PORTD.PIN7CTRL = 0x0;
    PORTF.PIN0CTRL = 0x0;
    PORTF.PIN1CTRL = 0x0;
    PORTF.PIN2CTRL = 0x0;
    PORTF.PIN3CTRL = 0x0;
    PORTF.PIN4CTRL = 0x0;
    PORTF.PIN5CTRL = 0x0;
    PORTF.PIN6CTRL = 0x0;
    PORTF.PIN7CTRL = 0x0;

  /* PORTMUX Initialization */
    PORTMUX.CCLROUTEA = 0x0;
    PORTMUX.EVSYSROUTEA = 0x0;
    PORTMUX.SPIROUTEA = 0x0;
    PORTMUX.TCAROUTEA = 0x5;
    PORTMUX.TCBROUTEA = 0x0;
    PORTMUX.TWIROUTEA = 0x0;
    PORTMUX.USARTROUTEA = 0x0;

  // register default ISC callback functions at runtime; use these methods to register a custom function
    IO_PA1_SetInterruptHandler(IO_PA1_DefaultInterruptHandler);
    IO_PA0_SetInterruptHandler(IO_PA0_DefaultInterruptHandler);
    IO_PF0_SetInterruptHandler(IO_PF0_DefaultInterruptHandler);
    IO_PF1_SetInterruptHandler(IO_PF1_DefaultInterruptHandler);
    IO_PF2_SetInterruptHandler(IO_PF2_DefaultInterruptHandler);
    IO_PF3_SetInterruptHandler(IO_PF3_DefaultInterruptHandler);
    SS_SetInterruptHandler(SS_DefaultInterruptHandler);
    LED_SetInterruptHandler(LED_DefaultInterruptHandler);
    M1_IN2_SetInterruptHandler(M1_IN2_DefaultInterruptHandler);
    M1_IN1_SetInterruptHandler(M1_IN1_DefaultInterruptHandler);
    M01_STBY_SetInterruptHandler(M01_STBY_DefaultInterruptHandler);
    M0_IN1_SetInterruptHandler(M0_IN1_DefaultInterruptHandler);
    M23_STBY_SetInterruptHandler(M23_STBY_DefaultInterruptHandler);
    M3_IN2_SetInterruptHandler(M3_IN2_DefaultInterruptHandler);
    M3_IN1_SetInterruptHandler(M3_IN1_DefaultInterruptHandler);
    M0_IN2_SetInterruptHandler(M0_IN2_DefaultInterruptHandler);
    M2_IN1_SetInterruptHandler(M2_IN1_DefaultInterruptHandler);
    M2_IN2_SetInterruptHandler(M2_IN2_DefaultInterruptHandler);
}

/**
  Allows selecting an interrupt handler for IO_PA1 at application runtime
*/
void IO_PA1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PA1_InterruptHandler = interruptHandler;
}

void IO_PA1_DefaultInterruptHandler(void)
{
    // add your IO_PA1 interrupt custom code
    // or set custom function using IO_PA1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for IO_PA0 at application runtime
*/
void IO_PA0_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PA0_InterruptHandler = interruptHandler;
}

void IO_PA0_DefaultInterruptHandler(void)
{
    // add your IO_PA0 interrupt custom code
    // or set custom function using IO_PA0_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for IO_PF0 at application runtime
*/
void IO_PF0_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PF0_InterruptHandler = interruptHandler;
}

void IO_PF0_DefaultInterruptHandler(void)
{
    // add your IO_PF0 interrupt custom code
    // or set custom function using IO_PF0_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for IO_PF1 at application runtime
*/
void IO_PF1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PF1_InterruptHandler = interruptHandler;
}

void IO_PF1_DefaultInterruptHandler(void)
{
    // add your IO_PF1 interrupt custom code
    // or set custom function using IO_PF1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for IO_PF2 at application runtime
*/
void IO_PF2_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PF2_InterruptHandler = interruptHandler;
}

void IO_PF2_DefaultInterruptHandler(void)
{
    // add your IO_PF2 interrupt custom code
    // or set custom function using IO_PF2_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for IO_PF3 at application runtime
*/
void IO_PF3_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    IO_PF3_InterruptHandler = interruptHandler;
}

void IO_PF3_DefaultInterruptHandler(void)
{
    // add your IO_PF3 interrupt custom code
    // or set custom function using IO_PF3_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for SS at application runtime
*/
void SS_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    SS_InterruptHandler = interruptHandler;
}

void SS_DefaultInterruptHandler(void)
{
    // add your SS interrupt custom code
    // or set custom function using SS_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for LED at application runtime
*/
void LED_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    LED_InterruptHandler = interruptHandler;
}

void LED_DefaultInterruptHandler(void)
{
    // add your LED interrupt custom code
    // or set custom function using LED_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M1_IN2 at application runtime
*/
void M1_IN2_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M1_IN2_InterruptHandler = interruptHandler;
}

void M1_IN2_DefaultInterruptHandler(void)
{
    // add your M1_IN2 interrupt custom code
    // or set custom function using M1_IN2_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M1_IN1 at application runtime
*/
void M1_IN1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M1_IN1_InterruptHandler = interruptHandler;
}

void M1_IN1_DefaultInterruptHandler(void)
{
    // add your M1_IN1 interrupt custom code
    // or set custom function using M1_IN1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M01_STBY at application runtime
*/
void M01_STBY_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M01_STBY_InterruptHandler = interruptHandler;
}

void M01_STBY_DefaultInterruptHandler(void)
{
    // add your M01_STBY interrupt custom code
    // or set custom function using M01_STBY_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M0_IN1 at application runtime
*/
void M0_IN1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M0_IN1_InterruptHandler = interruptHandler;
}

void M0_IN1_DefaultInterruptHandler(void)
{
    // add your M0_IN1 interrupt custom code
    // or set custom function using M0_IN1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M23_STBY at application runtime
*/
void M23_STBY_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M23_STBY_InterruptHandler = interruptHandler;
}

void M23_STBY_DefaultInterruptHandler(void)
{
    // add your M23_STBY interrupt custom code
    // or set custom function using M23_STBY_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M3_IN2 at application runtime
*/
void M3_IN2_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M3_IN2_InterruptHandler = interruptHandler;
}

void M3_IN2_DefaultInterruptHandler(void)
{
    // add your M3_IN2 interrupt custom code
    // or set custom function using M3_IN2_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M3_IN1 at application runtime
*/
void M3_IN1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M3_IN1_InterruptHandler = interruptHandler;
}

void M3_IN1_DefaultInterruptHandler(void)
{
    // add your M3_IN1 interrupt custom code
    // or set custom function using M3_IN1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M0_IN2 at application runtime
*/
void M0_IN2_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M0_IN2_InterruptHandler = interruptHandler;
}

void M0_IN2_DefaultInterruptHandler(void)
{
    // add your M0_IN2 interrupt custom code
    // or set custom function using M0_IN2_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M2_IN1 at application runtime
*/
void M2_IN1_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M2_IN1_InterruptHandler = interruptHandler;
}

void M2_IN1_DefaultInterruptHandler(void)
{
    // add your M2_IN1 interrupt custom code
    // or set custom function using M2_IN1_SetInterruptHandler()
}
/**
  Allows selecting an interrupt handler for M2_IN2 at application runtime
*/
void M2_IN2_SetInterruptHandler(void (* interruptHandler)(void)) 
{
    M2_IN2_InterruptHandler = interruptHandler;
}

void M2_IN2_DefaultInterruptHandler(void)
{
    // add your M2_IN2 interrupt custom code
    // or set custom function using M2_IN2_SetInterruptHandler()
}
ISR(PORTA_PORT_vect)
{ 
    // Call the interrupt handler for the callback registered at runtime
    if(VPORTA.INTFLAGS & PORT_INT1_bm)
    {
       IO_PA1_InterruptHandler(); 
    }
    if(VPORTA.INTFLAGS & PORT_INT0_bm)
    {
       IO_PA0_InterruptHandler(); 
    }
    if(VPORTA.INTFLAGS & PORT_INT7_bm)
    {
       SS_InterruptHandler(); 
    }
    /* Clear interrupt flags */
    VPORTA.INTFLAGS = 0xff;
}

ISR(PORTC_PORT_vect)
{ 
    // Call the interrupt handler for the callback registered at runtime
    if(VPORTC.INTFLAGS & PORT_INT3_bm)
    {
       LED_InterruptHandler(); 
    }
    /* Clear interrupt flags */
    VPORTC.INTFLAGS = 0xff;
}

ISR(PORTD_PORT_vect)
{ 
    // Call the interrupt handler for the callback registered at runtime
    if(VPORTD.INTFLAGS & PORT_INT0_bm)
    {
       M1_IN2_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT1_bm)
    {
       M1_IN1_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT2_bm)
    {
       M01_STBY_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT3_bm)
    {
       M0_IN1_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT4_bm)
    {
       M23_STBY_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT5_bm)
    {
       M3_IN2_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT6_bm)
    {
       M3_IN1_InterruptHandler(); 
    }
    if(VPORTD.INTFLAGS & PORT_INT7_bm)
    {
       M0_IN2_InterruptHandler(); 
    }
    /* Clear interrupt flags */
    VPORTD.INTFLAGS = 0xff;
}

ISR(PORTF_PORT_vect)
{ 
    // Call the interrupt handler for the callback registered at runtime
    if(VPORTF.INTFLAGS & PORT_INT0_bm)
    {
       IO_PF0_InterruptHandler(); 
    }
    if(VPORTF.INTFLAGS & PORT_INT1_bm)
    {
       IO_PF1_InterruptHandler(); 
    }
    if(VPORTF.INTFLAGS & PORT_INT2_bm)
    {
       IO_PF2_InterruptHandler(); 
    }
    if(VPORTF.INTFLAGS & PORT_INT3_bm)
    {
       IO_PF3_InterruptHandler(); 
    }
    if(VPORTF.INTFLAGS & PORT_INT4_bm)
    {
       M2_IN1_InterruptHandler(); 
    }
    if(VPORTF.INTFLAGS & PORT_INT5_bm)
    {
       M2_IN2_InterruptHandler(); 
    }
    /* Clear interrupt flags */
    VPORTF.INTFLAGS = 0xff;
}

/**
 End of File
*/