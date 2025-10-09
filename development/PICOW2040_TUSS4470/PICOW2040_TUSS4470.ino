#include <SPI.h>
#include "hardware/adc.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"

// -------------------- PIN DEFINITIONS --------------------
const int SPI_CS = 17;    // Chip select for TUSS4470
const int IO1 = 3;        // Enable pin or control (set HIGH)
const int IO2 = 2;        // Burst output pin (transducer drive)
const int O4 = 20;        // TUSS4470 OUT4 threshold detect input
const int analogIn = 26;  // ADC0 (GPIO26)

// -------------------- SAMPLING SETTINGS --------------------
#define NUM_SAMPLES 5000
#define BLINDZONE_SAMPLE_END 450
#define THRESHOLD_VALUE 0x19

uint16_t samples[NUM_SAMPLES];
volatile bool detectedDepth = false;
volatile int depthDetectSample = 0;
volatile int sampleIndex = 0;

float temperature = 0.0f;
int vDrv = 0;

// -------------------- SPI BUFFERS --------------------
byte misoBuf[2];
byte inByteArr[2];

// -------------------- BURST GENERATION --------------------
void generateBurst(uint pin, float frequency, uint cycles) {
  PIO pio = pio0;
  uint sm = pio_claim_unused_sm(pio, true);

  float clk_sys_hz = (float)clock_get_hz(clk_sys);
  float period = 1.0f / frequency;
  float half_period = period / 2.0f;
  float target_rate = 1.0f / half_period;
  float div = clk_sys_hz / target_rate;

  static const uint16_t program[] = {
    0xe081,  // set pins, 1
    0xe001   // set pins, 0
  };
  uint offset = pio_add_program_at_offset(pio, (const pio_program_t*)&program, 0);

  pio_gpio_init(pio, pin);
  pio_sm_set_consecutive_pindirs(pio, sm, pin, 1, true);

  pio_sm_config c = pio_get_default_sm_config();
  sm_config_set_set_pins(&c, pin, 1);
  sm_config_set_clkdiv(&c, div);
  sm_config_set_wrap(&c, offset, offset + 1);
  pio_sm_init(pio, sm, offset, &c);
  pio_sm_set_enabled(pio, sm, true);

  for (uint i = 0; i < cycles; i++) {
    pio_sm_exec(pio, sm, pio_encode_set(pio_pins, 1));
    sleep_us(half_period * 1e6);
    pio_sm_exec(pio, sm, pio_encode_set(pio_pins, 0));
    sleep_us(half_period * 1e6);
  }

  pio_sm_set_enabled(pio, sm, false);
  pio_remove_program(pio, (const pio_program_t*)&program, offset);
  pio_sm_unclaim(pio, sm);
}

// -------------------- INTERRUPT HANDLER --------------------
void handleInterrupt() {
  if (!detectedDepth) {
    depthDetectSample = sampleIndex;
    detectedDepth = true;
  }
}

// -------------------- SPI UTILS --------------------
void spiTransfer(byte* mosi, byte sizeOfArr) {
  memset(misoBuf, 0x00, sizeof(misoBuf));

  digitalWrite(SPI_CS, LOW);
  for (int i = 0; i < sizeOfArr; i++) {
    misoBuf[i] = SPI.transfer(mosi[i]);
  }
  digitalWrite(SPI_CS, HIGH);
}

unsigned int BitShiftCombine(unsigned char x_high, unsigned char x_low) {
  return (x_high << 8) | x_low;
}

byte parity16(unsigned int val) {
  byte ones = 0;
  for (int i = 0; i < 16; i++) {
    if ((val >> i) & 1) {
      ones++;
    }
  }
  return (ones + 1) % 2;
}

byte tuss4470Parity(byte* spi16Val) {
  return parity16(BitShiftCombine(spi16Val[0], spi16Val[1]));
}

