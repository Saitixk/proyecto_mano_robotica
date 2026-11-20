
    #include <WiFi.h>
#include <WebServer.h>

// ================= WIFI =================
const char* ssid = "Carrito_ESP32";
const char* password = "12345678";

WebServer server(80);

// ============== TB6612FNG ==============
const int AIN1 = 26;
const int AIN2 = 27;
const int PWMA = 25;
const int STBY = 33;

// ============== SERVO MG996R ===========
const int SERVO_PIN = 13;

// ============== LEDS ===================
const int LED_IZQ_DEL = 14;
const int LED_IZQ_TRA = 16;
const int LED_DER_DEL = 17;
const int LED_DER_TRA = 18;

// ============== VARIABLES ===============
bool direccionalIzq = false;
bool direccionalDer = false;
bool intermitentes = false;
bool estadoLED = false;

unsigned long tiempoLED = 0;
unsigned long ultimoControl = 0;

int posicionServo = 90;
int velocidadMotor = 0;

const int VELOCIDAD = 180;

// ============== SERVO ==================
void moverServo(int angulo) {
  angulo = constrain(angulo, 45, 135);
  posicionServo = angulo;

  uint32_t pulso = map(angulo, 0, 180, 500, 2400);
  uint32_t duty = (pulso * 65535UL) / 20000UL;

  ledcWrite(SERVO_PIN, duty);
}

// ============== MOTOR ==================
void adelante(int velocidad) {
  digitalWrite(STBY, HIGH);
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  velocidad = constrain(velocidad, 0, 255);
  ledcWrite(PWMA, velocidad);
  velocidadMotor = velocidad;
}

void atras(int velocidad) {
  digitalWrite(STBY, HIGH);
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  velocidad = constrain(velocidad, 0, 255);
  ledcWrite(PWMA, velocidad);
  velocidadMotor = velocidad;
}

void parar() {
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  ledcWrite(PWMA, 0);
  velocidadMotor = 0;
}

// ============== LUCES ==================
void apagarLEDs() {
  digitalWrite(LED_IZQ_DEL, LOW);
  digitalWrite(LED_IZQ_TRA, LOW);
  digitalWrite(LED_DER_DEL, LOW);
  digitalWrite(LED_DER_TRA, LOW);
}

void actualizarLEDs() {
  if (millis() - tiempoLED >= 350) { // Destello más fluido a 350ms
    tiempoLED = millis();
    estadoLED = !estadoLED;

    if (intermitentes) {
      digitalWrite(LED_IZQ_DEL, estadoLED);
      digitalWrite(LED_IZQ_TRA, estadoLED);
      digitalWrite(LED_DER_DEL, estadoLED);
      digitalWrite(LED_DER_TRA, estadoLED);
    }
    else if (direccionalIzq) {
      digitalWrite(LED_IZQ_DEL, estadoLED);
      digitalWrite(LED_IZQ_TRA, estadoLED);
      digitalWrite(LED_DER_DEL, LOW);
      digitalWrite(LED_DER_TRA, LOW);
    }
    else if (direccionalDer) {
      digitalWrite(LED_DER_DEL, estadoLED);
      digitalWrite(LED_DER_TRA, estadoLED);
      digitalWrite(LED_IZQ_DEL, LOW);
      digitalWrite(LED_IZQ_TRA, LOW);
    }
    else {
      apagarLEDs();
    }
  }
}

// ============== PAGINA WEB ==============
void paginaPrincipal() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html lang="es">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-select=no">
<meta charset="UTF-8">
<title>Control Carrito RC</title>

<style>
* {
  box-sizing: border-box;
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
}

