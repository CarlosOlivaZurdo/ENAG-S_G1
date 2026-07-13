# Documentación técnica — Comparador Regulatorio de Calidad de Gas

*Gas natural · biometano · hidrógeno. Documento único de referencia: consolida toda la
explicación del sistema —qué hace, cómo está construido y cómo funciona cada componente—.
Cotejado con el código y con los datos reales — versión de ontología **3.2.0**,
revisión **2026-07**. Los diagramas de arquitectura y de la ontología se
conservan como ficheros de imagen independientes y se incluyen también en este documento.*

## Índice

1. Introducción y objetivo
2. Visión general de la arquitectura
3. Principio de diseño: cero cifras inventadas
4. Las tres capas de datos
5. La ontología (base de conocimiento)
6. Los 10 parámetros de calidad
7. Las 21 jurisdicciones y sus normas
8. El servidor de aplicación (FastAPI) frente a la API de OpenAI
9. El motor determinista
10. La normalización de condiciones (ISO 13443)
11. La capa de inteligencia artificial (LLM)
12. La recuperación documental (RAG)
13. El chat y el historial persistente
14. Estado real de los datos
15. Ampliación del alcance: biometano e hidrógeno
16. Metodología de construcción y verificación
17. Garantías del sistema
18. Stack tecnológico y despliegue
19. Diseño ideal frente a implementación real
20. Alcance y limitaciones del prototipo
21. Glosario

---

## Documentos del proyecto

Conjunto de entregables (carpeta `docs/`). Cada uno cumple un papel distinto; **este documento es
la referencia técnica y de funcionamiento completa** (el "manual"), y basta por sí solo para
explicar el sistema.

| Documento | Formato | Para qué sirve |
|---|---|---|
| **Documentacion_Comparador_Gas** (este) | MD · PDF | Referencia técnica y de funcionamiento completa. |
| **Presentacion_15min** · **Presentacion_7min** | PDF · PPTX | Diapositivas de la exposición (completa y ejecutiva), con notas del ponente. |
| **Guion_Presentacion_15min** · **_7min** | MD | El texto a decir, diapositiva a diapositiva y con tiempos. |
| **Prospeccion_Normativa_Hidrogeno** | MD | Marco regulatorio del hidrógeno verificado + hoja de ruta de escalado. |
| **Estudio_Terminologia_Biometano** | MD | Justificación (medida) de una capa de búsqueda semántica. |
| **Arquitectura_Esquema_Cajas** · **Ontologia_Estructura** | PNG · SVG | Los dos diagramas (embebidos en este documento). |

Fuera de `docs/`: `LEER_PRIMERO.txt` (guía rápida de arranque) y `README.md` (especificación de
diseño del proyecto).

---

## 1. Introducción y objetivo

Cada país regula la calidad admisible del gas natural mediante su propia normativa: poder
calorífico, índice de Wobbe, contenido de azufre, de CO₂, puntos de rocío, etc. Esas
especificaciones están dispersas en boletines oficiales distintos, en varios idiomas y con
unidades y condiciones de referencia diferentes. Comparar dos marcos regulatorios de forma
manual es laborioso y propenso a error.

El **Comparador** es un asistente que compara esa calidad regulatoria entre **21
jurisdicciones** y **10 parámetros**, y responde en lenguaje natural. Su principio
de diseño es la **ausencia de cifras no verificadas**: el sistema no genera ningún valor por
estimación; todas las cifras proceden de una base contrastada frente a la normativa oficial y
se presentan con su cita correspondiente.

El alcance inicial —el gas natural— se ha **ampliado a biometano e hidrógeno** como una capa
aditiva que no altera nada de lo anterior (ver §15). Salvo indicación en contra, las secciones
1 a 14 describen el sistema tomando el gas natural como referencia; la mecánica (motor, ontología,
normalización, IA y RAG) es común a los tres gases.

---

## 2. Visión general de la arquitectura

El sistema se estructura en cuatro componentes con responsabilidades bien delimitadas: una
**interfaz web**, un **servidor de aplicación** (el núcleo), una **base de conocimiento** (la
ontología) y un **servicio de inteligencia artificial** externo, invocado de forma acotada.

![Arquitectura del sistema](Arquitectura_Esquema_Cajas.png)

**Recorrido de una consulta:** la interfaz web (`index.html`) envía la pregunta al servidor
(`api.py`, FastAPI). Allí, un **router determinista** decide cómo resolverla: si es una
consulta cuantitativa, la resuelve el propio código leyendo la ontología; si es de texto
abierto, la deriva al modelo de lenguaje (OpenAI), que a su vez puede consultar la ontología
y buscar en los documentos (RAG). El servidor expone varios servicios (endpoints): interfaz,
chat (con detección de **interconexiones/cadenas**), comparación puntual, matriz comparativa,
**validación de un gas concreto** y **exportación de informes** (Excel/PDF). La arquitectura de
cuatro componentes no cambia con estas funciones: son endpoints y vistas nuevos dentro de las
mismas cajas. La ampliación a **biometano** e **hidrógeno** (§15) tampoco cambia la arquitectura:
se añade un parámetro `tipo_gas` que enruta a la sección de ontología del gas elegido, con
`gas_natural` por defecto para no alterar el comportamiento existente.