byte tuss4470Read(byte addr) {
  inByteArr[0] = 0x80 + ((addr & 0x3F) << 1);
  inByteArr[1] = 0x00;
  inByteArr[0] |= tuss4470Parity(inByteArr);
  spiTransfer(inByteArr, sizeof(inByteArr));
  return misoBuf[1];
}

void tuss4470Write(byte addr, byte data) {
  inByteArr[0] = (addr & 0x3F) << 1;
  inByteArr[1] = data;
  inByteArr[0] |= tuss4470Parity(inByteArr);
  spiTransfer(inByteArr, sizeof(inByteArr));
}

void sendData() {
  Serial.write(0xAA);

  uint8_t checksum = 0;

  uint8_t depthHigh = depthDetectSample >> 8;
  uint8_t depthLow = depthDetectSample & 0xFF;
  Serial.write(depthHigh);
  Serial.write(depthLow);
  checksum ^= depthHigh ^ depthLow;

  int16_t temp_scaled = temperature * 100;
  uint8_t tempHigh = temp_scaled >> 8;
  uint8_t tempLow = temp_scaled & 0xFF;
  Serial.write(tempHigh);
  Serial.write(tempLow);
  checksum ^= tempHigh ^ tempLow;

  uint16_t vDrv_scaled = vDrv * 100;
  uint8_t vDrvHigh = vDrv_scaled >> 8;
  uint8_t vDrvLow = vDrv_scaled & 0xFF;
  Serial.write(vDrvHigh);
  Serial.write(vDrvLow);
  checksum ^= vDrvHigh ^ vDrvLow;

  for (int i = 0; i < NUM_SAMPLES; i++) {
    uint8_t highByte = samples[i] >> 8;
    uint8_t lowByte = samples[i] & 0xFF;
    Serial.write(highByte);
    Serial.write(lowByte);
    checksum ^= highByte ^ lowByte;
  }

  Serial.write(checksum);
}

void setup() {
  Serial.begin(115200);
  delay(100);

  SPI.begin();
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));

  pinMode(SPI_CS, OUTPUT);
  digitalWrite(SPI_CS, HIGH);

  pinMode(IO1, OUTPUT);
  digitalWrite(IO1, HIGH);
  pinMode(O4, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(O4), handleInterrupt, RISING);

  // --- Initialize TUSS4470 ---
  tuss4470Write(0x10, 0x00);             // BPF 40kHz
  tuss4470Write(0x16, 0x0F);             // Enable VDRV
  tuss4470Write(0x1A, 0x0F);             // 16 pulses
  tuss4470Write(0x17, THRESHOLD_VALUE);  // Threshold detect OUT4

  // --- ADC init ---
  adc_init();
  adc_gpio_init(analogIn);
  adc_select_input(0);
}

// -------------------- LOOP --------------------
void loop() {
  tuss4470Write(0x1B, 0x01);         // Start time-of-flight
  generateBurst(IO2, 40000.0f, 16);  // 40kHz, 16 cycles
  // generateBurst(IO2, 1000000.0f, 16);  // 1000kHz, 16 cycles needs to be fixed!! #TODO

  unsigned long startTime = micros();

  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    adc_select_input(0);
    adc_run(true);
    adc_hw->cs |= ADC_CS_START_ONCE_BITS;
    while (adc_hw->cs & ADC_CS_START_ONCE_BITS)
      ;
    samples[sampleIndex] = adc_hw->result;
    delayMicroseconds(5);  // 6 uS total sampling per sample
    //delayMicroseconds(11); //    delayMicroseconds(12); // 13 uS total sampling per sample

    if (sampleIndex == BLINDZONE_SAMPLE_END)
      detectedDepth = false;
  }

  tuss4470Write(0x1B, 0x00);  // Stop time-of-flight

  unsigned long elapsedTime = micros() - startTime;

  // Serial.println(elapsedTime);
  sendData();

  delay(10);
}
