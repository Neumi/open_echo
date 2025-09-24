#include "routes.h"
#include "wifi_server.h"
#include "settings.h"
#include <WiFiS3.h>
#include <ctype.h>
#include <string.h>
#include <stdlib.h>
// Generated from www/* by tools/embed_assets.py
#include "embedded_assets.h"

// Values provided in settings.h

// Basic runtime UI setting

static void handleStaticCss(WiFiClient& client, const String&, const String&, const String&, const String&) { sendResponse(client, STYLE_CSS, "text/css", 200); }
static void handleStaticJsColor(WiFiClient& client, const String&, const String&, const String&, const String&) { sendResponse(client, JSCOLORMAPS_JS, "application/javascript", 200); }
static void handleStaticSpectrogramJs(WiFiClient& client, const String&, const String&, const String&, const String&) {
  sendResponse(client, SPECTROGRAM_JS_TPL, "application/javascript", 200);
}
static void handleHome(WiFiClient& client, const String&, const String&, const String&, const String&) { sendResponse(client, FRONTEND_HTML, "text/html", 200); }

void registerRoutes() {
  addRoute("/", handleHome);
  addRoute("/static/style.css", handleStaticCss);
  addRoute("/static/js-colormaps.js", handleStaticJsColor);
  addRoute("/static/spectrogram.js", handleStaticSpectrogramJs);
}