---

## 3. Principio de diseño: cero cifras inventadas

El sistema combina dos mundos separados a propósito:

- **Mundo determinista** (código + ontología): la **única** fuente autorizada de cifras,
  límites, conversiones y comparaciones. Nunca improvisa un número.
- **Mundo conversacional** (LLM): interpreta la pregunta y **redacta** la respuesta, pero
  tiene prohibido generar cifras — las obtiene llamando a herramientas deterministas.

La regla está implementada como **determinista-primero, IA-como-respaldo**: las preguntas
estructuradas se resuelven con código (sin riesgo de alucinación); solo las abiertas pasan al
LLM, obligado a apoyarse en herramientas y documentos oficiales.

---

## 4. Las tres capas de datos

Es habitual asumir que existe una única base de datos. No es el caso: la información se
organiza en **tres capas** con funciones distintas.

| Capa | Contenido | Función |
|---|---|---|
| **1. Documentos oficiales** | Los PDF de las normas (BOE, ERSE, DVGW, Fluxys, National Grid…) | Fuente primaria y última de verdad. |
| **2. Ontología** | Fichero estructurado con las **210 cifras** extraídas de esos PDF | Repositorio del que salen las respuestas. |
| **3. Índice documental (RAG)** | Índice del **texto** de los PDF, segmentado en fragmentos con solape (continuos, cruzan el salto de página) | Buscador interno, para consultas abiertas. |

Las **cifras** residen en la capa 2 (la ontología), y cada una referencia su documento
oficial de la capa 1. La capa 3 **no almacena ninguna cifra**: es un índice de búsqueda sobre
el texto de los documentos. Los documentos (~22 PDF) se guardan **localmente** en `data/raw`
para no depender de la disponibilidad de sitios web externos.

---

## 5. La ontología (base de conocimiento)

**Archivo:** `data/ontologia/ontologia_enagas.yaml`

La ontología es el elemento central del sistema: la **extracción verificada** de los PDF
oficiales, en un formato estructurado y legible. El motor determinista lee de aquí; el LLM
nunca calcula ni inventa valores.

### 5.1. Estructura

La ontología se organiza así:

| Clave | Contenido |
|---|---|
| `ontologia.fuentes_normativas` | El **catálogo de las 39 normas** oficiales: `id`, `nombre`, `organismo`, `publicacion`, `url` (cita) y `pdf` (copia local). |
| `ontologia.tipos_gas` | El **registro de los 3 tipos de gas** (gas natural, biometano, hidrógeno) y a qué sección de parámetros apunta cada uno. |
| `parametros` | **Gas natural**: los **10 parámetros**, cada uno con un bloque `limites:` con una entrada **por país** (×21). |
| `parametros_biometano` | **Biometano**: 12 parámetros, con `limites:` por jurisdicción (España, Portugal, Francia, UE). |
| `parametros_hidrogeno` | **Hidrógeno**: 18 parámetros, con `limites:` por jurisdicción (dominio de red y de producto). |

Las tres secciones de parámetros comparten **exactamente el mismo esquema** (ver §5.2); solo
cambian el conjunto de jurisdicciones y las fuentes. El detalle del biometano y del hidrógeno
está en la §15.

![Estructura de la ontología](Ontologia_Estructura.png)

### 5.2. Anatomía de un valor

Cada límite (por parámetro y país) **no es solo un número**: guarda todo su contexto
normativo. Ejemplo real del O₂ de España, con cada campo anotado:

```yaml
      ES:
        fuente: ORDEN_TED_181_2025
        articulo: "Tabla 3, apartado 2.5.2.1 (pág. 27)"
        tipo_limite: maximo
        valor: 0.01
        unidad: pct_mol
        expresion_original: "O2: – / 0,01 % mol"
        condiciones_referencia: { temperatura_volumen_C: 0, presion_bar: 1.01325 }
        estado_verificacion: VERIFICADO
```

- `fuente` — de qué norma sale (enlaza al catálogo de fuentes).
- `articulo` — dónde exactamente (tabla, apartado, página).
- `tipo_limite` — máximo, mínimo o rango.
- `valor` (o `valor_min`/`valor_max`) — la cifra.
- `unidad` — la unidad de la cifra.
- `expresion_original` — el **texto literal** de la norma.
- `condiciones_referencia` — temperatura y presión de referencia.
- `estado_verificacion` — la garantía frente a la invención de datos.

### 5.3. Estados de verificación

- **`VERIFICADO`** — cifra contrastada **verbatim** contra su fuente oficial (176 valores).
- **`NO_VERIFICABLE_SIN_FUENTE`** — la norma citada **no fija** esa cifra → **no se inventa**,
  se marca como hueco honesto y se explica (34 valores).

