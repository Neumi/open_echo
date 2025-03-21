#include "Arduino.h"
#include <SPI.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "stm32f1xx.h"


#define ANALOG_IN_PIN PB0  // ADC Channel 0
#define NUM_SAMPLES 2500
#define ANALOG_IN_CHANNEL 8  // PB0 -> ADC1_IN8
#define BLINDZONE_SAMPLE_END 25

uint16_t analogValues[NUM_SAMPLES];

const int SPI_CS = PB1;
const int IO1 = PA12;
const int IO2 = PA11;
const int O3 = PB12;
const int O4 = PB13;
const int analogIn = PB0;
#define ONE_WIRE_BUS PB3


byte misoBuf[2];  // SPI receive buffer
byte inByteArr[2];  // SPI transmit buffer

volatile int pulseCount = 0;

volatile int sampleIndex = 0;

const int interruptPin = 3;  // Pin for external interrupt
volatile bool detectedDepth = false;  // Condition flag
volatile int depthDetectSample = 0;

float temperature = 0.0f;

volatile bool interruptTriggered = false;

unsigned long lastReadTime = 0;
const long interval = 3000;  // Read temperature every 3000ms

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
HardwareTimer timer(TIM1);

void generateBurst(int pulses) {
  int frequency = 200000;  // 200 kHz
  int period = 1000000 / frequency;  // 5 µs period

  // Configure the timer for PWM mode on Channel 4 (PA11)
  timer.pause();
  timer.setMode(4, TIMER_OUTPUT_COMPARE_PWM1, IO2); // Channel 4 for PA11
  timer.setPrescaleFactor(72);  // STM32F103 runs at 72 MHz → 72 prescaler = 1 MHz timer clock
  timer.setOverflow(period, MICROSEC_FORMAT);  // Set period to 5 µs
  timer.setCaptureCompare(4, period / 2, MICROSEC_COMPARE_FORMAT);  // 50% duty cycle
  timer.resume();

  // Wait for the required number of pulses (burst)
  delayMicroseconds(pulses * period);

  // Stop PWM after the burst
  timer.pause();
  digitalWrite(IO2, HIGH);  // Ensure the pin goes LOW after burst

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


void setup() {
  Serial1.begin(921600);
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

  pinMode(analogIn, INPUT_ANALOG);  // Set ADC pin (PA0 as an example)


  pinMode(O4, INPUT_PULLDOWN);  // Set PB13 as input with pull-down resistor

  attachInterrupt(digitalPinToInterrupt(O4), handleInterrupt, RISING);



  sensors.begin();

  tuss4470Write(0x10, 0x1E);  // Set BPF center frequency to 200kHz TODO:reg check why 0x1E and not 0x0F!

  tuss4470Write(0x13, 0x00);

  tuss4470Write(0x16, 0x1F);  // Enable VDRV (not Hi-Z)
  tuss4470Write(0x1A, 0x1F);  // Set burst pulses to 16

  tuss4470Write(0x17, 0x19); // enable threshold detection (Pin 5 and 3 need to be connected to work!)


  // Enable Clocks for ADC1 and GPIOB
  RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;  // Enable ADC1 clock
  RCC->APB2ENR |= RCC_APB2ENR_IOPBEN;  // Enable GPIOB clock

  // Configure PB0 as Analog Input
  GPIOB->CRL &= ~(GPIO_CRL_MODE0 | GPIO_CRL_CNF0);

  // Configure ADC1 (Channel 8)
  ADC1->SQR3 = ANALOG_IN_CHANNEL;  // Select ADC1_IN8
  ADC1->SMPR2 |= ADC_SMPR2_SMP8_1 | ADC_SMPR2_SMP8_2;  // Set 55.5 cycles sample time (fast but stable)

  // Enable ADC
  ADC1->CR2 |= ADC_CR2_ADON;
  delay(1);
  ADC1->CR2 |= ADC_CR2_ADON;  // Required second ADON to start ADC

  Serial1.print("setup done!");

}

void loop() {

  // Check if data is available on the serial port
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');  // Read input string until newline

    input.trim();  // Remove leading/trailing whitespaces

    // Check if the input starts with "0x" and is a valid hex string
    if (input.startsWith("0x") && input.length() > 2) {
      // Convert the hex string (without "0x") to an integer
      long hexValue = strtol(input.substring(2).c_str(), NULL, 16);

      // Now, execute the tuss4470Write with the new input as the second parameter
      tuss4470Write(0x13, hexValue);
    }
  }



  //int oldMillis = micros();
  tuss4470Write(0x1B, 0x01);
  generateBurst(18);

  for (sampleIndex = 0; sampleIndex < NUM_SAMPLES; sampleIndex++) {
    ADC1->CR2 |= ADC_CR2_ADON;  // Start Conversion
    while (!(ADC1->SR & ADC_SR_EOC));  // Wait for conversion to complete
    analogValues[sampleIndex] = ADC1->DR;  // Read ADC value
    if (sampleIndex == BLINDZONE_SAMPLE_END) detectedDepth = false;
  }

  tuss4470Write(0x1B, 0x00);
  //Serial1.println(micros() - oldMillis);

  if (millis() - lastReadTime >= interval) {
    lastReadTime = millis();
    sensors.requestTemperatures();  // Request temperature conversion
    temperature = sensors.getTempCByIndex(0);  // Get temperature
  }

  Serial1.print("dds"); // depth detect sample
  Serial1.print(depthDetectSample);
  Serial1.print(";tmp"); // depth detect sample
  Serial1.print(temperature);
  Serial1.print(";sp");

  for (int i = 0; i < NUM_SAMPLES; i++) {
    Serial.print(analogValues[i]);
    if (i < NUM_SAMPLES - 1) {
      Serial1.print(", ");
    }
  }
  Serial1.println();

  delay(50);
}
