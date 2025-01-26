#define PLATFORM_ARDUINO
#include "tuss4470.h"
#include "tuss4470_arduino.h"
#include <SPI.h>


const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 6;
const int O4 = 5;
const int analogIn = A0;


void setup() {
  Serial.begin(115200);

  // Using default contructor which uses the internal Arduino SPI
  // Use .beginCustomSPI() for different platforms
  TUSS4470 tuss;
  int err = tuss.begin();
  if (err)
  {
      Serial.println("Error init tuss");
      return;
  }
  // Read the complete configuration from TUSS device
  err = tuss.readConfig();
  if (err) {
    Serial.println("Error reading config");
  }
  Serial.println("TUSS4470 Configuration:");
  uint8_t *cfg_data = (uint8_t *)tuss.getConfig();
  for (int i = 0; i < sizeof(tuss4470_config_t); ++i) {
    Serial.print("Register 0x");
    Serial.print(tuss4470_register_map[i], HEX);
    Serial.print(": 0x");
    Serial.println(cfg_data[i], HEX);
  }

  // Set a specific register, the register is written to the device and automatically read again
  // written value must match read value otherwise error will be returned
  // Also the value is checked if it is in the valid range
  err = tuss.setBPF_HPFFreq(0x1D);
  if (err) {
    Serial.println(F("Failed to set parameter HPFFreq to 0x1D"));
    return;
  }
  Serial.println(F("Successfully set parameter HPFFreq to 0x1D"));
}

void loop() {
  

}
