#include <WiFi.h>
#include <ESPmDNS.h>
#include <WebServer.h>

// Your WiFi credentials.
const char *ssid = "Domov Duchodcu";
const char *password = "JanBouska1";

// Web server
WebServer server(80);

// LED State
bool ledState = LOW;
const int ledPin = 2; // Most ESP32 dev boards have an LED on pin 2

void handleRoot() {
  Serial.println("GET /");
  char temp[400];
  int sec = millis() / 1000;
  int min = sec / 60;
  int hr = min / 60;

  snprintf(temp, 400,
           "<html>\
  <head>\
    <meta http-equiv='refresh' content='5'/>\
    <title>ESP32 Demo</title>\
    <style>\
      body { background-color: #cccccc; font-family: Arial, Helvetica, Sans-Serif; Color: #000088; }\
    </style>\
  </head>\
  <body>\
    <h1>Hello from ESP32!</h1>\
    <p>Uptime: %02d:%02d:%02d</p>\
    <p>LED is now %s.</p>\
    <a href=\"/toggle\">Toggle LED</a>\
  </body>\
</html>",
           hr, min % 60, sec % 60, (ledState ? "ON" : "OFF"));
  server.send(200, "text/html", temp);
}

void handleToggle() {
  ledState = !ledState;
  Serial.printf("LED toggled to %s\n", (ledState ? "ON" : "OFF"));
  digitalWrite(ledPin, ledState);
  server.sendHeader("Location", "/");
  server.send(302, "text/plain", "");
}

void handleNotFound() {
  digitalWrite(ledPin, 1);
  String message = "File Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";

  for (uint8_t i = 0; i < server.args(); i++) {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }

  server.send(404, "text/plain", message);
  digitalWrite(ledPin, 0);
}


void setup()
{
  Serial.begin(115200);
  Serial.println("Boot");

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.waitForConnectResult() != WL_CONNECTED)
  {
    Serial.println("Connection Failed! Rebooting...");
    delay(5000);
    ESP.restart();
  }

  if (MDNS.begin("esp32")) {
    Serial.println("MDNS responder started");
  }

  server.on("/", handleRoot);
  server.on("/toggle", handleToggle);
  server.onNotFound(handleNotFound);
  server.begin();

  Serial.println("Ready");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("HTTP server started");
}

void loop()
{
  server.handleClient();
}
