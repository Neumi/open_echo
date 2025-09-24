// Simplified networking: WiFi connection + UDP broadcast only
#include "settings.h"
#include "wifi_server.h"
#include <WiFi.h>
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
  while (WiFi.status() != WL_CONNECTED && (millis() - t0 < 60000)) { delay(250); Serial.print('.'); }
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
  } else {
    Serial.println("[WiFi] Connection failed!");
  }

  // UDP setup (sender-only): bind a local port to satisfy stacks that require binding
  // and to keep a predictable source port.
  if (udp.begin(0)) {
    udpReady = true;
    Serial.println("[UDP] Sender ready");
  } else {
    Serial.println("[UDP] Failed to init UDP; UDP send disabled");
  }

  IPAddress ip = WiFi.localIP();
  Serial.print("[NET] Ready. IP: "); Serial.println(ip);
}

bool udpBroadcastBIN(const uint8_t* data, size_t len, uint16_t port) {
  if (!udpReady) {
    Serial.println("[UDP BIN] udp not ready");
    return false;
  }

  // Validate destination IP (non-zero)
  IPAddress dst = UDP_ECHO_IP;
  if (dst[0] == 0 && dst[1] == 0 && dst[2] == 0 && dst[3] == 0) {
    Serial.println("[UDP BIN] Invalid destination IP (0.0.0.0)");
    return false;
  }

  // Many stacks limit UDP payload size (~1200-1472 bytes). Send in chunks.
  // Conservative chunk size; some stacks fail above ~1024 bytes.
  const size_t MAX_CHUNK = 1024;
  size_t totalSent = 0;
  size_t offset = 0;

  while (offset < len) {
    size_t chunk = (len - offset) < MAX_CHUNK ? (len - offset) : MAX_CHUNK;

    int ok = udp.beginPacket(dst, port);
    if (ok != 1) {
      Serial.print("[UDP BIN] beginPacket failed to ");
      Serial.print(dst);
      Serial.print(":");
      Serial.println(port);
      return false;
    }

    size_t wrote = udp.write(data + offset, chunk);
    if (wrote != chunk) {
      Serial.print("[UDP BIN] write short chunk: ");
      Serial.print(wrote);
      Serial.print(" / ");
      Serial.println(chunk);
    }

    // Guard: if WiFi dropped, endPacket will fail; check and report
    // Automatically attempts reconnect, as if you are using UDP echoes
    // we assume you are NOT using a Serial connection, so this is critical.
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[UDP BIN] WiFi not connected; aborting send");
      wifiSetup(WIFI_SSID, WIFI_PASS);
      return false;
    }

    ok = udp.endPacket();
    if (ok != 1) {
      Serial.println("[UDP BIN] endPacket failed");
      return false;
    }

    offset += chunk;
    totalSent += wrote;
    // Small pacing to avoid overwhelming buffers
    delay(1);
  }

  if (totalSent != len) {
    Serial.print("[UDP BIN] total short: ");
    Serial.print(totalSent);
    Serial.print(" / ");
    Serial.println(len);
    return false;
  }
  return true;
}


bool udpBroadcastNMEA(const char* data, size_t len, uint16_t port) {
  if (!udpReady) return false;
  udp.beginPacket(broadcastIp, port);
  udp.write(data, len);
  udp.endPacket();
  return true;
}