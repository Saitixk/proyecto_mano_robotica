#include <Arduino.h>
#include <ESP32Servo.h>

// ==========================================
// MANO ROBOTICA V2.0 - SOLO SERVOS
// ESP32 + 5 SERVOS controlados por camara
// (sin MPU6050, sin TCA9548A, sin guante)
// Usar con: mano_camara.py
// ==========================================

// Orden de los dedos (el mismo que manda Python):
// 0 Pulgar, 1 Indice, 2 Medio, 3 Anular, 4 Menique
const uint8_t NUM_DEDOS = 5;

// Pines inferidos de la PCB.
// CONFIRMAR con multimetro o esquema KiCad.
const uint8_t PIN_SERVO[NUM_DEDOS] = {
  12, 14, 27, 26, 32
};

// DRV8833 (motor DC): NO se usa, pero sus pines
// se dejan en LOW para que el motor no se mueva solo.
const uint8_t IN1 = 25;
const uint8_t IN2 = 33;

// ==========================================
// CONFIGURACION DE MOVIMIENTO
// ==========================================

// Angulo del servo con el dedo ABIERTO y CERRADO.
// Ajustar segun la mecanica de tu mano.
// Si un dedo se mueve al reves, intercambia
// sus dos valores.
const int SERVO_ABIERTO[NUM_DEDOS] = {
  90, 30, 30, 30, 30
};

const int SERVO_CERRADO[NUM_DEDOS] = {
  150, 140, 140, 140, 140
};

// Suavizado: 0.0 a 1.0
// Valor pequeno = mas suave, mas lento.
const float FILTRO = 0.20;

// Maximo cambio de grados por ciclo.
// Mas alto = mas rapido (4.0 o 5.0 con cuidado).
const float PASO_MAXIMO = 3.0;

// Intervalos
const uint32_t PERIODO_CONTROL = 25;   // ms
const uint32_t PERIODO_ESTADO = 500;   // ms
const uint32_t TIEMPO_SIN_DATOS = 1000; // ms

// ==========================================
// VARIABLES
// ==========================================

Servo servos[NUM_DEDOS];

float objetivo[NUM_DEDOS];
float filtrado[NUM_DEDOS];
float posicion[NUM_DEDOS];

uint32_t ultimoControl = 0;
uint32_t ultimoEstado = 0;
uint32_t ultimoComando = 0;
bool algunaVezRecibio = false;

char lineaSerial[64];
uint8_t indiceSerial = 0;

// ==========================================
// MOVIMIENTO
// ==========================================

// Convierte 0-100 % de flexion a grados
float porcentajeAAngulo(int pct, uint8_t dedo) {
  pct = constrain(pct, 0, 100);
  return SERVO_ABIERTO[dedo] +
    (pct / 100.0) *
    (SERVO_CERRADO[dedo] - SERVO_ABIERTO[dedo]);
}

// Filtro + limite de velocidad
void moverSuave(uint8_t i) {
  filtrado[i] += FILTRO * (objetivo[i] - filtrado[i]);

  float diferencia = constrain(
    filtrado[i] - posicion[i],
    -PASO_MAXIMO, PASO_MAXIMO
  );

  posicion[i] += diferencia;

  servos[i].write((int)round(posicion[i]));
}

// ==========================================
// COMANDOS DESDE PYTHON / MONITOR SERIAL
// ==========================================

// H:p,i,m,a,q -> flexion 0-100 % de cada dedo
//               (lo manda mano_camara.py)
//               Ej: H:0,100,100,100,100
// S:d,ang     -> mover un dedo a un angulo exacto
//               (para encontrar ABIERTO/CERRADO)
//               Ej: S:1,90  (indice a 90 grados)
// A           -> abrir toda la mano

void procesarComando(char *comando) {
  if (strncmp(comando, "H:", 2) == 0) {
    int v[NUM_DEDOS];

    int leidos = sscanf(
      comando + 2, "%d,%d,%d,%d,%d",
      &v[0], &v[1], &v[2], &v[3], &v[4]
    );

    if (leidos != NUM_DEDOS) return; // comando roto

    for (uint8_t i = 0; i < NUM_DEDOS; i++) {
      objetivo[i] = porcentajeAAngulo(v[i], i);
    }

    ultimoComando = millis();
    algunaVezRecibio = true;
  }
  else if (strncmp(comando, "S:", 2) == 0) {
    int dedo, angulo;

    if (sscanf(comando + 2, "%d,%d", &dedo, &angulo) == 2 &&
        dedo >= 0 && dedo < NUM_DEDOS) {
      objetivo[dedo] = constrain(angulo, 0, 180);
      Serial.printf("Dedo %d -> %d grados\n", dedo, angulo);
    }
  }
  else if (strcmp(comando, "A") == 0) {
    for (uint8_t i = 0; i < NUM_DEDOS; i++) {
      objetivo[i] = SERVO_ABIERTO[i];
    }
  }
}

void recibirSerial() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      lineaSerial[indiceSerial] = '\0';
      procesarComando(lineaSerial);
      indiceSerial = 0;
    }
    else if (c != '\r') {
      if (indiceSerial < sizeof(lineaSerial) - 1) {
        lineaSerial[indiceSerial++] = c;
      } else {
        indiceSerial = 0;
      }
    }
  }
}

// ==========================================
// ESTADO HACIA PYTHON
// Se ve en la parte de abajo de la ventana:
// SERVOS:90,30,30,30,30 CAMARA OK
// ==========================================

void enviarEstado() {
  Serial.print("SERVOS:");

  for (uint8_t i = 0; i < NUM_DEDOS; i++) {
    Serial.print((int)round(posicion[i]));
    if (i < NUM_DEDOS - 1) Serial.print(",");
  }

  if (!algunaVezRecibio) {
    Serial.println(" ESPERANDO CAMARA");
  } else if (millis() - ultimoComando > TIEMPO_SIN_DATOS) {
    // Sin datos: los dedos se quedan donde estaban
    Serial.println(" SIN DATOS");
  } else {
    Serial.println(" CAMARA OK");
  }
}

// ==========================================
// SETUP
// ==========================================

void setup() {
  Serial.begin(115200);

  Serial.println("INICIANDO MANO ROBOTICA (SOLO SERVOS)");

  // Motor apagado
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  // Servos a 50 Hz, empezando con la mano abierta
  for (uint8_t i = 0; i < NUM_DEDOS; i++) {
    servos[i].setPeriodHertz(50);
    servos[i].attach(PIN_SERVO[i], 1000, 2000);

    objetivo[i] = SERVO_ABIERTO[i];
    filtrado[i] = SERVO_ABIERTO[i];
    posicion[i] = SERVO_ABIERTO[i];

    servos[i].write(SERVO_ABIERTO[i]);
  }

  delay(500);

  Serial.println("SISTEMA LISTO");
}

// ==========================================
// LOOP PRINCIPAL
// ==========================================

void loop() {
  uint32_t ahora = millis();

  recibirSerial();

  if (ahora - ultimoControl >= PERIODO_CONTROL) {
    ultimoControl = ahora;
    for (uint8_t i = 0; i < NUM_DEDOS; i++) {
      moverSuave(i);
    }
  }

  if (ahora - ultimoEstado >= PERIODO_ESTADO) {
    ultimoEstado = ahora;
    enviarEstado();
  }
}
