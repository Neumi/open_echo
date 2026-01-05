//
// Created by javerik on 20.01.25.
//

#ifndef TESTLIBTUSS_TUSS4470_TYPES_H
#define TESTLIBTUSS_TUSS4470_TYPES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif



// region Register map

// Define masks for each status bit
#define TUSS4470_STAT_VDRV_READY    (1 << 5)  // Bit 5
#define TUSS4470_STAT_PULSE_NUM_FLT (1 << 4)  // Bit 4
#define TUSS4470_STAT_DRV_PULSE_FLT (1 << 3)  // Bit 3
#define TUSS4470_STAT_EE_CRC_FLT    (1 << 2)  // Bit 2
#define TUSS4470_STAT_DEV_STATE     0x03      // Bits 1:0

typedef enum {
    TUSS4470_DEV_STATE_LISTEN = 0x00,  // 00
    TUSS4470_DEV_STATE_BURST = 0x01,   // 01
    TUSS4470_DEV_STATE_STANDBY = 0x02, // 10
    TUSS4470_DEV_STATE_SLEEP = 0x03    // 11
} tuss4470_device_state_t;

#define TUSS4470_REG_OFFSET 0x10
#define TUSS4470_REG_END 0x1E

typedef enum {
    BPF_CONFIG_1 = 0x10,    // Bandpass filter settings
    BPF_CONFIG_2 = 0x11,    // Bandpass filter settings
    DEV_CTRL_1   = 0x12,    // Log-amp configuration
    DEV_CTRL_2   = 0x13,    // Log-amp configuration
    DEV_CTRL_3   = 0x14,    // Device Configuration
    VDRV_CTRL    = 0x16,    // VDRV Regulator Control
    ECHO_INT_CONFIG = 0x17, // Echo Interrupt Control
    ZC_CONFIG    = 0x18,    // Zero Crossing configuration
    BURST_PULSE  = 0x1A,    // Burst pulse configuration
    TOF_CONFIG   = 0x1B,    // Time of Flight Config
    DEV_STAT     = 0x1C,    // Fault status bits
    DEVICE_ID    = 0x1D,    // Device ID
    REV_ID       = 0x1E     // Revision ID
} tuss4470_register_map_t;

const uint8_t tuss4470_register_map[] = {
        BPF_CONFIG_1,
        BPF_CONFIG_2,
        DEV_CTRL_1,
        DEV_CTRL_2,
        DEV_CTRL_3,
        VDRV_CTRL,
        ECHO_INT_CONFIG,
        ZC_CONFIG,
        BURST_PULSE,
        TOF_CONFIG,
        DEV_STAT,
        DEVICE_ID,
        REV_ID
};

// endregion

//region Register bits

typedef enum {
    BPF_FC_TRIM_FRC = (1 << 7), // Bit 7: Override factor settings for Bandpass filter trim
    BPF_BYPASS      = (1 << 6), // Bit 6: Select between Bandpass filter or High pass filter
    BPF_HPF_FREQ    = 0x3F      // Bits 5:0: Bandpass or High pass filter center frequency
} tuss4470_BPF_CONFIG_1_Bits;

typedef enum {
    tuss4470_BPF_Q_SEL = (0x3 << 4),  // Bits 5:4: Bandpass filter Q factor
    tuss4470_BPF_FC_TRIM = 0x0F       // Bits 3:0: Offset for BPF_HPF_FREQ
} tuss4470_BPF_CONFIG_2_Bits;

typedef enum {
    tuss4470_LOGAMP_FRC        = (1 << 7),  // Bit 7: Override for factory settings
    tuss4470_LOGAMP_SLOPE_ADJ  = (0x7 << 4), // Bits 6:4: Slope or gain adjustment
    tuss4470_LOGAMP_INT_ADJ    = 0x0F       // Bits 3:0: Logamp intercept adjustment
} tuss4470_DEV_CTRL_1_Bits;


typedef enum {
    tuss4470_LOGAMP_DIS_FIRST = (1 << 7), // Bit 7: Disable first logamp stage
    tuss4470_LOGAMP_DIS_LAST  = (1 << 6), // Bit 6: Disable last logamp stage
    tuss4470_VOUT_SCALE_SEL   = (1 << 2), // Bit 2: Select VOUT scaling
    tuss4470_LNA_GAIN         = 0x03      // Bits 1:0: Adjust LNA gain
} tuss4470_DEV_CTRL_2_Bits;

