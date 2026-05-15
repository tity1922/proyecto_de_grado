#include <ESP32Servo.h>

const int PIR_PIN = 13;   
const int SERVO_PIN = 12; 
const int FLASH_PIN = 4;  

Servo servoClasificador;
int contadorTotal = 0;

void finalizarSimulacion() {
  Serial.println("\n==============================================");
  Serial.println("          SIMULACIÓN FINALIZADA (UDI)         ");
  Serial.printf("  Total residuos procesados: %d\n", contadorTotal);
  Serial.println("==============================================");
  while(true) { delay(1000); }
}

void setup() {
  Serial.begin(115200);
  
  // En Velxio, a veces el PIR necesita PULLDOWN interno si flota
  pinMode(PIR_PIN, INPUT_PULLDOWN); 
  pinMode(FLASH_PIN, OUTPUT);
  
  servoClasificador.attach(SERVO_PIN);
  servoClasificador.write(90); 
  
  delay(2000); // Tiempo para que el sensor se estabilice
  Serial.println("\n>>> SISTEMA LISTO.");
  Serial.println(">>> PASE EL MOUSE SOBRE EL SENSOR PIR O ACTIVE EL BOTÓN.");
}

void loop() {
  // Leemos el estado del sensor
  int estadoPIR = digitalRead(PIR_PIN);

  if (estadoPIR == HIGH) {
    contadorTotal++;
    Serial.printf("\n[OK] ¡RESIDUO DETECTADO #%d!\n", contadorTotal);
    
    // Feedback visual (Flash)
    digitalWrite(FLASH_PIN, HIGH);
    delay(500);
    digitalWrite(FLASH_PIN, LOW);
    
    Serial.println("¿Qué detectó la IA? (A: Aprovechable / N: No Aprovechable)");

    // Esperar respuesta (Limpiando buffer primero)
    while(Serial.available() > 0) Serial.read(); 
    
    char decision = ' ';
    while (true) {
      if (Serial.available() > 0) {
        decision = toupper(Serial.read());
        if (decision == 'A' || decision == 'N') break;
      }
      delay(10); // Evita saturar el procesador de la simulación
    }

    if (decision == 'A') {
      Serial.println(">> ACCIÓN: Moviendo a contenedor RECICLAJE (0°)");
      servoClasificador.write(0);
    } else {
      Serial.println(">> ACCIÓN: Moviendo a contenedor BASURA (180°)");
      servoClasificador.write(180);
    }

    delay(2500); // Tiempo de caída del residuo
    servoClasificador.write(90);
    
    Serial.println("\n¿Desea continuar clasificado? (S/N)");
    
    // Esperar confirmación de continuación
    while(Serial.available() > 0) Serial.read(); 
    char continuar = ' ';
    while (true) {
      if (Serial.available() > 0) {
        continuar = toupper(Serial.read());
        if (continuar == 'S' || continuar == 'N') break;
      }
      delay(10);
    }

    if (continuar == 'N') {
      finalizarSimulacion();
    } else {
      Serial.println("\n>>> Sistema rearmado. Mueva el residuo del sensor...");
      delay(3000); // Tiempo para "limpiar" el área del sensor
      while(Serial.available() > 0) Serial.read(); 
    }
  }
}