No existe un estado intermedio: un valor consta en la norma, o se declara que la norma no lo
establece. *(Ejemplo: en Dinamarca, los límites de O₂/CO₂ de la norma corresponden al biogás
de distribución, no al gas natural de transporte; por eso, para gas natural, se marcaron como
no verificable en lugar de trasladar un valor de otro contexto.)*

### 5.4. Cómo se usa (el recorrido de un dato)

La ontología es la **única** fuente de las cifras:

1. Llega una consulta (p. ej. «¿límite de O₂ en España?»).
2. El servidor llama a `fuente_oficial.consultar(parámetro, país)`, que **lee la ontología**.
3. Devuelve el valor **con su cita** (0,01 % · Orden TED/181/2025, Tabla 3).
4. Si hay que comparar con otro país, `conversor_unidades` lo **normaliza** (ISO 13443, §10).
5. Se construye la respuesta.

El modelo de IA **nunca** lee cifras de otro sitio: invoca herramientas que leen la ontología.
De ella se alimentan por igual el **chat**, la **comparativa** y la **matriz**.

### 5.5. Por qué una ontología y no una base de datos relacional

El volumen de datos es reducido (210 registros) pero con abundante matiz
por celda. Un fichero estructurado en formato YAML (legible por una persona) resulta más
**auditable** y **trazable** que una base de datos relacional, y se versiona en el control de
cambios (git) junto con el código. Para esta escala, una base de datos añadiría complejidad
sin beneficio.

---

## 6. Los 10 parámetros de calidad

| # | Parámetro | Qué mide | Unidad (ES) | Límite en España |
|---|---|---|---|---|
| 1 | **Índice de Wobbe** | Mide la **intercambiabilidad** del gas (aporte calorífico a través de un quemador a presión dada). Criterio clave para saber si dos gases son intercambiables sin reajustar los equipos. | kWh/m³ | 13,403 – 16,058 kWh/m³ |
| 2 | **PCS (poder calorífico superior)** | **Energía** liberada por la combustión completa de 1 m³ de gas (con el agua de los humos condensada). Es lo que se factura. | kWh/m³ | 10,26 – 13,26 kWh/m³ |
| 3 | **Densidad relativa** | Densidad del gas dividida por la del aire (adimensional). Interviene en el Índice de Wobbe. | — | 0,555 – 0,7 |
| 4 | **Azufre total (S)** | **Azufre total** (todos los compuestos de azufre). Límite ambiental y de corrosión. | mg/m³ | ≤ 50 mg/m³ |
| 5 | **H₂S + COS** | Sulfuro de hidrógeno + sulfuro de carbonilo, **expresados como azufre**. Corrosión y toxicidad. | mg/m³ | ≤ 15 mg/m³ |
| 6 | **Mercaptanos (RSH)** | **Mercaptanos** (azufre mercaptánico). Son los odorizantes; se limitan aparte del H₂S. | mg/m³ | ≤ 17 mg/m³ |
| 7 | **O₂ (oxígeno)** | **Oxígeno**. Favorece corrosión y es incompatible con almacenamientos subterráneos. | % mol | ≤ 0,01 % mol |
| 8 | **CO₂** | **Dióxido de carbono**. Rebaja el poder calorífico y es corrosivo con humedad. | % mol | ≤ 2,5 % mol |
| 9 | **Punto de rocío del agua** | **Punto de rocío del agua**: temperatura a la que condensaría el agua del gas. Evita agua líquida en la red. | °C | ≤ 2 °C |
| 10 | **Punto de rocío de hidrocarburos** | **Punto de rocío de hidrocarburos**: temperatura a la que condensarían los hidrocarburos pesados. | °C | ≤ 5 °C |

> La "unidad (ES)" es la que usa la normativa española; cuando otro país usa otra unidad o
> condiciones, el sistema **normaliza** antes de comparar (ver §10).

---

## 7. Las 21 jurisdicciones y sus normas

Cada país aporta sus límites desde su **fuente oficial**. España es siempre la **base de
referencia** de la comparación. «Cond.» = temperatura de combustión / volumen (°C).

