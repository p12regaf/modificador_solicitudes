"""
Base de datos completa de PIDs OBD-II estándar (ISO 15031-5 / SAE J1979).
Fuente: Wikipedia + SAE J1979.

Cada OBDPid incluye:
  pid          : código hex (2 chars para modo 01; puede ser más para UDS)
  mode         : "01", "03", "07", "09", "22"
  nombre       : nombre en español
  nombre_en    : nombre en inglés (SAE)
  unidad       : unidad de medida
  categoria    : agrupación funcional
  freq_ms      : frecuencia sugerida en ms (0 = no periódico / disparo único)
  can_id       : ID CAN ("7DF" para broadcast OBD-II estándar)
  disparo_unico: True si debe enviarse solo al arrancar
  formula      : fórmula de conversión (bytes A, B... → valor físico)
  descripcion  : descripción ampliada
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OBDPid:
    pid: str           # Hex, ej "0C"
    mode: str          # "01", "03", "07", "09", "22"
    nombre: str
    nombre_en: str
    unidad: str
    categoria: str
    freq_ms: int       # ms sugerido; 0 = disparo único / no periódico
    can_id: str = "7DF"
    disparo_unico: bool = False
    formula: str = ""
    descripcion: str = ""

    @property
    def datos(self) -> str:
        """
        Trama CAN de 8 bytes (16 hex chars) para este PID (campo Datos del CSV).
        Formato: longitud(1B) + modo(1B) + PID(1B) + padding hasta 8 bytes.
        """
        m = self.mode
        p = self.pid.upper()
        if m == "01":
            # 02 01 PID 00 00 00 00 00  → 8 bytes → 16 hex chars
            return f"0201{p}0000000000"
        elif m == "03":
            return "0103000000000000"
        elif m == "07":
            return "0107000000000000"
        elif m == "09":
            # 02 09 InfoType 00 00 00 00 00
            return f"0209{p}0000000000"
        elif m == "22":
            # 03 22 ID_HIGH ID_LOW 00 00 00 00  (pid ya es 4 hex chars = 2 bytes)
            return f"0322{p}00000000"
        return f"0201{p}0000000000"

    @property
    def pid_full(self) -> str:
        return f"{self.mode}-{self.pid.upper()}"

    @property
    def display_name(self) -> str:
        return f"{self.nombre} [{self.unidad}]" if self.unidad else self.nombre


# ── Categorías ─────────────────────────────────────────────────────────────────

CATEGORIAS = [
    "Todas",
    "Motor",
    "Transmisión",
    "Combustible",
    "Temperatura",
    "Presión",
    "Electrico",
    "Sensores O2",
    "Turbo / EGR",
    "Diagnóstico",
    "Vehículo / Modo 09",
]

# ── Base de datos ──────────────────────────────────────────────────────────────
# fmt: off
OBD_PIDS: list[OBDPid] = [

    # ══ MOTOR ══════════════════════════════════════════════════════════════════
    OBDPid("0C", "01", "RPM motor",                      "Engine RPM",                  "rpm",  "Motor",        200,
           formula="(256A+B)/4",             descripcion="Velocidad de giro del cigüeñal. Rango: 0-16383 rpm"),
    OBDPid("04", "01", "Carga motor calculada",          "Calculated engine load",       "%",    "Motor",        500,
           formula="A/2.55",                descripcion="Porcentaje de carga actual respecto al máximo. Rango: 0-100%"),
    OBDPid("11", "01", "Posición mariposa (absoluta)",   "Throttle position",            "%",    "Motor",        500,
           formula="A/2.55",                descripcion="Apertura absoluta de la válvula de mariposa"),
    OBDPid("45", "01", "Posición mariposa (relativa)",   "Relative throttle position",   "%",    "Motor",        500,
           formula="A/2.55"),
    OBDPid("47", "01", "Posición mariposa B",            "Absolute throttle position B", "%",    "Motor",        500,
           formula="A/2.55"),
    OBDPid("48", "01", "Posición mariposa C",            "Absolute throttle position C", "%",    "Motor",        500,
           formula="A/2.55"),
    OBDPid("4C", "01", "Apertura mariposa comandada",    "Commanded throttle actuator",  "%",    "Motor",        500,
           formula="A/2.55"),
    OBDPid("10", "01", "Flujo masa de aire (MAF)",       "Mass air flow rate",           "g/s",  "Motor",        500,
           formula="(256A+B)/100",          descripcion="Masa de aire por segundo que entra al motor. Rango: 0-655 g/s"),
    OBDPid("66", "01", "Sensor MAF (ampliado)",          "Mass air flow sensor",         "g/s",  "Motor",        500),
    OBDPid("0E", "01", "Avance del encendido",           "Timing advance",               "°",    "Motor",        1000,
           formula="A/2 - 64",             descripcion="Grados de avance antes del PMS. Rango: -64 a 63.5°"),
    OBDPid("43", "01", "Carga absoluta motor",           "Absolute load value",          "%",    "Motor",        1000,
           formula="(256A+B)/2.55",        descripcion="Rango: 0-25700%"),
    OBDPid("44", "01", "Ratio aire/combustible (λ cmd)", "Commanded equiv. ratio",       "λ",    "Motor",        1000,
           formula="(256A+B)/32768"),
    OBDPid("49", "01", "Pedal acelerador D",             "Accelerator pedal pos. D",     "%",    "Motor",        1000,
           formula="A/2.55"),
    OBDPid("4A", "01", "Pedal acelerador E",             "Accelerator pedal pos. E",     "%",    "Motor",        1000,
           formula="A/2.55"),
    OBDPid("4B", "01", "Pedal acelerador F",             "Accelerator pedal pos. F",     "%",    "Motor",        1000,
           formula="A/2.55"),
    OBDPid("5A", "01", "Posición acelerador (relativa)", "Relative accel. pedal pos.",   "%",    "Motor",        500,
           formula="A/2.55"),
    OBDPid("8D", "01", "Posición acelerador G",          "Throttle position G",          "%",    "Motor",        1000,
           formula="A/2.55"),
    OBDPid("1F", "01", "Tiempo motor en marcha",         "Engine run time",              "s",    "Motor",        5000,
           formula="256A+B",               descripcion="Segundos desde que se puso en marcha el motor. Rango: 0-65535 s"),
    OBDPid("62", "01", "Par motor actual",               "Actual engine - percent torque","%",   "Motor",        1000,
           formula="A-125",                descripcion="Par actual como % del par de referencia. Rango: -125% a +125%"),
    OBDPid("61", "01", "Par motor demandado (conductor)","Driver demand engine torque",  "%",    "Motor",        1000,
           formula="A-125"),
    OBDPid("63", "01", "Par motor de referencia",        "Engine reference torque",      "Nm",   "Motor",        20000,
           formula="256A+B"),
    OBDPid("8E", "01", "Fricción motor (% par)",         "Engine friction - pct torque", "%",    "Motor",        5000,
           formula="A-125"),

    # ══ VELOCIDAD / VEHÍCULO ═══════════════════════════════════════════════════
    OBDPid("0D", "01", "Velocidad vehículo",             "Vehicle speed",               "km/h", "Vehículo / Modo 09", 200,
           formula="A",                    descripcion="Velocidad del vehículo medida por la ECU. Rango: 0-255 km/h"),
    OBDPid("A4", "01", "Relación de transmisión real",    "Transmission actual gear ratio","ratio","Transmisión", 1000,
           formula="(256C+D)/1000",          descripcion="Marcha actual de la transmisión automática"),

    # ══ TEMPERATURA ════════════════════════════════════════════════════════════
    OBDPid("05", "01", "Temperatura refrigerante",       "Engine coolant temperature",  "°C",   "Temperatura",  1000,
           formula="A-40",                 descripcion="Temperatura del líquido refrigerante. Rango: -40 a 215 °C"),
    OBDPid("0F", "01", "Temperatura admisión (IAT)",     "Intake air temperature",      "°C",   "Temperatura",  2000,
           formula="A-40",                 descripcion="Temperatura del aire en el colector. Rango: -40 a 215 °C"),
    OBDPid("46", "01", "Temperatura exterior (amb.)",    "Ambient air temperature",     "°C",   "Temperatura",  5000,
           formula="A-40",                 descripcion="Temperatura del aire exterior. Rango: -40 a 215 °C"),
    OBDPid("5C", "01", "Temperatura aceite motor",       "Engine oil temperature",      "°C",   "Temperatura",  5000,
           formula="A-40",                 descripcion="Rango: -40 a 210 °C"),
    OBDPid("3C", "01", "Temp. catalizador B1 S1",        "Catalyst temp. Bank1 Sens1",  "°C",   "Temperatura",  5000,
           formula="(256A+B)/10 - 40",    descripcion="Rango: -40 a 6513 °C"),
    OBDPid("3D", "01", "Temp. catalizador B2 S1",        "Catalyst temp. Bank2 Sens1",  "°C",   "Temperatura",  5000,
           formula="(256A+B)/10 - 40"),
    OBDPid("3E", "01", "Temp. catalizador B1 S2",        "Catalyst temp. Bank1 Sens2",  "°C",   "Temperatura",  5000,
           formula="(256A+B)/10 - 40"),
    OBDPid("3F", "01", "Temp. catalizador B2 S2",        "Catalyst temp. Bank2 Sens2",  "°C",   "Temperatura",  5000,
           formula="(256A+B)/10 - 40"),
    OBDPid("67", "01", "Temperatura refrigerante (2s)",  "Coolant temp. (2 sensors)",   "°C",   "Temperatura",  2000),
    OBDPid("68", "01", "Temperatura admisión (extendida)","Intake air temp. sensor",    "°C",   "Temperatura",  5000),
    OBDPid("84", "01", "Temp. superficie colector",      "Manifold surface temperature","°C",   "Temperatura",  5000),
    OBDPid("98", "01", "Temp. gases escape B1 (ext.)",   "EGT Bank 1 (extended)",       "°C",   "Temperatura",  2000),
    OBDPid("99", "01", "Temp. gases escape B2 (ext.)",   "EGT Bank 2 (extended)",       "°C",   "Temperatura",  2000),

    # ══ PRESIÓN ════════════════════════════════════════════════════════════════
    OBDPid("0B", "01", "Presión colector admisión (MAP)","Intake manifold abs. pressure","kPa", "Presión",      1000,
           formula="A",                    descripcion="Presión absoluta en el colector. Rango: 0-255 kPa"),
    OBDPid("0A", "01", "Presión combustible (relativa)", "Fuel pressure (gauge)",       "kPa",  "Presión",      5000,
           formula="3A",                   descripcion="Presión relativa del combustible. Rango: 0-765 kPa"),
    OBDPid("22", "01", "Presión combustible (vacío)",    "Fuel rail pressure (vacuum)",  "kPa", "Presión",      5000,
           formula="0.079*(256A+B)"),
    OBDPid("23", "01", "Presión raíl combustible",       "Fuel rail gauge pressure",    "kPa",  "Presión",      2000,
           formula="10*(256A+B)",          descripcion="Presión absoluta en el raíl de inyección. Rango: 0-655350 kPa"),
    OBDPid("59", "01", "Presión abs. raíl combustible",  "Fuel rail absolute pressure", "kPa",  "Presión",      2000,
           formula="10*(256A+B)"),
    OBDPid("33", "01", "Presión barométrica",            "Barometric pressure",         "kPa",  "Presión",      10000,
           formula="A",                    descripcion="Presión atmosférica medida por la ECU. Rango: 0-255 kPa"),
    OBDPid("32", "01", "Presión vapor sistema EVAP",     "Evap system vapor pressure",  "Pa",   "Presión",      10000,
           formula="(256A+B)/4 - 8192"),
    OBDPid("53", "01", "Presión abs. vapor EVAP",        "Absolute EVAP vapor pressure","kPa",  "Presión",      10000,
           formula="(256A+B)/200"),
    OBDPid("54", "01", "Presión vapor EVAP",             "EVAP system vapor pressure",  "Pa",   "Presión",      10000,
           formula="256A+B - 32767"),
    OBDPid("87", "01", "Presión abs. colector (ext.)",   "Abs. MAP (extended)",         "kPa",  "Presión",      1000),
    OBDPid("4F", "01", "Máx. ratio/voltO2/corrO2/MAP",  "Max equiv ratio/O2 volt/MAP",  "",     "Presión",      0,
           disparo_unico=True, formula="A(ratio) B(V) C(mA) D*10(kPa)"),
    OBDPid("50", "01", "Máximo flujo MAF",               "Max MAF flow rate",            "g/s",  "Presión",      0,
           disparo_unico=True, formula="A*10"),
    OBDPid("A3", "01", "Presión vapor EVAP (ext.)",      "EVAP vapor pressure (ext.)",  "Pa",   "Presión",      10000),

    # ══ COMBUSTIBLE ════════════════════════════════════════════════════════════
    OBDPid("5D", "01", "Sincronización inyección",        "Fuel injection timing",       "°",    "Combustible",  2000,
           formula="((256A+B)/128)-210",     descripcion="Sincronización de la inyección de combustible. Rango: -210 a 302°"),
    OBDPid("5E", "01", "Caudal de combustible",          "Engine fuel rate",            "L/h",  "Combustible",  5000,
           formula="(256A+B)/20",          descripcion="Consumo instantáneo de combustible. Rango: 0-3276 L/h"),
    OBDPid("9D", "01", "Tasa combustible motor",         "Engine fuel rate",            "g/s",  "Combustible",  5000),
    OBDPid("2F", "01", "Nivel depósito combustible",     "Fuel tank level input",       "%",    "Combustible",  10000,
           formula="A/2.55",              descripcion="Nivel del depósito. Rango: 0-100%"),
    OBDPid("06", "01", "Corrección comb. corto B1",      "Short term fuel trim Bank 1", "%",    "Combustible",  2000,
           formula="A/1.28 - 100",        descripcion="Ajuste a corto plazo mezcla banco 1. Rango: -100% a +99.2%"),
    OBDPid("07", "01", "Corrección comb. largo B1",      "Long term fuel trim Bank 1",  "%",    "Combustible",  5000,
           formula="A/1.28 - 100"),
    OBDPid("08", "01", "Corrección comb. corto B2",      "Short term fuel trim Bank 2", "%",    "Combustible",  2000,
           formula="A/1.28 - 100"),
    OBDPid("09", "01", "Corrección comb. largo B2",      "Long term fuel trim Bank 2",  "%",    "Combustible",  5000,
           formula="A/1.28 - 100"),
    OBDPid("03", "01", "Estado sistema combustible",     "Fuel system status",          "",     "Combustible",  5000,
           descripcion="Codificación en bits. Estado del lazo cerrado/abierto."),
    OBDPid("2E", "01", "Purga EVAP comandada",           "Commanded evaporative purge", "%",    "Combustible",  5000,
           formula="A/2.55"),
    OBDPid("51", "01", "Tipo de combustible",            "Fuel type",                   "",     "Combustible",  20000,
           descripcion="Código del tipo de combustible según tabla SAE J1979"),
    OBDPid("52", "01", "Porcentaje etanol",              "Ethanol fuel %",              "%",    "Combustible",  10000,
           formula="A/2.55"),

    # ══ ELÉCTRICO ══════════════════════════════════════════════════════════════
    OBDPid("42", "01", "Tensión módulo de control",      "Control module voltage",      "V",    "Electrico",    5000,
           formula="(256A+B)/1000",       descripcion="Tensión de alimentación del módulo de control. Rango: 0-65.5 V"),
    OBDPid("5B", "01", "Carga batería híbrida",          "Hybrid battery pack life",    "%",    "Electrico",    10000,
           formula="A/2.55"),
    OBDPid("9A", "01", "Datos batería híbrida/EV",       "Hybrid/EV battery data",      "",     "Electrico",    10000),

    # ══ SENSORES O2 ════════════════════════════════════════════════════════════
    OBDPid("14", "01", "Sensor O2 Banco1 Sensor1 (V)",   "O2 sensor B1S1 voltage",      "V",    "Sensores O2",  1000,
           formula="A:A/200  B: corrección %"),
    OBDPid("15", "01", "Sensor O2 Banco1 Sensor2 (V)",   "O2 sensor B1S2 voltage",      "V",    "Sensores O2",  1000,
           formula="A/200"),
    OBDPid("16", "01", "Sensor O2 Banco2 Sensor1 (V)",   "O2 sensor B2S1 voltage",      "V",    "Sensores O2",  1000),
    OBDPid("17", "01", "Sensor O2 Banco2 Sensor2 (V)",   "O2 sensor B2S2 voltage",      "V",    "Sensores O2",  1000),
    OBDPid("18", "01", "Sensor O2 5 (voltaje + trim)",   "O2 sensor 5 voltage/trim",    "V",    "Sensores O2",  1000,
           formula="A/200  B: B/1.28-100"),
    OBDPid("19", "01", "Sensor O2 6 (voltaje + trim)",   "O2 sensor 6 voltage/trim",    "V",    "Sensores O2",  1000),
    OBDPid("1A", "01", "Sensor O2 7 (voltaje + trim)",   "O2 sensor 7 voltage/trim",    "V",    "Sensores O2",  1000),
    OBDPid("1B", "01", "Sensor O2 8 (voltaje + trim)",   "O2 sensor 8 voltage/trim",    "V",    "Sensores O2",  1000),
    OBDPid("24", "01", "Sensor O2 B1S1 (λ + tensión)",   "O2 sensor B1S1 equiv+volt",   "λ/V",  "Sensores O2",  1000,
           formula="AB: (256A+B)/32768   CD: (256C+D)/8192"),
    OBDPid("25", "01", "Sensor O2 B1S2 (λ + tensión)",   "O2 sensor B1S2 equiv+volt",   "λ/V",  "Sensores O2",  1000),
    OBDPid("26", "01", "Sensor O2 B2S1 (λ + tensión)",   "O2 sensor B2S1 equiv+volt",   "λ/V",  "Sensores O2",  1000),
    OBDPid("27", "01", "Sensor O2 B2S2 (λ + tensión)",   "O2 sensor B2S2 equiv+volt",   "λ/V",  "Sensores O2",  1000),
    OBDPid("28", "01", "Sensor O2 5 (λ + tensión)",      "O2 sensor 5 equiv+volt",      "λ/V",  "Sensores O2",  1000),
    OBDPid("29", "01", "Sensor O2 6 (λ + tensión)",      "O2 sensor 6 equiv+volt",      "λ/V",  "Sensores O2",  1000),
    OBDPid("2A", "01", "Sensor O2 7 (λ + tensión)",      "O2 sensor 7 equiv+volt",      "λ/V",  "Sensores O2",  1000),
    OBDPid("2B", "01", "Sensor O2 8 (λ + tensión)",      "O2 sensor 8 equiv+volt",      "λ/V",  "Sensores O2",  1000),
    OBDPid("34", "01", "Sensor O2 B1S1 (λ + corriente)", "O2 sensor B1S1 equiv+current","λ/mA", "Sensores O2",  1000,
           formula="AB: (256A+B)/32768   CD: C+D/256-128"),
    OBDPid("35", "01", "Sensor O2 B1S2 (λ + corriente)", "O2 sensor B1S2 equiv+current","λ/mA", "Sensores O2",  1000),
    OBDPid("36", "01", "Sensor O2 3 (λ + corriente)",    "O2 sensor 3 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("37", "01", "Sensor O2 4 (λ + corriente)",    "O2 sensor 4 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("38", "01", "Sensor O2 5 (λ + corriente)",    "O2 sensor 5 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("39", "01", "Sensor O2 6 (λ + corriente)",    "O2 sensor 6 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("3A", "01", "Sensor O2 7 (λ + corriente)",    "O2 sensor 7 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("3B", "01", "Sensor O2 8 (λ + corriente)",    "O2 sensor 8 equiv+current",   "λ/mA", "Sensores O2",  1000),
    OBDPid("8C", "01", "Sensor O2 rango amplio",         "O2 sensor (wide range)",      "",     "Sensores O2",  1000),
    OBDPid("55", "01", "Trim O2 sec. corto B1/B3",       "Short term 2nd O2 trim B1B3", "%",    "Sensores O2",  2000,
           formula="A/1.28-100  B/1.28-100"),
    OBDPid("56", "01", "Trim O2 sec. largo B1/B3",       "Long term 2nd O2 trim B1B3",  "%",    "Sensores O2",  5000),
    OBDPid("57", "01", "Trim O2 sec. corto B2/B4",       "Short term 2nd O2 trim B2B4", "%",    "Sensores O2",  2000),
    OBDPid("58", "01", "Trim O2 sec. largo B2/B4",       "Long term 2nd O2 trim B2B4",  "%",    "Sensores O2",  5000),

    # ══ TURBO / EGR ════════════════════════════════════════════════════════════
    OBDPid("74", "01", "RPM turbocompresor",             "Turbocharger RPM",            "rpm",  "Turbo / EGR",  1000),
    OBDPid("70", "01", "Control presión sobrealimentación","Boost pressure control",    "kPa",  "Turbo / EGR",  1000),
    OBDPid("6F", "01", "Presión entrada compresor turbo","Turbo compressor inlet press.","kPa", "Turbo / EGR",  1000),
    OBDPid("73", "01", "Presión gases de escape",        "Exhaust pressure",            "kPa",  "Turbo / EGR",  2000),
    OBDPid("71", "01", "Control turbo geometría var. (VGT)","VGT control",             "%",    "Turbo / EGR",  1000),
    OBDPid("72", "01", "Control wastegate",              "Wastegate control",           "%",    "Turbo / EGR",  1000),
    OBDPid("75", "01", "Temperatura turbocompresor",     "Turbocharger temperature",    "°C",   "Turbo / EGR",  2000),
    OBDPid("76", "01", "Temperatura turbocompresor 2",   "Turbocharger temperature 2",  "°C",   "Turbo / EGR",  2000),
    OBDPid("77", "01", "Temp. intercooler (CACT)",       "Charge air cooler temp.",     "°C",   "Turbo / EGR",  2000),
    OBDPid("78", "01", "Temp. gases escape Banco 1",     "EGT Bank 1",                  "°C",   "Turbo / EGR",  2000),
    OBDPid("79", "01", "Temp. gases escape Banco 2",     "EGT Bank 2",                  "°C",   "Turbo / EGR",  2000),
    OBDPid("7A", "01", "Filtro partículas (DPF)",        "Diesel particulate filter",   "",     "Turbo / EGR",  10000),
    OBDPid("7B", "01", "Temperatura DPF",                "DPF temperature",             "°C",   "Turbo / EGR",  5000),
    OBDPid("7C", "01", "Presión diferencial DPF",        "DPF differential pressure",   "kPa",  "Turbo / EGR",  5000),
    OBDPid("2C", "01", "EGR comandado",                  "Commanded EGR",               "%",    "Turbo / EGR",  2000,
           formula="A/2.55"),
    OBDPid("2D", "01", "Error EGR",                      "EGR error",                   "%",    "Turbo / EGR",  2000,
           formula="A/1.28 - 100"),
    OBDPid("6B", "01", "Temperatura recirculación EGR",  "EGR temperature",             "°C",   "Turbo / EGR",  5000),
    OBDPid("69", "01", "EGR comandado y error EGR",      "Commanded EGR and error",     "",     "Turbo / EGR",  2000),
    OBDPid("6A", "01", "Control flujo aire admisión diesel","Diesel intake air flow",   "%",    "Turbo / EGR",  1000),
    OBDPid("6C", "01", "Control actuador mariposa (ext.)","Commanded throttle (ext.)",  "",     "Turbo / EGR",  1000),
    OBDPid("6D", "01", "Sistema control presión combustible","Fuel pressure ctrl sys.", "",     "Turbo / EGR",  2000),
    OBDPid("6E", "01", "Sistema control presión inyección","Injection pressure ctrl",   "",     "Turbo / EGR",  2000),
    OBDPid("7D", "01", "Estado área control NOx NTE",     "NOx NTE control area status","",    "Turbo / EGR",  20000),
    OBDPid("83", "01", "Sensor NOx",                     "NOx sensor",                  "ppm",  "Turbo / EGR",  5000),
    OBDPid("86", "01", "Sensor partículas (PM)",         "Particulate matter sensor",   "",     "Turbo / EGR",  10000),
    OBDPid("88", "01", "Sistema SCR",                    "SCR induction system",        "",     "Turbo / EGR",  10000),
    OBDPid("85", "01", "Sistema NOx reactivo",           "Reactive NOx system",         "",     "Turbo / EGR",  10000),
    OBDPid("9B", "01", "Datos fluido escape diésel (DEF)","Diesel exhaust fluid",       "",     "Turbo / EGR",  10000),
    OBDPid("9E", "01", "Flujo gases escape motor",       "Engine exhaust flow rate",    "kg/h", "Turbo / EGR",  2000),

    # ══ DIAGNÓSTICO ════════════════════════════════════════════════════════════
    OBDPid("21", "01", "Distancia con MIL encendido",    "Dist. traveled with MIL on",  "km",   "Diagnóstico",  20000,
           formula="256A+B",              descripcion="Kilómetros recorridos con el testigo de avería encendido"),
    OBDPid("31", "01", "Distancia desde borrado DTC",    "Dist. since codes cleared",   "km",   "Diagnóstico",  20000,
           formula="256A+B"),
    OBDPid("4D", "01", "Tiempo con MIL encendido",       "Time run with MIL on",        "min",  "Diagnóstico",  20000,
           formula="256A+B"),
    OBDPid("4E", "01", "Tiempo desde borrado DTC",       "Time since codes cleared",    "min",  "Diagnóstico",  20000,
           formula="256A+B"),
    OBDPid("30", "01", "Calentamientos desde borrado DTC","Warm-ups since codes cleared","",    "Diagnóstico",  20000,
           formula="A",                   descripcion="Número de calentamientos completos desde el último borrado"),
    OBDPid("01", "01", "Estado monitores OBD (MIL)",     "Monitor status since DTC clear","",   "Diagnóstico",  20000,
           descripcion="Bit 7 de byte A = MIL encendido; bits 6-0 = número de DTCs"),
    OBDPid("41", "01", "Estado monitores (ciclo actual)","Monitor status this drive cycle","",  "Diagnóstico",  20000),
    OBDPid("02", "01", "DTC del evento almacenado",      "Freeze frame DTC",            "",     "Diagnóstico",  20000,
           descripcion="Código DTC que causó el almacenamiento del frame de congelado"),
    OBDPid("1E", "01", "Estado entradas auxiliares",     "Auxiliary input status",      "",     "Diagnóstico",  20000,
           descripcion="Bit A0 = PTO activo"),
    OBDPid("1C", "01", "Estándar OBD implementado",      "OBD standard",                "",     "Diagnóstico",  20000,
           descripcion="Código del estándar OBD implementado en este vehículo"),
    OBDPid("00", "01", "PIDs implementados [01-20]",     "Supported PIDs [01-20]",       "",     "Diagnóstico",  0,
           disparo_unico=True, descripcion="Bitmap 32 bits: cada bit indica si el PID correspondiente está soportado"),
    OBDPid("20", "01", "PIDs implementados [21-40]",     "Supported PIDs [21-40]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("40", "01", "PIDs implementados [41-60]",     "Supported PIDs [41-60]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("60", "01", "PIDs implementados [61-80]",     "Supported PIDs [61-80]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("80", "01", "PIDs implementados [81-A0]",     "Supported PIDs [81-A0]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("A0", "01", "PIDs implementados [A1-C0]",     "Supported PIDs [A1-C0]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("C0", "01", "PIDs implementados [C1-E0]",     "Supported PIDs [C1-E0]",       "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("12", "01", "Estado aire secundario",         "Secondary air status",         "",     "Diagnóstico",  20000,
           descripcion="Codificación en bits. Estado del sistema de aire secundario controlado"),
    OBDPid("13", "01", "Sensores O2 presentes (2 bancos)","O2 sensors present (2 banks)","",     "Diagnóstico",  20000,
           descripcion="[A0..A3] == Banco 1 sensores 1-4. [A4..A7] == Banco 2 sensores 1-4"),
    OBDPid("1D", "01", "Sensores O2 presentes (4 bancos)","O2 sensors present (4 banks)","",    "Diagnóstico",  20000,
           descripcion="[A0..A7] == [B1S1, B1S2, B2S1, B2S2, B3S1, B3S2, B4S1, B4S2]"),
    OBDPid("5F", "01", "Requisitos de emisiones",        "Emission requirements",        "",     "Diagnóstico",  0,
           disparo_unico=True, descripcion="Codificación en bits. Tipo de normativa de emisiones del vehículo"),
    OBDPid("64", "01", "% torque motor (5 puntos)",      "Engine % torque data",         "%",    "Diagnóstico",  20000,
           formula="A-125 idle; B-125 pt1; C-125 pt2; D-125 pt3; E-125 pt4"),
    OBDPid("65", "01", "Entradas/salidas auxiliares",    "Auxiliary I/O supported",      "",     "Diagnóstico",  0,
           disparo_unico=True, descripcion="Codificación en bits. Entradas/salidas auxiliares implementadas"),
    OBDPid("7E", "01", "Estado área control PM NTE",     "PM NTE control area status",   "",     "Diagnóstico",  20000),
    OBDPid("7F", "01", "Tiempo motor en marcha (ext.)",  "Engine run time (extended)",   "s",    "Diagnóstico",  20000),
    OBDPid("81", "01", "Tiempo AECD #1-#5",              "AECD run time #1-#5",          "s",    "Diagnóstico",  20000),
    OBDPid("82", "01", "Tiempo AECD #6-#10",             "AECD run time #6-#10",         "s",    "Diagnóstico",  20000),
    OBDPid("89", "01", "Tiempo AECD #11-#15",            "AECD run time #11-#15",        "s",    "Diagnóstico",  20000),
    OBDPid("8A", "01", "Tiempo AECD #16-#20",            "AECD run time #16-#20",        "s",    "Diagnóstico",  20000),
    OBDPid("8B", "01", "Post-tratamiento diesel",        "Diesel aftertreatment",        "",     "Diagnóstico",  20000),
    OBDPid("8F", "01", "Sensores PM banco 1 y 2",        "PM sensors bank 1 & 2",        "",     "Diagnóstico",  10000),
    OBDPid("90", "01", "Info OBD vehículo (WWH-OBD)",    "Vehicle OBD system info",      "h",    "Diagnóstico",  0,
           disparo_unico=True, descripcion="Información del sistema OBD del vehículo según WWH-OBD"),
    OBDPid("91", "01", "Info OBD ECU (WWH-OBD)",         "ECU OBD system info",          "h",    "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("92", "01", "Sistema control combustible",    "Fuel system control",          "",     "Diagnóstico",  5000),
    OBDPid("93", "01", "Contadores OBD vehículo (WWH)",  "Vehicle OBD counters support", "h",    "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("94", "01", "Alerta NOx / sistema inducción", "NOx warning & inducement",     "h",    "Diagnóstico",  20000),
    OBDPid("95", "01", "PID reservada 0x95",             "Reserved 0x95",                "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("96", "01", "PID reservada 0x96",             "Reserved 0x96",                "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("97", "01", "PID reservada 0x97",             "Reserved 0x97",                "",     "Diagnóstico",  0,
           disparo_unico=True),
    OBDPid("9C", "01", "Datos sensor O2",                "O2 sensor data",               "",     "Diagnóstico",  1000),
    OBDPid("9F", "01", "Uso porcentual sistema combust.", "Fuel system percent use",      "",     "Diagnóstico",  5000),
    OBDPid("A1", "01", "Sensor NOx (corregido)",         "Corrected NOx sensor",         "ppm",  "Diagnóstico",  5000),
    OBDPid("A2", "01", "Tasa combustible cilindro",      "Cylinder fuel rate",           "mg/str","Diagnóstico", 2000,
           formula="(256A+B)/32"),
    OBDPid("A5", "01", "Dosificación DEF solicitada",    "DEF dosing requested",         "%",    "Diagnóstico",  5000,
           formula="B/2", descripcion="Dosificación solicitada del líquido de escape diésel (AdBlue)"),
    OBDPid("C3", "01", "Datos condición motor",          "Engine condition data",        "",     "Diagnóstico",  1000,
           descripcion="Muestra datos, incluye ID de la condición del motor y su velocidad"),
    OBDPid("C4", "01", "Estado ocioso / detención motor","Engine idle/stop request",     "",     "Diagnóstico",  5000,
           descripcion="B5: Solicitud estado ocioso. B6: Solicitud detener motor"),

    # ══ MODO 03 / 07 / 09 ══════════════════════════════════════════════════════
    OBDPid("00", "03", "DTC almacenados (Modo 03)",      "Stored DTCs",                 "",     "Vehículo / Modo 09", 0,
           can_id="7DF", disparo_unico=True,
           descripcion="Solicita códigos de fallo almacenados. Se envía una vez al arrancar."),
    OBDPid("00", "07", "DTC pendientes (Modo 07)",       "Pending DTCs",                "",     "Vehículo / Modo 09", 0,
           can_id="7DF", disparo_unico=True,
           descripcion="Solicita códigos de fallo pendientes. Se envía una vez al arrancar."),
    OBDPid("02", "09", "VIN — Nº de identificación",     "Vehicle Identification No.",  "",     "Vehículo / Modo 09", 0,
           can_id="7DF", disparo_unico=True,
           descripcion="Vehicle Identification Number (17 caracteres). Modo 09 info type 02."),
    OBDPid("04", "09", "CVN — Nº de calibración",        "Calibration Verification No.","",    "Vehículo / Modo 09", 0,
           can_id="7DF", disparo_unico=True,
           descripcion="Número de verificación de calibración de la ECU."),
]
# fmt: on


# ── Índice de búsqueda ─────────────────────────────────────────────────────────

_INDEX: dict[str, OBDPid] = {p.pid_full: p for p in OBD_PIDS}


def get_pid(pid_hex: str, mode: str = "01") -> Optional[OBDPid]:
    """Devuelve el OBDPid por PID hex y modo, o None."""
    return _INDEX.get(f"{mode}-{pid_hex.strip().upper()}")


def decode_datos(datos_hex: str, can_id: str = "") -> tuple[str, str]:
    """
    Decodifica el campo Datos del CSV y devuelve (nombre_es, unidad).
    Retorna ("Desconocido", "") si no puede decodificarse.
    """
    datos = datos_hex.strip().upper().replace(" ", "")
    if len(datos) < 4:
        return "Desconocido", ""

    mode = datos[2:4]

    if mode == "01" and len(datos) >= 6:
        pid = datos[4:6]
        entry = get_pid(pid, "01")
        if entry:
            return entry.nombre, entry.unidad
        return f"Modo 01 — PID 0x{pid}", ""

    if mode == "03":
        return "DTC almacenados (Modo 03)", ""
    if mode == "07":
        return "DTC pendientes (Modo 07)", ""
    if mode == "09" and len(datos) >= 6:
        info_type = datos[4:6]
        entry = get_pid(info_type, "09")
        if entry:
            return entry.nombre, ""
        return f"Modo 09 — tipo 0x{info_type}", ""
    if mode == "22" and len(datos) >= 8:
        param_id = datos[4:8]
        entry = get_pid(param_id, "22")
        if entry:
            return entry.nombre, entry.unidad
        return f"UDS ReadDataByID — 0x{param_id}", ""
    if mode == "19":
        return "UDS ReadDTCInformation (0x19)", ""

    return f"CAN ID={can_id} Datos={datos_hex}", ""
