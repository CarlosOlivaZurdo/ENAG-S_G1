# Comparador Regulatorio de Calidad de Gas

> Herramienta híbrida (**IA + motor determinista**) para consultar y comparar los requisitos de
> calidad de gas —**gas natural, biometano e hidrógeno**— entre jurisdicciones europeas, con
> **trazabilidad a la norma oficial** y el principio de **cero cifras inventadas**.

Prototipo desarrollado para **Enagás** en el marco de la **Cátedra de Industria Inteligente**
(Universidad Pontificia Comillas · ICAI).

- **Ontología (fuente de verdad):** v3.2.0 · rev. 2026-07
- **Cobertura:** 21 jurisdicciones (gas natural) · 39 normas oficiales · 277 registros trazables

---

## 1. Qué es

Una aplicación web conversacional que responde, en segundos y en lenguaje natural, preguntas sobre
**calidad de gas** que hoy exigen revisar varios reglamentos nacionales y europeos en distintos
idiomas, unidades y condiciones de referencia.

La clave del sistema es su **arquitectura híbrida**: la IA entiende y redacta, pero **ningún número
lo produce la IA**. Todas las cifras salen de una **ontología verificada** extraída de los PDF
oficiales, cada una con su cita (norma, artículo, página) y su estado de verificación. Antes de
comparar, los valores se **normalizan** a unas condiciones comunes (ISO 13443).

Es un **sistema de dominio cerrado**: solo calidad de gas. No es un chatbot generalista (ver §7).

---

## 2. Qué hace — los cinco modos

| Modo | Para qué sirve |
|---|---|
| **Consulta libre (gas natural)** | Chat en lenguaje natural. Responde tres tipos de pregunta: **valores** («¿límite de O₂ en España?»), **texto de la norma** («¿qué dice el artículo X?») y **explicaciones de concepto** («¿qué es el índice de Wobbe?»). La IA redacta; las cifras las pide al motor determinista, y el texto lo localiza en los PDF oficiales. |
| **Comparativa gas natural** | Compara un parámetro entre países (puntual) o genera la **matriz** completa (todos los parámetros × jurisdicciones), con normalización de condiciones y semáforo de comparabilidad. |
| **Analizar gas natural** | El usuario introduce la composición/medidas de un gas concreto (CO₂, O₂, H₂S, azufre, PCS, Wobbe, rocíos…) y el sistema responde, país a país, si **cumple / no cumple**. |
| **Comparativa biometano** | Misma comparativa, para el biometano de inyección en red (ES · PT · FR · UE). |
| **Comparativa hidrógeno** | Misma comparativa, para el marco —aún en construcción— del hidrógeno. |

Los informes de la matriz se pueden **exportar a Excel y a PDF**.

---

## 3. Cómo funciona — arquitectura

El sistema separa de forma **absoluta** el mundo conversacional (IA) del mundo del dato (determinista).

```
  Navegador (index.html, SPA)
        │  HTTP / JSON
  Backend (api.py · FastAPI + uvicorn)
        │  el "router determinista" decide quién resuelve la consulta
        ├── Ruta A · consulta cuantitativa  → Motor determinista  → Ontología (YAML)   ← las CIFRAS
        └── Ruta B · texto abierto          → Capa LLM (OpenAI)   → RAG (SQLite)        ← el TEXTO
                                                    (la IA PIDE la cifra al motor; nunca la inventa)
```

**Las tres capas de datos:**

1. **Documentos oficiales** (`data/raw/*.pdf`): los PDF de las normas (BOE, ERSE, GRTgaz, DVGW…),
   guardados en local. La fuente última de verdad.
2. **Ontología** (`data/ontologia/ontologia_enagas.yaml`): los 277 registros extraídos de esos PDF,
   cada uno con su cita. **De aquí salen todas las cifras verificadas del sistema.**
3. **Índice documental / RAG** (`data/pdf_database.sqlite3`): el texto de los PDF troceado para
   localizar pasajes en las consultas de texto. **No es fuente de cifras: devuelve texto, no valores.**

**Garantías** (ver §7 para el detalle):

