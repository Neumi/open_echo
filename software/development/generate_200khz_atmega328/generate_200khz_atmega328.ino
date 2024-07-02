void setup() {
  // Set pin 10 as an output
  pinMode(10, OUTPUT);

  // Stop the timer
  TCCR1A = 0;
  TCCR1B = 0;

  // Set to Fast PWM mode with TOP set by ICR1
  TCCR1A |= (1 << WGM11);
  TCCR1B |= (1 << WGM12) | (1 << WGM13);

  // Set the compare match value for 50% duty cycle
  OCR1B = 39;

  // Set the TOP value for 200 kHz frequency
  ICR1 = 79;

  // Set non-inverting mode on OC1B (pin 10)
  TCCR1A |= (1 << COM1B1);

  // Start the timer with no prescaler
  TCCR1B |= (1 << CS10);
}

void loop() {

}
