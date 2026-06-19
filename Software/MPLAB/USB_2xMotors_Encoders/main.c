 /*
 * MAIN Generated Driver File
 * 
 * @file main.c
 * 
 * @defgroup main MAIN
 * 
 * @brief This is the generated driver implementation file for the MAIN driver.
 *
 * @version MAIN Driver Version 1.0.2
 *
 * @version Package Version: 3.1.2
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
#include "mcc_generated_files/system/system.h"

#include "usb_cdc.h"
#include "usb_cdc_virtual_serial_port.h"

#include "../timer/delay.h"



// USB status variables
    volatile RETURN_CODE_t      usbStatus   = SUCCESS;
    volatile CDC_RETURN_CODE_t  cdcStatus   = CDC_SUCCESS;
    
/*
    Main application
*/
int main(void)
{
    // Data variable
        uint8_t cdcData;  
        uint8_t usartData;
        
    SYSTEM_Initialize();
        
    // Start USB operations
        usbStatus = USB_Start();   
        
    //Test
        //M01_STBY_SetHigh();
        //M0_IN1_SetHigh();
        //M0_IN2_SetLow();
        //TCA0.SPLIT.LCMP0 = 0xEF; 

    while(1)
    {        
        // Handle USB Transfers
            usbStatus = USBDevice_Handle();
        
        // If USB error detected
        if (SUCCESS != usbStatus)
        {
            while (1)
            {
                LED_Toggle();
                DELAY_milliseconds(100);
            }
        }
        else                      
        {
            uint8_t count = 0x00;    

            //Check and parse anything received
            while ( USB_CDCRead(&cdcData) == CDC_SUCCESS )  // Read one byte at a time
            {   
                USART0_Write(cdcData);
                
                switch ( count ) {
                    case 0:                             //Motor Standby
                        LED_Toggle();
                    
                        //Bit 0 to standby Motors 0 and 1
                            if ( cdcData&(1<<0) )   {   M01_STBY_SetHigh(); }
                            else                    {   M01_STBY_SetLow();  }
                        
                        //Bit 1 to standby Motors 2 and 3
                            if ( cdcData&(1<<1) )   {   M23_STBY_SetHigh(); }
                            else                    {   M23_STBY_SetLow();  }                        
                        
                    case 1:                             //M0 Control                    
                        //Bit 0 to M0_IN1
                            if ( cdcData&(1<<0) )   {   M0_IN1_SetHigh(); }
                            else                    {   M0_IN1_SetLow();  }
                        
                        //Bit 1 to M0_IN2
                            if ( cdcData&(1<<1) )   {   M0_IN2_SetHigh(); }
                            else                    {   M0_IN2_SetLow();  }                                            
                        
                    case 2:                             //M0 PWM       
                        TCA0.SPLIT.LCMP1 = cdcData;     //WO1 from IC
                    break;

                    case 3:                             //M1 Control                    
                        //Bit 0 to M1_IN1
                            if ( cdcData&(1<<0) )   {   M1_IN1_SetHigh(); }
                            else                    {   M1_IN1_SetLow();  }
                        
                        //Bit 1 to M1_IN2
                            if ( cdcData&(1<<1) )   {   M1_IN2_SetHigh(); }
                            else                    {   M1_IN2_SetLow();  }                     
                    
                    case 4:                             //M1 PWM
                        TCA0.SPLIT.LCMP0 = cdcData;     //WO0 from IC
                    break;

                    case 5:                             //M2 Control                    
                        //Bit 0 to M1_IN1
                            if ( cdcData&(1<<0) )   {   M2_IN1_SetHigh(); }
                            else                    {   M2_IN1_SetLow();  }
                        
                        //Bit 1 to M1_IN2
                            if ( cdcData&(1<<1) )   {   M2_IN2_SetHigh(); }
                            else                    {   M2_IN2_SetLow();  }                                         
                    
                    case 6:                             //M2 PWM                        
                        TCA0.SPLIT.HCMP0 = cdcData;     //WO3 from IC
                    break;
                    
                    case 7:                             //M3 Control                    
                        //Bit 0 to M1_IN1
                            if ( cdcData&(1<<0) )   {   M3_IN1_SetHigh(); }
                            else                    {   M3_IN1_SetLow();  }
                        
                        //Bit 1 to M1_IN2
                            if ( cdcData&(1<<1) )   {   M3_IN2_SetHigh(); }
                            else                    {   M3_IN2_SetLow();  }                                         
                    
                    case 8:                             //M3 PWM
                        TCA0.SPLIT.LCMP2 = cdcData;     //WO2 from IC
                    break;                    
                    
                    default:
                        
                    break;
                }
                    
            
                
                count = count + 1;
            }


            // Running CDC Virtual Serial Port handler
                usbStatus = USB_CDCVirtualSerialPortHandler();                                 
        }        
        
        //LED_Toggle();
        //DELAY_milliseconds(2000);
    }    
}























