//
// Created by javerik on 20.01.25.
//

#ifndef LIBTUSS4470_TUSS4470_H
#define LIBTUSS4470_TUSS4470_H

#include "tuss4470_types.h"
#include <stdint.h>


#ifdef __cplusplus
extern "C" {
#endif

    // region function definitions for hw communication
    typedef int (*tuss4470_spi_transfer_fptr)(uint8_t mode, uint8_t *data, uint8_t size, void *ctx);
    // endregion

    typedef struct {
        uint8_t raw_device_state;
        tuss4470_device_state_t device_state;
        int flag_vdrv_ready;
        int flag_pulse_num_flt;
        int flag_drv_pulse_flt;
        int flag_ee_crc_flt;
        tuss4470_config_t *config;
        tuss4470_spi_transfer_fptr spiTransfer_fptr;
        void *ctx;
    } tuss4470_t;

    int tuss4470_t_init(tuss4470_spi_transfer_fptr spiTransfer_fptr, tuss4470_t *tuss4470);
    int tuss4470_t_free(tuss4470_t *tuss4470);

    // region generic Register access
    int tuss4470_read_register(tuss4470_t *tuss4470, tuss4470_register_map_t reg, uint8_t *data);
    int tuss4470_write_register(tuss4470_t *tuss4470, tuss4470_register_map_t reg, uint8_t data);
    int tuss4470_read_config(tuss4470_t *tuss4470, tuss4470_config_t *config);
    int tuss4470_write_config(tuss4470_t *tuss4470, tuss4470_config_t *config);
    // endregion

    // region specific register access
    uint8_t tuss4470_get_config(uint8_t configData, uint8_t mask);
    uint8_t tuss4470_set_config(uint8_t configData, uint8_t mask, uint8_t value);
    // endregion

    // region utility functions
    int tuss4470_value_is_in_range(uint8_t mask, uint8_t value);
    // endregion


#ifdef __cplusplus
}
#endif

#endif //LIBTUSS4470_TUSS4470_H
