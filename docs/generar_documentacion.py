# -*- coding: utf-8 -*-
"""Genera el DOCUMENTO ÚNICO de documentación del Comparador (Markdown + PDF, estilo Enagás).

    python docs/generar_documentacion.py

Consolida toda la explicación del sistema en un solo documento profesional y detallado.
- La PROSA la fija este script (revisada a mano).
- Las TABLAS DE DATOS se generan desde la ontología (nunca se inventan ni se desincronizan).
- Embebe los dos diagramas (arquitectura y ontología).

Salida: docs/Documentacion_Comparador_Gas.md  y  .pdf
"""
import os, io, sys, collections, yaml
import markdown
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ONT = os.path.join(RAIZ, "data", "ontologia", "ontologia_enagas.yaml")
MD = os.path.join(AQUI, "Documentacion_Comparador_Gas.md")
PDF = os.path.join(AQUI, "Documentacion_Comparador_Gas.pdf")

d = yaml.safe_load(io.open(ONT, encoding="utf-8"))
ONTO = d["ontologia"]; P = d["parametros"]
FU = {f["id"]: f for f in ONTO["fuentes_normativas"]}

CODES = ["ES","PT","FR","IT","DE","NL","BE","NOR","PL","DK","HU","AT","CH","CZ","GR","IE","RO","SK","TR","GB","UE"]
COD2NOM = {"ES":"España","PT":"Portugal","FR":"Francia","IT":"Italia","DE":"Alemania","NL":"Países Bajos",
 "BE":"Bélgica","NOR":"Noruega","PL":"Polonia","DK":"Dinamarca","HU":"Hungría","AT":"Austria","CH":"Suiza",
 "CZ":"Chequia","GR":"Grecia","IE":"Irlanda","RO":"Rumanía","SK":"Eslovaquia","TR":"Turquía","GB":"Reino Unido","UE":"UE"}
PARAMS = ["WOBBE","PCS","DENS_REL","S_TOTAL","H2S_COS","RSH","O2","CO2","PR_H2O","PR_HC"]
PNOM = {"WOBBE":"Índice de Wobbe","PCS":"PCS (poder calorífico superior)","DENS_REL":"Densidad relativa",
 "S_TOTAL":"Azufre total (S)","H2S_COS":"H₂S + COS","RSH":"Mercaptanos (RSH)","O2":"O₂ (oxígeno)",
 "CO2":"CO₂","PR_H2O":"Punto de rocío del agua","PR_HC":"Punto de rocío de hidrocarburos"}
PDESC = {
 "WOBBE":"Mide la **intercambiabilidad** del gas (aporte calorífico a través de un quemador a presión dada). Criterio clave para saber si dos gases son intercambiables sin reajustar los equipos.",
 "PCS":"**Energía** liberada por la combustión completa de 1 m³ de gas (con el agua de los humos condensada). Es lo que se factura.",
 "DENS_REL":"Densidad del gas dividida por la del aire (adimensional). Interviene en el Índice de Wobbe.",
 "S_TOTAL":"**Azufre total** (todos los compuestos de azufre). Límite ambiental y de corrosión.",
 "H2S_COS":"Sulfuro de hidrógeno + sulfuro de carbonilo, **expresados como azufre**. Corrosión y toxicidad.",
 "RSH":"**Mercaptanos** (azufre mercaptánico). Son los odorizantes; se limitan aparte del H₂S.",
 "O2":"**Oxígeno**. Favorece corrosión y es incompatible con almacenamientos subterráneos.",
 "CO2":"**Dióxido de carbono**. Rebaja el poder calorífico y es corrosivo con humedad.",
 "PR_H2O":"**Punto de rocío del agua**: temperatura a la que condensaría el agua del gas. Evita agua líquida en la red.",
 "PR_HC":"**Punto de rocío de hidrocarburos**: temperatura a la que condensarían los hidrocarburos pesados.",
}
UNID = {"kWh_per_nm3":"kWh/m³","MJ_per_nm3":"MJ/m³","kcal_per_nm3":"kcal/m³","mg_per_nm3":"mg/m³",
 "g_per_nm3":"g/Nm³","pct_mol":"% mol","grados_C":"°C","adimensional":"—"}
COND = {"IT":"15/15","CZ":"15/15","IE":"15/15","RO":"15/15","TR":"15/15","GB":"15/15","UE":"15/15",
 "ES":"0/0","FR":"0/0","SK":"25/20"}
