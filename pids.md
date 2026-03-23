| PID(hex) | PID(dec) | Bytes de respuesta | Descripción | Valor mínimo | Valor máximo | Unidad | Fórmula |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **00** | 0 | 4 | PIDs implementados [01 - 20] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID 01..20] |
| **01** | 1 | 4 | Estado de los monitores de diagnóstico desde que se borraron los códigos de fallas DTC; incluye el estado de la luz indicadora de fallas, MIL, y la cantidad de códigos de fallas DTC | - | - | - | Codificación en bits. |
| **02** | 2 | 2 | Almacena los códigos de fallas de diagnóstico DTC de un evento | - | - | - | - |
| **03** | 3 | 2 | Estado del sistema de combustible | - | - | - | Codificación en bits. |
| **04** | 4 | 1 | Carga calculada del motor | 0 | 100 | % | A/2.55 |
| **05** | 5 | 1 | Temperatura del líquido de enfriamiento del motor | -40 | 215 | °C | A-40 |
| **06** | 6 | 1 | Ajuste de combustible a corto plazo—Banco 1 | -100 | 99.2 | % | A/1.28-100 |
| **07** | 7 | 1 | Ajuste de combustible a largo plazo—Banco 1 | - | - | - | - |
| **08** | 8 | 1 | Ajuste de combustible a corto plazo—Banco 2 | - | - | - | - |
| **09** | 9 | 1 | Ajuste de combustible a largo plazo—Banco 2 | - | - | - | - |
| **0A** | 10 | 1 | Presión del combustible | 0 | 765 | kPa | 3A |
| **0B** | 11 | 1 | Presión absoluta del colector de admisión | 0 | 255 | kPa | A |
| **0C** | 12 | 2 | RPM del motor | 0 | 16,383.75 | rpm | (256A+B)/4 |
| **0D** | 13 | 1 | Velocidad del vehículo | 0 | 255 | km/h | A |
| **0E** | 14 | 1 | Avance del tiempo | -64 | 63.5 | ° antes TDC | A/2-64 |
| **0F** | 15 | 1 | Temperatura del aire del colector de admisión | -40 | 215 | °C | A-40 |
| **10** | 16 | 2 | Velocidad del flujo del aire MAF | 0 | 655.35 | gr/sec | (256A+B)/100 |
| **11** | 17 | 1 | Posición del acelerador | 0 | 100 | % | A/2.55 |
| **12** | 18 | 1 | Estado del aire secundario controlado | - | - | - | Codificación en bits |
| **13** | 19 | 1 | Presencia de sensores de oxígeno (en 2 bancos) | - | - | - | [A0..A3] == Banco 1, sensores 1-4.<br>[A4..A7] == Banco 2... |
| **14** | 20 | 2 | Sensor de oxígeno 1<br>A: Voltaje<br>B: Ajuste de comb. corto plazo | 0<br>-100 | 1.275<br>99.2 | voltios<br>% | A: A/200<br>B: B/1.28-100<br>*(Si B==FF, no se usa en el cálculo)* |
| **15** | 21 | 2 | Sensor de oxígeno 2 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **16** | 22 | 2 | Sensor de oxígeno 3 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **17** | 23 | 2 | Sensor de oxígeno 4 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **18** | 24 | 2 | Sensor de oxígeno 5 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **19** | 25 | 2 | Sensor de oxígeno 6 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **1A** | 26 | 2 | Sensor de oxígeno 7 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **1B** | 27 | 2 | Sensor de oxígeno 8 (A: Voltaje, B: Ajuste) | - | - | - | - |
| **1C** | 28 | 1 | Estándar OBD implementado en este vehículo | - | - | - | Codificación en bits |
| **1D** | 29 | 1 | Sensores de oxígenos presentes en el banco 4 | - | - | - | Similar a PID 13, pero [A0..A7] == [B1S1, B1S2, B2S1, B2S2, B3S1, B3S2, B4S1, B4S2] |
| **1E** | 30 | 1 | Estado de las entradas auxiliares | - | - | - | A0 == Estado de PTO (1 == activo)<br>[A1..A7] sin uso |
| **1F** | 31 | 2 | Tiempo desde que se puso en marcha el motor | 0 | 65,535 | sec | 256A+B |
| **20** | 32 | 4 | PID implementados [21 - 40] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID 21..40] |
| **21** | 33 | 2 | Distancia recorrida con la luz indicadora de falla (MIL) encendida | 0 | 65,535 | km | 256A+B |
| **22** | 34 | 2 | Presión del tren de combustible, relativa al colector de vacío | 0 | 5177.265 | kPa | 0.079(256A+B) |
| **23** | 35 | 2 | Presión del medidor del tren de combustible (Diesel o inyección directa) | 0 | 655,350 | kPa | 10(256A+B) |
| **24** | 36 | 4 | Sensor de oxígeno 1<br>AB: Relación equiv. comb-aire<br>CD: Voltaje | 0<br>0 | < 2<br>< 8 | prop.<br>V | A, B: (256A+B)/32768<br>C, D: (256C+D)/8192 |
| **25** | 37 | 4 | Sensor de oxígeno 2 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **26** | 38 | 4 | Sensor de oxígeno 3 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **27** | 39 | 4 | Sensor de oxígeno 4 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **28** | 40 | 4 | Sensor de oxígeno 5 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **29** | 41 | 4 | Sensor de oxígeno 6 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **2A** | 42 | 4 | Sensor de oxígeno 7 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **2B** | 43 | 4 | Sensor de oxígeno 8 (AB: Relación, CD: Voltaje) | - | - | - | - |
| **2C** | 44 | 1 | EGR comandado | 0 | 100 | % | A/2.55 |
| **2D** | 45 | 1 | falla EGR | -100 | 99.2 | % | A/1.28-100 |
| **2E** | 46 | 1 | Purga evaporativa comandada | 0 | 100 | % | A/2.55 |
| **2F** | 47 | 1 | Nivel de entrada del tanque de combustible | 0 | 100 | % | A/2.55 |
| **30** | 48 | 1 | Cantidad de calentamientos desde que se borraron los fallas | 0 | 255 | cuenta | A |
| **31** | 49 | 2 | Distancia recorrida desde que se borraron los fallas | 0 | 65,535 | km | 256A+B |
| **32** | 50 | 2 | Presión de vapor del sistema evaporativo | -8,192 | 8191.75 | Pa | (256A + B) / 4 - 8192 |
| **33** | 51 | 1 | Presión barométrica absoluta | 0 | 255 | kPa | A |
| **34** | 52 | 4 | Sensor de oxígeno 1<br>AB: Relación equiv. comb-aire<br>CD: Actual | 0<br>-128 | < 2<br>< 128 | prop.<br>mA | A, B: (256A+B)/32768<br>C, D: C+D/256-128 |
| **35** | 53 | 4 | Sensor de oxígeno 2 (AB: Relación, CD: Actual) | - | - | - | - |
| **36** | 54 | 4 | Sensor de oxígeno 3 (AB: Relación, CD: Actual) | - | - | - | - |
| **37** | 55 | 4 | Sensor de oxígeno 4 (AB: Relación, CD: Actual) | - | - | - | - |
| **38** | 56 | 4 | Sensor de oxígeno 5 (AB: Relación, CD: Actual) | - | - | - | - |
| **39** | 57 | 4 | Sensor de oxígeno 6 (AB: Relación, CD: Actual) | - | - | - | - |
| **3A** | 58 | 4 | Sensor de oxígeno 7 (AB: Relación, CD: Actual) | - | - | - | - |
| **3B** | 59 | 4 | Sensor de oxígeno 8 (AB: Relación, CD: Actual) | - | - | - | - |
| **3C** | 60 | 2 | Temperatura del catalizador: Banco 1, Sensor 1 | -40 | 6,513.5 | °C | (256A+B)/10-40 |
| **3D** | 61 | 2 | Temperatura del catalizador: Banco 1, Sensor 1 | - | - | - | - |
| **3E** | 62 | 2 | Temperatura del catalizador: Banco 1, Sensor 2 | - | - | - | - |
| **3F** | 63 | 2 | Temperatura del catalizador: Banco 2, Sensor 2 | - | - | - | - |
| **40** | 64 | 4 | PID implementados [41 - 60] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID 41..60] |
| **41** | 65 | 4 | Estado de los monitores en este ciclo de manejo | - | - | - | Codificación en bits |
| **42** | 66 | 2 | Voltaje del módulo de control | 0 | 65.535 | V | (256A+B)/1000 |
| **43** | 67 | 2 | Valor absoluta de carga | 0 | 25,700 | % | (256A+B)/2.55 |
| **44** | 68 | 2 | Relación equivaliente comandada de combustible - aire | 0 | < 2 | prop. | (256A+B)/32768 |
| **45** | 69 | 1 | Posición relativa del acelerador | 0 | 100 | % | A/2.55 |
| **46** | 70 | 1 | Temperatura del aire ambiental | -40 | 215 | °C | A-40 |
| **47** | 71 | 1 | Posición absoluta del acelerador B | 0 | 100 | % | A/2.55 |
| **48** | 72 | 1 | Posición absoluta del acelerador C | - | - | - | - |
| **49** | 73 | 1 | Posición del pedal acelerador D | - | - | - | - |
| **4A** | 74 | 1 | Posición del pedal acelerador E | - | - | - | - |
| **4B** | 75 | 1 | Posición del pedal acelerador F | - | - | - | - |
| **4C** | 76 | 1 | Actuador comandando del acelerador | - | - | - | - |
| **4D** | 77 | 2 | Tiempo transcurrido con MIL encendido | 0 | 65,535 | min | 256A+B |
| **4E** | 78 | 2 | Tiempo transcurrido desde que se borraron los códigos de fallas | - | - | - | - |
| **4F** | 79 | 4 | Valor máximo de la relación de equivalencia de combustible - aire, voltaje y corriente del sensor de oxígeno, y presión absoluta del colector de entrada | 0, 0, 0, 0 | 255, 255, 255, 2550 | prop., V, mA, kPa | A, B, C, D*10 |
| **50** | 80 | 4 | Valor máximo de la velocidad de flujo de aire del sensor de flujo de aire masivo | 0 | 2550 | g/s | A*10 (B, C, y D reservados) |
| **51** | 81 | 1 | Tipo de combustible | - | - | - | Ver tabla de estándar |
| **52** | 82 | 1 | Porcentaje de combustible etanol | 0 | 100 | % | A/2.55 |
| **53** | 83 | 2 | Presión absoluta del vapor del sistema de evaporación | 0 | 327.675 | kPa | (256A+B)/200 |
| **54** | 84 | 2 | Presión del vapor del sistema de evaporación | -32,767 | 32,768 | Pa | 256A+B-32767 |
| **55** | 85 | 2 | Ajuste del sensor de oxígeno secundario de plazo corto.<br>A: banco 1<br>B: banco 3 | -100 | 99.2 | % | A: A/1.28-100<br>B: B/1.28-100 |
| **56** | 86 | 2 | Ajuste del sensor de oxígeno secundario de plazo largo (A: banco 1, B: banco 3) | - | - | - | - |
| **57** | 87 | 2 | Ajuste del sensor de oxígeno secundario de plazo corto (A: banco 2, B: banco 4) | - | - | - | - |
| **58** | 88 | 2 | Ajuste del sensor de oxígeno secundario de plazo largo (A: banco 2, B: banco 4) | - | - | - | - |
| **59** | 89 | 2 | Presión absoluta del tren de combustible | 0 | 655,350 | kPa | 10(256A+B) |
| **5A** | 90 | 1 | Posición relativa del pedal del acelerador | 0 | 100 | % | A/2.55 |
| **5B** | 91 | 1 | Tiempo de vida del banco de baterías híbridas | 0 | 100 | % | A/2.55 |
| **5C** | 92 | 1 | Temperatura del aceite del motor | -40 | 210 | °C | A-40 |
| **5D** | 93 | 2 | Sincronización de la inyección de combustible | -210.00 | 301.992 | ° | ((256A+B)/128)-210 |
| **5E** | 94 | 2 | Velocidad del combustible del motor | 0 | 3276.75 | L/h | (256A+B)/20 |
| **5F** | 95 | 1 | Requisitos de emisiones para los que el vehículo fue diseñado | - | - | - | Codificación en bits |
| **60** | 96 | 4 | PID implementados [61 - 80] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID 61..80] |
| **61** | 97 | 1 | Porcentaje de torque solicitado por el conductor | -125 | 125 | % | A-125 |
| **62** | 98 | 1 | Porcentaje de torque actual del motor | -125 | 125 | % | A-125 |
| **63** | 99 | 2 | Torque de referencia del motor | 0 | 65,535 | Nm | 256A+B |
| **64** | 100 | 5 | Datos del porcentaje de torque del motor | -125 | 125 | % | A-125 Ocioso<br>B-125 Motor punto 1<br>C-125 Motor punto 2<br>D-125 Motor punto 3<br>E-125 Motor punto 4 |
| **65** | 101 | 2 | Entrada / salida auxiliar implementada | - | - | - | Codificación en bits |
| **66** | 102 | 5 | Sensor de flujo de aire masivo | - | - | - | - |
| **67** | 103 | 3 | Temperatura del enfriador del motor | - | - | - | - |
| **68** | 104 | 7 | Sensor de temperatura de aire de entrada | - | - | - | - |
| **69** | 105 | 7 | EGR comandado y falla de EGR | - | - | - | - |
| **6A** | 106 | 5 | Control comandado del flujo de aire de entrada de Diesel y posición relativa de la entrada | - | - | - | - |
| **6B** | 107 | 5 | Temperatura de recirculación del gas del escape | - | - | - | - |
| **6C** | 108 | 5 | Control comandado del actuador del acelerador y posición relativa del acelerador | - | - | - | - |
| **6D** | 109 | 6 | Sistema de control de presión del combustible | - | - | - | - |
| **6E** | 110 | 5 | Sistema de control de presión de inyección | - | - | - | - |
| **6F** | 111 | 3 | Presión de entrada del compresor del turbocargador | - | - | - | - |
| **70** | 112 | 9 | Control de presión de aumento | - | - | - | - |
| **71** | 113 | 5 | Control del turbo de geometría variable (VGT) | - | - | - | - |
| **72** | 114 | 5 | Control de la compuerta de desperdicio | - | - | - | - |
| **73** | 115 | 5 | Presión del escape | - | - | - | - |
| **74** | 116 | 5 | RPM del turbocargador | - | - | - | - |
| **75** | 117 | 7 | Temperatura del turbocargador | - | - | - | - |
| **76** | 118 | 7 | Temperatura del turbocargador | - | - | - | - |
| **77** | 119 | 5 | Temperatura del enfriador del aire de carga (CACT) | - | - | - | - |
| **78** | 120 | 9 | Temperatura del gas del escape (EGT) Banco 1 | - | - | - | PID especial |
| **79** | 121 | 9 | Temperatura del gas del escape (EGT) Banco 2 | - | - | - | PID especial |
| **7A** | 122 | 7 | Filtro de partículas Diesel (DPF) | - | - | - | - |
| **7B** | 123 | 7 | Filtro de partículas Diesel (DPF) | - | - | - | - |
| **7C** | 124 | 9 | Temperatura del filtro de partículas Diesel (DPF) | - | - | - | - |
| **7D** | 125 | 1 | Estado del área de control NOx NTE | - | - | - | - |
| **7E** | 126 | 1 | Estado del área de control PM NTE | - | - | - | - |
| **7F** | 127 | 13 | Tiempo que el motor ha estado en marcha | - | - | - | - |
| **80** | 128 | 4 | PID implementados [81 - A0] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID 81..A0] |
| **81** | 129 | 21 | Tiempo de marcha del motor para el disp. auxiliar de control de emisiones (AECD) | - | - | - | - |
| **82** | 130 | 21 | Tiempo de marcha del motor para el disp. auxiliar de control de emisiones (AECD) | - | - | - | - |
| **83** | 131 | 5 | Sensor de NOx | - | - | - | - |
| **84** | 132 | 1 | Temperatura de superficie del colector | - | - | - | - |
| **85** | 133 | 10 | Sistema reactivo NOx | - | - | - | - |
| **86** | 134 | 5 | Sensor de partículas (PM) | - | - | - | - |
| **87** | 135 | 5 | Presión absoluta del colector de admisión | - | - | - | - |
| **88** | 136 | 13 | Sistema de inducción SCR (reducción catalítica selectiva) | - | - | - | - |
| **89** | 137 | 41 | Tiempo de ejecución para AECD #11-#15 | - | - | - | - |
| **8A** | 138 | 41 | Tiempo de ejecución para AECD #16-#20 | - | - | - | - |
| **8B** | 139 | 7 | Post-tratamiento de diesel | - | - | - | - |
| **8C** | 140 | 17 | Sensor de O2 (amplio rango) | - | - | - | - |
| **8D** | 141 | 1 | Posición acelerador G | 0 | 100 | % | - |
| **8E** | 142 | 1 | Fricción del motor - Porcentaje de par | -125 | 130 | % | A-125 |
| **8F** | 143 | 7 | Banco de sensores PM 1 y 2 | - | - | - | - |
| **90** | 144 | 3 | Información del sistema OBD (vehículo) según WWH-OBD | - | - | h | - |
| **91** | 145 | 5 | Información del sistema OBD (ECU) según WWH-OBD | - | - | h | - |
| **92** | 146 | 2 | Sistema de control de combustible | - | - | - | - |
| **93** | 147 | 3 | Soporte de contadores de OBD del vehículo según WWH-OBD | - | - | h | - |
| **94** | 148 | 12 | Alerta por NOx y sistema de inducción | - | - | h | - |
| **95** | 149 | - | Reservada | - | - | - | - |
| **96** | 150 | - | Reservada | - | - | - | - |
| **97** | 151 | - | Reservada | - | - | - | - |
| **98** | 152 | 9 | Sensor de temperatura de gases de escape - Banco 1 | - | - | - | - |
| **99** | 153 | 9 | Sensor de temperatura de gases de escape - Banco 2 | - | - | - | - |
| **9A** | 154 | 6 | Datos del sistema de vehículo híbrido/eléctrico, batería, voltaje | - | - | - | - |
| **9B** | 155 | 4 | Datos del sensor de líquido de escape diésel | - | - | - | - |
| **9C** | 156 | 17 | Datos del sensor de O2 | - | - | - | - |
| **9D** | 157 | 4 | Tasa de combustible del motor | - | - | g/s | - |
| **9E** | 158 | 2 | Tasa de flujo de escape del motor | - | - | kg/h | - |
| **9F** | 159 | 9 | Uso porcentual del sistema de combustible | - | - | - | - |
| **A0** | 160 | 4 | PID implementados [A1 - C0] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID A1..C0] |
| **A1** | 161 | 9 | Datos corregidos del sensor de NOx | - | - | ppm | - |
| **A2** | 162 | 2 | Tasa de combustible del cilindro | 0 | 2047.96875 | mg/carrera | (256A+B)/32 |
| **A3** | 163 | 9 | Presión de vapor del sistema de evaporación | - | - | Pa | - |
| **A4** | 164 | 4 | Relación de transmisión real | 0 | 65535 | ratio | [A1]==implementado<br>(256C+D)/1000 |
| **A5** | 165 | 4 | Dosificación solicitada del líquido de escape diésel | 0 | 127.5 | % | [A0]==1:implementado; 0:no impl.<br>B/2 |
| **C0** | 192 | 4 | PID implementados [C1 - E0] | - | - | - | Cada bit indica si los siguientes 32 PID están implementados (1) o no (0): [A7..D0] == [PID C1..E0] |
| **C3** | 195 | ? | Muestra datos, incluye ID de la condición del motor y su velocidad | ? | ? | ? | ? |
| **C4** | 196 | ? | B5: Solicitud de poner el motor en estado ocioso<br>B6: Solicitud de detener el motor | ? | ? | ? | ? |