| País | Cód. | Norma de referencia | Cond. |
|---|---|---|---|
| España *(base)* | ES | Orden TED/181/2025 | 0/0 |
| Portugal | PT | Regulamento n.º 826/2023 | 25/0 |
| Francia | FR | GRTgaz | 0/0 |
| Italia | IT | Qualità del gas naturale | 15/15 |
| Alemania | DE | DVGW Arbeitsblatt G 260 (2021) | 25/0 |
| Países Bajos | NL | Energieregeling (Países Bajos), art. 3.16 «invoed- en afleverspe… | 25/0 |
| Bélgica | BE | Fluxys Belgium | 25/0 |
| Noruega | NOR | Gassco | 25/0 |
| Polonia | PL | Rozporządzenie w sprawie szczegółowych warunków funkcjonowania s… | 25/0 |
| Dinamarca | DK | Bekendtgørelse om gaskvalitet (BEK nr 230 af 21/03/2018) | 25/0 |
| Hungría | HU | 19/2009. (I. 30.) Korm. rendelet, 11. számú melléklet «A földgáz… | 25/0 |
| Austria | AT | Gas Connect Austria | 25/0 |
| Suiza | CH | SVGW/SSIGE Richtlinie G18 «Gasbeschaffenheit» | 25/0 |
| Chequia | CZ | Řád provozovatele přepravní soustavy (Network Code de NET4GAS), … | 15/15 |
| Grecia | GR | Κώδικας Διαχείρισης ΕΣΦΑ (DESFA Network Code), ΠΑΡΑΡΤΗΜΑ I «Προδ… | 25/0 |
| Irlanda | IE | Gas Networks Ireland | 15/15 |
| Rumanía | RO | Regulament de măsurare a gazelor naturale, Anexa nr. 5 «Cerințe … | 15/15 |
| Eslovaquia | SK | Technické podmienky de eustream, a.s. (PPS), Príloha č. 1 «Kvali… | 25/20 |
| Turquía | TR | BOTAŞ Şebeke İşleyiş Düzenlemelerine İlişkin Esaslar (ŞİD), EK-1… | 15/15 |
| Reino Unido | GB | The Gas Safety (Management) Regulations 1996 (GS(M)R), Schedule … | 15/15 |
| UE | UE | EN 16726:2025 | 15/15 |

---

## 8. El servidor de aplicación (FastAPI) frente a la API de OpenAI

Conviene distinguir dos componentes que a veces se confunden por su nombre, ya que ambos
incluyen el término «API».

| | **FastAPI** | **API de OpenAI** |
|---|---|---|
| Naturaleza | Framework para **desarrollar nuestro servidor** | **Servicio externo** que consumimos |
| Titularidad | Propia (es nuestro backend) | De OpenAI (somos cliente) |
| Coste | Sin coste (código abierto) | De pago, por uso |
| Papel | Núcleo de la aplicación | Proveedor auxiliar, invocado de forma controlada |

El servidor de aplicación es imprescindible porque: (1) atiende la interfaz web y las
peticiones; (2) accede a la base de conocimiento y recupera el dato exacto —el modelo no
dispone de esos datos—; (3) ejecuta los cálculos exactos de forma determinista; (4) decide,
para cada consulta, si la resuelve directamente o si requiere la IA (en la mayoría de casos
no la usa); y (5) custodia las credenciales del servicio externo, que nunca se exponen en el
navegador.

---

## 9. El motor determinista

**`api.py` → `_validate_measurement_gate`.** Toda consulta pasa primero por este componente de
enrutado. «Determinista» significa que, ante la misma consulta, produce siempre la misma
respuesta, calculada por código, sin aleatoriedad ni IA.

Distingue dos tipos de consulta:

- **Cuantitativas** (un límite, una comprobación de cumplimiento, una comparación, una
  conversión): las resuelve el código leyendo la ontología. Sin IA, sin posibilidad de generar
  un valor incorrecto.
- **De texto abierto** («¿en qué consiste el índice de Wobbe?»): se derivan al servicio de IA.

Resuelve **sin IA** siete tipos de intención: (1) valor de un límite; (2) comprobación de
cumplimiento de un valor medido; (3) norma de la que procede; (4) intercambiabilidad entre
gases; (5) comparación de restrictividad frente a España; (6) comparación directa
España-país; (7) conversión a las condiciones de referencia españolas.

---

## 10. La normalización de condiciones (ISO 13443)

Cada país expresa sus límites en unidades y condiciones de referencia distintas: unos en
kWh/m³, otros en MJ/m³; unos referidos a 0 °C, otros a 15 o a 25 °C. Comparar los valores en
bruto sería metodológicamente incorrecto.

Para una comparación rigurosa, todos los valores se llevan a la **base de referencia española**
aplicando los **factores literales de la Tabla A.1 de la norma ISO 13443** (que viven en
`conversor_unidades._TABLA_A1`):

| A condiciones de España (0/0) | PCS | Wobbe |
|---|---|---|
| **25/0 → 0/0** (Portugal, Alemania, P. Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Grecia) | 1,0026 | 1,0026 |
| **15/15 → 0/0** (Italia, UE, Chequia, Irlanda, Rumanía, Turquía, Reino Unido) | 1,0570 | 1,0569 |
| **25/20 → 0/0** (Eslovaquia — par no tabulado, ecuaciones del Anexo B) | ≈1,076 | ≈1,076 |
| **0/0 → 0/0** (España, Francia) | ×1 (identidad) | ×1 |

Estos factores no se estiman: se toman literalmente de la norma y están implementados y
verificados. Además de kWh/m³ y MJ/m³, el conversor admite **kcal/m³** (Turquía y Rumanía).
Las concentraciones másicas (mg/m³) referidas a un volumen a T ≠ 0 °C (p. ej. Italia a 15 °C)
se normalizan con el factor de gas ideal (273,15+T)/273,15. El % mol, lo adimensional y los
puntos de rocío no dependen de la temperatura del volumen. Los valores **derivados** de estos
cálculos se muestran con 2 decimales (sin falsa precisión); los originales, con su precisión
de origen.