def cond(c): return COND.get(c, "25/0")
def esp(x): return (f"{x:g}").replace(".", ",")
def fmt_lim(l):
    if l is None: return "—"
    if "NO_VERIF" in (l.get("estado_verificacion") or ""): return "*no fijado*"
    u = "" if l.get("unidad") == "adimensional" else UNID.get(l.get("unidad"), l.get("unidad") or "")
    if l.get("valor") is not None:
        v = esp(l["valor"]); return f"≤ {v} {u}".strip() if l.get("tipo_limite")=="maximo" else f"{v} {u}".strip()
    lo, hi = l.get("valor_min"), l.get("valor_max")
    g = lambda x: esp(x) if isinstance(x,(int,float)) else "—"
    return f"{g(lo)} – {g(hi)} {u}".strip()

# ---- Tabla de parámetros ----
t_par = ["| # | Parámetro | Qué mide | Unidad (ES) | Límite en España |","|---|---|---|---|---|"]
for i,p in enumerate(PARAMS,1):
    les = (P[p].get("limites") or {}).get("ES"); u = UNID.get((les or {}).get("unidad"),"—")
    t_par.append(f"| {i} | **{PNOM[p]}** | {PDESC[p]} | {u} | {fmt_lim(les)} |")
TBL_PARAMS = "\n".join(t_par)

# ---- Tabla de jurisdicciones ----
def norma_pais(c):
    cnt = collections.Counter()
    for p in PARAMS:
        l = (P[p].get("limites") or {}).get(c)
        if l and l.get("fuente"): cnt[l["fuente"]]+=1
    if not cnt: return "—"
    return FU.get(cnt.most_common(1)[0][0],{}).get("nombre","—")
def corta(s,n=64):
    s=(s or "").split(" — ")[0].split(" («")[0].split(", de ")[0].split(": «")[0]
    return (s[:n]+"…") if len(s)>n else s
t_jur = ["| País | Cód. | Norma de referencia | Cond. |","|---|---|---|---|"]
for c in CODES:
    t_jur.append(f"| {COD2NOM[c]}{' *(base)*' if c=='ES' else ''} | {c} | {corta(norma_pais(c))} | {cond(c)} |")
TBL_JUR = "\n".join(t_jur)

# ---- Cobertura ----
def celda(p,c):
    l=(P[p].get("limites") or {}).get(c)
    if l is None: return "·"
    e=l.get("estado_verificacion","")
    return "✓" if e=="VERIFICADO" else ("○" if "NO_VERIF" in e else "?")
verif=sum(1 for p in PARAMS for c in CODES if celda(p,c)=="✓")
noverf=sum(1 for p in PARAMS for c in CODES if celda(p,c)=="○")
t_cov=["| Parámetro | "+" | ".join(CODES)+" |","|---|"+"|".join([":-:"]*len(CODES))+"|"]
for p in PARAMS:
    t_cov.append(f"| {PNOM[p].split(' (')[0]} | "+" | ".join(celda(p,c) for c in CODES)+" |")
TBL_COV="\n".join(t_cov)
gaps=collections.defaultdict(list)
for p in PARAMS:
    for c in CODES:
        l=(P[p].get("limites") or {}).get(c)
        if l and "NO_VERIF" in (l.get("estado_verificacion") or ""): gaps[c].append(PNOM[p].split(" (")[0])
t_gap=["| País | Parámetros que su norma no fija |","|---|---|"]
for c in CODES:
    if gaps[c]: t_gap.append(f"| {COD2NOM[c]} | {', '.join(gaps[c])} |")
TBL_GAPS="\n".join(t_gap)

# ---- Ejemplo real de bloque de límite ----
raw=io.open(ONT,encoding="utf-8").read().split("\n")
def bloque(param,code):
    out=[];en_par=en_lim=cap=False
    import re
    for s in raw:
        if s.startswith(f"  {param}:"): en_par=True; continue
        if en_par and s.strip()=="limites:": en_lim=True; continue
        if en_lim and not cap:
            m=re.match(r"^(\s{6})([A-Za-z]+):\s*$",s)
            if m and m.group(2)==code: cap=True; out.append(s); continue
        elif cap:
            if re.match(r"^(\s{6})([A-Za-z]+):\s*$",s): break
            out.append(s)
            if len(out)>13: break
    return "\n".join(out)
EJ_ES = bloque("O2","ES")

# ---- Ampliación: biometano e hidrógeno (dinámico desde la ontología) ----
PB = d.get("parametros_biometano") or {}
PH = d.get("parametros_hidrogeno") or {}
def _estados(P):
    c = collections.Counter()
    for v in P.values():
        for lim in (v.get("limites") or {}).values():
            c[(lim or {}).get("estado_verificacion", "?")] += 1
    return c
