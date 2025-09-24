#pragma once
#include <Arduino.h>

// Number of ADC samples to take per measurement cycle
// Each sample takes approximately 13.2 microseconds
// This value must match the number of samples expected by the Python visualization tool
// Max ~12000
#define NUM_SAMPLES 8000

// Number of initial samples to ignore after sending the transducer pulse
// These ignored samples represent the "blind zone" where the transducer is still ringing
#define BLINDZONE_SAMPLE_END 45

// Threshold level for detecting the bottom echo
// The first echo stronger than this value (after the blind zone) is considered the bottom
#define THRESHOLD_VALUE 0x19

// ---------------------- DRIVE FREQUENCY SETTINGS ----------------------
// Sets the output frequency of the ultrasonic transducer by configuring FspTimer
#define DRIVE_FREQUENCY 150000

// ---------------------- BANDPASS FILTER SETTINGS ----------------------
// Sets the digital band-pass filter frequency on the TUSS4470 driver chip
// This should roughly match the transducer drive frequency
// For additional register values, see TUSS4470 datasheet, Table 7.1 (pages 17–18)
// #define FILTER_FREQUENCY_REGISTER 0x00 // 40 kHz
// #define FILTER_FREQUENCY_REGISTER 0x09 // 68 kHz
// #define FILTER_FREQUENCY_REGISTER 0x10 // 100 kHz
#define FILTER_FREQUENCY_REGISTER 0x18 // 151 kHz
// #define FILTER_FREQUENCY_REGISTER 0x1E // 200 kHz

// ---------------------- GRADIENT DEPTH OVERRIDE ----------------------
// If enabled, software will scan the captured analogValues[] after each
// acquisition and choose the first sample index after the blind zone
// whose positive gradient (value[i] - value[i-1]) exceeds GRADIENT_THRESHOLD.
// If no such gradient is found, the hardware threshold detection result is kept.
#define USE_GRADIENT_OVERRIDE true
#define GRADIENT_THRESHOLD 15 // Difference on 0-255 scaled samples

// WiFi credentials (Station mode)
// If not found, will fall back to Access Point mode with SSID "OpenEcho" and password "openecho"
static const char WIFI_SSID[] = "Your SSID";
static const char WIFI_PASS[] = "Your Password";