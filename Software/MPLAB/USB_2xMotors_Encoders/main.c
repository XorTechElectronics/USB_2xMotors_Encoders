/*
 * MAIN Generated Driver File
 * XorTech 2-Motor USB CDC Controller
 * 
 * Packet protocol:
 *   Command  (Host->FW): 0x55, 13 bytes
 *   Config   (Host->FW): 0xBB, 22 bytes  
 *   RPM      (FW->Host): 0xAA, 14 bytes
 *   PID Debug(FW->Host): 0xBB, 27 bytes
 */

#include "mcc_generated_files/system/system.h"

#include <math.h>
#include <stdio.h>
#include "string.h"

#include "usb_cdc.h"
#include "usb_cdc_virtual_serial_port.h"

#include "../timer/delay.h"

// Debug output control ? set to 1 to enable UART debug, 0 for production
#define DEBUG_UART  0

#if DEBUG_UART
    #define DEBUG_PRINT(s)      UART_PrintString(s)
    #define DEBUG_PRINTL(s)     UART_PrintString(s); UART_PrintString("\r\n")
    #define DEBUG_LONG(v)       UART_PrintLong(v)
    #define DEBUG_NL()          UART_PrintString("\r\n")
#else
    #define DEBUG_PRINT(s)
    #define DEBUG_PRINTL(s)
    #define DEBUG_LONG(v)
    #define DEBUG_NL()
#endif


// Each encoder tick fires 4 interrupt on each edge of encA
    #define QUADRATURE_DECODE   4   // 4x decoding: both edges, both channels

// Packet Sizing from the Host to set settings or commands
    #define CMD_PACKET_SIZE     11
    #define CONFIG_PACKET_SIZE  22
    #define C_BIGGEST_PACKET    22

    // CMD Byte 1 Motor Flags
        #define FLAG_M01_STBY       (1 << 0)

    // CMD Byte 6 Control flags
        #define FLAG_M1_PID         (1 << 0)
        #define FLAG_M2_PID         (1 << 1)
        #define FLAG_SYNC           (1 << 2)

    // CFG Byte 21 flags
        #define CONFIG_FLAG_DEBUG_ENABLED    (1 << 0)
        #define CONFIG_FLAG_ENCODER_INVERTED (1 << 1)


// TCA0 underflow timebase for RPM calculation
// At 24MHz / prescaler 4 / 256 counts = 23,437 Hz overflow rate
// 2344 overflows = ~100ms RPM update window
    #define TCA0_OVERFLOW_RATE  23437UL
    #define RPM_WINDOW_MS       100UL
    #define RPM_WINDOW_TICKS    ((TCA0_OVERFLOW_RATE * RPM_WINDOW_MS) / 1000UL)  // 2344

//Sync Gains - how aggressively motor 2 corrects drift
    #define SYNC_GAIN       0.1f
    #define SYNC_MAX_RPM 6000.0f    



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
        
    
//M1_encA_GetValue returns something like 0x40, depending on port position as a '1' so convert here to pin value
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
        uint8_t  max_pwm_step;
        bool     debug_enabled;
        bool     encoder_inverted;
    } MotorConfig_t;

    MotorConfig_t motor_config[2];
    
// Used to sync encoder rates together
    volatile bool   sync_directions_opposite    = false;
    volatile bool   sync_enabled                = false;
    volatile long   m1_sync_total               = 0;
    volatile long   m2_sync_total               = 0;    


//##############################################################################    
//SETTINGs and COMMANDs from Host
//##############################################################################
    typedef enum {
        WAIT_HEADER,      // waiting for 0x55 or 0xBB
        READ_COMMAND,     // reading remaining 11 bytes of command packet
        READ_CONFIG       // reading remaining 19 bytes of config packet
    } RxState_t;

    RxState_t rx_state        = WAIT_HEADER;
    uint8_t   rx_buffer[C_BIGGEST_PACKET];  // big enough for largest packet
    uint8_t   rx_count        = 0;    

