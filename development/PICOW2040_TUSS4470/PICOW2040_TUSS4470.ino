#include "settings.h"
#include <SPI.h>
#include "hardware/adc.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include <SoftwareSerial.h>

#if WIFI_ENABLED
  #include "wifi_server.h"
#endif

// -------------------- PIN DEFINITIONS --------------------
const int SPI_CS = 17;    // Chip select for TUSS4470
const int IO1 = 3;        // Enable pin or control (set HIGH)
const int IO2 = 2;        // Burst output pin (transducer drive)
const int O4 = 20;        // TUSS4470 OUT4 threshold detect input
const int analogIn = 26;  // ADC0 (GPIO26)

struct __attribute__((packed)) Frame {
  uint8_t  start = 0xAA;
  uint16_t  depth_index;            
  int16_t  temp_scaled;     
  uint16_t vDrv_scaled;     
  uint8_t  samples[NUM_SAMPLES];
  uint8_t  checksum;         
};

static Frame frame;  // Data frame to send over WebSocket
static uint8_t samplesXor = 0;   // Accumulate XOR while sampling

volatile bool detectedDepth = false;
volatile int depthDetectSample = 0;
volatile int sampleIndex = 0;

float temperature = 0.0f;
int vDrv = 0;

SoftwareSerial nmeaSerial(4, 5); // RX, TX

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
  // Header fields
  frame.depth_index = depthDetectSample;

  frame.temp_scaled = (int16_t)(temperature * 100.0f);
  frame.vDrv_scaled = (uint16_t)(vDrv * 100);

  // Compute checksum (XOR of depth bytes, temp bytes, vDrv bytes, all samples)
  uint8_t cs = 0;
  // depth
  cs ^= (uint8_t)(frame.depth_index & 0xFF);
  cs ^= (uint8_t)(frame.depth_index >> 8);
  // temp
  cs ^= (uint8_t)(frame.temp_scaled & 0xFF);
  cs ^= (uint8_t)(frame.temp_scaled >> 8);
  // vDrv
  cs ^= (uint8_t)(frame.vDrv_scaled & 0xFF);
  cs ^= (uint8_t)(frame.vDrv_scaled >> 8);
  // samples (already accumulated)
  cs ^= samplesXor;
  frame.checksum = cs;

  // Total length (packed, known)
  const size_t len = 1 + 2 + 2 + 2 + NUM_SAMPLES + 1;

  Serial.write(reinterpret_cast<uint8_t*>(&frame), len);

  #if WIFI_ENABLED && ENABLE_UDP_ECHO
    udpBroadcastBIN(reinterpret_cast<uint8_t*>(&frame), len, UDP_ECHO_PORT);
  #endif
}