body {
  margin: 0;
  padding: 10px;
  background: #0f172a;
  color: white;
  font-family: system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

header { text-align: center; }
h2 { color: #38bdf8; margin: 4px 0; font-size: 20px; }
p { color: #94a3b8; margin: 2px 0 10px; font-size: 13px; }

/* Luces arriba */
.panel-luces {
  background: #1e293b;
  padding: 10px;
  border-radius: 16px;
  max-width: 500px;
  margin: 0 auto 10px auto;
  width: 100%;
}

.grid-luces {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* Mando Gamepad abajo */
.gamepad-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  width: 100%;
  max-width: 650px;
  margin: 0 auto;
  flex-grow: 1;
}

.mando {
  background: #1e293b;
  padding: 14px;
  border-radius: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}

.mando-titulo {
  font-size: 12px;
  font-weight: bold;
  color: #64748b;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.btn-mando-vert {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 140px;
}

.btn-mando-horiz {
  display: flex;
  flex-direction: row;
  gap: 10px;
  width: 100%;
}

button {
  border: 0;
  border-radius: 18px;
  font-weight: bold;
  color: white;
  background: #334155;
  touch-action: none;
  cursor: pointer;
  transition: background 0.1s;
}

button:active {
  filter: brightness(1.4);
  transform: scale(0.96);
}

.btn-drive {
  background: #0284c7;
  height: 70px;
  font-size: 16px;
  width: 100%;
}

.btn-steer {
  background: #7c3aed;
  height: 80px;
  font-size: 16px;
  flex: 1;
}

.btn-stop {
  background: #ef4444;
  height: 40px;
  font-size: 12px;
  width: 100%;
  margin-top: 10px;
}

.btn-center {
  background: #475569;
  height: 40px;
  font-size: 12px;
  width: 100%;
  margin-top: 10px;
}

.btn-signal {
  background: #d97706;
  padding: 10px 4px;
  font-size: 13px;
  min-height: 48px;
}

.btn-off {
  background: #475569;
  padding: 10px 4px;
  font-size: 13px;
  min-height: 48px;
}

#estado {
  font-size: 12px;
  text-align: center;
  margin-top: 8px;
}
</style>
</head>

<body>

<header>
  <h2>🚗 CARRITO RC</h2>
  <p id="estado">Conectado</p>
</header>

<!-- LUCES EN LA PARTE SUPERIOR -->
<div class="panel-luces">
  <div class="grid-luces">
    <button class="btn-signal" onclick="enviar('/emergencia')">⚠ INTERMITENTES</button>
    <button class="btn-off" onclick="enviar('/apagar')">APAGAR LUCES</button>
  </div>
</div>

<!-- CONTROLES SEPARADOS (ESTILO GAMEPAD) -->
<div class="gamepad-container">
  
  <!-- IZQUIERDA: DIRECCIÓN -->
  <div class="mando">
    <div class="mando-titulo">Dirección</div>
    <div class="btn-mando-horiz">
      <button class="btn-steer"
        onpointerdown="direccion('izquierda',event)"
        onpointerup="soltarDireccion(event)"
        onpointercancel="soltarDireccion(event)"
        onpointerleave="soltarDireccion(event)">
        ◀️
      </button>
      <button class="btn-steer"
        onpointerdown="direccion('derecha',event)"
        onpointerup="soltarDireccion(event)"
        onpointercancel="soltarDireccion(event)"
        onpointerleave="soltarDireccion(event)">
        ▶️
      </button>
    </div>
    <button class="btn-center" onclick="enviar('/centro')">CENTRAR</button>
  </div>

  <!-- DERECHA: TRACCIÓN -->
  <div class="mando">
    <div class="mando-titulo">Tracción</div>
    <div class="btn-mando-vert">
      <button class="btn-drive"
        onpointerdown="motor('adelante',event)"
        onpointerup="soltarMotor(event)"
        onpointercancel="soltarMotor(event)"
        onpointerleave="soltarMotor(event)">
        ▲<br>ADELANTE
      </button>
      <button class="btn-drive"
        onpointerdown="motor('atras',event)"
        onpointerup="soltarMotor(event)"
        onpointercancel="soltarMotor(event)"
        onpointerleave="soltarMotor(event)">
        ▼<br>ATRÁS
      </button>
    </div>
    <button class="btn-stop" onclick="detener()">■ PARAR</button>
  </div>

</div>

<script>
let intervaloMotor = null;
let motorActivo = false;
let direccionActiva = false;

function enviar(ruta) {
  fetch(ruta).catch(() => {
    document.getElementById('estado').textContent = 'Error de conexión';
  });
}

function motor(tipo, e) {
  if (e) e.preventDefault();
  if (motorActivo) return;

  motorActivo = true;
  enviar('/' + tipo);

  intervaloMotor = setInterval(() => {
    enviar('/' + tipo);
  }, 400);
}

function soltarMotor(e) {
  if (e) e.preventDefault();
  if (!motorActivo) return;

  motorActivo = false;
  clearInterval(intervaloMotor);
  intervaloMotor = null;
  enviar('/parar');
}

function detener() {
  motorActivo = false;
  clearInterval(intervaloMotor);
  intervaloMotor = null;
  enviar('/parar');
}

function direccion(tipo, e) {
  if (e) e.preventDefault();
  if (direccionActiva) return;

  direccionActiva = true;
  enviar('/' + tipo);
}

function soltarDireccion(e) {
  if (e) e.preventDefault();
  if (!direccionActiva) return;

  direccionActiva = false;
  enviar('/centro');
}
</script>

</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

// ============== CONFIGURACION ===========
void setup() {
  Serial.begin(115200);

  // Motor
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(STBY, OUTPUT);

  ledcAttach(PWMA, 5000, 8);

  digitalWrite(STBY, HIGH);
  parar();

  // LEDs
  pinMode(LED_IZQ_DEL, OUTPUT);
  pinMode(LED_IZQ_TRA, OUTPUT);
  pinMode(LED_DER_DEL, OUTPUT);
  pinMode(LED_DER_TRA, OUTPUT);

  apagarLEDs();

  // Servo
  if (!ledcAttach(SERVO_PIN, 50, 16)) {
    Serial.println("Error al configurar el servo");
  } else {
    moverServo(90);
  }

  // AP Wi-Fi
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);

  Serial.println("\nCarrito RC iniciado");
  Serial.print("IP: ");
  Serial.println(WiFi.softAPIP());

  // Servidor Web
  server.on("/", HTTP_GET, paginaPrincipal);

  server.on("/adelante", HTTP_GET, []() {
    ultimoControl = millis();
    adelante(VELOCIDAD);
    server.send(200, "text/plain", "Adelante");
  });

  server.on("/atras", HTTP_GET, []() {
    ultimoControl = millis();
    atras(VELOCIDAD);
    server.send(200, "text/plain", "Atras");
  });

  server.on("/parar", HTTP_GET, []() {
    parar();
    server.send(200, "text/plain", "Motor detenido");
  });

  // DIRECCIÓN + DIRECCIONALES AUTOMÁTICAS
  server.on("/izquierda", HTTP_GET, []() {
    moverServo(50);
    direccionalIzq = true;
    direccionalDer = false;
    server.send(200, "text/plain", "Izquierda");
  });

  server.on("/derecha", HTTP_GET, []() {
    moverServo(130);
    direccionalDer = true;
    direccionalIzq = false;
    server.send(200, "text/plain", "Derecha");
  });

  server.on("/centro", HTTP