- **Cero alucinaciones numéricas** — ningún número procede del conocimiento del LLM.
- **Trazabilidad completa** — cada valor cita norma, artículo, página y fuente.
- **No se asumen condiciones** — la comparación normaliza con ISO 13443; lo que la norma no fija se
  declara «no verificable», no se rellena.
- **Funciona sin IA** — si no hay clave de OpenAI (o falla), el chat cae a **modo determinista** y
  sigue respondiendo consultas de valores y comparación (igual de fiable).

---

## 4. Datos y cobertura

**Ontología** (`ontologia_enagas.yaml`) — un único fichero YAML, legible y versionado en git.

| Sección | Contenido |
|---|---|
| `parametros` | **Gas natural** — 10 parámetros × 21 jurisdicciones = **210 celdas** |
| `parametros_biometano` | **Biometano** — 12 parámetros · **27 celdas** (4 jurisdicciones: ES · PT · FR · UE) |
| `parametros_hidrogeno` | **Hidrógeno** — 18 parámetros · **40 celdas** (dominio de red + producto) |

**Total: 277 registros trazables** — cada uno con su estado de verificación:

| Estado | Nº | Significado |
|---|---|---|
| `VERIFICADO` | 209 | Contrastado *verbatim* contra el boletín/documento oficial. |
| `VERIFICADO_SECUNDARIO` | 20 | La norma primaria es de pago: valor tomado de una fuente pública secundaria, citada. |
| `NO_VERIFICABLE` | 48 | La norma no fija ese parámetro. No se inventa: se declara el hueco. |

**Los 10 parámetros de gas natural:** Índice de Wobbe · PCS · densidad relativa · azufre total ·
H₂S + COS (como S) · mercaptanos RSH (como S) · O₂ · CO₂ · punto de rocío de agua · punto de rocío
de hidrocarburos.

**Las 21 jurisdicciones (gas natural):** ES, PT, FR, UE, IT, DE, NL, BE, NO, PL, DK, HU, AT, CH, CZ,
GR, IE, RO, SK, TR, GB.

Las cifras se apoyan en **39 normas oficiales** catalogadas en la ontología (organismo, publicación,
URL y copia local del PDF).

---

## 5. Cómo ejecutarlo

