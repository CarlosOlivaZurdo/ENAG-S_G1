# Arquitectura del Comparador Regulatorio de Calidad de Gas Natural — Enagás

*Documento técnico. Describe la arquitectura **real** del sistema (cotejada con el código), no el diseño teórico.*

---

## 1. Filosofía: arquitectura híbrida "cero alucinaciones numéricas"

El sistema combina **dos mundos separados a propósito**:

- **Mundo determinista** (código + ontología): la **única** fuente autorizada de cifras, límites, conversiones y comparaciones. Nunca improvisa un número.
- **Mundo conversacional** (LLM): interpreta la pregunta en lenguaje natural y **redacta** la respuesta, pero tiene prohibido generar números — los obtiene llamando a herramientas deterministas.

La regla de oro está implementada en el flujo del chat: **determinista-primero, LLM-fallback**. Las preguntas estructuradas se resuelven con código determinista (sin riesgo de alucinación); solo las preguntas abiertas pasan al LLM, que está obligado a apoyarse en herramientas y en los documentos oficiales.

---

## 2. Mapa de componentes

```
+--------------------------------------------------------------+
|  FRONTEND  index.html  (SPA en JS puro, servida por FastAPI) |
|   - Pestaña "Consulta libre" (chat)                          |
|   - Pestaña "Comparativa" (puntual + matriz / heatmap)       |
+-------------------------+------------------------------------+
                          | HTTP / JSON
+-------------------------v------------------------------------+
|  BACKEND  api.py  (FastAPI + uvicorn)                        |
|  Endpoints: /  /api/status  /api/chat  /api/parametros       |
|             /api/comparar   /api/matriz                      |
|                                                              |
|  /api/chat -> _validate_measurement_gate (ROUTER DETERMINISTA)|
|                 - reconoce la intencion -> responde sin LLM  |
|                 - si None -> responder_con_openai (LLM+tools) |
+----------+----------------------------+----------------------+
           | (motor determinista)       | (LLM constrenido)
+----------v---------------+   +---------v----------------------+
| fuente_oficial.py        |   | OpenAI (gpt-4o-mini)           |
| conversor_unidades.py    |   |  function-calling, temp=0      |
| condiciones_referencia.py|   |  tools = funciones deterministas|
+----------+---------------+   |         + buscar_pdfs (RAG)     |
           | lee              +---------+----------------------+
+----------v---------------+            | recupera
| ONTOLOGIA (YAML)         |   +--------v-----------------------+
| data/ontologia/          |   | RAG: agente_pdf.py + SQLite    |
| ontologia_enagas.yaml    |   | indice lexico de los PDF       |
| = FUENTE DE VERDAD       |   | (data/raw/*.pdf -> sqlite3)    |
+--------------------------+   +--------------------------------+
```

---

## 3. La ontología — el corazón del sistema

**Archivo:** `data/ontologia/ontologia_enagas.yaml`

Es la **fuente primaria de verdad**: la extracción verificada de los PDF oficiales. El motor determinista lee de aquí; el LLM nunca calcula ni inventa valores.

### Estructura de nivel superior

| Clave | Contenido |
|---|---|
| `ontologia.fuentes_normativas` | Las normas: `id`, organismo, publicación, `url` (enlace de cita), `pdf` (copia local), condiciones de referencia y notas. |
| `parametros` | Los **10 parámetros**, cada uno con su bloque `limites:` por país. |
| `unidades`, `flags` | Catálogos auxiliares. |
| `orquestador`, `motor_reglas`, `rag` | Diseño/pipeline ideal (parte es aspiracional — ver §8). |

### Cada límite (por parámetro y país) lleva

- `valor` o `valor_min`/`valor_max`, `unidad`, `tipo_limite` (rango / maximo / minimo)
- `condiciones_referencia` (temperatura de combustión / volumen, presión, notación)
- `expresion_original` (texto literal de la fuente)
- **`estado_verificacion`**: `VERIFICADO` o `NO_VERIFICABLE_SIN_FUENTE` (lo que no consta en fuente oficial **no se inventa**)
- cita: `fuente` (id de la norma) + `articulo` (sección y página)

### Cobertura actual

- **10 parámetros:** Índice de Wobbe, PCS, densidad relativa, azufre total, H₂S+COS, mercaptanos (RSH), O₂, CO₂, punto de rocío del agua, punto de rocío de hidrocarburos.
- **Jurisdicciones (21):** España (base), Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Chequia, Grecia, Irlanda, Rumanía, Eslovaquia, Turquía, Reino Unido y la UE (EN 16726).

