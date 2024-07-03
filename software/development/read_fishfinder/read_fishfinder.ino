// Define the interrupt pin (2 for INT0)
const int interruptPin = 2; // Using pin 2 (INT0)

// Define the analog input pin
const int analogPin = A2;

// Number of samples to take (adjust based on your requirements)
const int numSamples = 300;

volatile bool interruptFlag = false;
volatile bool measureFlag = false;
int analogValues[numSamples];

void setup() {
  // Initialize Serial communication at 115200 baud
  Serial.begin(115200);

  // Configure the interrupt pin as input
  pinMode(interruptPin, INPUT);

  // Attach the interrupt to the pin, and specify the ISR function to call on interrupt
  attachInterrupt(digitalPinToInterrupt(interruptPin), interruptServiceRoutine, FALLING);
}

void loop() {
  // Check if the interrupt flag is set
  if (interruptFlag) {
    // Clear the flag
    interruptFlag = false;

    // Set the measure flag
    measureFlag = true;

    // Perform the measurement sequence
    //int startMicros = micros();

    for (int i = 0; i < numSamples; i++) {
      analogValues[i] = analogRead(analogPin);
    }
    //int elapsedTime = micros() - startMicros;
    //float sampleTime = elapsedTime / numSamples;
    /*
    Serial.print("Sample time: ");
    Serial.println(sampleTime);
    Serial.print("Sample resolution: ");
    Serial.println(sampleTime);
    */
    


    Serial.print("sp");
    for (int i = 0; i < numSamples; i++) {
      Serial.print(analogValues[i]);
      if (i < numSamples - 1) {
        Serial.print(", ");
      }
    }
    Serial.println();

    // Clear the measure flag
    measureFlag = false;
  }
}

// Interrupt Service Routine (ISR)
void interruptServiceRoutine() {
  // Set the interrupt flag
  interruptFlag = true;
}
