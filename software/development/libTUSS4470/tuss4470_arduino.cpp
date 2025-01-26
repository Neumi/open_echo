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

int TUSS4470::beginCustomSPI(tuss4470_spi_transfer_fptr spiTransfer_fptr, void *ctx) {
    int err = tuss4470_t_init(spiTransfer_fptr, &tuss4470);
    if (err)
    {
        return err;
    }
    tuss4470.ctx = ctx;
    return 0;
}

// region register access functions

int TUSS4470::setBPF_HPFFreq(uint8_t freq) {
    if (tuss4470_value_is_in_range(BPF_HPF_FREQ, freq)) {
        return 1;
    }
    tuss4470.config->BPF_CONFIG_1 = setConfig(tuss4470.config->BPF_CONFIG_1, BPF_HPF_FREQ, freq);
    return tuss4470_write_register(&tuss4470, BPF_CONFIG_1, tuss4470.config->BPF_CONFIG_1);
}

int TUSS4470::setBPF_Bypass(bool value) {
    tuss4470.config->BPF_CONFIG_1 = setConfig(tuss4470.config->BPF_CONFIG_1, BPF_BYPASS, value);
    return tuss4470_write_register(&tuss4470, BPF_CONFIG_1, tuss4470.config->BPF_CONFIG_1);
}

int TUSS4470::setBPF_FCTrimFrc(bool value) {
    tuss4470.config->BPF_CONFIG_1 = setConfig(tuss4470.config->BPF_CONFIG_1, BPF_FC_TRIM_FRC, value);
    return tuss4470_write_register(&tuss4470, BPF_CONFIG_1, tuss4470.config->BPF_CONFIG_1);
}

int TUSS4470::setBPF_QSel(uint8_t qSel) {
    if (tuss4470_value_is_in_range(tuss4470_BPF_Q_SEL, qSel)) {
        return 1;
    }
    tuss4470.config->BPF_CONFIG_2 = setConfig(tuss4470.config->BPF_CONFIG_2, tuss4470_BPF_Q_SEL, qSel);
    return tuss4470_write_register(&tuss4470, BPF_CONFIG_2, tuss4470.config->BPF_CONFIG_2);
}

int TUSS4470::setBPF_FCTrim(uint8_t fcTrim) {
    if (tuss4470_value_is_in_range(tuss4470_BPF_FC_TRIM, fcTrim)) {
        return 1;
    }
    tuss4470.config->BPF_CONFIG_2 = setConfig(tuss4470.config->BPF_CONFIG_2, tuss4470_BPF_FC_TRIM, fcTrim);
    return tuss4470_write_register(&tuss4470, BPF_CONFIG_2, tuss4470.config->BPF_CONFIG_2);
}

int TUSS4470::setDEV_LogAmpFrc(bool value) {
    tuss4470.config->DEV_CTRL_1 = setConfig(tuss4470.config->DEV_CTRL_1, tuss4470_LOGAMP_FRC, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_1, tuss4470.config->DEV_CTRL_1);
}

int TUSS4470::setDEV_LogAmpSlopeAdj(uint8_t value) {
    if (tuss4470_value_is_in_range(tuss4470_LOGAMP_SLOPE_ADJ, value)) {
        return 1;
    }
    tuss4470.config->DEV_CTRL_1 = setConfig(tuss4470.config->DEV_CTRL_1, tuss4470_LOGAMP_SLOPE_ADJ, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_1, tuss4470.config->DEV_CTRL_1);
}

int TUSS4470::setDEV_LogAmpIntAdj(uint8_t value) {
    if (tuss4470_value_is_in_range(tuss4470_LOGAMP_INT_ADJ, value)) {
        return 1;
    }
    tuss4470.config->DEV_CTRL_1 = setConfig(tuss4470.config->DEV_CTRL_1, tuss4470_LOGAMP_INT_ADJ, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_1, tuss4470.config->DEV_CTRL_1);
}

int TUSS4470::setLogAmpDisableFirstStage(bool value) {
    tuss4470.config->DEV_CTRL_2 = setConfig(tuss4470.config->DEV_CTRL_2, tuss4470_LOGAMP_DIS_FIRST, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_2, tuss4470.config->DEV_CTRL_2);
}

int TUSS4470::setLogAmpDisableLastStage(bool value) {
    tuss4470.config->DEV_CTRL_2 = setConfig(tuss4470.config->DEV_CTRL_2, tuss4470_LOGAMP_DIS_LAST, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_2, tuss4470.config->DEV_CTRL_2);
}