//##############################################################################    
//ISRs    
//##############################################################################
    // Motor 1 encoder ISR ? triggered on encA's and encB's rising & falling edge
    void M1_enc_ISR(void) {
        uint8_t new_state = read_encoder_state_M1();
        uint8_t index     = (m1_prev_state << 2) | new_state;
        int8_t  delta     = QEM_TABLE[index];
        motor1_count     += motor_config[0].encoder_inverted ? -delta : delta;
        m1_prev_state     = new_state;
    }

    // Motor 2 encoder ISR ? triggered on encA's and encB's rising & falling edge
    void M2_enc_ISR(void) {
        uint8_t new_state = read_encoder_state_M2();
        uint8_t index     = (m2_prev_state << 2) | new_state;
        int8_t  delta     = QEM_TABLE[index];
        motor2_count     += motor_config[1].encoder_inverted ? -delta : delta;
        m2_prev_state     = new_state;
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
        // buf[1]  = motor flags [bit0=M01_STBY]
        // buf[2]  = M1 direction
        // buf[3]  = M1 PWM
        // buf[4]  = M2 direction
        // buf[5]  = M2 PWM
        // buf[6]  = control flags [bit0=M1_PID, bit1=M2_PID, bit2=SYNC]
        // buf[7]  = M1 setpoint high
        // buf[8]  = M1 setpoint low
        // buf[9]  = M2 setpoint high
        // buf[10] = M2 setpoint low

        LED0_Toggle();

        // Motor enable
            if (buf[1] & FLAG_M01_STBY) { M01_STBY_SetHigh(); }
            else                        { M01_STBY_SetLow();  }

        // Motor 1 direction
            if (buf[2] & (1<<0)) { M0_IN1_SetHigh(); } else { M0_IN1_SetLow(); }
            if (buf[2] & (1<<1)) { M0_IN2_SetHigh(); } else { M0_IN2_SetLow(); }

        // Motor 1 PWM (manual only)
            if (!pid[0].enabled) TCA0.SPLIT.LCMP1 = buf[3];

        // Motor 2 direction
            if (buf[4] & (1<<0)) { M1_IN1_SetHigh(); } else { M1_IN1_SetLow(); }
            if (buf[4] & (1<<1)) { M1_IN2_SetHigh(); } else { M1_IN2_SetLow(); }

        // Motor 2 PWM (manual only)
            if (!pid[1].enabled) TCA0.SPLIT.LCMP0 = buf[5];
        
        // Determine if motors are running in opposite directions for sync correction
        // CW  = IN1 high, IN2 low (buf bit0=1, bit1=0) = dir_byte & 0x03 == 1
        // CCW = IN1 low, IN2 high (buf bit0=0, bit1=1) = dir_byte & 0x03 == 2
            uint8_t m1_dir = buf[2] & 0x03;
            uint8_t m2_dir = buf[4] & 0x03;
            sync_directions_opposite = (m1_dir != m2_dir) && (m1_dir != 0) && (m2_dir != 0);        
        
        

        // Sync coast-stop ? after direction pins set, before PID update
        if (sync_enabled && buf[2] == 0x00) {
            M1_IN1_SetLow(); M1_IN2_SetLow();
            TCA0.SPLIT.LCMP0  = 0;
            pid[1].integral   = 0.0f;
            pid[1].prev_error = 0.0f;
            m1_sync_total     = 0;
            m2_sync_total     = 0;
        }

        // Control flags
            uint8_t ctrl = buf[6];
            bool pid0_was_enabled = pid[0].enabled;
            bool pid1_was_enabled = pid[1].enabled;

        pid[0].enabled = (ctrl & FLAG_M1_PID) != 0;
        pid[1].enabled = (ctrl & FLAG_M2_PID) != 0;

        // If sync active and Motor 1 PID disabled, kill Motor 2 too
        if (sync_enabled && !pid[0].enabled) {
            pid[1].enabled    = false;
            pid[1].integral   = 0.0f;
            pid[1].prev_error = 0.0f;
            TCA0.SPLIT.LCMP0  = 0;
        }

        // Setpoints
            pid[0].setpoint_rpm = (float)(((uint16_t)buf[7] << 8) | buf[8])  / 10.0f;
            pid[1].setpoint_rpm = (float)(((uint16_t)buf[9] << 8) | buf[10]) / 10.0f;

        // Zero PWM on PID disable transition
        if (pid0_was_enabled && !pid[0].enabled) {
            TCA0.SPLIT.LCMP1  = 0;
            pid[0].integral   = 0.0f;
            pid[0].prev_error = 0.0f;
        }
        if (pid1_was_enabled && !pid[1].enabled) {
            TCA0.SPLIT.LCMP0  = 0;
            pid[1].integral   = 0.0f;
            pid[1].prev_error = 0.0f;
        }

    // Sync enable
        bool sync_was_enabled = sync_enabled;
        sync_enabled = (ctrl & FLAG_SYNC) != 0;

        if (sync_enabled && !sync_was_enabled) {
            m1_sync_total = 0;
            m2_sync_total = 0;
        }
        if (buf[2] == 0x00 || buf[4] == 0x00) {
            m1_sync_total = 0;
            m2_sync_total = 0;
        }

        //DEBUG_PRINT("CMD:");        DEBUG_NL();
        //DEBUG_PRINT("M1DIR:");      DEBUG_LONG(buf[2]);  DEBUG_NL();
        //DEBUG_PRINT("M1PWM:");      DEBUG_LONG(buf[3]);  DEBUG_NL();
        //DEBUG_PRINT("M2DIR:");      DEBUG_LONG(buf[4]);  DEBUG_NL();
        //DEBUG_PRINT("M2PWM:");      DEBUG_LONG(buf[5]);  DEBUG_NL();
        //DEBUG_PRINT("CTRL:");       DEBUG_LONG(buf[6]);  DEBUG_NL();
        //DEBUG_PRINT("M1SP:");       DEBUG_LONG((int32_t)(((uint16_t)buf[7] << 8) | buf[8]));  DEBUG_NL();
        //DEBUG_PRINT("M2SP:");       DEBUG_LONG((int32_t)(((uint16_t)buf[9] << 8) | buf[10])); DEBUG_NL();
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
        motor_config[idx].max_pwm_step          =  buf[20];
        
        uint8_t flags                           =  buf[21];
        motor_config[idx].debug_enabled         = (flags & CONFIG_FLAG_DEBUG_ENABLED)    != 0;
        motor_config[idx].encoder_inverted      = (flags & CONFIG_FLAG_ENCODER_INVERTED) != 0;

        // Update live PID gains immediately
        pid[idx].kp             = motor_config[idx].kp;
        pid[idx].ki             = motor_config[idx].ki;
        pid[idx].kd             = motor_config[idx].kd;
        pid[idx].integral_limit = motor_config[idx].integral_limit;
        
        
        // UART dump to confirm received values
        DEBUG_PRINT("Config Motor:");   DEBUG_LONG((int32_t)motor_id);                              DEBUG_NL();  
        
        DEBUG_PRINT("PPR:");            DEBUG_LONG((int32_t) motor_config[idx].ppr);                DEBUG_NL(); 
        DEBUG_PRINT("Kp*1000:");        DEBUG_LONG((int32_t)(motor_config[idx].kp * 1000));         DEBUG_NL(); 
        DEBUG_PRINT("Ki*1000:");        DEBUG_LONG((int32_t)(motor_config[idx].ki * 1000));         DEBUG_NL(); 
        DEBUG_PRINT("Kd*1000:");        DEBUG_LONG((int32_t)(motor_config[idx].kd * 1000));         DEBUG_NL(); 
        DEBUG_PRINT("Limit:");          DEBUG_LONG((int32_t) motor_config[idx].integral_limit);     DEBUG_NL(); 
        DEBUG_PRINT("Step:");           DEBUG_LONG((int32_t) motor_config[idx].max_pwm_step);       DEBUG_NL(); 
        DEBUG_PRINT("Inverted:");       DEBUG_LONG((int32_t) motor_config[idx].encoder_inverted);   DEBUG_NL();
        DEBUG_PRINT("Debug:");          DEBUG_LONG((int32_t) motor_config[idx].debug_enabled);      DEBUG_NL(); 
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
        uint8_t packet[14];
        packet[0] = 0xAA;
        memcpy(&packet[1], &rpm1_x10, sizeof(int32_t));             // bytes 1-4
        memcpy(&packet[5], &rpm2_x10, sizeof(int32_t));             // bytes 5-8
        int32_t sync_err = (int32_t)(m1_sync_total - m2_sync_total);
        memcpy(&packet[9], &sync_err, sizeof(int32_t));             // bytes 9-12
        packet[13] = sync_enabled ? 1 : 0;                          // byte 13

        for (int i = 0; i < 14; i++) {
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
    
    void SendPIDDebugBinary(uint8_t motor_id,   float setpoint, float measured,
                            float error,        float p_term,   float i_term,
                            float d_term,       uint8_t pwm ) {
        uint8_t packet[27];
        packet[0] = 0xBB;
        packet[1] = motor_id;
        memcpy(&packet[2],  &setpoint, sizeof(float));
        memcpy(&packet[6],  &measured, sizeof(float));
        memcpy(&packet[10], &error,    sizeof(float));
        memcpy(&packet[14], &p_term,   sizeof(float));
        memcpy(&packet[18], &i_term,   sizeof(float));
        memcpy(&packet[22], &d_term,   sizeof(float));
        packet[26] = pwm;

        for (int i = 0; i < 27; i++) {
            if (USB_CDCWrite(packet[i]) == CDC_BUFFER_FULL) { }
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
        
        // Accumulate sync totals
            m1_sync_total += m1_delta;
            m2_sync_total += sync_directions_opposite ? -m2_delta : m2_delta;        
        
        // Sync ? Motor 2 tracks Motor 1
        // GUI enforces both start from stopped so no transient issues
        if (sync_enabled && pid[0].enabled) {
            long sync_error = m1_sync_total - m2_sync_total;
            pid[1].setpoint_rpm = pid[0].setpoint_rpm + ((float)sync_error * SYNC_GAIN);
            
            if (pid[1].setpoint_rpm < 0.0f)         pid[1].setpoint_rpm = 0.0f;
            if (pid[1].setpoint_rpm > SYNC_MAX_RPM) pid[1].setpoint_rpm = SYNC_MAX_RPM;
        }
        
#if DEBUG_UART            
        static uint8_t sync_debug_count = 0;
        if (sync_enabled) {
            if (++sync_debug_count >= 10) {
                sync_debug_count = 0;
                DEBUG_PRINT("SyncErr:");    DEBUG_LONG(m1_sync_total - m2_sync_total);                  DEBUG_NL();
                
                DEBUG_PRINT("M1d:");        DEBUG_LONG(m1_delta);                                       DEBUG_NL();
                DEBUG_PRINT("M1SP:");       DEBUG_LONG((int32_t)pid[0].setpoint_rpm);                   DEBUG_NL();
                DEBUG_PRINT("M1RPM:");      DEBUG_LONG((int32_t)(motor1_rpm_x10 / 10));                 DEBUG_NL();
                DEBUG_PRINT("M1inv:");      DEBUG_LONG((int32_t)motor_config[0].encoder_inverted);      DEBUG_NL();
                
                DEBUG_PRINT("M2d:");        DEBUG_LONG(m2_delta);                                       DEBUG_NL();                                
                DEBUG_PRINT("M2SP:");       DEBUG_LONG((int32_t)pid[1].setpoint_rpm);                   DEBUG_NL();
                DEBUG_PRINT("M2RPM:");      DEBUG_LONG((int32_t)(motor2_rpm_x10 / 10));                 DEBUG_NL();
                DEBUG_PRINT("M2inv:");      DEBUG_LONG((int32_t)motor_config[1].encoder_inverted);      DEBUG_NL();
            }
        }     
#endif
        
        Calculate_PID(&pid[0], fabsf((float)motor1_rpm_x10 / 10.0f), 0);
        Calculate_PID(&pid[1], fabsf((float)motor2_rpm_x10 / 10.0f), 1);  
    }    
    
//##############################################################################    
//PID Calculations
//##############################################################################    
    void Calculate_PID(PID_t *pid, float measured_rpm, uint8_t motor_idx) {
        if (!pid->enabled || pid->setpoint_rpm <= 0.0f) {
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

        float p_term = pid->kp * error;
        float i_term = pid->ki * pid->integral;
        float d_term = pid->kd * derivative;
        float output = p_term + i_term + d_term;

        if (output < 0.0f)   output = 0.0f;
        if (output > 255.0f) output = 255.0f;

        // Rate limit PWM change per 100ms
        int16_t current_pwm = (motor_idx == 0) ? TCA0.SPLIT.LCMP1 : TCA0.SPLIT.LCMP0;
        int16_t new_pwm     = (int16_t)output;
        uint8_t step        = motor_config[motor_idx].max_pwm_step;
        
        if (new_pwm - current_pwm >  (int16_t)step) new_pwm = current_pwm + step;
        if (new_pwm - current_pwm < -(int16_t)step) new_pwm = current_pwm - step;

        pid->pwm_output = (uint8_t)new_pwm;

        if (motor_idx == 0) TCA0.SPLIT.LCMP1 = pid->pwm_output;
        if (motor_idx == 1) TCA0.SPLIT.LCMP0 = pid->pwm_output;

        // Send debug packet if enabled for this motor
        if (motor_config[motor_idx].debug_enabled) {
            SendPIDDebugBinary( motor_idx + 1,         // motor_id 1-based
                                pid->setpoint_rpm,
                                measured_rpm,
                                error,
                                p_term,
                                i_term,
                                d_term,
                                pid->pwm_output);
        }
    
    // Temp debug
    //UART_PrintString("=== PID DEBUG ===");
    //UART_PrintString("Setpoint:");  UART_PrintLong((int32_t)pid->setpoint_rpm);
    //UART_PrintString("Measured:");  UART_PrintLong((int32_t)measured_rpm);
    //UART_PrintString("Ki*10000:");  UART_PrintLong((int32_t)(pid->ki * 10000));
    //UART_PrintString("Integ*100:"); UART_PrintLong((int32_t)(pid->integral * 100));
    //UART_PrintString("PWM:");       UART_PrintLong((int32_t)new_pwm);
    //UART_PrintString("---");    
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
        motor_config[i].ppr                 = 14;
        motor_config[i].kp                  = 0.0f;
        motor_config[i].ki                  = 0.0f;
        motor_config[i].kd                  = 0.0f;
        motor_config[i].integral_limit      = 255.0f;
        motor_config[i].max_pwm_step        = 10;
        motor_config[i].encoder_inverted    = false;
        motor_config[i].debug_enabled       = false;

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























