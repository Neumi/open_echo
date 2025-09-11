#include <SPI.h>

#define ARDUINO_R4 false

#if ARDUINO_R4
  #include <Arduino.h>
  #include <FspTimer.h>
#endif

// Pin configuration
const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 3;
const int O4 = 2;
const int analogIn = A0;


// Number of ADC samples to take per measurement cycle
// Each sample takes approximately 13.2 microseconds
// This value must match the number of samples expected by the Python visualization tool
// Max 1800 on R3, ~10000 on R4
#define NUM_SAMPLES 1800

// Number of initial samples to ignore after sending the transducer pulse
// These ignored samples represent the "blind zone" where the transducer is still ringing
#define BLINDZONE_SAMPLE_END 450

// Threshold level for detecting the bottom echo
// The first echo stronger than this value (after the blind zone) is considered the bottom
#define THRESHOLD_VALUE 0x19


// ---------------------- DRIVE FREQUENCY SETTINGS ----------------------
// Sets the output frequency of the ultrasonic transducer
// Uses DRIVE_FREQUENCY directly for R4, uses divider for R3
#define DRIVE_FREQUENCY 40000
const int DRIVE_FREQUENCY_TIMER_DIVIDER = (16000000 / (2 * DRIVE_FREQUENCY)) - 1;

// ---------------------- BANDPASS FILTER SETTINGS ----------------------
// Sets the digital band-pass filter frequency on the TUSS4470 driver chip
// This should roughly match the transducer drive frequency
// For additional register values, see TUSS4470 datasheet, Table 7.1 (pages 17–18)
#define FILTER_FREQUENCY_REGISTER 0x00 // 40 kHz
// #define FILTER_FREQUENCY_REGISTER 0x09 // 68 kHz
// #define FILTER_FREQUENCY_REGISTER 0x10 // 100 kHz
// #define FILTER_FREQUENCY_REGISTER 0x18 // 151 kHz
// #define FILTER_FREQUENCY_REGISTER 0x1E // 200 kHz

#if ARDUINO_R4
  // ---------------------- ADC SETUP FOR ARDUINO R4 ----------------------
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
#endif


byte misoBuf[2];  // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer

byte analogValues[NUM_SAMPLES];
volatile int pulseCount = 0;
volatile int sampleIndex = 0;

float temperature = 0.0f;
int vDrv = 0;

volatile bool detectedDepth = false;  // Condition flag
volatile int depthDetectSample = 0;

#if ARDUINO_R4
  // --- Burst Control Timer ---
  FspTimer burstTimer;

  void burstCallback(timer_callback_args_t *) {
    digitalWrite(IO2, !digitalRead(IO2));
    pulseCount++;
    if (pulseCount >= 32) {
      burstTimer.stop();
    }
  }
#else

  ISR(TIMER1_COMPA_vect)
  {
    pulseCount++;
    if (pulseCount >= 32)
    {
      stopTransducer();
      pulseCount = 0;  // Reset counter for next cycle
    }
  }

  void startTransducerBurst()
  {
    TCCR1A = _BV(COM1A0);  // Toggle OC1A (pin 9) on Compare Match
    TCCR1B = _BV(WGM12) | _BV(CS10);  // CTC mode, no prescaler

    OCR1A = DRIVE_FREQUENCY_TIMER_DIVIDER;

    TIMSK1 = _BV(OCIE1A);  // Enable Timer1 Compare Match A interrupt
  }

  void stopTransducer()
  {
    TCCR1A = 0;
    TCCR1B = 0;  // Stop Timer1 by clearing clock select bits
    TIMSK1 = 0;  // Disable Timer1 interrupt
  }

#endif

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
  #if ARDUINO_R4
    SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1)); 
  #else
    SPI.setBitOrder(MSBFIRST);
    SPI.setClockDivider(SPI_CLOCK_DIV16);
    SPI.setDataMode(SPI_MODE1);  // CPOL=0, CPHA=1
  #endif

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

  #if ARDUINO_R4
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
  #else
    // Set up ADC
    ADCSRA = (1 << ADEN)  |  // Enable ADC
            (1 << ADPS2);   // Set prescaler to 16 (16 MHz / 16 = 1 MHz ADC clock)
    ADMUX = (1 << REFS0);    // Reference voltage: AVcc
    // Input channel: ADC0 (default)
    ADCSRB = 0;              // Free-running mode
    ADCSRA |= (1 << ADATE);  // Enable auto-trigger (free-running)
    ADCSRA |= (1 << ADSC);   // Start conversion
  #endif
}

void loop()
{
  // Trigger time-of-flight measurement
  tuss4470Write(0x1B, 0x01);

  #if ARDUINO_R4
    burstTimer.start();
  #else
    startTransducerBurst();
  #endif

  //int startTime = micros();

  // Read analog values from A0
  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    #if ARDUINO_R4
      ADCSR |= (1u << 15);        // Set ADST (start)
      while (ADCSR & (1u << 15));  // Wait while ADST remains 1
      analogValues[sampleIndex] = ADDR09 >> 4; // Read ADC value, 12 bit >> 8 bit

      delayMicroseconds(11.5);
    #else
      while (!(ADCSRA & (1 << ADIF))); // Wait for conversion to complete
      ADCSRA |= (1 << ADIF);           // Clear the interrupt flag
      analogValues[sampleIndex] = ADC >> 2;           // Read ADC value
    #endif

    if (sampleIndex == BLINDZONE_SAMPLE_END) {
      detectedDepth = false;
    }
  }
  //int runTime = micros() - startTime;

  // Stop time-of-flight measurement
  tuss4470Write(0x1B, 0x00);
  
  sendData();

  delay(10);
}


void sendData() {
  Serial.write(0xAA);  // Start byte

  uint8_t checksum = 0;

  // Depth
  uint8_t depthHigh = depthDetectSample >> 8;
  uint8_t depthLow  = depthDetectSample & 0xFF;
  Serial.write(depthHigh);
  Serial.write(depthLow);
  checksum ^= depthHigh ^ depthLow;

  // Temperature × 100
  int16_t temp_scaled = temperature * 100;
  uint8_t tempHigh = temp_scaled >> 8;
  uint8_t tempLow  = temp_scaled & 0xFF;
  Serial.write(tempHigh);
  Serial.write(tempLow);
  checksum ^= tempHigh ^ tempLow;

  // Drive Voltage × 100
  uint16_t vDrv_scaled = vDrv * 100;
  uint8_t vDrvHigh = vDrv_scaled >> 8;
  uint8_t vDrvLow  = vDrv_scaled & 0xFF;
  Serial.write(vDrvHigh);
  Serial.write(vDrvLow);
  checksum ^= vDrvHigh ^ vDrvLow;

  // Analog samples directly from analogValues[]
  // TODO: Optimize by sending raw bytes instead of splitting into high/low bytes
  for (int i = 0; i < NUM_SAMPLES; i++) {
    uint8_t highByte = analogValues[i] >> 8;
    uint8_t lowByte  = analogValues[i] & 0xFF;
    Serial.write(highByte);
    Serial.write(lowByte);
    checksum ^= highByte ^ lowByte;
  }

  // Send checksum
  Serial.write(checksum);
}
