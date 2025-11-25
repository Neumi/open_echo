#pragma once

#include <Arduino.h>

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

  
// ---------------------- DEPTH OVERRIDE ----------------------
// If enabled, software will scan the captured analogValues[] after each
// acquisition and choose the max sample after the blind zone to be 
// the bottom echo, instead of the first sample above the threshold.
#define USE_DEPTH_OVERRIDE 1


// ---------------------- NMEA SETTINGS ----------------------
// Fast or slow baud rate for NMEA output on SoftwareSerial (pin 4)
#define NMEA_BAUD_RATE 4800
// #define NMEA_BAUD_RATE 38400

// Depth offset in meters to add to all reported depths (can be negative)
#define DEPTH_OFFSET 0.0f

// ---------------------- WIFI SETTINGS ----------------------
// Only required for Arduino R4 WiFi
#define WIFI_ENABLED 1

// If not found, will fall back to Access Point mode with SSID "OpenEcho" and password "openecho"
static const char WIFI_SSID[] = "Your SSID";
static const char WIFI_PASS[] = "Your Password";

// ---------------------- UDP BROADCAST SETTINGS ----------------------
// Enable/disable UDP broadcast of the binary frame (same payload as Serial / WebSocket)
// This cannot be sent to all, so a specific broadcast IP must be set
#define ENABLE_UDP_ECHO 1
#define UDP_ECHO_PORT 31338
static const IPAddress UDP_ECHO_IP(10, 17, 20, 117);

#define ENABLE_UDP_NMEA 0
#define UDP_NMEA_PORT 31337