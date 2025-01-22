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


int spiTransfer(uint8_t mode, uint8_t *data, uint8_t size) {
  static uint8_t buffer[2];
  digitalWrite(SPI_CS, LOW);
  data[0] = SPI.transfer(data[0]);
  data[1] = SPI.transfer(data[1]);
  digitalWrite(SPI_CS, HIGH);
  return 0;
}

void setup() {
  Serial.begin(115200);

  TUSS4470 tuss;
  int err = tuss.begin();
  if (err)
  {
      Serial.println("Error init tuss");
      return;
  }
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
}

void loop() {
  

}
