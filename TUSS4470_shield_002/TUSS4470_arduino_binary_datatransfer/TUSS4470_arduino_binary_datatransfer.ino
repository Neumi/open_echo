#include <SPI.h>

const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 3;
const int O4 = 2;
const int analogIn = A0;

byte misoBuf[2];  // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer

#define NUM_SAMPLES 300 // sample size (one sample is about 13 microseconds long) (has to be equal to python visualization sample size)
int analogValues[NUM_SAMPLES];

volatile int pulseCount = 0;

volatile int sampleIndex = 0;


float temperature = 0.0f;
int vDrv = 0;


const int interruptPin = 3;  // Pin for external interrupt
volatile bool detectedDepth = false;  // Condition flag
volatile int depthDetectSample = 0;

#define BLINDZONE_SAMPLE_END 25

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
  
  //OCR1A = 199; // 40kHz (car parking sensor)
  //OCR1A = 160; // 50kHz
  //OCR1A = 120; // 66kHz
  //OCR1A = 80; // 100kHz (chrhartz DIY transducer)
  //OCR1A = 52; // 151kHz (muebau transducer)
  OCR1A = 39; // 200kHz (Raymarine CPT-S 200kHz)
  //OCR1A = 36; // 216kHz (mini transducer)
  //OCR1A = 34; // 230kHz (18mm 200kHz Aliexpress transducer)
  //OCR1A = 22; // 19 cycles at 16 MHz = 350kHz
  //OCR1A = 19; // 400kHz
  //OCR1A = 17; // 455kHz (Lowrance Hook 3TS sidescan)
  //OCR1A = 11; // 658kHz


  
  
  
  TIMSK1 = _BV(OCIE1A);  // Enable Timer1 Compare Match A interrupt
}

void stopTransducer()
{
  TCCR1A = 0;
  TCCR1B = 0;  // Stop Timer1 by clearing clock select bits
  TIMSK1 = 0;  // Disable Timer1 interrupt
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
  pinMode(interruptPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(interruptPin), handleInterrupt, RISING);

  // Initialize TUSS4470 with specific configurations
  // check TUSS4470 datasheet for more settings!
  //tuss4470Write(0x10, 0x09);  // Set BPF center frequency to 68kHz
  //tuss4470Write(0x10, 0x10);  // Set BPF center frequency to 100kHz
  //tuss4470Write(0x10, 0x18); // Set BPF center frequency to 151kHz
  tuss4470Write(0x10, 0x1E);  // Set BPF center frequency to 200kHz TODO: check why 0x1E and not 0x0F!
  
  
  tuss4470Write(0x16, 0xF);  // Enable VDRV (not Hi-Z)
  tuss4470Write(0x1A, 0x0F);  // Set burst pulses to 16

  tuss4470Write(0x17, 0x19); // enable threshold detection (Pin 5 and 3 need to be connected to work!)

  // Set up ADC
  ADCSRA = (1 << ADEN)  |  // Enable ADC
           (1 << ADPS2);   // Set prescaler to 16 (16 MHz / 16 = 1 MHz ADC clock)
  ADMUX = (1 << REFS0);    // Reference voltage: AVcc
                           // Input channel: ADC0 (default)
  ADCSRB = 0;              // Free-running mode
  ADCSRA |= (1 << ADATE);  // Enable auto-trigger (free-running)
  ADCSRA |= (1 << ADSC);   // Start conversion
}

void loop()
{
  // Trigger time-of-flight measurement
  tuss4470Write(0x1B, 0x01);

  startTransducerBurst();
  
  //int startTime = micros();
  
  // Read analog values from A0
  sampleIndex = 0;
  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    while (!(ADCSRA & (1 << ADIF))); // Wait for conversion to complete
    ADCSRA |= (1 << ADIF);           // Clear the interrupt flag
    analogValues[sampleIndex] = ADC;           // Read ADC value
    if(sampleIndex == BLINDZONE_SAMPLE_END) detectedDepth = false;
  }
  //int runTime = micros() - startTime;
  
  // Stop time-of-flight measurement
  tuss4470Write(0x1B, 0x00);
  
  sendData();
  
  delay(50);
}


void sendData() {
  Serial.write(0xAA);  // Start byte

  uint8_t payload[2 + 2 + 2 + 2 * NUM_SAMPLES];
  int idx = 0;

  // Depth
  payload[idx++] = depthDetectSample >> 8;
  payload[idx++] = depthDetectSample & 0xFF;

  // Temperature × 100
  int16_t temp_scaled = temperature * 100;
  payload[idx++] = temp_scaled >> 8;
  payload[idx++] = temp_scaled & 0xFF;

  // Drive Voltage × 100
  uint16_t vDrv_scaled = vDrv * 100;
  payload[idx++] = vDrv_scaled >> 8;
  payload[idx++] = vDrv_scaled & 0xFF;

  // Analog samples
  for (int i = 0; i < NUM_SAMPLES; i++) {
    payload[idx++] = analogValues[i] >> 8;
    payload[idx++] = analogValues[i] & 0xFF;
  }

  // Compute checksum (XOR of payload)
  uint8_t checksum = 0;
  for (int i = 0; i < idx; i++) {
    checksum ^= payload[i];
  }

  // Send payload and checksum
  Serial.write(payload, idx);
  Serial.write(checksum);
}
