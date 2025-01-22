//
// Created by javerik on 20.01.25.
//
#include "tuss4470.h"


#ifdef PLATFORM_X86
#include <malloc.h>
#elif defined(PLATFORM_ARM)
#include <stdint.h>
#elif defined(PLATFORM_ARDUINO)


#endif


#include <stdint.h>
#include <stddef.h>
uint8_t parity(const uint8_t *data) {
    uint16_t data16 = (data[0] << 8) | data[1];
    uint8_t parity = 0;
    for (int i = 0; i < 16; ++i) {
        if ((data16 >> i) & 1) {
            parity++;
        }
    }
    return (parity + 1) % 2;
}

int evaluate_status(uint8_t status, tuss4470_t *tuss4470) {
    tuss4470->raw_device_state = status;
    tuss4470->device_state = (tuss4470_device_state_t)(status & TUSS4470_STAT_DEV_STATE);
    tuss4470->flag_vdrv_ready = (status & TUSS4470_STAT_VDRV_READY) >> 5;
    tuss4470->flag_pulse_num_flt = (status & TUSS4470_STAT_PULSE_NUM_FLT) >> 4;
    tuss4470->flag_drv_pulse_flt = (status & TUSS4470_STAT_DRV_PULSE_FLT) >> 3;
    tuss4470->flag_ee_crc_flt = (status & TUSS4470_STAT_EE_CRC_FLT) >> 2;
    if ((tuss4470->flag_ee_crc_flt || tuss4470->flag_drv_pulse_flt || tuss4470->flag_drv_pulse_flt )) {
        return 1;
    } else {
        return 0;
    }
}

int tuss4470_t_init(tuss4470_spi_transfer_fptr spiTransfer_fptr, tuss4470_t *tuss4470) {
    tuss4470->spiTransfer_fptr = spiTransfer_fptr;
    tuss4470->config = (tuss4470_config_t *)malloc(sizeof(tuss4470_config_t));
    if (tuss4470->config == NULL) {
        return 1;
    }
    tuss4470->ctx = NULL;
    return 0;
}

int tuss4470_t_free(tuss4470_t *tuss4470) {
    free(tuss4470->config);
    return 0;
}

int tuss4470_read_config(tuss4470_t *tuss4470, tuss4470_config_t *config) {
    uint8_t *cfg_data = (uint8_t *)config;
    int err = 0;
    uint8_t data = 0;
    for (size_t i = 0; i < sizeof(tuss4470_config_t); i++)
    {
        err = tuss4470_read_register(tuss4470, (tuss4470_register_map_t) (tuss4470_register_map[i]), &data);
        if (err) return err;
        cfg_data[i] = data;  
    }
    return 0;
}

int tuss4470_write_config(tuss4470_t *tuss4470, tuss4470_config_t *config) {
    uint8_t *cfg_data = (uint8_t *)config;
    int err = 0;
    for (size_t i = 0; i < sizeof(tuss4470_config_t); i++)
    {
        err = tuss4470_write_register(tuss4470, (tuss4470_register_map_t) (tuss4470_register_map[i]), cfg_data[i]);
        if (err) return err;
    }
    return 0;
}

int tuss4470_read_register(tuss4470_t *tuss4470, tuss4470_register_map_t reg, uint8_t *data) {
    if (tuss4470->spiTransfer_fptr == NULL) {
        return 1;
    }
    static uint8_t spi_mode = 0x80;

    uint8_t tx_data[2] = {0};
    tx_data[0] = 0x80 + ((reg & 0x3F) << 1);
    tx_data[1] = 0;
    tx_data[0] |= parity(tx_data);

    int err = tuss4470->spiTransfer_fptr(spi_mode, tx_data, 2, tuss4470->ctx);
    if (err) {
        return err;
    }
    err = evaluate_status(tx_data[0], tuss4470);
    if (err) {
        return err;
    }
    *data = tx_data[1];
    return 0;
}

int tuss4470_write_register(tuss4470_t *tuss4470, tuss4470_register_map_t reg, uint8_t data) {
    if (tuss4470->spiTransfer_fptr == NULL) {
        return 1;
    }
    static uint8_t spi_mode = 0x00;
    uint8_t tx_data[2] = {0};
    tx_data[0] = (reg & 0x3F) << 1;
    tx_data[1] = data;
    tx_data[0] |= parity(tx_data);
    int err = tuss4470->spiTransfer_fptr(spi_mode, tx_data, 2, tuss4470->ctx);
    if (err) {
        return err;
    }
    err = evaluate_status(tx_data[0], tuss4470);
    if (err) {
        return err;
    }
    err = tuss4470_read_register(tuss4470, reg, &tx_data[1]);
    if (err) {
        return err;
    }
    if (tx_data[1] != data) {
        return 1;
    }
    return 0;
}

uint8_t tuss4470_get_config(uint8_t configData, uint8_t mask) {
    uint8_t dataOut = configData & mask;
    // to have a nicer representation of the data, we need to shift it to the right
    uint8_t copy_mask = mask;
    // count number of bits to shift left until bit 0 is set
    uint8_t shift = 0;
    while ((copy_mask & 1) == 0) {
        copy_mask >>= 1;
        shift++;
    }
    dataOut >>= shift;
    return dataOut;
}

uint8_t tuss4470_set_config(uint8_t configData, uint8_t mask, uint8_t value) {
    // first we need to clear the bits that are set in the mask
    uint8_t dataOut = configData & ~mask;
    // now we need to shift the value to the left until the bits are set in the mask
    uint8_t copy_mask = mask;
    // count number of bits to shift left until bit 0 is set
    uint8_t shift = 0;
    while ((copy_mask & 1) == 0) {
        copy_mask >>= 1;
        shift++;
    }
    value <<= shift;
    dataOut |= value;
    return dataOut;
}