EB, EH = _estados(PB), _estados(PH)
bio_verif = EB.get("VERIFICADO", 0); bio_sec = EB.get("VERIFICADO_SECUNDARIO", 0)
bio_nov = EB.get("NO_VERIFICABLE_SIN_FUENTE", 0)
h2_verif = EH.get("VERIFICADO", 0); h2_sec = EH.get("VERIFICADO_SECUNDARIO", 0)
h2_nov = EH.get("NO_VERIFICABLE_SIN_FUENTE", 0)
n_bio, n_h2 = len(PB), len(PH)
n_gases = len(ONTO.get("tipos_gas", []) or [])

SEC_AMPLIACION = f"""## 15. Ampliación del alcance: biometano e hidrógeno

El sistema nació para el gas natural y se ha ampliado a **biometano** e **hidrógeno** como una
**capa aditiva**. Se añade una dimensión de **tipo de gas** (registrada en `tipos_gas`, con
{n_gases} valores) que por defecto vale `gas_natural`: así **todo el gas natural queda intacto**
—mismo motor, mismas garantías, mismas pruebas— y los gases nuevos **reutilizan la misma
maquinaria** (consulta, comparativa, matriz, normalización ISO 13443 y estados de verificación).
El principio de **cero cifras inventadas** se mantiene idéntico.

| Tipo de gas | Sección de la ontología | Jurisdicciones | Parámetros |
|---|---|---|---|
| **Gas natural** | `parametros` | 21 (España … UE) | {len(PARAMS)} |
| **Biometano** | `parametros_biometano` | 4 · España · Portugal · Francia · UE | {n_bio} |
| **Hidrógeno** | `parametros_hidrogeno` | RED (CEN · GIE/UE · ES · FR · PT) + producto (ISO 14687) | {n_h2} |

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

Cobertura: **{bio_verif} valores verificados** (verbatim), **{bio_sec} verificados por fuente
pública secundaria** (norma primaria de pago) y **{bio_nov} no verificables** (la norma no fija
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
**{h2_verif} verificados**, **{h2_sec} por fuente secundaria** y **{h2_nov} no verificables**.

### 15.3. Estudio de terminología (¿hace falta una capa semántica?)

Antes de nada se midió cuánto varían los **nombres** de un mismo parámetro entre normas (índice de
variación terminológica): **27,4** en gas natural, **9,2** en biometano y **7,3** en hidrógeno
(umbral 7,0), según `Estudio_Terminologia_Biometano.md`. El estudio **justifica** una capa de
búsqueda semántica multilingüe, que se deja **preparada y opcional** (no activa por defecto): sin
ella, la búsqueda documental es la léxica descrita en §12, plenamente reproducible.

---

"""

