# Documentación técnica — Comparador Regulatorio de Calidad de Gas Natural

*Documento único de referencia. Consolida toda la explicación del sistema: qué hace, cómo
está construido y cómo funciona cada componente. Cotejado con el código y con los datos
reales — versión de ontología **3.1.0**, revisión **2026-06**.
Los diagramas de arquitectura y de la ontología se conservan como ficheros de imagen
independientes y se incluyen también en este documento.*

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
15. Metodología de construcción y verificación
16. Garantías del sistema
17. Stack tecnológico y despliegue
18. Diseño ideal frente a implementación real
19. Glosario

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
y buscar en los documentos (RAG). El servidor expone unos pocos servicios (endpoints):
interfaz, chat, comparación puntual y matriz comparativa.

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
| **3. Índice documental (RAG)** | Índice del **texto** de los PDF, segmentado por página | Buscador interno, para consultas abiertas. |

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

La ontología tiene dos partes principales:

| Clave | Contenido |
|---|---|
| `ontologia.fuentes_normativas` | El **catálogo de las 28 normas** oficiales: `id`, `nombre`, `organismo`, `publicacion`, `url` (cita) y `pdf` (copia local). |
| `parametros` | Los **10 parámetros**, cada uno con un bloque `limites:` con una entrada **por país**. |

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

- **`VERIFICADO`** — cifra contrastada **verbatim** contra su fuente oficial (175 valores).
- **`NO_VERIFICABLE_SIN_FUENTE`** — la norma citada **no fija** esa cifra → **no se inventa**,
  se marca como hueco honesto y se explica (35 valores).

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
   `pdfplumber`, lo **trocea por página** y lo guarda en una base **SQLite** que actúa de índice.
   La indexación es **incremental**: solo se reprocesa un documento nuevo o modificado, por lo
   que el arranque es casi inmediato.
2. **Recuperación:** `buscar_pdfs(query)` realiza una **búsqueda léxica** (SQLite `LIKE` sobre el
   texto normalizado) y devuelve los fragmentos más relevantes con archivo, página y snippet.

Es una búsqueda **léxica** (por palabra clave), **no vectorial** (sin embeddings ni similitud
semántica). Es un enfoque más simple, suficiente para este caso y **plenamente reproducible**,
al no depender de servicios externos para localizar la información.

---

## 13. El chat y el historial persistente

- **Frontend (`index.html`):** SPA en JavaScript puro; render de Markdown con `marked` +
  saneado con `DOMPurify`. Dos pestañas: *Consulta libre* (chat) y *Comparativa*
  (puntual + matriz).
- **Historial persistente:** cada turno (pregunta + respuesta) se guarda por sesión en el
  navegador (`localStorage`) y se **restaura al recargar la página o tras reiniciar el
  servidor**, de modo que el usuario no pierde sus consultas. «Nueva consulta» abre una sesión
  limpia.
- **Contexto en el backend:** `_registrar_turno` guarda **todos** los turnos (deterministas y
  de IA, acotados a los últimos 40 mensajes por sesión), de forma que el asistente conserva el
  contexto para las preguntas de seguimiento.

---

## 14. Estado real de los datos

Cobertura actual: **175 celdas VERIFICADO**, **35 NO_VERIFICABLE**, 0 pendientes,
sobre 210 celdas (10 parámetros × 21 jurisdicciones).
Las 210 celdas resuelven por la ruta real de la aplicación.

**✓** = verificado verbatim · **○** = la norma no fija ese parámetro (hueco honesto)

| Parámetro | ES | PT | FR | IT | DE | NL | BE | NOR | PL | DK | HU | AT | CH | CZ | GR | IE | RO | SK | TR | GB | UE |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Índice de Wobbe | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ |
| PCS | ✓ | ○ | ✓ | ✓ | ○ | ○ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ○ |
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
| Alemania | PCS |
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

## 15. Metodología de construcción y verificación

Para cada jurisdicción: (1) se identificó la **normativa oficial vigente**; (2) se **obtuvo el
documento** y se archivó localmente; (3) se **transcribió cada cifra literalmente**, sin
interpretación; (4) se **verificó individualmente** contra el documento; (5) lo que la norma
**no fija, no se completa** (se marca como no verificable, con su justificación); (6) se
incorporó la **normalización** (ISO 13443) para comparaciones homogéneas.

El proceso cuenta con **controles de calidad automatizados** que comprueban que las
210 celdas se resuelven, que los enlaces a las fuentes funcionan y que no
hay incoherencias.

---

## 16. Garantías del sistema

- **Ausencia de cifras inventadas**, por diseño: los valores proceden de código y datos
  verificados, no del modelo.
- **Trazabilidad completa**: cada valor cita norma, artículo, página y enlace.
- **Transparencia**: lo que la norma no fija se declara explícitamente; no se completa.
- **Reproducibilidad**: con el mismo código y datos, el resultado es idéntico en cualquier
  entorno.
- **Auditabilidad**: la base de conocimiento es consultable y permite verificar el origen de
  cada valor.

---

## 17. Stack tecnológico y despliegue

**Backend:** Python · FastAPI · uvicorn · OpenAI SDK (GPT-4o-mini, function-calling) · pydantic
· PyYAML (ontología) · pdfplumber (extracción de PDF) · sqlite3 (índice RAG).
**Frontend:** HTML + JavaScript vanilla (marked, DOMPurify).
**Endpoints HTTP:** `/` (sirve la web) · `/api/status` · `/api/chat` · `/api/parametros` ·
`/api/comparar` · `/api/matriz`.
**Despliegue:** `iniciar_chatbot.bat` — lanzador del equipo que se auto-actualiza
(`git pull --ff-only`), libera el puerto 8000 y arranca `uvicorn`. La web se sirve **sin caché**
(siempre la última versión tras un `git pull`).

*(La interfaz es `index.html` servida por FastAPI; el sistema **no** usa Streamlit.)*

---

## 18. Diseño ideal frente a implementación real (honestidad de ingeniería)

| El diseño / la ontología describe… | La realidad del código es… |
|---|---|
| RAG con **Vector DB + similitud semántica** | **Búsqueda léxica** SQLite `LIKE` (sin vectores) |
| Normalización **"con `pint`"** | `pint` no se importa; conversiones = tablas verificadas a mano |
| Interfaz con **Streamlit** (prototipo inicial) | **`index.html`** (JavaScript puro) servido por FastAPI |

---

## 19. Glosario

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

*Fin del documento.*
