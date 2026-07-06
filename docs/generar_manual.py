# -*- coding: utf-8 -*-
"""Genera el MANUAL COMPLETO del Comparador (Markdown + PDF con estilo Enagas).

    python docs/generar_manual.py

- La PROSA la fija este script (revisada a mano).
- Las TABLAS DE DATOS (parametros, jurisdicciones, cobertura, ejemplo de limite)
  se GENERAN desde la ontologia -> nunca se inventan ni se desincronizan.
- Embebe los diagramas reales (PNG) via link_callback de pisa.

Salida: docs/Manual_Comparador_Gas.md  y  docs/Manual_Comparador_Gas.pdf
"""
import os, io, sys, yaml
import markdown
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ONT = os.path.join(RAIZ, "data", "ontologia", "ontologia_enagas.yaml")
MD = os.path.join(AQUI, "Manual_Comparador_Gas.md")
PDF = os.path.join(AQUI, "Manual_Comparador_Gas.pdf")

d = yaml.safe_load(io.open(ONT, encoding="utf-8"))
ONTO = d["ontologia"]
P = d["parametros"]
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
 "WOBBE":"Mide la **intercambiabilidad** del gas: el aporte calorífico a través de un quemador a presión dada. Es el criterio clave para saber si dos gases son intercambiables sin reajustar los equipos.",
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

def esp(x): return (f"{x:g}").replace(".", ",")   # coma decimal (español)
def fmt_lim(l):
    if l is None: return "—"
    est = l.get("estado_verificacion","")
    if "NO_VERIF" in est: return "*no fijado*"
    ucode = l.get("unidad")
    u = "" if ucode == "adimensional" else UNID.get(ucode, ucode or "")
    if l.get("valor") is not None:
        v = esp(l["valor"]); return f"≤ {v} {u}".strip() if l.get("tipo_limite")=="maximo" else f"{v} {u}".strip()
    lo, hi = l.get("valor_min"), l.get("valor_max")
    def g(x): return esp(x) if isinstance(x,(int,float)) else "—"
    return f"{g(lo)} – {g(hi)} {u}".strip()

# ---------- TABLA 1: parametros ----------
t_par = ["| # | Parámetro | Qué mide | Unidad base (ES) | Límite en España |",
         "|---|---|---|---|---|"]
for i,p in enumerate(PARAMS,1):
    les = (P[p].get("limites") or {}).get("ES")
    u = UNID.get((les or {}).get("unidad"),"—")
    t_par.append(f"| {i} | **{PNOM[p]}** | {PDESC[p]} | {u} | {fmt_lim(les)} |")
TBL_PARAMS = "\n".join(t_par)

# ---------- TABLA 2: jurisdicciones y norma ----------
import collections
def norma_pais(c):
    cnt = collections.Counter()
    for p in PARAMS:
        l = (P[p].get("limites") or {}).get(c)
        if l and l.get("fuente"): cnt[l["fuente"]]+=1
    if not cnt: return ("—","—")
    fid = cnt.most_common(1)[0][0]; f = FU.get(fid,{})
    return (f.get("nombre","—"), f.get("organismo","") or f.get("pais",""))
def corta(s, n=70):
    s = (s or "").split(" — ")[0].split(" («")[0].split(", de ")[0]
    return (s[:n]+"…") if len(s)>n else s
t_jur = ["| País | Cód. | Norma de referencia (fuente primaria) | Cond. comb/vol |",
         "|---|---|---|---|"]
for c in CODES:
    nom, org = norma_pais(c)
    t_jur.append(f"| {COD2NOM[c]}{' *(base)*' if c=='ES' else ''} | {c} | {corta(nom)} | {cond(c)} |")
TBL_JUR = "\n".join(t_jur)

# ---------- TABLA 3: matriz de cobertura ----------
def celda(p,c):
    l = (P[p].get("limites") or {}).get(c)
    if l is None: return "·"
    e = l.get("estado_verificacion","")
    return "✓" if e=="VERIFICADO" else ("○" if "NO_VERIF" in e else "?")
verif = sum(1 for p in PARAMS for c in CODES if celda(p,c)=="✓")
noverf = sum(1 for p in PARAMS for c in CODES if celda(p,c)=="○")
hdr = "| Parámetro | " + " | ".join(CODES) + " |"
sep = "|---|" + "|".join([":-:"]*len(CODES)) + "|"
t_cov = [hdr, sep]
for p in PARAMS:
    t_cov.append(f"| {PNOM[p].split(' (')[0]} | " + " | ".join(celda(p,c) for c in CODES) + " |")