---

## 11. La capa de inteligencia artificial (LLM)

**`api.py` → `responder_con_llm`.** El LLM es la **capa de lenguaje**: interpreta la pregunta y
**redacta** la respuesta, pero **nunca genera cifras**.

- **Modelo:** OpenAI **GPT-4o-mini** (configurable con `OPENAI_MODEL`), con **temperatura 0**
  (máxima previsibilidad), y un bucle de hasta 5 iteraciones de llamadas a herramientas.
- **Herramientas** que puede invocar (function calling): `consultar` (lee la ontología),
  `evaluar_cumplimiento`, `convertir_unidades`, `convertir_condiciones_referencia` /
  `convertir_condiciones_iso13443`, y **`buscar_pdfs`** (RAG).
- **Salvaguardas:** el `SYSTEM_PROMPT` le **prohíbe inventar cifras**, le obliga a **citar** y
  limita su ámbito a la calidad del gas.
- **Tolerancia a fallos:** si OpenAI no está disponible (sin clave, red o límite), el sistema
  **conmuta automáticamente al motor determinista**. El chat nunca devuelve un error.

**Ejemplo (pregunta abierta):** «Explícame la diferencia de azufre entre España y Alemania».
El router no la reconoce como estructurada → la pasa al LLM → el LLM llama a `consultar` para
el azufre de ES y de DE → el backend **lee la ontología** y devuelve los números con su cita →
el LLM **redacta** la explicación con esos valores, sin inventar nada.

---

## 12. La recuperación documental (RAG)

**`agente_pdf.py` + `data/pdf_database.sqlite3`.** El RAG permite que, en las consultas de texto
abierto, la respuesta se fundamente en los documentos oficiales.

1. **Indexación:** al arrancar, el sistema lee los PDF de `data/raw/`, extrae el texto con
   `pdfplumber`, lo **trocea en fragmentos con solape mediante una ventana deslizante sobre el
   documento completo** (no por página) y lo guarda en una base **SQLite** que actúa de índice.
   Que la ventana sea continua garantiza que **una respuesta partida entre dos páginas quede
   entera dentro de un mismo fragmento** y, por tanto, sea recuperable. La indexación es
   **incremental**: solo se reprocesa un documento nuevo o modificado, por lo que el arranque
   es casi inmediato.
2. **Recuperación:** `buscar_pdfs(query)` realiza una **búsqueda léxica** (SQLite `LIKE` sobre el
   texto normalizado) y devuelve los fragmentos más relevantes con archivo, página y snippet.

Es una búsqueda **léxica** (por palabra clave), **no vectorial** (sin embeddings ni similitud
semántica). Es un enfoque más simple, suficiente para este caso y **plenamente reproducible**,
al no depender de servicios externos para localizar la información.

---

## 13. El chat y el historial persistente

- **Frontend (`index.html`):** SPA en JavaScript puro; render de Markdown con `marked` +
  saneado con `DOMPurify`. Cinco secciones: *Consulta libre gas natural* (chat), *Comparativa
  gas natural* (puntual + matriz), *Analizar gas natural* (validación de un gas concreto) y las
  dos de la ampliación —*Comparativa biometano* y *Comparativa hidrógeno*— con la misma
  presentación (ver §15).
- **Analizar gas (`/api/analizar-gas`):** el usuario introduce la composición/medidas de un gas
  (CO₂, O₂, H₂S, azufre, PCS, Wobbe, rocíos…) y el sistema responde, país a país, si **cumple /
  está en zona de alerta / no cumple / no tiene límite**, con la cita oficial de cada límite. La
  *zona de alerta* marca los valores que cumplen pero quedan a menos del 10 % del límite. Reutiliza
  el motor determinista (unidad + condiciones ISO 13443); no inventa PCS/Wobbe a partir de la
  composición (los componentes no normativos, como el CH₄, se muestran como informativos).
- **Exportación de informes (`/api/exportar-matriz`):** desde la matriz se puede seleccionar un
  subconjunto de jurisdicciones y descargar la comparativa completa (países × 10 parámetros) en
  **Excel** (`openpyxl`) o **PDF** (`xhtml2pdf`), con las celdas coloreadas por nivel. Serializa
  los mismos datos que la matriz de la web (no genera cifras nuevas).
- **Interconexión / cadena (por el chat):** si el usuario pregunta por una interconexión (p. ej.
  «interconexión España-Francia-Alemania»), el sistema detecta la cadena de países y calcula, por
  parámetro, la **intersección** de los límites de todos ellos (normalizados a España, ISO 13443):
  el rango de gas que puede atravesar toda la cadena, **qué país impone la restricción más estricta**
  (cuello de botella) y una **alerta** si para algún parámetro no queda rango común (incompatibilidad).
  Es determinista (intercepta antes del LLM) y reutiliza el motor comparativo (`_rango_en_condiciones_es`).
