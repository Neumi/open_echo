#include "settings.h"
#include <SPI.h>

// Pin configuration
const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 3;
const int O4 = 2;
const int analogIn = A0;

struct __attribute__((packed)) Frame {
  uint8_t start = 0xAA;
  uint16_t depth_index;
  int16_t temp_scaled;
  uint16_t vDrv_scaled;
  uint8_t samples[NUM_SAMPLES];
  uint8_t checksum;
};

static Frame frame;             // Data frame to send over WebSocket
static uint8_t samplesXor = 0;  // Accumulate XOR while sampling

byte misoBuf[2];    // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer
float temperature = 0.0f;
int vDrv = 0;

volatile int pulseCount = 0;
volatile int sampleIndex = 0;

volatile bool detectedDepth = false;  // Condition flag
volatile uint16_t depthDetectSample = 0;

ISR(TIMER1_COMPA_vect) {
  pulseCount++;
  if (pulseCount >= 32) {
    stopTransducer();
    pulseCount = 0;  // Reset counter for next cycle
  }
}

void startTransducerBurst() {
  TCCR1A = _BV(COM1A0);             // Toggle OC1A (pin 9) on Compare Match
  TCCR1B = _BV(WGM12) | _BV(CS10);  // CTC mode, no prescaler

  OCR1A = DRIVE_FREQUENCY_TIMER_DIVIDER;

  TIMSK1 = _BV(OCIE1A);  // Enable Timer1 Compare Match A interrupt
}

void stopTransducer() {
  TCCR1A = 0;
  TCCR1B = 0;  // Stop Timer1 by clearing clock select bits
  TIMSK1 = 0;  // Disable Timer1 interrupt
}

byte tuss4470Read(byte addr) {
  inByteArr[0] = 0x80 + ((addr & 0x3F) << 1);  // Set read bit and address
  inByteArr[1] = 0x00;                         // Empty data byte
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

void setup() {
  Serial.begin(250000);

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
  pinMode(O4, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(O4), handleInterrupt, RISING);

  // Initialize TUSS4470 with specific configurations
  // check TUSS4470 datasheet for more settings!
  tuss4470Write(0x10, FILTER_FREQUENCY_REGISTER);  // Set BPF center frequency
  tuss4470Write(0x16, 0xF);                        // Enable VDRV (not Hi-Z)
  tuss4470Write(0x1A, 0x0F);                       // Set burst pulses to 16
  tuss4470Write(0x17, THRESHOLD_VALUE);            // enable threshold detection on OUT_4
  tuss4470Write(0x13, 0x01);                       // Set LNA gain (0x00 = 15V/V, 0x01 = 10V/V, 0x02 = 20V/V, 0x03 = 12.5V/V)

  // Set up ADC
  ADCSRA = (1 << ADEN) |  // Enable ADC
           (1 << ADPS2);  // Set prescaler to 16 (16 MHz / 16 = 1 MHz ADC clock)
  ADMUX = (1 << REFS0);   // Reference voltage: AVcc
  // Input channel: ADC0 (default)
  ADCSRB = 0;              // Free-running mode
  ADCSRA |= (1 << ADATE);  // Enable auto-trigger (free-running)
  ADCSRA |= (1 << ADSC);   // Start conversion
}

void loop() {
  // Trigger time-of-flight measurement
  tuss4470Write(0x1B, 0x01);

  startTransducerBurst();

  //int startTime = micros();

  // Read analog values from A0
  samplesXor = 0;
  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    while (!(ADCSRA & (1 << ADIF)))
      ;                     // Wait for conversion to complete
    ADCSRA |= (1 << ADIF);  // Clear the interrupt flag
    uint8_t v = ADC >> 2;   // Read ADC value, 10 bit >> 8 bit
    frame.samples[sampleIndex] = v;
    samplesXor ^= v;  // Accumulate XOR for checksum

    if (sampleIndex == BLINDZONE_SAMPLE_END) {
      detectedDepth = false;
    }
  }
  //int runTime = micros() - startTime;

  // Stop time-of-flight measurement
  tuss4470Write(0x1B, 0x00);

// Software depth override
#if USE_DEPTH_OVERRIDE
  int overrideSample = 0;
  uint8_t max = 0;
  for (int i = BLINDZONE_SAMPLE_END; i < NUM_SAMPLES; i++) {
    if (frame.samples[i] > max) {
      max = frame.samples[i];
      overrideSample = i;
    }
  }
  if (overrideSample > 0) {
    depthDetectSample = overrideSample;
  }
#endif

  sendData();

  delay(10);
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
}