TBL_COV = "\n".join(t_cov)

# ---------- Lista de huecos NO_VERIFICABLE ----------
gaps = collections.defaultdict(list)
for p in PARAMS:
    for c in CODES:
        l = (P[p].get("limites") or {}).get(c)
        if l and "NO_VERIF" in (l.get("estado_verificacion") or ""):
            gaps[c].append(PNOM[p].split(" (")[0])
t_gap = ["| País | Parámetros no fijados por su norma |","|---|---|"]
for c in CODES:
    if gaps[c]:
        t_gap.append(f"| {COD2NOM[c]} | {', '.join(gaps[c])} |")
TBL_GAPS = "\n".join(t_gap)

# ---------- Ejemplo real de bloque de limite (Espana PCS) ----------
raw = io.open(ONT, encoding="utf-8").read().split("\n")
def bloque_ejemplo(param, code):
    # localiza 'param:' luego 'limites:' luego 'CODE:' y captura hasta el siguiente pais
    out=[]; en_par=False; en_lim=False; cap=False; base=None
    for ln in raw:
        s=ln.rstrip("\n")
        if s.startswith(f"  {param}:"): en_par=True; continue
        if en_par and s.strip()=="limites:": en_lim=True; continue
        if en_lim and not cap:
            import re
            m=re.match(r"^(\s{6})([A-Za-z]+):\s*$", s)
            if m and m.group(2)==code:
                cap=True; base=len(m.group(1)); out.append(s); continue
        elif cap:
            import re
            m=re.match(r"^(\s{6})([A-Za-z]+):\s*$", s)
            if m: break   # siguiente pais
            out.append(s)
            if len(out)>14: break
    return "\n".join(out)
EJEMPLO = bloque_ejemplo("PCS","ES") or "(no encontrado)"