int TUSS4470::setVOUTScaling(bool value) {
    tuss4470.config->DEV_CTRL_2 = setConfig(tuss4470.config->DEV_CTRL_2, tuss4470_VOUT_SCALE_SEL, value);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_2, tuss4470.config->DEV_CTRL_2);
}

int TUSS4470::setLNAGain(uint8_t gain) {
    if (tuss4470_value_is_in_range(tuss4470_LNA_GAIN, gain)) {
        return 1;
    }
    tuss4470.config->DEV_CTRL_3 = setConfig(tuss4470.config->DEV_CTRL_3, tuss4470_LNA_GAIN, gain);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_3, tuss4470.config->DEV_CTRL_3);
}

int TUSS4470::setDriverPulseFaultDeglitchTime(uint8_t time) {
    if (tuss4470_value_is_in_range(tuss4470_DRV_PLS_FLT_DT, time)) {
        return 1;
    }
    tuss4470.config->DEV_CTRL_3 = setConfig(tuss4470.config->DEV_CTRL_3, tuss4470_DRV_PLS_FLT_DT, time);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_3, tuss4470.config->DEV_CTRL_3);
}

int TUSS4470::setLowVoltageIOConfig(uint8_t config) {
    if (tuss4470_value_is_in_range(tuss4470_IO_MODE, config)) {
        return 1;
    }
    tuss4470.config->DEV_CTRL_3 = setConfig(tuss4470.config->DEV_CTRL_3, tuss4470_IO_MODE, config);
    return tuss4470_write_register(&tuss4470, DEV_CTRL_3, tuss4470.config->DEV_CTRL_3);
}

int TUSS4470::setDisableVDRVRegulationInListenMode(bool value) {
    tuss4470.config->VDRV_CTRL = setConfig(tuss4470.config->VDRV_CTRL, tuss4470_DIS_VDRV_REG_LSTN, value);
    return tuss4470_write_register(&tuss4470, VDRV_CTRL, tuss4470.config->VDRV_CTRL);
}

int TUSS4470::setVDRVHighImpedance(bool value) {
    tuss4470.config->VDRV_CTRL = setConfig(tuss4470.config->VDRV_CTRL, tuss4470_VDRV_HI_Z, value);
    return tuss4470_write_register(&tuss4470, VDRV_CTRL, tuss4470.config->VDRV_CTRL);
}

int TUSS4470::setVDRVCurrentLevel(bool value) {
    tuss4470.config->VDRV_CTRL = setConfig(tuss4470.config->VDRV_CTRL, tuss4470_VDRV_CURRENT_LEVEL, value);
    return tuss4470_write_register(&tuss4470, VDRV_CTRL, tuss4470.config->VDRV_CTRL);
}

int TUSS4470::setVDRVVoltageLevel(uint8_t level) {
    if (tuss4470_value_is_in_range(tuss4470_VDRV_VOLTAGE_LEVEL, level)) {
        return 1;
    }
    tuss4470.config->VDRV_CTRL = setConfig(tuss4470.config->VDRV_CTRL, tuss4470_VDRV_VOLTAGE_LEVEL, level);
    return tuss4470_write_register(&tuss4470, VDRV_CTRL, tuss4470.config->VDRV_CTRL);
}

int TUSS4470::setEchoInterruptComparatorEnable(bool value) {
    tuss4470.config->ECHO_INT_CONFIG = setConfig(tuss4470.config->ECHO_INT_CONFIG, tuss4470_ECHO_INT_CMP_EN, value);
    return tuss4470_write_register(&tuss4470, ECHO_INT_CONFIG, tuss4470.config->ECHO_INT_CONFIG);
}

int TUSS4470::setEchoInterruptThreshold(uint8_t threshold) {
    if (tuss4470_value_is_in_range(tuss4470_ECHO_INT_THR_SEL, threshold)) {
        return 1;
    }
    tuss4470.config->ECHO_INT_CONFIG = setConfig(tuss4470.config->ECHO_INT_CONFIG, tuss4470_ECHO_INT_THR_SEL, threshold);
    return tuss4470_write_register(&tuss4470, ECHO_INT_CONFIG, tuss4470.config->ECHO_INT_CONFIG);
}

int TUSS4470::setZeroCrossComparatorEnable(bool value) {
    tuss4470.config->ZC_CONFIG = setConfig(tuss4470.config->ZC_CONFIG, tuss4470_ZC_CMP_EN, value);
    return tuss4470_write_register(&tuss4470, ZC_CONFIG, tuss4470.config->ZC_CONFIG);
}