typedef enum {
    tuss4470_DRV_PLS_FLT_DT = (0x7 << 2), // Bits 4:2: Driver Pulse Fault Deglitch Time
    tuss4470_IO_MODE        = 0x03        // Bits 1:0: Configuration for low voltage IO pins
} tuss4470_DEV_CTRL_3_Bits;

typedef enum {
    tuss4470_DIS_VDRV_REG_LSTN = (1 << 6), // Bit 6: Automatically disable VDRV charging in listen mode
    tuss4470_VDRV_HI_Z         = (1 << 5), // Bit 5: Turn off current source and disable VDRV regulation
    tuss4470_VDRV_CURRENT_LEVEL = (1 << 4), // Bit 4: Pull-up current at VDRV pin
    tuss4470_VDRV_VOLTAGE_LEVEL = 0x0F     // Bits 3:0: Regulated voltage level at VDRV pin
} tuss4470_VDRV_CTRL_Bits;


typedef enum {
    tuss4470_ECHO_INT_CMP_EN   = (1 << 4), // Bit 4: Enable echo interrupt comparator output
    tuss4470_ECHO_INT_THR_SEL  = 0x0F     // Bits 3:0: Threshold level to issue interrupt
} tuss4470_ECHO_INT_CONFIG_Bits;


typedef enum {
    tuss4470_ZC_CMP_EN         = (1 << 7), // Bit 7: Enable Zero Cross Comparator for frequency detection
    tuss4470_ZC_EN_ECHO_INT    = (1 << 6), // Bit 6: Provide ZC information only when object is detected
    tuss4470_ZC_CMP_IN_SEL     = (1 << 5), // Bit 5: Zero Comparator Input Select
    tuss4470_ZC_CMP_STG_SEL    = (0x3 << 3), // Bits 4:3: Zero Cross Comparator Stage Select
    tuss4470_ZC_CMP_HYST       = 0x07      // Bits 2:0: Zero Cross Comparator Hysteresis Selection
} tuss4470_ZC_CONFIG_Bits;


typedef enum {
    tuss4470_HALF_BRG_MODE   = (1 << 7), // Bit 7: Enable/disable half-bridge mode
    tuss4470_PRE_DRIVER_MODE = (1 << 6), // Bit 6: Enable/disable pre-driver mode
    tuss4470_BURST_PULSE     = 0x3F      // Bits 5:0: Number of burst pulses
} tuss4470_BURST_PULSE_Bits;


typedef enum {
    tuss4470_SLEEP_MODE_EN  = (1 << 7), // Bit 7: Enable/disable sleep mode
    tuss4470_STDBY_MODE_EN  = (1 << 6), // Bit 6: Enable/disable standby mode
    tuss4470_VDRV_TRIGGER   = (1 << 1), // Bit 1: Control charging of VDRV pin
    tuss4470_CMD_TRIGGER    = (1 << 0)  // Bit 0: Control enabling of burst mode
} tuss4470_TOF_CONFIG_Bits;

typedef enum {
    tuss4470_VDRV_READY    = (1 << 3), // Bit 3: VDRV pin voltage status
    tuss4470_PULSE_NUM_FLT = (1 << 2), // Bit 2: Driver has not received the number of pulses defined by BURST_PULSE
    tuss4470_DRV_PULSE_FLT = (1 << 1), // Bit 1: Driver stuck in a single state in burst mode
    tuss4470_EE_CRC_FLT    = (1 << 0)  // Bit 0: CRC error for internal memory
} tuss4470_DEV_STAT_Bits;

// endregion

// region Configuration structure

typedef struct __attribute__((packed)) {
    uint8_t BPF_CONFIG_1;
    uint8_t BPF_CONFIG_2;
    uint8_t DEV_CTRL_1;
    uint8_t DEV_CTRL_2;
    uint8_t DEV_CTRL_3;
    uint8_t VDRV_CTRL;
    uint8_t ECHO_INT_CONFIG;
    uint8_t ZC_CONFIG;
    uint8_t BURST_PULSE;
    uint8_t TOF_CONFIG;
    uint8_t DEV_STAT;
    uint8_t DEVICE_ID;
    uint8_t REV_ID;
} tuss4470_config_t;

// endregion

#ifdef __cplusplus
}
#endif

#endif //TESTLIBTUSS_TUSS4470_TYPES_H
