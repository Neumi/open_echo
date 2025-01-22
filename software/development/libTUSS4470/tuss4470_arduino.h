#ifndef LIBTUSS_TUSS4470_ARDUINO_H
#define LIBTUSS_TUSS4470_ARDUINO_H

#include <stdint.h>
#include <Arduino.h>
#include <SPI.h>
#include "tuss4470.h"

class TUSS4470 {
    public:
        TUSS4470();
        TUSS4470(int cs, int io1, int io2, int o3, int o4, int analogIn);
        ~TUSS4470();

        int begin();
        int readConfig();
        int writeConfig();

        int readRawRegister(tuss4470_register_map_t reg, uint8_t *data);
        int writeRawRegister(tuss4470_register_map_t reg, uint8_t data);

        uint8_t getConfig(uint8_t configData, uint8_t mask);
        uint8_t setConfig(uint8_t configData, uint8_t mask, uint8_t value);

        int spiTransfer(uint8_t mode, uint8_t *data, uint8_t size);

        tuss4470_t *getTuss4470() { return &tuss4470; }
        tuss4470_config_t *getConfig() { return tuss4470.config; }

    private:
        int cs, io1, io2, o3, o4, analogIn;
        tuss4470_t tuss4470;

        

};

#endif //LIBTUSS_TUSS4470_ARDUINO_H