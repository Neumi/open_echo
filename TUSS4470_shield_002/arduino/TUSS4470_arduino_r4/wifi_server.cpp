// Simplified networking: WiFi connection + UDP broadcast only
#include "wifi_server.h"
#include <WiFiS3.h>
#include <WiFiUdp.h>

static WiFiUDP udp;
static bool udpReady = false;
static IPAddress broadcastIp(255,255,255,255);

static IPAddress waitForIP(uint32_t timeoutMs = 10000) {
  unsigned long t0 = millis();
  IPAddress ip = WiFi.localIP();
  while ((ip[0] == 0 && ip[1] == 0 && ip[2] == 0 && ip[3] == 0) && (millis() - t0 < timeoutMs)) {
    delay(100);
    ip = WiFi.localIP();
  }
  return ip;
}

void wifiSetup(const char* ssid, const char* pass) {
  Serial.println("[WiFi] Connecting (UDP only)...");
  WiFi.disconnect();
  WiFi.end();
  delay(200);
  WiFi.begin(ssid, pass);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - t0 < 20000)) { delay(250); Serial.print('.'); }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    IPAddress ip = waitForIP(15000);
    Serial.print("[WiFi] STA IP: "); Serial.println(ip);
    IPAddress mask = WiFi.subnetMask();
    if (!(mask[0] == 0 && mask[1] == 0 && mask[2] == 0 && mask[3] == 0)) {
      broadcastIp = IPAddress(
        (ip[0] & mask[0]) | (~mask[0] & 0xFF),
        (ip[1] & mask[1]) | (~mask[1] & 0xFF),
        (ip[2] & mask[2]) | (~mask[2] & 0xFF),
        (ip[3] & mask[3]) | (~mask[3] & 0xFF)
      );
    }
    Serial.print("[WiFi] Broadcast IP: "); Serial.println(broadcastIp);
  }

  // UDP broadcast setup (optional)
  // Begin without binding a specific port for listening (we only send)
  // Some stacks still require begin; choose ephemeral 0 or same port.
  if (udp.begin(0)) {
    udpReady = true;
    Serial.print("[UDP] Broadcast enabled");
  } else {
    Serial.println("[UDP] Failed to init UDP; broadcast disabled");
  }

  IPAddress ip = WiFi.localIP();
  Serial.print("[NET] Ready. IP: "); Serial.println(ip);
}

bool udpBroadcastBIN(const uint8_t* data, size_t len, uint16_t port) {
  if (!udpReady) return false;
  udp.beginPacket(broadcastIp, port);
  udp.write(data, len);
  udp.endPacket();
  return true;
}


bool udpBroadcastNMEA(const char* data, size_t len, uint16_t port) {
  if (!udpReady) return false;
  udp.beginPacket(broadcastIp, port);
  udp.write(data, len);
  udp.endPacket();
  return true;
}