void sendNmeaDBT() {
  // Calculate depth in meters
  float time_of_flight = depthDetectSample * 13.2e-6f;
  float depth_m = (time_of_flight * 1450.0f) / 2.0f;

  float depth_ft = depth_m * 3.28084f;
  float depth_fa = depth_m / 1.8288f;

  // Convert floats to strings
  char str_ft[10], str_m[10], str_fa[10];
  dtostrf(depth_ft, 4, 1, str_ft);
  dtostrf(depth_m, 4, 1, str_m);
  dtostrf(depth_fa, 4, 1, str_fa);

  // Trim leading spaces (manually)
  char* ptr_ft = str_ft;
  char* ptr_m = str_m;
  char* ptr_fa = str_fa;
  while (*ptr_ft == ' ') ptr_ft++;
  while (*ptr_m == ' ') ptr_m++;
  while (*ptr_fa == ' ') ptr_fa++;

  // Build the NMEA DBT sentence
  char dbt_sentence[80];
  snprintf(dbt_sentence, sizeof(dbt_sentence),
           "$SDDBT,%s,f,%s,M,%s,F", ptr_ft, ptr_m, ptr_fa);

  // Calculate checksum (XOR of chars between $ and *)
  uint8_t dbt_checksum = 0;
  for (int i = 1; dbt_sentence[i] != '\0'; i++) {
    dbt_checksum ^= dbt_sentence[i];
  }

  // Final output with checksum
  char fullDBTSentence[90];
  snprintf(fullDBTSentence, sizeof(fullDBTSentence), "%s*%02X\r\n", dbt_sentence, dbt_checksum);

  nmeaSerial.print(fullDBTSentence);
  #if WIFI_ENABLED && ENABLE_UDP_NMEA
    udpBroadcastNMEA(fullDBTSentence, strlen(fullDBTSentence), UDP_NMEA_PORT);
  #endif

  // Build the NMEA DPT sentence
  char str_offset[10];
  dtostrf(DEPTH_OFFSET, 4, 1, str_offset);
  char* ptr_offset = str_offset;
  while (*ptr_offset == ' ') ptr_offset++;

  // We are (possibly optimistically) reporting max depth of 100m
  char dpt_sentence[80];
  snprintf(dpt_sentence, sizeof(dpt_sentence),
           "$SDDPT,%s,%s,100", ptr_m, ptr_offset);

  // Calculate checksum (XOR of chars between $ and *)
  uint8_t dpt_checksum = 0;
  for (int i = 1; dpt_sentence[i] != '\0'; i++) {
    dpt_checksum ^= dpt_sentence[i];
  }

  // Final output with checksum
  char fullDPTSentence[90];
  snprintf(fullDPTSentence, sizeof(fullDPTSentence), "%s*%02X\r\n", dpt_sentence, dpt_checksum);

  nmeaSerial.print(fullDPTSentence);
  #if WIFI_ENABLED && ENABLE_UDP_NMEA
    udpBroadcastNMEA(fullDPTSentence, strlen(fullDPTSentence), UDP_NMEA_PORT);
  #endif
}

void setup() {
  Serial.begin(250000);
  nmeaSerial.begin(NMEA_BAUD_RATE);
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
  tuss4470Write(0x10, FILTER_FREQUENCY_REGISTER);             // BPF 40kHz
  tuss4470Write(0x16, 0x0F);             // Enable VDRV
  tuss4470Write(0x1A, 0x0F);             // 16 pulses
  tuss4470Write(0x17, THRESHOLD_VALUE);  // Threshold detect OUT4

  // --- ADC init ---
  adc_init();
  adc_gpio_init(analogIn);
  adc_select_input(0);

  // --- WiFi init ---
  #if WIFI_ENABLED
    wifiSetup(WIFI_SSID, WIFI_PASS);
  #endif
}

// -------------------- LOOP --------------------
void loop() {
  tuss4470Write(0x1B, 0x01);         // Start time-of-flight
  generateBurst(IO2, DRIVE_FREQUENCY, 16);  // 40kHz, 16 cycles

  unsigned long startTime = micros();

  samplesXor = 0;
  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    adc_select_input(0);
    adc_run(true);
    adc_hw->cs |= ADC_CS_START_ONCE_BITS;
    while (adc_hw->cs & ADC_CS_START_ONCE_BITS)
      ;
    
    uint8_t value = adc_hw->result >> 4;  // Scale 12-bit to 8-bit
    frame.samples[sampleIndex] = value;
    samplesXor ^= value;
    delayMicroseconds(5);  // 6 uS total sampling per sample
    //delayMicroseconds(11); //    delayMicroseconds(12); // 13 uS total sampling per sample

    if (sampleIndex == BLINDZONE_SAMPLE_END)
      detectedDepth = false;
  }

  tuss4470Write(0x1B, 0x00);  // Stop time-of-flight

  unsigned long elapsedTime = micros() - startTime;
  // Serial.println(elapsedTime);

  // Software gradient-based override
  #if USE_GRADIENT_OVERRIDE
  int overrideSample = 0;
  uint8_t prev = frame.samples[BLINDZONE_SAMPLE_END];
  for (int i = BLINDZONE_SAMPLE_END + 1; i < NUM_SAMPLES; i++) {
    uint8_t cur = frame.samples[i];
    uint8_t diff = cur - prev;
    if (diff >= GRADIENT_THRESHOLD) {
      overrideSample = i;
      break;
    }
    prev = cur;
  }
  if (overrideSample > 0) {
    depthDetectSample = overrideSample;
  }
  #endif

  sendNmeaDBT();
  sendData();

  delay(10);
}