- **Historial persistente:** cada turno (pregunta + respuesta) se guarda por sesión en el
  navegador (`localStorage`) y se **restaura al recargar la página o tras reiniciar el
  servidor**, de modo que el usuario no pierde sus consultas. «Nueva consulta» abre una sesión
  limpia.
- **Contexto en el backend:** `_registrar_turno` guarda **todos** los turnos (deterministas y
  de IA, acotados a los últimos 40 mensajes por sesión), de forma que el asistente conserva el
  contexto para las preguntas de seguimiento.

---

## 14. Estado real de los datos

Cobertura actual **del gas natural**: **176 celdas VERIFICADO**, **34 NO_VERIFICABLE**,
0 pendientes, sobre 210 celdas (10 parámetros × 21
jurisdicciones). Las 210 celdas resuelven por la ruta real de la aplicación.
*(La cobertura de biometano e hidrógeno se detalla en la §15.)*

**✓** = verificado verbatim · **○** = la norma no fija ese parámetro (hueco honesto)

| Parámetro | ES | PT | FR | IT | DE | NL | BE | NOR | PL | DK | HU | AT | CH | CZ | GR | IE | RO | SK | TR | GB | UE |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Índice de Wobbe | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ |
| PCS | ✓ | ○ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ○ |
| Densidad relativa | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ○ | ○ | ○ | ✓ | ○ | ○ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ○ | ✓ | ✓ |
| Azufre total | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| H₂S + COS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Mercaptanos | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ○ | ○ | ○ | ✓ | ✓ | ○ | ✓ |
| O₂ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CO₂ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ○ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Punto de rocío del agua | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Punto de rocío de hidrocarburos | ✓ | ○ | ✓ | ✓ | ✓ | ○ | ○ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Los huecos **no** son errores: son parámetros que **la norma de ese país no fija
numéricamente** (y por política no se inventan). Detalle:

| País | Parámetros que su norma no fija |
|---|---|
| Portugal | PCS, Mercaptanos, O₂, CO₂, Punto de rocío del agua, Punto de rocío de hidrocarburos |
| Países Bajos | PCS, Densidad relativa, Punto de rocío de hidrocarburos |
| Bélgica | Densidad relativa, Mercaptanos, O₂, CO₂, Punto de rocío del agua, Punto de rocío de hidrocarburos |
| Noruega | Densidad relativa |
| Polonia | Densidad relativa, Punto de rocío de hidrocarburos |
| Dinamarca | PCS, O₂, CO₂ |
| Hungría | Densidad relativa, Mercaptanos, CO₂ |
| Austria | Densidad relativa |
| Grecia | Mercaptanos |
| Irlanda | Mercaptanos, Punto de rocío del agua |
| Rumanía | Índice de Wobbe, Densidad relativa, Mercaptanos |
| Turquía | Densidad relativa |
| Reino Unido | Mercaptanos |
| UE | PCS |

---

## 15. Ampliación del alcance: biometano e hidrógeno

El sistema nació para el gas natural y se ha ampliado a **biometano** e **hidrógeno** como una
**capa aditiva**. Se añade una dimensión de **tipo de gas** (registrada en `tipos_gas`, con
3 valores) que por defecto vale `gas_natural`: así **todo el gas natural queda intacto**
—mismo motor, mismas garantías, mismas pruebas— y los gases nuevos **reutilizan la misma
maquinaria** (consulta, comparativa, matriz, normalización ISO 13443 y estados de verificación).
El principio de **cero cifras inventadas** se mantiene idéntico.

| Tipo de gas | Sección de la ontología | Jurisdicciones | Parámetros |
|---|---|---|---|
| **Gas natural** | `parametros` | 21 (España … UE) | 10 |
| **Biometano** | `parametros_biometano` | 4 · España · Portugal · Francia · UE | 12 |
| **Hidrógeno** | `parametros_hidrogeno` | RED (CEN · GIE/UE · ES · FR · PT) + producto (ISO 14687) | 18 |

En la interfaz esto se traduce en dos secciones nuevas —**Comparativa biometano** y **Comparativa
hidrógeno**— idénticas en aspecto y funcionamiento a la del gas natural (misma tabla, matriz,
condiciones de referencia y exportación), con España siempre como base de comparación.

### 15.1. Biometano (inyección en red)

Parámetros clave del comparador: **CH₄ mínimo · CO₂ máximo · siloxanos** (como silicio total),
además de las impurezas de inyección (O₂, azufre total, H₂S+COS, NH₃, aminas, compuestos
halogenados, aceite de compresor y rocío de agua). Fuentes oficiales empleadas:

- **EN 16723-1:2016** — fija límite a 4 parámetros (silicio, CO, NH₃, aminas).
- **EN 16726:2025** — calidad de la red que admite biometano (CO₂, O₂, azufre, H₂S+COS).
- **CEN/TR 17238:2018** — metodología de evaluación de valores límite.
- **Reglamento (UE) 2024/1789** y **Directiva (UE) 2024/1788** — marco de mercado del gas
  renovable y del hidrógeno (art. 23 de especificaciones comunes aún no ejercido).
