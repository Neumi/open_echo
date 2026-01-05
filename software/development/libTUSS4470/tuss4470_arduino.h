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
        int beginCustomSPI(tuss4470_spi_transfer_fptr spiTransfer_fptr, void *ctx);
        int readConfig();
        int writeConfig();

        // region specific register access
        int setBPF_HPFFreq(uint8_t freq);
        int setBPF_Bypass(bool value);
        int setBPF_FCTrimFrc(bool value);

        int setBPF_QSel(uint8_t qSel);
        int setBPF_FCTrim(uint8_t fcTrim);

        int setDEV_LogAmpFrc(bool value);
        int setDEV_LogAmpSlopeAdj(uint8_t value);
        int setDEV_LogAmpIntAdj(uint8_t value);

        int setLogAmpDisableFirstStage(bool value);
        int setLogAmpDisableLastStage(bool value);
        int setVOUTScaling(bool value);
        int setLNAGain(uint8_t gain);


        int setDriverPulseFaultDeglitchTime(uint8_t time);
        int setLowVoltageIOConfig(uint8_t config);


        int setDisableVDRVRegulationInListenMode(bool value);
        int setVDRVHighImpedance(bool value);
        int setVDRVCurrentLevel(bool value);
        int setVDRVVoltageLevel(uint8_t level);


        int setEchoInterruptComparatorEnable(bool value);
        int setEchoInterruptThreshold(uint8_t threshold);

        int setZeroCrossComparatorEnable(bool value);
        int setZeroCrossEnableEchoInterrupt(bool value);
        int setZeroComparatorInputSelect(bool value);
        int setZeroCrossComparatorStageSelect(uint8_t stage);
        int setZeroCrossComparatorHysteresis(uint8_t hysteresis);

        int setHalfBridgeMode(bool value);
        int setPreDriverMode(bool value);
        int setBurstPulseNumber(uint8_t pulseCount);

        int setSleepModeEnable(bool value);
        int setStandbyModeEnable(bool value);
        int setVDRVTriggerControl(bool value);
        int setCommandTriggerControl(bool value);


        uint8_t getBPF_HPFFreq();
        bool getBPF_Bypass();
        bool getBPF_FCTrimFrc();

        uint8_t getBPF_QSel();
        uint8_t getBPF_FCTrim();

        bool getDEV_LogAmpFrc();
        uint8_t getDEV_LogAmpSlopeAdj();
        uint8_t getDEV_LogAmpIntAdj();

        bool getLogAmpDisableFirstStage();
        bool getLogAmpDisableLastStage();
        bool getVOUTScaling();
        uint8_t getLNAGain();

        uint8_t getDriverPulseFaultDeglitchTime();
        uint8_t getLowVoltageIOConfig();

        bool getDisableVDRVRegulationInListenMode();
        bool getVDRVHighImpedance();
        bool getVDRVCurrentLevel();
        uint8_t getVDRVVoltageLevel();

        bool getEchoInterruptComparatorEnable();
        uint8_t getEchoInterruptThreshold();

        bool getZeroCrossComparatorEnable();
        bool getZeroCrossEnableEchoInterrupt();
        bool getZeroComparatorInputSelect();
        uint8_t getZeroCrossComparatorStageSelect();
        uint8_t getZeroCrossComparatorHysteresis();

        bool getHalfBridgeMode();
        bool getPreDriverMode();
        uint8_t getBurstPulseNumber();

        bool getSleepModeEnable();
        bool getStandbyModeEnable();
        bool getVDRVTriggerControl();
        bool getCommandTriggerControl();


        // endregion

        

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