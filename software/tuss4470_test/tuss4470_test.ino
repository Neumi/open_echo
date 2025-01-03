#include <SPI.h>

const int SPI_CS = 10;
const int IO1 = 8;
const int IO2 = 9;
const int O3 = 6;
const int O4 = 5;
const int analogIn = A0;

// SPI Buffers
byte misoBuf[2];  // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer

const int numSamples = 100;
int analogValues[numSamples];

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

  // Initialize TUSS4470 with specific configurations
  tuss4470Write(0x10, 0x00);  // Set BPF center frequency to 40kHz
  tuss4470Write(0x16, 0x01);  // Enable VDRV (not Hi-Z)
  tuss4470Write(0x1A, 0x08);  // Set burst pulses to 8
}

void loop() {
  // Trigger time-of-flight measurement
  tuss4470Write(0x1B, 0x01);

  generatePulses(8);

  // Read analog values
  for (int i = 0; i < numSamples; i++) {
    analogValues[i] = analogRead(analogIn);
  }

  // Stop time-of-flight measurement
  tuss4470Write(0x1B, 0x00);

  // Print sampled values
  Serial.print("sp");
  for (int i = 0; i < numSamples; i++) {
    Serial.print(analogValues[i]);
    if (i < numSamples - 1) {
      Serial.print(", ");
    }
  }
  Serial.println();

  delay(100);
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

void generatePulses(int numPulses) {
  for (int i = 0; i < numPulses; i++) {
    PORTB |= (1 << PB1);  // Set PB1 (pin 9) high
    delayMicroseconds(13);
    PORTB &= ~(1 << PB1);  // Set PB1 low
    delayMicroseconds(13);
  }
  digitalWrite(IO2, HIGH);
}