- **Orden TED/181/2025** (España) · **GRTgaz / GRDF** (Francia) · **RQS — Regulamento 826/2023,
  Anexo XI** (Portugal).

Cobertura: **17 valores verificados** (verbatim), **2 verificados por fuente
pública secundaria** (norma primaria de pago) y **8 no verificables** (la norma no fija
el valor — hueco honesto, no se inventa).

### 15.2. Hidrógeno (marco en construcción)

A diferencia del gas natural, **la normativa de hidrógeno aún no está madura**: a fecha de esta
revisión **no existe todavía un código de red de hidrógeno consolidado** (ENNOH, el organismo que
lo desarrollará, sigue en constitución). Por eso el hidrógeno se aborda como **prospección
normativa** —mapa del marco y su calendario, detallado en `Prospeccion_Normativa_Hidrogeno.md`—
registrando **solo lo que de verdad es vinculante**. La distinción esencial es de **dominio**:

- **Dominio de RED** (gasoducto — el de Enagás como operador de transporte): **CEN/TS 17977:2023**
  (norma CEN de redes reconvertidas) y la **recomendación del GIE**. Pureza de H₂ ≥ 98 % mol,
  O₂ ≤ 0,1 % mol, a condiciones ISO 13443 (15/15). **Portugal** (RQS, Anexo XII) es la única
  jurisdicción que hoy lo fija como **vinculante** (≥ 98 %); España y Francia regulan el
  *blending* (incorporación de H₂ en el gas natural); la UE lo **recomienda** vía GIE.
- **Dominio de PRODUCTO / VEHÍCULO**: **ISO 14687:2019 Grade D** (y su equivalente europeo
  **EN 17124**), pureza 99,97 % para pilas de combustible PEM de automoción. **No es lo que
  necesita un operador de red**; se incluye por completitud, marcado explícitamente como dominio
  de vehículo para no confundirlo con la calidad de red.

Parámetros clave del comparador: **pureza de H₂ · O₂ · trazas de compresores**. Cobertura:
**16 verificados**, **18 por fuente secundaria** y **6 no verificables**.

### 15.3. Estudio de terminología (¿hace falta una capa semántica?)

Antes de nada se midió cuánto varían los **nombres** de un mismo parámetro entre normas (índice de
variación terminológica): **27,4** en gas natural, **9,2** en biometano y **7,3** en hidrógeno
(umbral 7,0), según `Estudio_Terminologia_Biometano.md`. El estudio **justifica** una capa de
búsqueda semántica multilingüe, que se deja **preparada y opcional** (no activa por defecto): sin
ella, la búsqueda documental es la léxica descrita en §12, plenamente reproducible.

---

## 16. Metodología de construcción y verificación

Para cada jurisdicción: (1) se identificó la **normativa oficial vigente**; (2) se **obtuvo el
documento** y se archivó localmente; (3) se **transcribió cada cifra literalmente**, sin
interpretación; (4) se **verificó individualmente** contra el documento; (5) lo que la norma
**no fija, no se completa** (se marca como no verificable, con su justificación); (6) se
incorporó la **normalización** (ISO 13443) para comparaciones homogéneas.

El proceso cuenta con **controles de calidad automatizados** que comprueban que las
210 celdas se resuelven, que los enlaces a las fuentes funcionan y que no
hay incoherencias.

---

## 17. Garantías del sistema

- **Ausencia de cifras inventadas**, por diseño: los valores proceden de código y datos
  verificados, no del modelo.
- **Trazabilidad completa**: cada valor cita norma, artículo, página y enlace.
- **Transparencia**: lo que la norma no fija se declara explícitamente; no se completa.
- **Reproducibilidad**: con el mismo código y datos, el resultado es idéntico en cualquier
  entorno.
- **Auditabilidad**: la base de conocimiento es consultable y permite verificar el origen de
  cada valor.

---

## 18. Stack tecnológico y despliegue

**Backend:** Python · FastAPI · uvicorn · OpenAI SDK (GPT-4o-mini, function-calling) ·
pydantic · PyYAML (ontología) · pdfplumber (extracción de PDF) · sqlite3 (índice RAG) ·
openpyxl + xhtml2pdf (informes Excel/PDF) · cryptography (certificado HTTPS, opcional).
**Frontend:** HTML + JavaScript vanilla (marked, DOMPurify).
**Endpoints HTTP:** `/` (sirve la web) · `/api/status` · `/api/chat` (chat en lenguaje natural;
también resuelve **interconexiones/cadenas**) · `/api/parametros` · `/api/comparar` · `/api/matriz` ·
`/api/analizar-gas` (valida un gas concreto contra la normativa de cada país) · `/api/exportar-matriz`
(informe Excel/PDF de la matriz para las jurisdicciones seleccionadas).
**Despliegue:** `iniciar_chatbot.bat` — lanzador del equipo que se auto-actualiza
(`git pull --ff-only`), libera el puerto 8000 y arranca `uvicorn` por **HTTP**
(`http://localhost:8000/`), pensado para **uso interno/local**. La web se sirve **sin caché**
(siempre la última versión tras un `git pull`). El frontend se adapta solo al protocolo con el que
se le sirve (usa `location.origin`), por lo que no hay URLs fijas a cambiar.

