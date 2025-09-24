#include "wifi_server.h"
#include <WiFiS3.h>
#define WEBSOCKETS_SERVER_CLIENT_MAX 2
#include <WebSocketsServer.h>

struct RouteEntry { const char* path; RouteHandler handler; };
static RouteEntry routes[8];
static size_t routeCount = 0;

static WiFiServer httpServer(80);
static WebSocketsServer wsServer(81);

static IPAddress waitForIP(uint32_t timeoutMs = 10000) {
  unsigned long t0 = millis();
  IPAddress ip = WiFi.localIP();
  while ((ip[0] == 0 && ip[1] == 0 && ip[2] == 0 && ip[3] == 0) && (millis() - t0 < timeoutMs)) {
    delay(100);
    ip = WiFi.localIP();
  }
  return ip;
}

static void handleHttpClient(WiFiClient& client) {
  char line[160];
  size_t n = client.readBytesUntil('\n', line, sizeof(line) - 1);
  if (n == 0) return;
  line[n] = 0;
  // Parse method and path (manual to avoid sscanf)
  char method[8] = {0};
  char url[120] = {0};
  size_t i = 0, j = 0;
  while (i < sizeof(method) - 1 && line[i] != ' ' && line[i] != '\0' && line[i] != '\r' && line[i] != '\n') { method[i] = line[i]; i++; }
  method[i] = 0;
  // skip spaces
  while (line[i] == ' ') i++;
  while (j < sizeof(url) - 1 && line[i] != ' ' && line[i] != '\0' && line[i] != '\r' && line[i] != '\n') { url[j++] = line[i++]; }
  url[j] = 0;
  // Separate query
  char* qmark = strchr(url, '?');
  String path;
  String query;
  if (qmark) {
    *qmark = '\0';
    path = url;
    query = qmark + 1;
  } else {
    path = url;
  }
  // Consume headers
  int headerLines = 0;
  while (client.connected() && headerLines < 20) {
    n = client.readBytesUntil('\n', line, sizeof(line) - 1);
    if (n == 0) break;
    line[n] = 0;
    if (strcmp(line, "\r") == 0 || line[0] == '\r' || line[0] == '\n') break;
    headerLines++;
  }
  for (size_t i = 0; i < routeCount; ++i) {
    if (routes[i].path && path == routes[i].path && routes[i].handler) {
      routes[i].handler(client, String(method), path, query, String());
      return;
    }
  }
  sendResponse(client, "Not Found", "text/plain", 404);
}

void sendResponse(WiFiClient& client, const char* body, const char* contentType, int status) {
  client.print("HTTP/1.1 "); client.print(status); client.print(" "); client.println(status == 200 ? "OK" : "ERROR");
  client.print("Content-Type: "); client.println(contentType);
  size_t len = strlen(body);
  client.print("Content-Length: "); client.println(len);
  client.println("Connection: close");
  client.println();
  client.print(body);
  client.println();
  client.flush();
  delay(2);
  client.stop();
}

bool addRoute(const char* path, RouteHandler handler) {
  if (routeCount >= (sizeof(routes)/sizeof(routes[0]))) return false;
  routes[routeCount++] = { path, handler };
  return true;
}

static void onWsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  if (type == WStype_TEXT) {
    wsServer.sendTXT(num, payload, length);
  }
}

void wifiSetup(const char* ssid, const char* pass) {
  Serial.println("Adding health route");
  // Built-in health route
  addRoute("/health", [](WiFiClient& c, const String&, const String&, const String&, const String&){
    sendResponse(c, "OK", "text/plain", 200);
  });

  Serial.println("[WiFi] Connecting...");
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
  } else {
    Serial.println("[WiFi] STA failed. Starting AP fallback...");
    const char* apSsid = "OpenEcho";
    const char* apPass = "openecho";
    if (WiFi.beginAP(apSsid, apPass)) {
      IPAddress ip = waitForIP(10000);
      Serial.print("[WiFi] AP "); Serial.print(apSsid); Serial.print(" IP: "); Serial.println(ip);
    } else {
      Serial.println("[WiFi] AP start failed");
    }
  }

  httpServer.begin();
  wsServer.begin();
  wsServer.onEvent(onWsEvent);

  IPAddress ip = WiFi.localIP();
  Serial.print("[HTTP] http://"); Serial.println(ip);
  Serial.print("[WS]   ws://"); Serial.print(ip); Serial.print(":81");
}

void wifiLoop() {
  WiFiClient client = httpServer.available();
  if (client) {
    client.setTimeout(1000);
    handleHttpClient(client);
  }
  wsServer.loop();
}

bool wsBroadcastBIN(const uint8_t* data, size_t len) {
  // Print number of connected clients
  wsServer.broadcastBIN(data, len);
  return true;
}
