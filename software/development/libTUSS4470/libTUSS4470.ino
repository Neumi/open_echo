#define PLATFORM_ARDUINO
#include "tuss4470.h"
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

  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  SPI.setClockDivider(SPI_CLOCK_DIV16);
  SPI.setDataMode(SPI_MODE1);  // CPOL=0, CPHA=1


  pinMode(SPI_CS, OUTPUT);
  digitalWrite(SPI_CS, HIGH);

    // Configure GPIOs
  pinMode(IO1, OUTPUT);
  digitalWrite(IO1, HIGH);
  pinMode(IO2, OUTPUT);
  pinMode(O3, INPUT);
  pinMode(O4, INPUT);

  Serial.println("Initialize TUSS lib");
  tuss4470_t tuss4470;
  int err = tuss4470_t_init(&spiTransfer, &tuss4470);
  if (err)
  {
    Serial.println("Failed to init TUSS lib");
  }
  
  tuss4470_config_t config;
  err = tuss4470_read_config(&tuss4470, tuss4470.config);
  if (err) {
    Serial.println("Failed to read config");
    return;
  }

  Serial.println("TUSS4470 Configuration:");
  uint8_t *cfg_data = (uint8_t *)tuss4470.config;
  for (int i = 0; i < sizeof(tuss4470_config_t); ++i) {
    Serial.print("Register 0x");
    Serial.print(tuss4470_register_map[i], HEX);
    Serial.print(": 0x");
    Serial.println(cfg_data[i], HEX);
  }
}

void loop() {
  

}