# =====================================================================
MDTXT = f"""# Documentación técnica — Comparador Regulatorio de Calidad de Gas

*Gas natural · biometano · hidrógeno. Documento único de referencia: consolida toda la
explicación del sistema —qué hace, cómo está construido y cómo funciona cada componente—.
Cotejado con el código y con los datos reales — versión de ontología **{ONTO.get('version')}**,
revisión **{ONTO.get('fecha_revision')}**. Los diagramas de arquitectura y de la ontología se
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
| **Preguntas_Respuestas_Defensa** | MD · PDF | Batería de preguntas y respuestas para preparar la defensa del proyecto. |
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

El **Comparador** es un asistente que compara esa calidad regulatoria entre **{len(CODES)}
jurisdicciones** y **{len(PARAMS)} parámetros**, y responde en lenguaje natural. Su principio
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
| **2. Ontología** | Fichero estructurado con las **{len(PARAMS)*len(CODES)} cifras** extraídas de esos PDF | Repositorio del que salen las respuestas. |
| **3. Índice documental (RAG)** | Índice del **texto** de los PDF, segmentado en fragmentos con solape (continuos, cruzan el salto de página) | Buscador interno, para consultas abiertas. |

Las **cifras** residen en la capa 2 (la ontología), y cada una referencia su documento
oficial de la capa 1. La capa 3 **no es fuente de cifras**: es un índice de búsqueda sobre el
texto de los documentos (que se devuelve citado, nunca como valores extraídos). Los documentos
(~25 PDF) se guardan **localmente** en `data/raw` para no depender de la disponibilidad de sitios
web externos.

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
| `ontologia.fuentes_normativas` | El **catálogo de las {len(FU)} normas** oficiales: `id`, `nombre`, `organismo`, `publicacion`, `url` (cita) y `pdf` (copia local). |
| `ontologia.tipos_gas` | El **registro de los {n_gases} tipos de gas** (gas natural, biometano, hidrógeno) y a qué sección de parámetros apunta cada uno. |
| `parametros` | **Gas natural**: los **{len(PARAMS)} parámetros**, cada uno con un bloque `limites:` con una entrada **por país** (×{len(CODES)}). |
| `parametros_biometano` | **Biometano**: {n_bio} parámetros, con `limites:` por jurisdicción (España, Portugal, Francia, UE). |
| `parametros_hidrogeno` | **Hidrógeno**: {n_h2} parámetros, con `limites:` por jurisdicción (dominio de red y de producto). |

Las tres secciones de parámetros comparten **exactamente el mismo esquema** (ver §5.2); solo
cambian el conjunto de jurisdicciones y las fuentes. El detalle del biometano y del hidrógeno
está en la §15.

![Estructura de la ontología](Ontologia_Estructura.png)

### 5.2. Anatomía de un valor

Cada límite (por parámetro y país) **no es solo un número**: guarda todo su contexto
normativo. Ejemplo real del O₂ de España, con cada campo anotado:

```yaml
{EJ_ES}
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

- **`VERIFICADO`** — cifra contrastada **verbatim** contra su fuente oficial ({verif} valores).
- **`NO_VERIFICABLE_SIN_FUENTE`** — la norma citada **no fija** esa cifra → **no se inventa**,
  se marca como hueco honesto y se explica ({noverf} valores).

En gas natural solo se dan esos dos estados. Existe además un tercero, **`VERIFICADO_SECUNDARIO`**
—para las normas de pago, sobre todo en biometano e hidrógeno—: el valor se toma de una fuente
pública secundaria citada (ver §15). *(Ejemplo: en Dinamarca, los límites de O₂/CO₂ de la norma corresponden al biogás
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

El volumen de datos es reducido ({len(PARAMS)*len(CODES)} registros) pero con abundante matiz
por celda. Un fichero estructurado en formato YAML (legible por una persona) resulta más
**auditable** y **trazable** que una base de datos relacional, y se versiona en el control de
cambios (git) junto con el código. Para esta escala, una base de datos añadiría complejidad
sin beneficio.

---

## 6. Los 10 parámetros de calidad

{TBL_PARAMS}

> La "unidad (ES)" es la que usa la normativa española; cuando otro país usa otra unidad o
> condiciones, el sistema **normaliza** antes de comparar (ver §10).

---

## 7. Las {len(CODES)} jurisdicciones y sus normas

Cada país aporta sus límites desde su **fuente oficial**. España es siempre la **base de
referencia** de la comparación. «Cond.» = temperatura de combustión / volumen (°C).

{TBL_JUR}

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
  dos de la ampliación —*Comparativa biometano* y *Comparativa hidrógeno*— con el mismo
  formato (ver §15).
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

Cobertura actual **del gas natural**: **{verif} celdas VERIFICADO**, **{noverf} NO_VERIFICABLE**,
0 pendientes, sobre {len(PARAMS)*len(CODES)} celdas ({len(PARAMS)} parámetros × {len(CODES)}
jurisdicciones). Las {len(PARAMS)*len(CODES)} celdas resuelven por la ruta real de la aplicación.
*(La cobertura de biometano e hidrógeno se detalla en la §15.)*

**✓** = verificado verbatim · **○** = la norma no fija ese parámetro (hueco honesto)

{TBL_COV}

Los huecos **no** son errores: son parámetros que **la norma de ese país no fija
numéricamente** (y por política no se inventan). Detalle:

{TBL_GAPS}

---

{SEC_AMPLIACION}## 16. Metodología de construcción y verificación

Para cada jurisdicción: (1) se identificó la **normativa oficial vigente**; (2) se **obtuvo el
documento** y se archivó localmente; (3) se **transcribió cada cifra literalmente**, sin
interpretación; (4) se **verificó individualmente** contra el documento; (5) lo que la norma
**no fija, no se completa** (se marca como no verificable, con su justificación); (6) se
incorporó la **normalización** (ISO 13443) para comparaciones homogéneas.

El proceso cuenta con **controles de calidad automatizados** que comprueban que las
{len(PARAMS)*len(CODES)} celdas se resuelven, que los enlaces a las fuentes funcionan y que no
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
| Normalización **"con `pint`"** | `pint` no se importa; los factores de conversión provienen de la norma **ISO 13443** (transcritos y verificados, sin librería externa) |
| Interfaz con **Streamlit** (prototipo inicial) | **`index.html`** (JavaScript puro) servido por FastAPI |

---

## 20. Alcance y limitaciones del prototipo

Para una lectura honesta, conviene explicitar qué es y qué no es hoy el sistema:

- **Prototipo demostrativo, no producción.** Está pensado para **uso interno/local** (se sirve por
  HTTP; ver §18) y para demostrar la arquitectura y el rigor de los datos, no para una explotación a
  gran escala ni multiusuario concurrente.
- **Sin autenticación.** No incorpora control de acceso ni gestión de usuarios: se asume una red de
  confianza. Añadir autenticación —o servir tras un proxy inverso con TLS— queda para el despliegue (§18).
- **Cobertura de datos delimitada.** Gas natural: {len(PARAMS)} parámetros × {len(CODES)}
  jurisdicciones ({verif} verificados, {noverf} no verificables). Biometano e hidrógeno: alcance
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
- **Ontología:** repositorio estructurado donde residen las {len(PARAMS)*len(CODES)} cifras con
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
"""

