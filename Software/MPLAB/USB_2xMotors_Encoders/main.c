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
© [2026] Microchip Technology Inc. and its subsidiaries.

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

#include <stdio.h>
#include "string.h"

#include "usb_cdc.h"
#include "usb_cdc_virtual_serial_port.h"

#include "../timer/delay.h"

// USB status variables
    volatile RETURN_CODE_t      usbStatus   = SUCCESS;
    volatile CDC_RETURN_CODE_t  cdcStatus   = CDC_SUCCESS;
    
//Encoder Counters
    volatile uint8_t    m1_prev_state = 0;    
    volatile long       motor1_count  = 0;
    
    volatile uint8_t    m2_prev_state = 0;
    volatile long       motor2_count  = 0;    
    
    const int8_t QEM_TABLE[16] = {
         0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0
    };    
    
    
static inline uint8_t read_encoder_state_M1(void) {
    uint8_t a = M1_encA_GetValue() ? 1 : 0;
    uint8_t b = M1_encB_GetValue() ? 1 : 0;
    return (a << 1) | b;
}    

static inline uint8_t read_encoder_state_M2(void) {
    uint8_t a = M2_encA_GetValue() ? 1 : 0;
    uint8_t b = M2_encB_GetValue() ? 1 : 0;
    return (a << 1) | b;
}
    
//##############################################################################    
//ISRs    
//##############################################################################
    // Add a separate counter just to count raw ISR calls, 
    // completely independent of the quadrature logic:
        volatile uint32_t m1_isr_call_count = 0;    



    // Motor 1 encoder ISR ? triggered on encA's and encB's rising & falling edge
    void M1_enc_ISR() {    
        m1_isr_call_count++;
        
        uint8_t new_state   = read_encoder_state_M1();
        uint8_t index       = (m1_prev_state << 2) | new_state;
        int8_t delta        = QEM_TABLE[index];
        motor1_count       += delta;
                
        // TEMP DEBUG: send raw values out so we can see the actual sequence
        //SendDebugBytes(m1_prev_state, new_state, index, delta);  // however you want to get this out ? UART print, USB packet, even just blink a pattern
                
        m1_prev_state = new_state;
    } 

    // Motor 2 encoder ISR ? triggered on encA's and encB's rising & falling edge
    void M2_enc_ISR() {
        uint8_t new_state   = read_encoder_state_M2();
        uint8_t index       = (m2_prev_state << 2) | new_state;
        int8_t delta        = QEM_TABLE[index];
        motor2_count       += delta;
                
        // TEMP DEBUG: send raw values out so we can see the actual sequence
        //SendDebugBytes(m2_prev_state, new_state, index, delta);  // however you want to get this out ? UART print, USB packet, even just blink a pattern
                
        m2_prev_state = new_state;
    } 
    
//##############################################################################    
//USB CDC Send functions
//##############################################################################    
    
    void SendEncoderDataBinary(long enc1, long enc2)
    {
        uint8_t packet[9];
        packet[0] = 0xAA;  // sync byte so host can find the start

        memcpy(&packet[1], &enc1, sizeof(long));
        memcpy(&packet[5], &enc2, sizeof(long));

        for (int i = 0; i < 9; i++)
        {
            if (USB_CDCWrite(packet[i]) == CDC_BUFFER_FULL)
            {
                // byte was dropped ? buffer was full, decide how you want to handle this
            }
        }
    }   
    
    void SendDebugBytes(uint8_t prev_state, uint8_t new_state, uint8_t index, int8_t delta)
    {
        uint8_t packet[5];
        packet[0] = 0xBB;
        packet[1] = prev_state;
        packet[2] = new_state;
        packet[3] = index;
        packet[4] = (uint8_t)delta;

        for (int i = 0; i < 5; i++)
        {
            USB_CDCWrite(packet[i]);
        }
    }    
  
//##############################################################################    
//UART functions
//##############################################################################     
void UART_WriteByte(uint8_t byte) {
    while (!USART0_IsTxReady());
    USART0_Write(byte);
}    
    
    
void UART_PrintLong(int32_t value) {
    char buf[12];
    int8_t i = 0;

    if (value == INT32_MIN) {
        const char *s = "-2147483648\r\n";
        while (*s) { UART_WriteByte((uint8_t)*s++); }// DELAY_milliseconds(5); }
        return;
    }

    if (value < 0) {
        UART_WriteByte('-');
        //DELAY_milliseconds(5);
        value = -value;
    }

    if (value == 0) {
        UART_WriteByte('0');
    } else {
        while (value > 0) {
            buf[i++] = '0' + (value % 10);
            value /= 10;
        }
        for (int8_t j = i - 1; j >= 0; j--) {
            UART_WriteByte((uint8_t)buf[j]);
            //DELAY_milliseconds(5);
        }
    }

    UART_WriteByte('\r');
    //DELAY_milliseconds(5);
    UART_WriteByte('\n');
    //DELAY_milliseconds(5);
} 
    
    
    
    
/*
    Main application
*/