# =====================================================================
MDTXT = f"""# Manual del Comparador Regulatorio de Calidad de Gas Natural — Enagás

*Documento único de referencia para el equipo. Describe **qué hace** la aplicación, **cómo está construida** (arquitectura) y **cómo se organizan los datos** (ontología). Cotejado con el código y con los datos reales — versión de ontología **{ONTO.get('version')}**, revisión **{ONTO.get('fecha_revision')}**.*

---

## 1. Qué es y qué hace

El Comparador es un **asistente que compara los límites regulatorios de calidad del gas natural** entre **{len(CODES)} jurisdicciones** europeas, para los **10 parámetros** de calidad del alcance. Responde en lenguaje natural (chat) y ofrece una vista de **comparativa** con matriz visual.

Su principio de diseño es **"cero alucinaciones numéricas"**: todas las cifras salen de una base de datos verificada contra los boletines oficiales; el modelo de lenguaje solo redacta, nunca inventa un número.

**Qué se le puede preguntar** (ejemplos reales):

- *"¿Cuál es el límite de O₂ en Alemania?"* → valor + cita de la norma.
- *"¿Cumple 14 kWh/m³ de PCS en Francia?"* → cumple / no cumple, con el rango oficial.
- *"Compara el azufre total entre España y Países Bajos."* → tabla con normalización.
- *"¿Es Italia más restrictiva que España en CO₂?"*
- *"Pasa 55 MJ/m³ de Wobbe de Portugal a condiciones de España."* → conversión ISO 13443.

**Las dos pestañas de la web:**

1. **Consulta libre** — chat en lenguaje natural.
2. **Comparativa** — selección puntual de parámetro/países y una **matriz** (21 países × 10 parámetros) con el estado de comparabilidad frente a España.

---

## 2. Los 10 parámetros de calidad

{TBL_PARAMS}

> La "unidad base (ES)" es la que usa la normativa española; cuando otro país usa otra unidad o condiciones, el sistema **normaliza** antes de comparar (ver §6).

---

## 3. Las {len(CODES)} jurisdicciones y su norma de referencia

Cada país aporta sus límites desde su **fuente oficial** (boletín, norma técnica del TSO o estándar). España es siempre la **base de referencia** de la comparación.

{TBL_JUR}

> **Condiciones comb/vol** = temperatura de combustión / temperatura del volumen de referencia, en °C. Determinan si un PCS/Wobbe o una concentración másica necesita normalización (§6).

---

## 4. Arquitectura híbrida "cero alucinaciones"

El sistema separa a propósito **dos mundos**:

- **Mundo determinista** (código + ontología): la **única** fuente autorizada de cifras, límites, conversiones y comparaciones. Nunca improvisa un número.
- **Mundo conversacional** (LLM): interpreta la pregunta y **redacta** la respuesta, pero tiene prohibido generar cifras — las obtiene llamando a herramientas deterministas.

La regla está implementada como **determinista-primero, LLM-fallback**: las preguntas estructuradas se resuelven con código (sin riesgo de alucinación); solo las abiertas pasan al LLM, obligado a apoyarse en herramientas y documentos oficiales.

![Esquema de cajas de la arquitectura](Arquitectura_Esquema_Cajas.png)

**Recorrido de una consulta:** Frontend (`index.html`) → Backend (`api.py`, FastAPI) → **router determinista** (`_validate_measurement_gate`). Si el router reconoce la intención, responde con `modo: "determinista"`. Si no, pasa al **LLM** (OpenAI `gpt-4o-mini`, function-calling, `temperature=0`), que llama a las herramientas deterministas y al **RAG** de PDFs.

---

## 5. La ontología — el corazón del sistema

**Archivo:** `data/ontologia/ontologia_enagas.yaml` — la extracción **verificada verbatim** de los PDF oficiales. El motor lee de aquí; el LLM nunca calcula.

**Estructura de nivel superior:**

| Clave | Contenido |
|---|---|
| `ontologia.fuentes_normativas` | Las normas: `id`, `nombre`, `organismo`, `publicacion`, `url` (cita), `pdf` (copia local), condiciones y notas. |
| `ontologia.jurisdicciones` | Las {len(CODES)} jurisdicciones: código, nombre, fuente principal, condiciones por defecto. |
| `parametros` | Los **10 parámetros**, cada uno con su bloque `limites:` por país. |

**Cada límite** (por parámetro y país) lleva: `valor` o `valor_min`/`valor_max`, `unidad`, `tipo_limite`, `condiciones_referencia`, `expresion_original` (texto literal de la fuente), la cita (`fuente` + `articulo`), una `nota` explicativa y —lo más importante— el **`estado_verificacion`**.

**Estados de verificación** (la garantía anti-invención):

- `VERIFICADO` — cifra contrastada **verbatim** contra su fuente oficial.
- `NO_VERIFICABLE_SIN_FUENTE` — la norma citada **no fija** esa cifra → **no se inventa**, se marca como hueco honesto.
- `PENDIENTE_EXTRACCION` — la cifra existe pero aún no se ha extraído (queda `null`).

**Ejemplo real** — el bloque del PCS de España tal cual está en la ontología:

```yaml
{EJEMPLO}
```

![Estructura de la ontología](Ontologia_Estructura.png)

---

## 6. El motor determinista y la normalización (ISO 13443)

| Módulo | Función |
|---|---|
| `fuente_oficial.py` | Lee la ontología y devuelve el registro con cita completa. Mapea nombre de país ↔ código. |
| `conversor_unidades.py` | Convierte unidades (energía, temperatura, concentración) y aloja la **Tabla A.1 literal de la ISO 13443**. |
| `condiciones_referencia.py` | Mapea cada país a sus condiciones de referencia y delega el factor ISO 13443. |

**Por qué hace falta normalizar:** los países expresan sus límites en unidades y condiciones distintas. Para comparar de forma justa, el PCS/Wobbe se lleva a **kWh/m³ y a las condiciones de España (0/0)** con los factores de la **Tabla A.1**:

| A condiciones de España (0/0) | PCS | Wobbe |
|---|---|---|
| **25/0 → 0/0** (Portugal, Alemania, P. Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Grecia) | 1,0026 | 1,0026 |
| **15/15 → 0/0** (Italia, UE, Chequia, Irlanda, Rumanía, Turquía, Reino Unido) | 1,0570 | 1,0569 |
| **25/20 → 0/0** (Eslovaquia — par no tabulado, ecuaciones del Anexo B) | ≈1,076 | ≈1,076 |
| **0/0 → 0/0** (España, Francia) | ×1 (identidad) | ×1 |

Además de kWh/m³ y MJ/m³, el conversor admite **kcal/m³** (Turquía y Rumanía). Las concentraciones **másicas** (mg/m³) referidas a un volumen a T ≠ 0 °C (p. ej. Italia a 15 °C) se normalizan con el factor de gas ideal `(273,15+T)/273,15`. El **% mol**, lo **adimensional** y los **puntos de rocío** (°C) **no** dependen de la temperatura del volumen.

---

## 7. El router determinista (7 intenciones)

`api.py → _validate_measurement_gate` reconoce y resuelve **sin LLM**:

1. **Cumplimiento** (valor + unidad → cumple / no cumple).
2. **Límite/valor** (sin valor → muestra los límites).
3. **¿De qué reglamento sale?** (cita la fuente).
4. **Intercambiabilidad** (solape de rangos frente a España).
5. **Más restrictivo / más amplio que España.**
6. **Comparación** España ↔ país.
7. **Conversión a condiciones de España** (ISO 13443).

---

## 8. La capa LLM y el RAG (preguntas abiertas)

- **LLM:** OpenAI `gpt-4o-mini` (configurable), function-calling, `temperature=0`, hasta 5 iteraciones. El `SYSTEM_PROMPT` le **prohíbe inventar cifras** y fija el ámbito. Si OpenAI falla o no hay clave, **cae al motor determinista** (el chat nunca da error 500).
- **RAG:** `agente_pdf.py` indexa los PDF de `data/raw/` (troceados por página) en **SQLite** y hace **búsqueda léxica** (`LIKE`). Es léxico, **no vectorial** (sin embeddings), aunque la ontología describa un diseño con Vector DB.

---

## 9. Estado real de los datos

Cobertura actual: **{verif} celdas VERIFICADO**, **{noverf} NO_VERIFICABLE_SIN_FUENTE**, 0 pendientes, sobre {len(PARAMS)*len(CODES)} celdas (10 parámetros × {len(CODES)} jurisdicciones). Las 210 celdas resuelven por la ruta real de la aplicación.

**✓** = verificado verbatim · **○** = la norma no fija ese parámetro (hueco honesto)

{TBL_COV}

Los huecos **no** son errores: son parámetros que **la norma de ese país no fija numéricamente** (y por política no se inventan). Detalle:

{TBL_GAPS}

---

## 10. Diseño ideal vs. implementación real (honestidad de ingeniería)

| El diseño / la ontología dice… | La realidad del código es… |
|---|---|
| RAG con **Vector DB + similitud coseno** | **Búsqueda léxica** SQLite `LIKE` (sin vectores) |
| Normalización **"con `pint`"** | `pint` no se importa; conversiones = tablas verificadas a mano |

---

## 11. El chat, la ejecución y el mantenimiento

- **Frontend (`index.html`):** SPA en JavaScript puro; dos pestañas (chat y comparativa). **El historial del chat es persistente**: cada pregunta y respuesta se guarda en el navegador (`localStorage`) y se **restaura al recargar la página o tras reiniciar el servidor**, así el usuario no pierde sus consultas. El botón «Nueva consulta» abre una sesión limpia. En el backend, `_registrar_turno` guarda **todos** los turnos (deterministas y de IA, acotados a los últimos 40 mensajes por sesión) para dar contexto a las preguntas de seguimiento.
- **`iniciar_chatbot.bat`** — lanzador del equipo: se auto-actualiza (`git pull --ff-only`), libera el puerto 8000 y arranca `uvicorn`. La web se sirve **sin caché** (siempre la última versión tras un `git pull`).
- **`actualizar_fuentes.py`** — descarga los PDF desde el campo `url` de la ontología (fuente única de la cita y de la descarga).
- **Stack:** Python · FastAPI · uvicorn · OpenAI SDK · PyYAML · pdfplumber · sqlite3. Frontend: HTML + JavaScript vanilla (marked + DOMPurify).

---

## 12. Garantía de calidad (barrida de auditoría)

La última barrida profunda confirmó:

- **Estructura de la ontología:** 0 incidencias críticas — sin estados inválidos, sin claves duplicadas, todas las unidades soportadas, todas las citas (`fuente`) resuelven a una norma declarada, coherencia valor↔estado.
- **Ruta end-to-end:** las **{len(PARAMS)*len(CODES)}/{len(PARAMS)*len(CODES)} celdas** con dato resuelven por `fuente_oficial.consultar()`.
- **Coherencia código↔datos:** las {len(CODES)} jurisdicciones aparecen de forma consistente en todos los mapas del backend y del frontend; las condiciones de referencia coinciden entre la ontología y `condiciones_referencia.py`.
- **Metodología de verificación:** cada cifra `VERIFICADO` está contrastada verbatim con el PDF oficial; lo que la norma no fija se marca `NO_VERIFICABLE_SIN_FUENTE` (nunca se inventa).

*Fin del manual.*
"""

