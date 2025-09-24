#pragma once
#include <Arduino.h>
#include <WiFiS3.h>

// Route handler signature:
// - client: the connected client
// - method: e.g., "GET", "POST"
// - url: full URL path (e.g., "/config?x=1")
// - query: the query string without '?', may be empty
// - body: request body for POST/PUT (may be empty)
typedef void (*RouteHandler)(WiFiClient& client,
							 const String& method,
							 const String& url,
							 const String& query,
							 const String& body);

// Initialize WiFi (STA with AP fallback) and start HTTP + WebSocket servers
void wifiSetup(const char* ssid, const char* pass);

// Process HTTP and WebSocket events; call from loop()
void wifiLoop();

// Register a simple path-based route (exact match)
bool addRoute(const char* path, RouteHandler handler);

// Send a basic HTTP response (status, content-type, body)
void sendResponse(WiFiClient& client, const char* body, const char* contentType = "text/html", int status = 200);

// Broadcast binary data to all WebSocket clients
bool wsBroadcastBIN(const uint8_t* data, size_t len);