> El campo `url` de cada fuente es **fuente única**: lo usan a la vez la cita en pantalla (`fuente_oficial.url_de`) y el descargador de PDFs (`actualizar_fuentes.py`).

---

## 4. El motor determinista (de dónde salen las cifras)

| Módulo | Función |
|---|---|
| `fuente_oficial.py` | Capa de datos: lee la ontología y devuelve registros con cita completa (documento, organismo, artículo, página, URL, notación). Mapea nombre de país → código. |
| `conversor_unidades.py` | Conversión de unidades (energía, temperatura, concentración) **y la `_TABLA_A1` literal de la ISO 13443** (factores entre condiciones de referencia). Todo cableado y verificado a mano. |
| `condiciones_referencia.py` | Mapea cada país a sus condiciones de referencia y delega el factor ISO 13443 en el conversor. |
| `motor_determinista.py` | Capa heredada del Excel/CSV (ya retirado); hoy degrada con elegancia y solo hace de puente al RAG. |

### ISO 13443 (normalización a condiciones de España)

Para comparar PCS e Índice de Wobbe entre países con distinta temperatura de combustión/volumen, se aplican los **factores literales de la Tabla A.1** (gas real, base volumétrica), que viven en un único sitio (`conversor_unidades._TABLA_A1`):

| Conversión a España (0/0) | PCS | Wobbe | PCI |
|---|---|---|---|
| **25/0 → 0/0** (Portugal, Alemania, Países Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Grecia) | 1,0026 | 1,0026 | 1,0003 |
| **15/15 → 0/0** (Italia, UE, Chequia, Irlanda, Rumanía, Turquía, Reino Unido) | 1,0570 | 1,0569 | 1,0555 |
| **25/20 → 0/0** (Eslovaquia — par no tabulado) | ≈1,076 (Anexo B) | ≈1,076 | |
| 0/0 → 0/0 (España, Francia) | identidad (×1) | | |

> **Unidades de energía:** además de kWh/m³ y MJ/m³, el conversor admite **kcal/m³** (Turquía y Rumanía expresan el Wobbe/PCS en kcal; 1 kWh ≈ 859,85 kcal). El par **25/20** de Eslovaquia (volumen a 20 °C) no está en la Tabla A.1, así que se resuelve con las **ecuaciones del Anexo B** de la ISO 13443.

Las concentraciones másicas (mg/m³) referidas a un volumen distinto de 0 °C (p. ej. Italia a 15 °C) se normalizan con el factor de gas ideal `(273,15+T)/273,15`. El % mol, lo adimensional y los puntos de rocío no dependen de la temperatura del volumen.

---

## 5. El router determinista (orquestación del chat)

**`api.py` → `_validate_measurement_gate(session_id, mensaje)`**

Antes de tocar el LLM, analiza el mensaje (parámetro + valor + unidad + países detectados) y resuelve **deterministamente** las preguntas estructuradas:

1. **Cumplimiento** — valor + unidad → cumple / no cumple.
2. **Límite/valor** — sin valor → muestra los límites (nunca "cumple"; sin valor no hay nada que cumplir).
3. **¿De qué reglamento sale?** — cita la fuente oficial.
4. **Intercambiabilidad** — solape de rangos frente a España.
5. **Más restrictivo / más amplio que España.**
6. **Comparación** España ↔ país (formato Enagás).
7. **Conversión a condiciones de España** (ISO 13443).

Si reconoce la intención → responde con `modo: "determinista"`. Si **no** la reconoce → devuelve `None` y la petición pasa al LLM.

---

## 6. La capa LLM (preguntas abiertas)

**`api.py` → `responder_con_openai`**

- Modelo **OpenAI `gpt-4o-mini`** (configurable con la variable `OPENAI_MODEL`), **function-calling**, `temperature=0`, bucle de hasta 5 iteraciones de llamadas a herramientas.
- El `SYSTEM_PROMPT` (`src/llm/prompts.py`) le prohíbe inventar cifras, fija el ámbito (calidad de gas) y los países soportados.
- **Herramientas** que puede invocar (todas deterministas, salvo el RAG):
  `consultar_excel`, `evaluar_cumplimiento`, `convertir_unidades`,
  `convertir_condiciones_referencia` / `convertir_condiciones_iso13443`, y **`buscar_pdfs`** (RAG).
- **Tolerancia a fallos:** si OpenAI falla (clave inválida, red, límite) o no hay clave → cae al motor determinista (`_fallback_deterministic_response`). El chat nunca devuelve un error 500.

---