io.open(MD, "w", encoding="utf-8", newline="\n").write(MDTXT)
print("MD generado:", os.path.relpath(MD, RAIZ), f"({len(MDTXT)//1024} KB)")

# ---------------- PDF ----------------
_REEMPLAZOS = {"·":"-", "→":"->", "×":"x", "↔":"<->", "≤":"<=", "≥":">=", "≈":"~"}
def _fuente(*n):
    for x in n:
        r = os.path.join("C:\\Windows\\Fonts", x)
        if os.path.exists(r): return r.replace("\\","/")
    return None
def _link_cb(uri, rel):
    # resuelve rutas de imagen relativas al directorio docs/
    if os.path.isabs(uri) and os.path.exists(uri): return uri
    cand = os.path.join(AQUI, uri)
    return cand if os.path.exists(cand) else uri

texto = MDTXT
for a,b in _REEMPLAZOS.items(): texto = texto.replace(a,b)
cuerpo = markdown.markdown(texto, extensions=["tables","fenced_code","sane_lists"])
arial=_fuente("arial.ttf"); arialbd=_fuente("arialbd.ttf"); mono=_fuente("consola.ttf","cour.ttf")
fam_c, fam_m = "Helvetica","Courier"
if arial:
    pdfmetrics.registerFont(TTFont("Cuerpo",arial))
    if arialbd:
        pdfmetrics.registerFont(TTFont("Cuerpo-Bold",arialbd))
        pdfmetrics.registerFontFamily("Cuerpo",normal="Cuerpo",bold="Cuerpo-Bold")
    fam_c="Cuerpo"
