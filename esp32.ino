/**
 * PROYECTO DE GRADO - UDI
 * Prueba de Clasificación Manual
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "OPPO A80 5G";
const char* password = "lule2345";
const char* serverUrl = "http://10.166.251.1:5000/clasificar"; 

const int PIN_SENSOR = 13;
const int PIN_SERVO  = 12;
const int PIN_FLASH  = 4;

Servo miServo;

// --- PINES CÁMARA ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SENSOR, INPUT);
  pinMode(PIN_FLASH, OUTPUT);
  
  // Configuración del Servo
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  miServo.setPeriodHertz(50);
  miServo.attach(PIN_SERVO, 500, 2400);
  
  // Posición inicial de prueba
  Serial.println("Probando Servo...");
  miServo.write(90); 
  delay(500);

  // Configuración Cámara
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA; 
  config.jpeg_quality = 10;
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Error cámara");
    return;
  }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n✅ Wi-Fi Conectado");
}

void loop() {
  if (digitalRead(PIN_SENSOR) == LOW) {
    Serial.println("¡Objeto detectado!");
    digitalWrite(PIN_FLASH, HIGH);
    delay(500);

    camera_fb_t * fb = esp_camera_fb_get();
    if (fb) {
      HTTPClient http;
      http.begin(serverUrl);
      http.addHeader("Content-Type", "image/jpeg");
      
      int httpCode = http.POST(fb->buf, fb->len);
      
      // APAGAMOS EL FLASH ANTES DE MOVER EL SERVO
      digitalWrite(PIN_FLASH, LOW);

      if (httpCode > 0) {
        String resp = http.getString();
        resp.trim(); // LIMPIEZA CLAVE
        
        Serial.print("Respuesta recibida: ");
        Serial.println(resp);

        if (resp == "1") {
          Serial.println("Moviendo a APROVECHABLES");
          miServo.write(130);
          delay(2500);
        } 
        else if (resp == "2") {
          Serial.println("Moviendo a NO APROVECHABLES");
          miServo.write(50);
          delay(2500);
        }
        
        miServo.write(90); // Regresa a posición neutra
      } else {
        Serial.printf("Error HTTP: %s\n", http.errorToString(httpCode).c_str());
      }
      http.end();
      esp_camera_fb_return(fb);
    }
    delay(2000); // Pausa para evitar múltiples disparos
  }
}