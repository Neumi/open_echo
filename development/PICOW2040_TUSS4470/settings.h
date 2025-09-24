// ---------------------- DRIVE FREQUENCY SETTINGS ----------------------
// Sets the output frequency of the ultrasonic transducer
#define DRIVE_FREQUENCY 40000

// ---------------------- BANDPASS FILTER SETTINGS ----------------------
// Sets the digital band-pass filter frequency on the TUSS4470 driver chip
// This should roughly match the transducer drive frequency
// For additional register values, see TUSS4470 datasheet, Table 7.1 (pages 17–18)
#define FILTER_FREQUENCY_REGISTER 0x00 // 40 kHz
// #define FILTER_FREQUENCY_REGISTER 0x09 // 68 kHz
// #define FILTER_FREQUENCY_REGISTER 0x10 // 100 kHz
// #define FILTER_FREQUENCY_REGISTER 0x18 // 151 kHz
// #define FILTER_FREQUENCY_REGISTER 0x1E // 200 kHz

// Number of ADC samples to take per measurement cycle
// This value must match the number of samples expected by the Python visualization tool
#define NUM_SAMPLES 12000

// Number of initial samples to ignore after sending the transducer pulse
// These ignored samples represent the "blind zone" where the transducer is still ringing
#define BLINDZONE_SAMPLE_END 450

// Threshold level for detecting the bottom echo
// The first echo stronger than this value (after the blind zone) is considered the bottom
#define THRESHOLD_VALUE 0x19

  
// ---------------------- GRADIENT DEPTH OVERRIDE ----------------------
// If enabled, software will scan the captured analogValues[] after each
// acquisition and choose the first sample index after the blind zone
// whose positive gradient (value[i] - value[i-1]) exceeds GRADIENT_THRESHOLD.
// If no such gradient is found, the hardware threshold detection result is kept.
#define USE_GRADIENT_OVERRIDE 0
#define GRADIENT_THRESHOLD 150 // Difference on 0-255 scaled samples


// ---------------------- NMEA SETTINGS ----------------------
// Fast or slow baud rate for NMEA output on SoftwareSerial (pin 4)
#define NMEA_BAUD_RATE 4800
// #define NMEA_BAUD_RATE 38400

// Depth offset in meters to add to NMEA reported depths (can be negative)
#define DEPTH_OFFSET 0.0f

// ---------------------- WIFI SETTINGS ----------------------
#define WIFI_ENABLED 1

#if WIFI_ENABLED
  // If not found, will fall back to Access Point mode with SSID "OpenEcho" and password "openecho"
  static const char WIFI_SSID[] = "Your SSID";
  static const char WIFI_PASS[] = "Your Password";

  // ---------------------- UDP BROADCAST SETTINGS ----------------------
  // Enable/disable UDP broadcast of the binary frame (same payload as Serial / WebSocket)
  #define ENABLE_UDP_ECHO 1
  #define UDP_ECHO_PORT 31338

  #define ENABLE_UDP_NMEA 1
  #define UDP_NMEA_PORT 31337
#endif