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

#include <math.h>
#include <stdio.h>
#include "string.h"

#include "usb_cdc.h"
#include "usb_cdc_virtual_serial_port.h"

#include "../timer/delay.h"

// Each encoder tick fires 4 interrupt on each edge of encA
    #define QUADRATURE_DECODE  4   // 4x decoding: both edges, both channels

// Packet Sizing from the Host to set settings or commands
    #define CMD_PACKET_SIZE     12
    #define CONFIG_PACKET_SIZE  20

// TCA0 underflow timebase for RPM calculation
// At 24MHz / prescaler 4 / 256 counts = 23,437 Hz overflow rate
// 2344 overflows = ~100ms RPM update window
    #define TCA0_OVERFLOW_RATE  23437UL
    #define RPM_WINDOW_MS       100UL
    #define RPM_WINDOW_TICKS    ((TCA0_OVERFLOW_RATE * RPM_WINDOW_MS) / 1000UL)  // 2344



// USB status variables
    volatile RETURN_CODE_t      usbStatus   = SUCCESS;
    volatile CDC_RETURN_CODE_t  cdcStatus   = CDC_SUCCESS;
    
//Interrupt counters 
    volatile uint16_t   tca0_underflow_count    = 0;
    volatile bool       rpm_window_ready        = false;    
    
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
        
    
//M1_encA_GetValue returns 0x40, depending on port position as a '1' so convert here to pin value
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

// Snapshot values written by main loop, read by send function
    volatile int32_t  motor1_rpm_x10 = 0;
    volatile int32_t  motor2_rpm_x10 = 0;
     
// PID Controller
    typedef struct {
        float    kp;
        float    ki;
        float    kd;
        float    setpoint_rpm;
        float    integral;
        float    integral_limit;
        float    prev_error;
        uint8_t  pwm_output;
        bool     enabled;
    } PID_t;

    PID_t pid[2];  // index 0 = motor 1, index 1 = motor 2    

// Per-motor configuration received from GUI
    typedef struct {
        uint16_t ppr;
        float    kp;
        float    ki;
        float    kd;
        float    integral_limit;
    } MotorConfig_t;

    MotorConfig_t motor_config[2];
    
//##############################################################################    
//SETTINGs and COMMANDs from Host
//##############################################################################
    typedef enum {
        WAIT_HEADER,      // waiting for 0x55 or 0xBB
        READ_COMMAND,     // reading remaining 11 bytes of command packet
        READ_CONFIG       // reading remaining 19 bytes of config packet
    } RxState_t;

    RxState_t rx_state        = WAIT_HEADER;
    uint8_t   rx_buffer[20];  // big enough for largest packet
    uint8_t   rx_count        = 0;    