## 7. El RAG (preguntas abiertas, fundamentadas en los PDF)

**`agente_pdf.py` + `data/pdf_database.sqlite3`**

- Indexa los **PDF oficiales** de `data/raw/` (extracción con `pdfplumber`), troceados **por página**, en una base **SQLite**.
- `buscar_pdfs(query)` realiza una **búsqueda léxica** (SQLite `LIKE` sobre el texto normalizado + nombre/título del documento) y devuelve los fragmentos más relevantes con archivo, página y snippet.
- El LLM lo usa como herramienta para responder preguntas abiertas **citando** los documentos, sin inventar.

> **Importante:** el RAG es **léxico** (palabra clave), no vectorial. No hay embeddings ni similitud semántica, aunque la sección `rag` de la ontología describa un diseño con Vector DB.

---

## 8. Spec vs. implementación (qué prometer y qué no)

| El diseño / la ontología dice… | La realidad del código es… |
|---|---|
| RAG con **Vector DB + similitud coseno + reranking** | **Búsqueda léxica** SQLite `LIKE` (sin vectores) |
| Normalización **"con `pint`"** | `pint` **no se importa en ningún módulo** (dependencia muerta); las conversiones son tablas verificadas a mano |
| Respuesta del LLM en **"7 secciones"** | El prompt pide tabla + evidencias; las preguntas estructuradas las redacta el **código**, no el LLM |
| Historial de conversación | **Persistente en el navegador** (`localStorage`): se restaura al recargar la página y sobrevive al reinicio del servidor. El backend además registra **todos** los turnos —incluidos los deterministas— en RAM por sesión (acotados a los últimos 40 mensajes). No hay base de datos de conversaciones en servidor |

---

## 9. Frontend, despliegue y mantenimiento

- **`index.html`** — SPA en **JavaScript puro** (sin framework). Render de Markdown con `marked` + saneado con `DOMPurify`. Identidad visual Enagás (azul + verde). Dos pestañas: *Consulta libre* (chat) y *Comparativa* (puntual + matriz/heatmap).
- **Historial persistente** — cada turno (pregunta + respuesta) se guarda por sesión en el navegador (`localStorage`) y se **restaura al recargar la página** o tras reiniciar el servidor; así el usuario no pierde sus consultas. El botón *«Nueva consulta»* empieza una sesión limpia. En el backend, `_registrar_turno` guarda **todos** los turnos (deterministas y de IA) para que el asistente tenga contexto en las preguntas de seguimiento.
- **`iniciar_chatbot.bat`** — lanzador para los compañeros: **se auto-actualiza** (`git pull --ff-only`), **libera el puerto 8000** si quedó un servidor anterior y arranca `uvicorn`. La web se sirve **sin caché** (siempre la última versión).
- **`actualizar_fuentes.py`** — descarga los PDF desde el campo `url` de la ontología (fuente única); las fuentes HTML/sin PDF directo se marcan para descarga manual.

---

## 10. Stack tecnológico

**Backend:** Python · FastAPI · uvicorn · OpenAI SDK (gpt-4o-mini, function-calling) · pydantic · PyYAML (ontología) · pdfplumber (extracción PDF) · sqlite3 (índice RAG).

**Frontend:** HTML + JavaScript vanilla (marked, DOMPurify).

**Endpoints HTTP:** `/` (sirve la web) · `/api/status` · `/api/chat` · `/api/parametros` · `/api/comparar` · `/api/matriz`.

*(En `requirements.txt` figuran `pandas`, `openpyxl` y `pint`, pero ya no se usan en el código.)*

---

## 11. Flujo de una consulta (ejemplo)

**Pregunta:** *"¿cumple 14 kWh/m³ de PCS en Francia?"*

1. `POST /api/chat` → `_validate_measurement_gate`.
2. El router detecta: parámetro = PCS, valor = 14, unidad = kWh/m³, país = Francia, señal de cumplimiento.
3. Llama a `_evaluar_paises` → `fuente_oficial` lee el límite francés de PCS de la ontología (con su cita) → `conversor_unidades` normaliza unidades/condiciones si hace falta.
4. Compara 14 kWh/m³ con el rango francés → **cumple / no cumple**, con la cita oficial.
5. Devuelve la respuesta con `modo: "determinista"` — **sin pasar por el LLM**, sin posibilidad de inventar la cifra.

Una pregunta abierta como *"¿qué es el índice de Wobbe?"* no la reconoce el router → pasa al LLM, que la responde apoyándose en `buscar_pdfs` (RAG) y citando la fuente.