int TUSS4470::setZeroCrossEnableEchoInterrupt(bool value) {
    tuss4470.config->ZC_CONFIG = setConfig(tuss4470.config->ZC_CONFIG, tuss4470_ZC_EN_ECHO_INT, value);
    return tuss4470_write_register(&tuss4470, ZC_CONFIG, tuss4470.config->ZC_CONFIG);
}

int TUSS4470::setZeroComparatorInputSelect(bool value) {
    tuss4470.config->ZC_CONFIG = setConfig(tuss4470.config->ZC_CONFIG, tuss4470_ZC_CMP_IN_SEL, value);
    return tuss4470_write_register(&tuss4470, ZC_CONFIG, tuss4470.config->ZC_CONFIG);
}

int TUSS4470::setZeroCrossComparatorStageSelect(uint8_t stage) {
    if (tuss4470_value_is_in_range(tuss4470_ZC_CMP_STG_SEL, stage)) {
        return 1;
    }
    tuss4470.config->ZC_CONFIG = setConfig(tuss4470.config->ZC_CONFIG, tuss4470_ZC_CMP_STG_SEL, stage);
    return tuss4470_write_register(&tuss4470, ZC_CONFIG, tuss4470.config->ZC_CONFIG);
}

int TUSS4470::setZeroCrossComparatorHysteresis(uint8_t hysteresis) {
    if (tuss4470_value_is_in_range(tuss4470_ZC_CMP_HYST, hysteresis)) {
        return 1;
    }
    tuss4470.config->ZC_CONFIG = setConfig(tuss4470.config->ZC_CONFIG, tuss4470_ZC_CMP_HYST, hysteresis);
    return tuss4470_write_register(&tuss4470, ZC_CONFIG, tuss4470.config->ZC_CONFIG);
}

int TUSS4470::setHalfBridgeMode(bool value) {
    tuss4470.config->BURST_PULSE = setConfig(tuss4470.config->BURST_PULSE, tuss4470_HALF_BRG_MODE, value);
    return tuss4470_write_register(&tuss4470, BURST_PULSE, tuss4470.config->BURST_PULSE);
}

int TUSS4470::setPreDriverMode(bool value) {
    tuss4470.config->BURST_PULSE = setConfig(tuss4470.config->BURST_PULSE, tuss4470_PRE_DRIVER_MODE, value);
    return tuss4470_write_register(&tuss4470, BURST_PULSE, tuss4470.config->BURST_PULSE);
}

int TUSS4470::setBurstPulseNumber(uint8_t pulseCount) {
    if (tuss4470_value_is_in_range(tuss4470_BURST_PULSE, pulseCount)) {
        return 1;
    }
    tuss4470.config->BURST_PULSE = setConfig(tuss4470.config->BURST_PULSE, tuss4470_BURST_PULSE, pulseCount);
    return tuss4470_write_register(&tuss4470, BURST_PULSE, tuss4470.config->BURST_PULSE);
}

int TUSS4470::setSleepModeEnable(bool value) {
    tuss4470.config->TOF_CONFIG = setConfig(tuss4470.config->TOF_CONFIG, tuss4470_SLEEP_MODE_EN, value);
    return tuss4470_write_register(&tuss4470, TOF_CONFIG, tuss4470.config->TOF_CONFIG);
}

int TUSS4470::setStandbyModeEnable(bool value) {
    tuss4470.config->TOF_CONFIG = setConfig(tuss4470.config->TOF_CONFIG, tuss4470_STDBY_MODE_EN, value);
    return tuss4470_write_register(&tuss4470, TOF_CONFIG, tuss4470.config->TOF_CONFIG);
}

int TUSS4470::setVDRVTriggerControl(bool value) {
    tuss4470.config->TOF_CONFIG = setConfig(tuss4470.config->TOF_CONFIG, tuss4470_VDRV_TRIGGER, value);
    return tuss4470_write_register(&tuss4470, TOF_CONFIG, tuss4470.config->TOF_CONFIG);
}

int TUSS4470::setCommandTriggerControl(bool value) {
    tuss4470.config->TOF_CONFIG = setConfig(tuss4470.config->TOF_CONFIG, tuss4470_CMD_TRIGGER, value);
    return tuss4470_write_register(&tuss4470, TOF_CONFIG, tuss4470.config->TOF_CONFIG);
}

// endregion


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
