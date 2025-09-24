#pragma once
#include <Arduino.h>
#include <WiFi.h>

// Initialize WiFi (STA with AP fallback to simple AP) and prepare UDP broadcast.
void wifiSetup(const char* ssid, const char* pass);

// Optional periodic housekeeping (currently no-op, keep for future reconnect logic)
void wifiLoop();

// Broadcast raw binary frame via UDP broadcast address. Returns true on (attempted) send.
bool udpBroadcastBIN(const uint8_t* data, size_t len, uint16_t port);
bool udpBroadcastNMEA(const char* data, size_t len, uint16_t port);