int main(void)
{
    // Data variable
        uint8_t cdcData;  
        
    SYSTEM_Initialize();
    
    //Encoder State Initialization
        m1_prev_state = read_encoder_state_M1();
        m2_prev_state = read_encoder_state_M2();
        
    //Interrupt on both edges of encA and encB, firing off the same ISR
        M1_encA_SetInterruptHandler ( M1_enc_ISR );
        M1_encB_SetInterruptHandler ( M1_enc_ISR );
    
        M2_encA_SetInterruptHandler ( M2_enc_ISR );
        M2_encB_SetInterruptHandler ( M2_enc_ISR );
        
    // Start USB operations
        usbStatus = USB_Start();   
        
        

        
    //Test
        //M01_STBY_SetHigh();
        //M0_IN1_SetHigh();
        //M0_IN2_SetLow();
        //TCA0.SPLIT.LCMP0 = 0xEF; 
        //long test  = 29997; 
        //UART_PrintLong ( test );    
        
    // Add near top of main, before while(1):
    static uint16_t enc_send_counter = 0;        

    while(1)
    {        
        // Handle USB Transfers
            usbStatus = USBDevice_Handle();
        
        // If USB error detected
        if (SUCCESS != usbStatus)
        {
            while (1)
            {
                LED0_Toggle();
                DELAY_milliseconds(100);
            }
        }
        else                      
        {
            uint8_t count = 0x00;    
            
            // Read encoders safely into loop
//            cli();
//                long motor1_encoders_safe = motor1_count;
//                long motor2_encoders_safe = motor2_count;
//                
//                //long motor1_encoders_safe = 67;
//               //long motor2_encoders_safe = 45;
//            sei();            
//            
//            SendEncoderDataBinary( motor1_encoders_safe, motor2_encoders_safe );
            
            // Only send encoder data every N iterations rather than
            // every loop. Tune N until delta is non-zero in the GUI.
            // At ~1us/loop you'd need N~10000 for 10ms; at ~10us/loop
            // N~1000. Start with 1000 and adjust.
            enc_send_counter++;
            if (enc_send_counter >= 3000)
            {
                LED0_Toggle();
                
                enc_send_counter = 0;
                cli();
                    long motor1_encoders_safe = motor1_count;
                    long motor2_encoders_safe = motor2_count;
                sei();
                SendEncoderDataBinary(motor1_encoders_safe, motor2_encoders_safe);
            }            
            
            
            
            

            //Check and parse anything received
            while ( USB_CDCRead(&cdcData) == CDC_SUCCESS )  // Read one byte at a time
            {   
                //USART0_Write(cdcData);
                
                switch ( count ) {
                    case 0:                             //Motor Standby
                        LED0_Toggle();
                    
                        //Bit 0 to standby Motors 0 and 1
                            if ( cdcData&(1<<0) )   {   M01_STBY_SetHigh(); }
                            else                    {   M01_STBY_SetLow();  }
                        
//                        //Bit 1 to standby Motors 2 and 3
//                            if ( cdcData&(1<<1) )   {   M23_STBY_SetHigh(); }
//                            else                    {   M23_STBY_SetLow();  }
                    break;
                        
                    case 1:                             //M0 Control                    
                        //Bit 0 to M0_IN1
                            if ( cdcData&(1<<0) )   {   M0_IN1_SetHigh(); }
                            else                    {   M0_IN1_SetLow();  }
                        
                        //Bit 1 to M0_IN2
                            if ( cdcData&(1<<1) )   {   M0_IN2_SetHigh(); }
                            else                    {   M0_IN2_SetLow();  }  
                            
                        //Debug 
                        //motor1_encoders_safe onto UART
                            UART_PrintLong ( motor1_count );
                            UART_PrintLong ( m1_isr_call_count );
                            
                    break;
                            
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
                    break;
                    
                    case 4:                             //M1 PWM
                        TCA0.SPLIT.LCMP0 = cdcData;     //WO0 from IC
                    break;
                    
                    default:
                        
                    break;
                }
                                    
                count = count + 1;
            }


            // Running CDC Virtual Serial Port handler
                usbStatus = USB_CDCVirtualSerialPortHandler();                                 
        }        
        
        //LED0_Toggle();
        //DELAY_milliseconds(10);
    }    
}