**Servir en producción (HTTPS) — dejado indicado:** el proyecto incluye todo lo necesario para
elevar a HTTPS sin reprogramar nada. En el propio `iniciar_chatbot.bat` (nota *[HTTPS OPCIONAL]*)
se explica: (1) descomentar `generar_certificado.py` (genera un certificado autofirmado
`cert.pem`/`key.pem`) y (2) añadir `--ssl-keyfile key.pem --ssl-certfile cert.pem` al comando
`uvicorn`. Para un despliegue robusto, lo recomendado es situarlo **tras un proxy inverso**
(nginx, IIS…) que gestione el TLS con un certificado de confianza. Esa decisión se deja al equipo
que lo opere.

*(La interfaz es `index.html` servida por FastAPI; el sistema **no** usa Streamlit.)*

---

## 19. Diseño ideal frente a implementación real (honestidad de ingeniería)

| El diseño / la ontología describe… | La realidad del código es… |
|---|---|
| RAG con **Vector DB + similitud semántica** | **Búsqueda léxica** SQLite `LIKE` (sin vectores) |
| Normalización **"con `pint`"** | `pint` no se importa; conversiones = tablas verificadas a mano |
| Interfaz con **Streamlit** (prototipo inicial) | **`index.html`** (JavaScript puro) servido por FastAPI |

---

## 20. Alcance y limitaciones del prototipo

Para una lectura honesta, conviene explicitar qué es y qué no es hoy el sistema:

- **Prototipo demostrativo, no producción.** Está pensado para **uso interno/local** (se sirve por
  HTTP; ver §18) y para demostrar la arquitectura y el rigor de los datos, no para una explotación a
  gran escala ni multiusuario concurrente.
- **Sin autenticación.** No incorpora control de acceso ni gestión de usuarios: se asume una red de
  confianza. Añadir autenticación —o servir tras un proxy inverso con TLS— queda para el despliegue (§18).
- **Cobertura de datos delimitada.** Gas natural: 10 parámetros × 21
  jurisdicciones (176 verificados, 34 no verificables). Biometano e hidrógeno: alcance
  acotado y, en el hidrógeno, **marco normativo aún en construcción** (se trata como prospección; ver §15).
- **Búsqueda documental léxica.** El RAG es por términos, no semántico (§12, §19); la capa vectorial
  está preparada pero desactivada por defecto.
- **La IA es opcional y acotada.** Sin clave de OpenAI el sistema funciona en modo determinista (igual
  de fiable para límites y comparaciones); y la IA **nunca genera cifras** (§11).

Ninguna de estas limitaciones afecta a la garantía central: **las cifras nunca se inventan** y todo
es trazable a su fuente. Son el alcance natural de un prototipo, y el camino a producción está
indicado (§18).

---

## 21. Glosario

- **Backend / servidor de aplicación:** el programa que da soporte a la web y ejecuta la lógica.
- **FastAPI:** framework con el que se ha desarrollado el servidor. Es infraestructura propia.
- **API de OpenAI:** servicio externo de IA que se consume para tareas de texto. Es de terceros.
- **Ontología:** repositorio estructurado donde residen las 210 cifras con
  su contexto y su fuente.
- **YAML:** formato de fichero de texto, legible por personas, en el que está escrita la ontología.
- **Determinista:** que ante la misma entrada produce siempre la misma salida, sin aleatoriedad ni IA.
- **Router / motor determinista:** el componente que decide si una consulta la resuelve el código o la IA.
- **Normalización (ISO 13443):** llevar todos los valores a una base común para compararlos.
- **RAG:** técnica de recuperación documental que fundamenta las respuestas en las fuentes.
- **Indexación:** preparar el buscador procesando los documentos y almacenando su texto segmentado.
- **SQLite:** base de datos ligera; aquí se emplea únicamente como índice del buscador documental.
- **VERIFICADO / NO_VERIFICABLE:** cifra contrastada con la norma / parámetro que la norma no fija.
- **VERIFICADO_SECUNDARIO:** valor no tomado del texto primario (norma de pago), sino de una fuente pública secundaria citada; usado sobre todo en biometano/hidrógeno.
- **tipo_gas:** la dimensión que selecciona el gas (gas natural, biometano o hidrógeno); por defecto `gas_natural`.
- **Dominio de red vs. de producto (hidrógeno):** calidad del H₂ para el gasoducto (red, CEN/TS 17977, GIE) frente a la del H₂ como combustible de vehículo (producto, ISO 14687); son especificaciones distintas y no comparables.
- **Biometano / hidrógeno:** gases renovables añadidos como capa aditiva; ver §15.

*Fin del documento.*