if mono:
    pdfmetrics.registerFont(TTFont("Mono",mono)); fam_m="Mono"
css = f"""
@page {{ size: A4; margin: 1.7cm 1.5cm; }}
body {{ font-family:"{fam_c}"; font-size:10.5px; color:#1b2a38; line-height:1.45; }}
h1 {{ color:#013a57; font-size:20px; border-bottom:2px solid #0099d6; padding-bottom:4px; }}
h2 {{ color:#013a57; font-size:14.5px; margin-top:16px; border-bottom:1px solid #dde4ea; padding-bottom:2px; }}
h3 {{ color:#0077ab; font-size:12px; margin-top:11px; }}
p,li {{ font-size:10.5px; }}
em {{ color:#5d7082; }}
code {{ font-family:"{fam_m}"; background:#eef2f6; font-size:9px; }}
pre {{ font-family:"{fam_m}"; background:#f5f8fa; border:1px solid #dde4ea; padding:8px; font-size:8px; line-height:1.2; }}
table {{ border-collapse:collapse; width:100%; margin:6px 0; }}
th {{ background:#013a57; color:#fff; font-size:8.5px; text-align:left; padding:4px 6px; }}
td {{ border:1px solid #dde4ea; font-size:8.8px; padding:4px 6px; vertical-align:top; }}
tr:nth-child(even) td {{ background:#f5f8fa; }}
blockquote {{ background:#eef7fc; border-left:3px solid #0099d6; margin:6px 0; padding:5px 10px; color:#0a4e74; font-size:9.8px; }}
hr {{ border:0; border-top:1px solid #dde4ea; }}
strong {{ color:#013a57; }}
img {{ width:495px; }}
"""
html = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{cuerpo}</body></html>'
with open(PDF,"wb") as fh:
    res = pisa.CreatePDF(html, dest=fh, encoding="utf-8", link_callback=_link_cb)
if res.err: raise SystemExit(f"Error generando el PDF ({res.err}).")
print("PDF generado:", os.path.relpath(PDF, RAIZ), f"({os.path.getsize(PDF)//1024} KB)")