**Requisito (una sola vez):** Python 3.11 o superior ([descarga](https://www.python.org/downloads/);
marca **«Add Python to PATH»** al instalar).

1. Ten la última versión: `git pull` (o descarga el ZIP desde GitHub).
2. **Doble clic en `iniciar_chatbot.bat`.** La primera vez instala las dependencias (1–2 min, con
   internet).
3. Se abre el navegador en **http://localhost:8000/**. Listo.

Para detener el servidor: cierra la ventana negra o pulsa `Ctrl+C`. Guía detallada en
[`LEER_PRIMERO.txt`](LEER_PRIMERO.txt).

### Activar la IA (opcional)

La herramienta funciona **sin IA** en modo determinista. Para activar el chat conversacional
completo (preguntas de texto y explicaciones), define una clave de OpenAI:

```bash
copy .env.example .env        # crea tu .env a partir de la plantilla
#   edita .env  ->  API_OPENAI=sk-...tu-clave...
```

El fichero `.env` es **secreto y no se versiona**. Puedes comprobar el modo activo en
`http://localhost:8000/api/status` (`"modo": "ia"` o `"determinista"`).

### Servir por HTTPS / en producción (opcional)

Por defecto se sirve por **HTTP** (uso interno/local). Cómo pasar a HTTPS está **dejado indicado**
dentro de `iniciar_chatbot.bat` (nota `[HTTPS OPCIONAL]`): generar el certificado y añadir los flags
TLS a uvicorn, o —mejor— servir tras un proxy inverso (nginx / IIS).

### Actualizar las normativas (opcional)

Los datos proceden de los PDF oficiales en `data/raw/`. Para refrescarlos a su última versión
publicada: doble clic en `actualizar_fuentes.bat` (BOE y EUR-Lex automáticos; para PT/FR se añade la
URL directa en `actualizar_fuentes.py`). Además **compara con la versión anterior y avisa de qué
fuentes han cambiado** (y en qué líneas), para re-verificar solo esas. Los números **no** se cambian
solos: los re-verifica una persona contra el PDF nuevo (así se sostiene el «cero cifras inventadas»).

---

## 6. Estructura del repositorio

```
api.py                       Backend FastAPI (endpoints, router determinista, chat)
index.html                   Interfaz web (SPA en JavaScript; marked + DOMPurify)
fuente_oficial.py            Motor determinista: lee la ontología (única fuente de cifras)
conversor_unidades.py        Conversión de unidades
condiciones_referencia.py    Normalización de condiciones (ISO 13443)
llm_interface.py             Capa de IA (agnóstica de proveedor: OpenAI / Anthropic / Ollama…)
agente_pdf.py                RAG: indexa y busca el texto de los PDF (pdfplumber → SQLite)
src/llm/prompts.py           Prompt de sistema del chat

data/ontologia/ontologia_enagas.yaml   Fuente de verdad (277 registros, con cita y estado)
data/raw/*.pdf                          Documentos oficiales (BOE, ERSE, GRTgaz, Snam, EN 16726…)
data/pdf_database.sqlite3               Índice del RAG (se regenera solo)

docs/                        Documentación, diagramas y sus generadores
tests/                       Pruebas (pytest)
iniciar_chatbot.bat          Arranque (actualiza, instala deps y sirve en el puerto 8000)
actualizar_fuentes.py/.bat   Refresco de los PDF oficiales
.env.example                 Plantilla de configuración (clave de IA opcional)
```

---

## 7. Ámbito y garantías

**Dominio cerrado.** El sistema cubre **exclusivamente la calidad de gas**. Quedan fuera mercado,
tarifas, peajes, capacidad, balance, almacenamiento, contratación, fiscalidad, etc. Cualquier
consulta fuera de ámbito se rechaza o redirige.

**No es** un chatbot generalista, ni un asistente legal, ni un buscador jurídico, ni un sistema
experto de derecho energético, ni una IA que genere conclusiones regulatorias por su cuenta.

**Restricciones críticas** (invariantes del diseño):

1. **Cero alucinaciones numéricas** — todo valor procede de la ontología / documentos, nunca del LLM.
2. **Trazabilidad completa** — toda afirmación se remonta a documento, país, artículo, tabla, página.
3. **No asumir condiciones** — nunca se suponen temperatura, presión, humedad o estado de referencia.
4. **No inventar conversiones** — sin base física o normativa, el resultado es 🔴 NO_COMPARABLE.
5. **Auditabilidad total** — cualquier respuesta puede reconstruirse a posteriori por un auditor.

**Reparto de responsabilidades:**

- La **IA** puede: interpretar preguntas, detectar intención, resumir y redactar respuestas.
- La **IA** no puede: generar límites, inventar valores, deducir conversiones ni inferir comparabilidad.
- El **motor determinista** es la única fuente autorizada de valores, unidades, límites, conversiones,
  condiciones de referencia y clasificación de compatibilidad.

---

## 8. Documentación

Toda la documentación técnica está en [`docs/`](docs/):

| Documento | Formato | Para qué sirve |
|---|---|---|
| **Documentacion_Comparador_Gas** | MD · PDF | Referencia técnica y de funcionamiento completa (el «manual»). |
| **Preguntas_Respuestas_Defensa** | MD · PDF | Batería de preguntas y respuestas para la defensa del proyecto. |
| **Prospeccion_Normativa_Hidrogeno** | MD | Marco regulatorio del hidrógeno verificado + hoja de ruta. |
| **Estudio_Terminologia_Biometano** | MD | Justificación (medida) de una capa de búsqueda semántica. |
| **Arquitectura_Esquema_Cajas** · **Ontologia_Estructura** | PNG · SVG | Los dos diagramas del sistema. |

> La **especificación original** del proyecto (el *prompt maestro* de partida) se conserva como
> referencia histórica en [`docs/Especificacion_Original.md`](docs/Especificacion_Original.md).

---

*Prototipo académico-profesional para Enagás · Cátedra de Industria Inteligente (Comillas ICAI).*