io.open(MD, "w", encoding="utf-8", newline="\n").write(MDTXT)
print("MD generado:", os.path.relpath(MD, RAIZ), f"({len(MDTXT)//1024} KB)")

# ---------------- PDF ----------------
_REEMP = {"₂":"2","₃":"3","₁":"1","₀":"0","·":"-","→":"->","×":"x","↔":"<->","≤":"<=","≥":">=","≈":"~"}
def _f(*n):
    for x in n:
        r=os.path.join("C:\\Windows\\Fonts",x)
        if os.path.exists(r): return r.replace("\\","/")
    return None
def _link(uri, rel):
    if os.path.isabs(uri) and os.path.exists(uri): return uri
    c=os.path.join(AQUI,uri); return c if os.path.exists(c) else uri
texto=MDTXT
for a,b in _REEMP.items(): texto=texto.replace(a,b)
cuerpo=markdown.markdown(texto, extensions=["tables","fenced_code","sane_lists"])
arial=_f("arial.ttf"); arialbd=_f("arialbd.ttf"); mono=_f("consola.ttf","cour.ttf")
fc,fm="Helvetica","Courier"
if arial:
    pdfmetrics.registerFont(TTFont("Cuerpo",arial))
    if arialbd:
        pdfmetrics.registerFont(TTFont("Cuerpo-Bold",arialbd)); pdfmetrics.registerFontFamily("Cuerpo",normal="Cuerpo",bold="Cuerpo-Bold")
    fc="Cuerpo"
if mono: pdfmetrics.registerFont(TTFont("Mono",mono)); fm="Mono"
css=f"""
@page {{ size:A4; margin:1.7cm 1.5cm; }}
body {{ font-family:"{fc}"; font-size:10.5px; color:#1b2a38; line-height:1.45; }}
h1 {{ color:#013a57; font-size:21px; border-bottom:2px solid #0099d6; padding-bottom:4px; }}
h2 {{ color:#013a57; font-size:15px; margin-top:16px; border-bottom:1px solid #dde4ea; padding-bottom:2px; }}
h3 {{ color:#0077ab; font-size:12.5px; margin-top:11px; }}
p,li {{ font-size:10.5px; }}
em {{ color:#5d7082; }}
code {{ font-family:"{fm}"; background:#eef2f6; font-size:9px; }}
pre {{ font-family:"{fm}"; background:#f5f8fa; border:1px solid #dde4ea; padding:8px; font-size:8px; line-height:1.2; }}
table {{ border-collapse:collapse; width:100%; margin:6px 0; }}
th {{ background:#013a57; color:#fff; font-size:8.5px; text-align:left; padding:4px 6px; }}
td {{ border:1px solid #dde4ea; font-size:8.8px; padding:4px 6px; vertical-align:top; }}
tr:nth-child(even) td {{ background:#f5f8fa; }}
blockquote {{ background:#eef7fc; border-left:3px solid #0099d6; margin:6px 0; padding:5px 10px; color:#0a4e74; font-size:9.8px; }}
hr {{ border:0; border-top:1px solid #dde4ea; }}
strong {{ color:#013a57; }}
img {{ width:470px; }}
"""
html=f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{cuerpo}</body></html>'
with open(PDF,"wb") as fh:
    res=pisa.CreatePDF(html, dest=fh, encoding="utf-8", link_callback=_link)
if res.err: raise SystemExit(f"Error generando el PDF ({res.err}).")
print("PDF generado:", os.path.relpath(PDF, RAIZ), f"({os.path.getsize(PDF)//1024} KB)")
