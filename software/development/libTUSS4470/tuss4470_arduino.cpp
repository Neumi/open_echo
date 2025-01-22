#include "tuss4470_arduino.h"

const int _default_cs = 10;
const int _default_io1 = 8;
const int _default_io2 = 9;
const int _default_o3 = 6;
const int _default_o4 = 5;
const int _default_analogIn = A0;


// region C callbacks for SPI communication

int _spiTransfer(uint8_t mode, uint8_t *data, uint8_t size, void *ctx) {
    TUSS4470 *tuss = (TUSS4470 *)ctx;
    return tuss->spiTransfer(mode, data, size);
}


// endregion



TUSS4470::TUSS4470() {
    cs = _default_cs;
    io1 = _default_io1;
    io2 = _default_io2;
    o3 = _default_o3;
    o4 = _default_o4;
    analogIn = _default_analogIn;
}

TUSS4470::~TUSS4470() {
    tuss4470_t_free(&tuss4470);
}

int TUSS4470::begin() {
    // Initialize SPI
    SPI.begin();
    SPI.setBitOrder(MSBFIRST);
    SPI.setClockDivider(SPI_CLOCK_DIV16);
    SPI.setDataMode(SPI_MODE1);  // CPOL=0, CPHA=1
    // Configure GPIOs
    pinMode(_default_cs, OUTPUT);

    digitalWrite(_default_cs, HIGH);
    pinMode(_default_io1, OUTPUT);
    digitalWrite(_default_io1, HIGH);
    pinMode(_default_io2, OUTPUT);
    pinMode(_default_o3, INPUT);
    pinMode(_default_o4, INPUT);

    int err = tuss4470_t_init(&_spiTransfer, &tuss4470);
    if (err)
    {
        return err;
    }
    tuss4470.ctx = (void*)this;
    return 0;
}

int TUSS4470::readConfig() {
    return tuss4470_read_config(&tuss4470, tuss4470.config);
}

int TUSS4470::writeConfig() {
    return tuss4470_write_config(&tuss4470, tuss4470.config);
}

int TUSS4470::readRawRegister(tuss4470_register_map_t reg, uint8_t *data) {
    return tuss4470_read_register(&tuss4470, reg, data);
}

int TUSS4470::writeRawRegister(tuss4470_register_map_t reg, uint8_t data) {
    return tuss4470_write_register(&tuss4470, reg, data);
}

uint8_t TUSS4470::getConfig(uint8_t configData, uint8_t mask) {
    return tuss4470_get_config(configData, mask);
}

uint8_t TUSS4470::setConfig(uint8_t configData, uint8_t mask, uint8_t value) {
    return tuss4470_set_config(configData, mask, value);
}

// region private functions
int TUSS4470::spiTransfer(uint8_t mode, uint8_t *data, uint8_t size) {
    digitalWrite(cs, LOW);
    data[0] = SPI.transfer(data[0]);
    data[1] = SPI.transfer(data[1]);
    digitalWrite(cs, HIGH);
    return 0;
}

// endregion