//##############################################################################    
//ISRs    
//##############################################################################
    // Motor 1 encoder ISR ? triggered on encA's and encB's rising & falling edge
    void M1_enc_ISR() {    
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
    
    // ISR ? TCA0 underflow to time the RPM Maths --- keep this as short as possible
    void TCA0_Underflow_ISR(void)
    {
        tca0_underflow_count++;
        if (tca0_underflow_count >= RPM_WINDOW_TICKS)
        {
            tca0_underflow_count = 0;
            rpm_window_ready    = true;  // signal main loop, nothing else
        }
    }    
    
//##############################################################################    
//USB CDC Received so process
//##############################################################################       
    void ProcessCommandPacket(uint8_t *buf) {
        // buf[0]  = 0x55 header
        // buf[1]  = enable flags
        // buf[2]  = M1 direction bits
        // buf[3]  = M1 PWM
        // buf[4]  = M2 direction bits
        // buf[5]  = M2 PWM
        // buf[6]  = M1 PID enable
        // buf[7]  = M1 setpoint high byte  } motor shaft RPM * 10
        // buf[8]  = M1 setpoint low byte   }
        // buf[9]  = M2 PID enable
        // buf[10] = M2 setpoint high byte
        // buf[11] = M2 setpoint low byte

        LED0_Toggle();
        
        UART_PrintLong((int32_t)buf[0]);  // should print 85 (0x55)
        UART_PrintLong((int32_t)buf[1]);  // should print 3
        UART_PrintLong((int32_t)buf[2]);  // should print direction
        UART_PrintLong((int32_t)buf[3]);  // should print PWM      

        // Enable flags
        if (buf[1] & (1<<0))    { M01_STBY_SetHigh(); }
        else                    { M01_STBY_SetLow();  }

        // Motor 1 direction
        if (buf[2] & (1<<0))    { M0_IN1_SetHigh(); } else { M0_IN1_SetLow(); }
        if (buf[2] & (1<<1))    { M0_IN2_SetHigh(); } else { M0_IN2_SetLow(); }

        // Motor 1 PWM (manual mode only - ignored if PID enabled)
        if (!pid[0].enabled)
            TCA0.SPLIT.LCMP1 = buf[3];

        // Motor 2 direction
        if (buf[4] & (1<<0)) { M1_IN1_SetHigh(); } else { M1_IN1_SetLow(); }
        if (buf[4] & (1<<1)) { M1_IN2_SetHigh(); } else { M1_IN2_SetLow(); }

        // Motor 2 PWM (manual mode only)
        if (!pid[1].enabled)
            TCA0.SPLIT.LCMP0 = buf[5];
        
        // Store previous enabled state before updating
        bool pid0_was_enabled = pid[0].enabled;
        bool pid1_was_enabled = pid[1].enabled;        

        // Motor 1 Enable
        pid[0].enabled      = buf[6];

        // Motor 2 Enable
        pid[1].enabled      = buf[9];
               
        //Setpoints
        // Cast to uint16_t before shifting ? on 8-bit AVR, uint8_t << 8 overflows to 0
        pid[0].setpoint_rpm = (float)(((uint16_t)buf[7]  << 8) | buf[8])  / 10.0f;
        pid[1].setpoint_rpm = (float)(((uint16_t)buf[10] << 8) | buf[11]) / 10.0f;        
        
        
        

        // Only zero PWM if PID just transitioned from enabled -> disabled
        if (pid0_was_enabled && !pid[0].enabled) { TCA0.SPLIT.LCMP1 = 0; pid[0].integral = 0.0f; }
        if (pid1_was_enabled && !pid[1].enabled) { TCA0.SPLIT.LCMP0 = 0; pid[1].integral = 0.0f; }
        
        
        //Debug...
        UART_PrintString("M2 PID:"); UART_PrintLong((int32_t)buf[9]);
        UART_PrintString("M2 SP:");  UART_PrintLong((int32_t)((buf[10] << 8) | buf[11]));        
    }    
    
    void ProcessConfigPacket(uint8_t *buf) {
        // buf[0]     = 0xBB header
        // buf[1]     = motor ID (1 or 2)
        // buf[2-3]   = PPR as uint16
        // buf[4-7]   = Kp as float
        // buf[8-11]  = Ki as float
        // buf[12-15] = Kd as float
        // buf[16-19] = integral limit as float

        uint8_t motor_id = buf[1];
        
        if (motor_id < 1 || motor_id > 2) return;
        
        uint8_t idx = motor_id - 1;

        memcpy(&motor_config[idx].ppr,            &buf[2],  sizeof(uint16_t));
        memcpy(&motor_config[idx].kp,             &buf[4],  sizeof(float));
        memcpy(&motor_config[idx].ki,             &buf[8],  sizeof(float));
        memcpy(&motor_config[idx].kd,             &buf[12], sizeof(float));
        memcpy(&motor_config[idx].integral_limit, &buf[16], sizeof(float));

        // Update live PID gains immediately
        pid[idx].kp             = motor_config[idx].kp;
        pid[idx].ki             = motor_config[idx].ki;
        pid[idx].kd             = motor_config[idx].kd;
        pid[idx].integral_limit = motor_config[idx].integral_limit;
        
        
        // UART dump to confirm received values
        UART_PrintLong((int32_t)motor_id);
        UART_PrintLong((int32_t)motor_config[idx].ppr);
        UART_PrintLong((int32_t)(motor_config[idx].kp * 1000));   // *1000 to see 3dp as integer
        UART_PrintLong((int32_t)(motor_config[idx].ki * 1000));
        UART_PrintLong((int32_t)(motor_config[idx].kd * 1000));
        UART_PrintLong((int32_t)motor_config[idx].integral_limit);        
    }    
    
    
//##############################################################################    
//USB CDC Send functions
//##############################################################################      
    void SendEncoderDataBinary(long enc1, long enc2) {
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
    
    void SendRPMDataBinary(int32_t rpm1_x10, int32_t rpm2_x10) {
        uint8_t packet[9];
        packet[0] = 0xAA;  // sync byte unchanged

        memcpy(&packet[1], &rpm1_x10, sizeof(int32_t));
        memcpy(&packet[5], &rpm2_x10, sizeof(int32_t));

        for (int i = 0; i < 9; i++)
        {
            if (USB_CDCWrite(packet[i]) == CDC_BUFFER_FULL) { }
        }
    }    
    
    void SendDebugBytes(uint8_t prev_state, uint8_t new_state, uint8_t index, int8_t delta) {
        uint8_t packet[5];
        packet[0] = 0xDD;
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
 
    void UART_PrintString(const char *s) {
        while (*s) UART_WriteByte((uint8_t)*s++);
        //UART_WriteByte('\r');
        //UART_WriteByte('\n');
    }    
    
    void UART_PrintLong(int32_t value) {
        char buf[12];
        int8_t i = 0;

        if (value == INT32_MIN) {
            const char *s = "-2147483648\r\n";
            while (*s) { UART_WriteByte((uint8_t)*s++); }
            return;
        }

        if (value < 0) {
            UART_WriteByte('-');
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
            }
        }

        UART_WriteByte('\r');
        UART_WriteByte('\n');
    } 

//##############################################################################    
//RPM Calculations
//##############################################################################
    void Calculate_RPM(void) {
        // Atomically snapshot and reset encoder counts
        cli();
            long m1_delta = motor1_count;
            long m2_delta = motor2_count;
            motor1_count  = 0;
            motor2_count  = 0;
        sei();

        // RPM = (counts / PPR) * (60 / window_seconds)
        // window_seconds = RPM_WINDOW_MS / 1000.0 = 0.1
        // RPM = counts * 60 / (PPR * 0.1)
        // RPM = counts * 600 / PPR
        // RPM * 10 = counts * 6000 / PPR  (fixed point, one decimal place)
        // With PPR=56: RPM*10 = counts * 6000 / 56 = counts * 107.14
        // Use integer maths: (counts * 6000) / PPR

        motor1_rpm_x10 = ((long)m1_delta * 6000L) / ( motor_config[0].ppr * QUADRATURE_DECODE );
        motor2_rpm_x10 = ((long)m2_delta * 6000L) / ( motor_config[1].ppr * QUADRATURE_DECODE );
        
        // PID uses actual RPM (not ×10), unsigned magnitude
        float m1_rpm = fabsf((float)motor1_rpm_x10 / 10.0f);
        float m2_rpm = fabsf((float)motor2_rpm_x10 / 10.0f);

        Calculate_PID(&pid[0], m1_rpm, 0);
        Calculate_PID(&pid[1], m2_rpm, 1);  
    }    
    
//##############################################################################    
//PID Calculations
//##############################################################################    
void Calculate_PID(PID_t *pid, float measured_rpm, uint8_t motor_idx)
{
    if (!pid->enabled || pid->setpoint_rpm <= 0.0f)
    {
        pid->integral   = 0.0f;
        pid->prev_error = 0.0f;
        return;
    }

    float error      = pid->setpoint_rpm - measured_rpm;
    pid->integral   += error * 0.1f;

    if (pid->integral >  pid->integral_limit) pid->integral =  pid->integral_limit;
    if (pid->integral < -pid->integral_limit) pid->integral = -pid->integral_limit;

    float derivative = (error - pid->prev_error) / 0.1f;
    pid->prev_error  = error;

    float output = (pid->kp * error) +
                   (pid->ki * pid->integral) +
                   (pid->kd * derivative);

    if (output < 0.0f)   output = 0.0f;
    if (output > 255.0f) output = 255.0f;

    // Rate limit PWM change per 100ms window to prevent bang-bang behaviour
    #define MAX_PWM_STEP  10

    int16_t current_pwm = (motor_idx == 0) ? TCA0.SPLIT.LCMP1 : TCA0.SPLIT.LCMP0;
    int16_t new_pwm     = (int16_t)output;

    if (new_pwm - current_pwm >  MAX_PWM_STEP) new_pwm = current_pwm + MAX_PWM_STEP;
    if (new_pwm - current_pwm < -MAX_PWM_STEP) new_pwm = current_pwm - MAX_PWM_STEP;

    pid->pwm_output = (uint8_t)new_pwm;

    // Temp debug
    //UART_PrintString("=== PID DEBUG ===");
    //UART_PrintString("Setpoint:");  UART_PrintLong((int32_t)pid->setpoint_rpm);
    //UART_PrintString("Measured:");  UART_PrintLong((int32_t)measured_rpm);
    //UART_PrintString("Ki*10000:");  UART_PrintLong((int32_t)(pid->ki * 10000));
    //UART_PrintString("Integ*100:"); UART_PrintLong((int32_t)(pid->integral * 100));
    //UART_PrintString("PWM:");       UART_PrintLong((int32_t)new_pwm);
    //UART_PrintString("---");

    if (motor_idx == 0) TCA0.SPLIT.LCMP1 = pid->pwm_output;
    if (motor_idx == 1) TCA0.SPLIT.LCMP0 = pid->pwm_output;
    
    
    
if (motor_idx == 1)
{
    UART_PrintString("\r\nM2:");
    UART_PrintString("\r\nSP:");    UART_PrintLong((int32_t)pid->setpoint_rpm);
    UART_PrintString("\r\nRPM:");   UART_PrintLong((int32_t)measured_rpm);
    UART_PrintString("\r\nInteg:"); UART_PrintLong((int32_t)(pid->integral));
    UART_PrintString("\r\nPWM:");   UART_PrintLong((int32_t)new_pwm);
}    
    
}   
    
//##############################################################################    
//##############################################################################    
//  Main application
//##############################################################################
//##############################################################################    
int main(void) {
    // Data variable
        uint8_t cdcData;  
        
    SYSTEM_Initialize();
    
    //Defaults
    // Safe defaults until GUI sends config
    for (uint8_t i = 0; i < 2; i++) {
        motor_config[i].ppr            = 56;
        motor_config[i].kp             = 0.0f;
        motor_config[i].ki             = 0.0f;
        motor_config[i].kd             = 0.0f;
        motor_config[i].integral_limit = 255.0f;

        pid[i].kp             = 0.0f;
        pid[i].ki             = 0.0f;
        pid[i].kd             = 0.0f;
        pid[i].setpoint_rpm   = 0.0f;
        pid[i].integral       = 0.0f;
        pid[i].integral_limit = 255.0f;
        pid[i].prev_error     = 0.0f;
        pid[i].pwm_output     = 0;
        pid[i].enabled        = false;
    }    
    
    
    
    
    
    //Encoder State Initialization - Must be before ISR registering
        m1_prev_state = read_encoder_state_M1();
        m2_prev_state = read_encoder_state_M2();
        
    //Interrupt on both edges of encA and encB, firing off the same ISR
        M1_encA_SetInterruptHandler     ( M1_enc_ISR );
        M1_encB_SetInterruptHandler     ( M1_enc_ISR );
    
        M2_encA_SetInterruptHandler     ( M2_enc_ISR );
        M2_encB_SetInterruptHandler     ( M2_enc_ISR );
        
        TCA0_LowCountCallbackRegister   ( TCA0_Underflow_ISR );
        
    // Start USB operations
        usbStatus = USB_Start();   
        
               
    //Test
        //M01_STBY_SetHigh();
        //M0_IN1_SetHigh();
        //M0_IN2_SetLow();
        //TCA0.SPLIT.LCMP0 = 0xEF; 
        //long test  = 29997; 
        //UART_PrintLong ( test );           

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
            
            //Flag from ISR underflow counter in order to do some RPM maths and update the Host      
            if ( rpm_window_ready )
            {
                LED0_Toggle();
                
                rpm_window_ready = false;
                
                Calculate_RPM();
                
                SendRPMDataBinary(motor1_rpm_x10, motor2_rpm_x10); 
            }           


            //Device has received a packet from the host so need to process
            while (USB_CDCRead(&cdcData) == CDC_SUCCESS) {
    
                switch (rx_state) {
                    
                    case WAIT_HEADER:
                        if (cdcData == 0x55) {
                            
                            rx_buffer[0] = cdcData;
                            rx_count     = 1;
                            rx_state     = READ_COMMAND;
                        }
                        else if (cdcData == 0xBB) {
                            
                            rx_buffer[0] = cdcData;
                            rx_count     = 1;
                            rx_state     = READ_CONFIG;
                        }
                        // any other byte silently discarded - keeps in sync
                    break;

                    case READ_COMMAND:
                        rx_buffer[rx_count++] = cdcData;
                        
                        if (rx_count >= CMD_PACKET_SIZE) {
                            
                            ProcessCommandPacket(rx_buffer);
                            rx_state = WAIT_HEADER;
                            rx_count = 0;
                        }
                    break;

                    case READ_CONFIG:
                        rx_buffer[rx_count++] = cdcData;
                        
                        if (rx_count >= CONFIG_PACKET_SIZE) {
                            ProcessConfigPacket(rx_buffer);
                            rx_state = WAIT_HEADER;
                            rx_count = 0;
                        }
                    break;
                }
            }            


            // Running CDC Virtual Serial Port handler
                usbStatus = USB_CDCVirtualSerialPortHandler();                                 
        }        
        
        //LED0_Toggle();
        //DELAY_milliseconds(10);
    }    
}























