#include <SPI.h>
#include "FspTimer.h"
#include <WiFiS3.h>
#include "wifi_server.h"
#include <ctype.h>
#include <string.h>
#include <stdlib.h>
#include "settings.h"
#include "routes.h"

// Pin configuration
const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 3;
const int O4 = 2;
const int analogIn = A0;

// ---------------------- ADC SETUP ----------------------
// Defines addresses and convenience functions for RA4M1 ADC
// Base addresses for ADC (from RA4M1 hardware manual)
// Taken from https://github.com/TriodeGirl/Arduino-UNO-R4-code-DAC-ADC-Ints-Fast_Pins/blob/main/Arduino_UNO_R4_Interrupts_ADC_and_DAC_1.ino
#define MSTP_BASE   0x40040000u
#define MSTPCRD    (*(volatile uint32_t *)(MSTP_BASE + 0x7008u))

#define ADC_BASE    0x40050000u
#define ADCSR      (*(volatile uint16_t *)(ADC_BASE + 0xC000u))
#define ADANSA0    (*(volatile uint16_t *)(ADC_BASE + 0xC004u))
#define ADCER      (*(volatile uint16_t *)(ADC_BASE + 0xC00Eu))
#define ADSTRGR    (*(volatile uint16_t *)(ADC_BASE + 0xC010u)) // Not currently used, could be used to trigger ADC from timer. If combined with DMA, could be even faster.
#define ADDR09     (*(volatile uint16_t *)(ADC_BASE + 0xC020u + 18)) // channel AN09 (A0 pin)

byte misoBuf[2];  // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer

struct __attribute__((packed)) Frame {
  uint8_t  start = 0xAA;
  uint16_t  depth;            
  int16_t  temp_scaled;     
  uint16_t vDrv_scaled;     
  uint8_t  samples[NUM_SAMPLES];
  uint8_t  checksum;         
};

static Frame frame;  // Data frame to send over WebSocket
static uint8_t samplesXor = 0;   // Accumulate XOR while sampling

volatile long lastRunTime = 0;

volatile int pulseCount = 0;
volatile int sampleIndex = 0;

float temperature = 0.0f;
int vDrv = 0;

volatile bool detectedDepth = false;  // Condition flag
volatile int depthDetectSample = 0;

// --- Burst Control Timer ---
FspTimer burstTimer;

void burstCallback(timer_callback_args_t *) {
  digitalWrite(IO2, !digitalRead(IO2));
  pulseCount++;
  if (pulseCount >= 32) {
    burstTimer.stop();
  }
}

byte tuss4470Read(byte addr) {
  inByteArr[0] = 0x80 + ((addr & 0x3F) << 1);  // Set read bit and address
  inByteArr[1] = 0x00;  // Empty data byte
  inByteArr[0] |= tuss4470Parity(inByteArr);
  spiTransfer(inByteArr, sizeof(inByteArr));

  return misoBuf[1];
}

void tuss4470Write(byte addr, byte data) {
  inByteArr[0] = (addr & 0x3F) << 1;  // Set write bit and address
  inByteArr[1] = data;
  inByteArr[0] |= tuss4470Parity(inByteArr);
  spiTransfer(inByteArr, sizeof(inByteArr));
}

byte tuss4470Parity(byte* spi16Val) {
  return parity16(BitShiftCombine(spi16Val[0], spi16Val[1]));
}

void spiTransfer(byte* mosi, byte sizeOfArr) {
  memset(misoBuf, 0x00, sizeof(misoBuf));

  digitalWrite(SPI_CS, LOW);
  for (int i = 0; i < sizeOfArr; i++) {
    misoBuf[i] = SPI.transfer(mosi[i]);
  }
  digitalWrite(SPI_CS, HIGH);
}

unsigned int BitShiftCombine(unsigned char x_high, unsigned char x_low) {
  return (x_high << 8) | x_low;  // Combine high and low bytes
}

byte parity16(unsigned int val) {
  byte ones = 0;
  for (int i = 0; i < 16; i++) {
    if ((val >> i) & 1) {
      ones++;
    }
  }
  return (ones + 1) % 2;  // Odd parity calculation
}

void handleInterrupt() {
  if (!detectedDepth) {
    depthDetectSample = sampleIndex;
    detectedDepth = true;
  }
}

void setup()
{
  Serial.begin(250000);

  SPI.begin();
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1)); 


  pinMode(SPI_CS, OUTPUT);
  digitalWrite(SPI_CS, HIGH);

  // Configure GPIOs
  pinMode(IO1, OUTPUT);
  digitalWrite(IO1, HIGH);
  pinMode(IO2, OUTPUT);
  pinMode(O4, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(O4), handleInterrupt, RISING);

  // Initialize TUSS4470 with specific configurations
  // check TUSS4470 datasheet for more settings!
  tuss4470Write(0x10, FILTER_FREQUENCY_REGISTER);  // Set BPF center frequency
  tuss4470Write(0x16, 0xF);  // Enable VDRV (not Hi-Z)
  tuss4470Write(0x1A, 0x0F);  // Set burst pulses to 16
  tuss4470Write(0x17, THRESHOLD_VALUE); // enable threshold detection on OUT_4

  // Set up timer for transducer burst
  uint8_t timerType = GPT_TIMER;                 // get_available_timer needs a modifiable lvalue reference
  uint8_t channel = FspTimer::get_available_timer(timerType); // returns -1 if none available
  burstTimer.begin(TIMER_MODE_PERIODIC, timerType, channel, DRIVE_FREQUENCY * 2, 0.0f, burstCallback);
  burstTimer.setup_overflow_irq();
  burstTimer.open();

  // Set up ADC
  MSTPCRD &= ~(1u << 16);// Enable module
  ADANSA0 = (1u << 9); // Select channel AN09 only
  ADCER = 0x0000;// 12-bit, right align (ADCER default is fine; set explicitly = 0)
  ADCSR &= ~(1u << 5); // Software trigger mode (TRGE=0), single scan (ADCS=00)

  // Configure routes
  registerRoutes();

  // Start WiFi + server + websocket via module
  wifiSetup(WIFI_SSID, WIFI_PASS);
}

void sendData() {
  // Header fields
  frame.depth = (uint16_t)depthDetectSample;
  frame.temp_scaled = (int16_t)(temperature * 100.0f);
  frame.vDrv_scaled = (uint16_t)(vDrv * 100);

  // Compute checksum (XOR of depth bytes, temp bytes, vDrv bytes, all samples)
  uint8_t cs = 0;
  // depth
  cs ^= (uint8_t)(frame.depth & 0xFF);
  cs ^= (uint8_t)(frame.depth >> 8);
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
  wsBroadcastBIN(reinterpret_cast<uint8_t*>(&frame), len);
}

void loop()
{
  wifiLoop();

  unsigned long currentTime = millis();
  if ((currentTime - lastRunTime) >= 250) { // Measure roughly 4x per second
    lastRunTime = currentTime;
    Serial.print("Run time: "); Serial.println(lastRunTime);

    // Trigger time-of-flight measurement
    tuss4470Write(0x1B, 0x01);

    burstTimer.start();

    //int startTime = micros();

    // Read analog values from A0
    sampleIndex = 0;
    samplesXor = 0;
    for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
      ADCSR |= (1u << 15);        // Set ADST (start)
      while (ADCSR & (1u << 15));  // Wait while ADST remains 1
      uint8_t v = ADDR09 >> 4; // Read ADC value, 12 bit >> 8 bit
      frame.samples[sampleIndex] = v; 
      samplesXor ^= v; // Accumulate XOR for checksum

      if (sampleIndex == BLINDZONE_SAMPLE_END) {
        detectedDepth = false;
      }

      delayMicroseconds(11.5);
    }
    //int runTime = micros() - startTime;

    // Stop time-of-flight measurement
    tuss4470Write(0x1B, 0x00);
    
    // Software gradient-based override
    if (USE_GRADIENT_OVERRIDE) {
      int overrideSample = -1;
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
      if (overrideSample >= 0) {
        depthDetectSample = overrideSample;
      }
    }
    
    sendData();
  }
}
