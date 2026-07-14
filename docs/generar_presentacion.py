# -*- coding: utf-8 -*-
"""Genera LA presentación del Comparador Regulatorio de Calidad de Gas (estilo Enagás).

    python docs/generar_presentacion.py

Presentación única y completa, centrada en:
  - la ARQUITECTURA del sistema (esquema DIBUJADO en la propia diapositiva, apaisado),
  - la ONTOLOGÍA (esquema DIBUJADO: el fichero y sus cinco claves),
  - TODAS LAS HERRAMIENTAS que usa la aplicación, indicando el papel de cada una.

Los esquemas NO son imágenes: se dibujan con formas nativas de PowerPoint, adaptadas al
formato 16:9, para que se lean bien y sean editables.
Las cifras de cobertura se leen de la ontología (nunca se teclean a mano).
Incluye NOTAS DEL PONENTE en cada diapositiva.

Salida: docs/Presentacion_Comparador_Gas.pptx
"""
import os
import io
import collections
import yaml
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ONT = os.path.join(RAIZ, "data", "ontologia", "ontologia_enagas.yaml")
PPTX = os.path.join(AQUI, "Presentacion_Comparador_Gas.pptx")

# ----------------------- Datos reales desde la ontología -----------------------
_d = yaml.safe_load(io.open(ONT, encoding="utf-8"))
ONTO = _d["ontologia"]
P = _d["parametros"]
PB = _d.get("parametros_biometano") or {}
PH = _d.get("parametros_hidrogeno") or {}
CODES = ["ES", "PT", "FR", "IT", "DE", "NL", "BE", "NOR", "PL", "DK", "HU",
         "AT", "CH", "CZ", "GR", "IE", "RO", "SK", "TR", "GB", "UE"]
PARAMS = ["WOBBE", "PCS", "DENS_REL", "S_TOTAL", "H2S_COS", "RSH", "O2", "CO2", "PR_H2O", "PR_HC"]

_c = collections.Counter()
for _k in PARAMS:
    for _lim in (P[_k].get("limites") or {}).values():
        _c[(_lim or {}).get("estado_verificacion", "?")] += 1
N_VERIF = _c.get("VERIFICADO", 0)
N_NOVER = _c.get("NO_VERIFICABLE_SIN_FUENTE", 0)
N_CELDAS = len(PARAMS) * len(CODES)
N_JUR, N_PAR = len(CODES), len(PARAMS)
N_FUENTES = len(ONTO["fuentes_normativas"])
N_GASES = len(ONTO.get("tipos_gas", []) or [])
VER_ONT = ONTO.get("version", "—")

# ----------------------------- Paleta y utilidades -----------------------------
AZUL = RGBColor(0x01, 0x3A, 0x57)      # corporativo oscuro
AZUL2 = RGBColor(0x0A, 0x5A, 0x82)     # azul medio
CYAN = RGBColor(0x00, 0x99, 0xD6)      # acento
VERDE = RGBColor(0x6C, 0xB3, 0x3E)
VERDEOS = RGBColor(0x3E, 0x6B, 0x22)
VERDECL = RGBColor(0xE8, 0xF4, 0xE2)
NARANJA = RGBColor(0xE8, 0x8A, 0x1A)
NARANJAOS = RGBColor(0xA5, 0x61, 0x0E)
NARANJACL = RGBColor(0xFD, 0xF0, 0xDF)
GRIS = RGBColor(0x4A, 0x5B, 0x68)
TINTA = RGBColor(0x1B, 0x2A, 0x38)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRISCL = RGBColor(0xEE, 0xF2, 0xF6)
BORDE = RGBColor(0xC8, 0xD4, 0xDD)
AZULCL = RGBColor(0xE4, 0xEF, 0xF6)
FUENTE = "Calibri"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height


def _slide():
    return prs.slides.add_slide(BLANK)


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _shape(slide, forma, l, t, w, h, fill=None, line=None, line_w=None, dash=False):
    shp = slide.shapes.add_shape(forma, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w or 1)
        if dash:
            shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    shp.shadow.inherit = False
    if shp.has_text_frame:
        shp.text_frame.word_wrap = True
    return shp


def _box(slide, l, t, w, h, **kw):
    return _shape(slide, MSO_SHAPE.RECTANGLE, l, t, w, h, **kw)


def _rbox(slide, l, t, w, h, **kw):
    """Rectángulo de esquinas redondeadas (aspecto más cuidado)."""
    shp = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h, **kw)
    try:
        shp.adjustments[0] = 0.06
    except Exception:
        pass
    return shp


def _flecha(slide, l, t, w, h, sentido="der", color=None):
    formas = {"der": MSO_SHAPE.RIGHT_ARROW, "izq": MSO_SHAPE.LEFT_ARROW,
              "arr": MSO_SHAPE.UP_ARROW, "aba": MSO_SHAPE.DOWN_ARROW}
    return _shape(slide, formas[sentido], l, t, w, h, fill=color or CYAN)


def _texto(slide, l, t, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6, font=FUENTE):
    """runs: lista de (texto, size, color, bold, bullet, level)."""
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = Pt(3); tf.margin_right = Pt(3); tf.margin_top = Pt(1); tf.margin_bottom = Pt(1)
    for i, r in enumerate(runs):
        txt, size, color, bold, bullet, level = (r + (None,) * 6)[:6]
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space); p.level = level or 0
        run = p.add_run(); run.text = ("• " + txt) if bullet else txt
        run.font.name = font; run.font.size = Pt(size)
        run.font.color.rgb = color; run.font.bold = bool(bold)
    return tb


def _cabecera(slide, titulo, n, kicker=None):
    _box(slide, 0, 0, 13.333, 1.02, fill=AZUL)
    _box(slide, 0, 1.02, 13.333, 0.055, fill=CYAN)
    ty = 0.24 if kicker else 0.16
    if kicker:
        _texto(slide, 0.55, 0.13, 11.5, 0.26, [(kicker.upper(), 11, CYAN, True, False, 0)])
        ty = 0.38
    _texto(slide, 0.55, ty, 11.6, 0.58, [(titulo, 25, BLANCO, True, False, 0)],
           anchor=MSO_ANCHOR.MIDDLE if not kicker else MSO_ANCHOR.TOP)
    _texto(slide, 0.55, 7.06, 9, 0.32,
           [("Comparador Regulatorio de Calidad de Gas — Enagás", 10, GRIS, False, False, 0)])
    _texto(slide, 12.2, 7.06, 0.85, 0.32, [(str(n), 10, GRIS, False, False, 0)], align=PP_ALIGN.RIGHT)


N = 0


def nxt():
    global N
    N += 1
    return N


def slide_seccion(numero, titulo, subtitulo):
    """Separador de bloque: da ritmo y aspecto profesional."""
    s = _slide()
    _box(s, 0, 0, 13.333, 7.5, fill=AZUL)
    _box(s, 0, 3.35, 13.333, 0.05, fill=CYAN)
    _box(s, 1.1, 2.35, 0.13, 1.6, fill=VERDE)
    _texto(s, 1.5, 2.3, 10.5, 0.6, [(f"BLOQUE {numero}", 14, CYAN, True, False, 0)])
    _texto(s, 1.5, 2.7, 10.8, 0.9, [(titulo, 40, BLANCO, True, False, 0)])
    _texto(s, 1.5, 3.7, 10.8, 0.8, [(subtitulo, 17, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0)])
    nxt()
    return s


def slide_tabla(titulo, headers, filas, notas="", intro=None, col_ratios=None,
                fsize=13, kicker=None):
    s = _slide(); _cabecera(s, titulo, nxt(), kicker)
    top = 1.42
    if intro:
        _texto(s, 0.6, top, 12.1, 0.5, [(intro, 14, GRIS, False, False, 0)])
        top += 0.58
    nrows, ncols = len(filas) + 1, len(headers)
    tw = Inches(12.1)
    # Alto disponible repartido: la tabla ocupa hasta 6.95
    alto = Inches((6.95 - top) / nrows)
    gr = s.shapes.add_table(nrows, ncols, Inches(0.6), Inches(top), tw, alto * nrows).table
    gr.first_row = False; gr.horz_banding = False
    for i in range(nrows):
        gr.rows[i].height = alto
    if col_ratios:
        tot = sum(col_ratios)
        for j, cr in enumerate(col_ratios):
            gr.columns[j].width = int(tw * cr / tot)
    for j, htxt in enumerate(headers):
        c = gr.cell(0, j); c.fill.solid(); c.fill.fore_color.rgb = AZUL
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        c.margin_left = Pt(8); c.margin_top = Pt(2); c.margin_bottom = Pt(2)
        p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = htxt
        r.font.name = FUENTE; r.font.size = Pt(fsize); r.font.bold = True; r.font.color.rgb = BLANCO
    for i, fila in enumerate(filas, start=1):
        for j, val in enumerate(fila):
            c = gr.cell(i, j); c.fill.solid()
            c.fill.fore_color.rgb = GRISCL if i % 2 else BLANCO
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = Pt(8); c.margin_top = Pt(2); c.margin_bottom = Pt(2)
            p = c.text_frame.paragraphs[0]; p.word_wrap = True
            mono = isinstance(val, str) and (val.endswith(".py") or val.startswith("/") or val.startswith("data/"))
            run = p.add_run(); run.text = val
            run.font.name = MONO if mono else FUENTE
            run.font.size = Pt(fsize - 1.5 if mono else fsize)
            run.font.bold = bool(j == 0 and not mono)
            run.font.color.rgb = AZUL if j == 0 else TINTA
    if notas:
        _notes(s, notas)
    return s


def slide_2col(titulo, izq, der, notas="", intro=None, kicker=None, alto=4.6, banda=None):
    """Dos paneles equilibrados: (encabezado, color, [puntos])."""
    s = _slide(); _cabecera(s, titulo, nxt(), kicker)
    top = 1.42
    if intro:
        _texto(s, 0.6, top, 12.1, 0.5, [(intro, 14, GRIS, False, False, 0)])
        top += 0.6
    for (enc, color, puntos), x in ((izq, 0.6), (der, 6.85)):
        _box(s, x, top, 5.9, alto, fill=GRISCL)
        _box(s, x, top, 5.9, 0.5, fill=color)
        _texto(s, x + 0.18, top + 0.06, 5.5, 0.4, [(enc, 15, BLANCO, True, False, 0)])
        runs = []
        for p in puntos:
            if isinstance(p, tuple):
                runs.append((p[0], 12.5, GRIS, False, False, 1))
            else:
                runs.append((p, 14.5, TINTA, False, True, 0))
        _texto(s, x + 0.2, top + 0.68, 5.5, alto - 0.85, runs, space=10)
    if banda:
        by = top + alto + 0.28
        _box(s, 0.6, by, 12.13, 6.92 - by, fill=AZULCL)
        _box(s, 0.6, by, 0.09, 6.92 - by, fill=AZUL)
        runs = [(banda[0], 14, AZUL, True, False, 0)]
        runs += [(t, 12.5, TINTA, False, False, 0) for t in banda[1:]]
        _texto(s, 0.9, by + 0.08, 11.7, 6.8 - by, runs, space=3)
    if notas:
        _notes(s, notas)
    return s


# ================================ CONTENIDO ================================

# ------------------------------ 1. Portada ------------------------------
s = _slide()
_box(s, 0, 0, 13.333, 7.5, fill=AZUL)
_box(s, 0, 4.62, 13.333, 0.06, fill=CYAN)
_box(s, 0.95, 2.05, 0.15, 2.25, fill=VERDE)
_texto(s, 1.35, 2.0, 11, 1.2, [
    ("Comparador Regulatorio", 42, BLANCO, True, False, 0),
    ("de Calidad de Gas", 42, BLANCO, True, False, 0),
], space=2)
_texto(s, 1.38, 4.85, 11, 1.2, [
    ("Arquitectura, ontología y herramientas del sistema", 21, CYAN, False, False, 0),
    (f"Gas natural · biometano · hidrógeno   |   {N_JUR} jurisdicciones · {N_PAR} parámetros · "
     f"{N_CELDAS} valores trazables", 15, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=7)
_texto(s, 1.38, 6.55, 11, 0.4,
       [(f"Ontología v{VER_ONT}  ·  Presentación técnica", 12, RGBColor(0x8F, 0xA6, 0xB8), False, False, 0)])
_notes(s, "Presentación del sistema. El hilo conductor es doble: CÓMO ESTÁ CONSTRUIDO (arquitectura, "
          "ontología y herramientas) y POR QUÉ ES FIABLE (trazabilidad total y cero cifras inventadas).")

# ------------------------------ 2. Índice ------------------------------
s = _slide(); _cabecera(s, "Índice", nxt())
bloques = [
    ("01", "Contexto", ["El problema regulatorio", "El sistema en cifras"], CYAN),
    ("02", "Arquitectura", ["Los cuatro componentes", "El recorrido de una consulta",
                            "Las tres capas de datos"], AZUL2),
    ("03", "Ontología", ["Estructura del fichero", "Anatomía de un valor",
                         "Estados de verificación"], VERDE),
    ("04", "Herramientas", ["El stack completo, pieza a pieza", "Módulos propios y endpoints",
                            "Motor, IA, RAG y ampliación"], NARANJA),
]
x = 0.6
for num, tit, items, color in bloques:
    _box(s, x, 1.75, 2.95, 4.6, fill=GRISCL)
    _box(s, x, 1.75, 2.95, 0.09, fill=color)
    _texto(s, x + 0.22, 1.95, 2.5, 0.6, [(num, 30, color, True, False, 0)])
    _texto(s, x + 0.22, 2.6, 2.6, 0.5, [(tit, 18, AZUL, True, False, 0)])
    _texto(s, x + 0.22, 3.25, 2.55, 2.9,
           [(i, 13, GRIS, False, True, 0) for i in items], space=11)
    x += 3.11
_notes(s, "Agenda en cuatro bloques. Primero el contexto; luego la ARQUITECTURA (la forma del sistema); "
          "luego la ONTOLOGÍA (el corazón del dato); y por último las HERRAMIENTAS (con qué está hecho, "
          "pieza a pieza). Cerramos con las garantías.")

# ------------------------- 3. Contexto y objetivo -------------------------
slide_2col("Contexto y objetivo",
    ("EL PROBLEMA", NARANJA, [
        "Cada país regula la calidad admisible del gas con SU PROPIA normativa: Wobbe, PCS, azufre, CO2, puntos de rocío.",
        "La información está dispersa en boletines oficiales distintos y en varios idiomas.",
        "Las unidades y las condiciones de referencia NO coinciden: unos miden a 0 °C, otros a 15 o a 25 °C.",
        "Compararlas a mano es laborioso, lento y propenso a error.",
    ]),
    ("LA SOLUCIÓN", VERDE, [
        f"Un asistente que compara la calidad regulatoria entre {N_JUR} jurisdicciones y {N_PAR} parámetros.",
        "Se pregunta en LENGUAJE NATURAL; responde con la CITA OFICIAL de cada cifra.",
        "Normaliza automáticamente unidades y condiciones (ISO 13443) para que la comparación sea válida.",
        "Principio de diseño: CERO CIFRAS INVENTADAS. Ningún valor se estima.",
    ]),
    intro="El problema es concreto, y la propuesta de valor también.",
    notas="El problema: la información regulatoria está dispersa y, sobre todo, NO ES DIRECTAMENTE COMPARABLE, "
          "porque cada país usa unidades y condiciones distintas. Nuestra solución compara 21 jurisdicciones y "
          "10 parámetros en lenguaje natural, normalizando antes de comparar. Y su principio de diseño es que "
          "no genera ninguna cifra por estimación.")

# ------------------------- 4. El sistema en cifras -------------------------
s = _slide(); _cabecera(s, "El sistema en cifras", nxt())
tarjetas = [(str(N_JUR), "jurisdicciones", CYAN), (str(N_PAR), "parámetros de calidad", CYAN),
            (str(N_CELDAS), "valores trazables", CYAN), ("0", "cifras inventadas", VERDE)]
x = 0.6
for num, txt, color in tarjetas:
    _box(s, x, 1.65, 2.95, 2.25, fill=GRISCL)
    _box(s, x, 1.65, 2.95, 0.09, fill=color)
    _texto(s, x, 1.95, 2.95, 1.1, [(num, 52, AZUL, True, False, 0)], align=PP_ALIGN.CENTER)
    _texto(s, x, 3.1, 2.95, 0.6, [(txt, 14, GRIS, False, False, 0)], align=PP_ALIGN.CENTER)
    x += 3.11
# Desglose del "0"
_box(s, 0.6, 4.25, 12.1, 2.0, fill=AZULCL)
_box(s, 0.6, 4.25, 0.09, 2.0, fill=AZUL)
_texto(s, 0.95, 4.4, 11.6, 0.4, [("Detrás de ese cero está lo importante:", 16, AZUL, True, False, 0)])
_box(s, 1.0, 4.9, 5.4, 1.15, fill=VERDECL)
_texto(s, 1.2, 5.02, 5.0, 0.9, [
    (f"{N_VERIF} VERIFICADOS", 17, VERDEOS, True, False, 0),
    ("Contrastados VERBATIM contra su boletín oficial.", 13, TINTA, False, False, 0),
], space=3)
_box(s, 6.9, 4.9, 5.4, 1.15, fill=NARANJACL)
_texto(s, 7.1, 5.02, 5.0, 0.9, [
    (f"{N_NOVER} NO VERIFICABLES", 17, NARANJAOS, True, False, 0),
    ("La norma de ese país no fija el parámetro: se declara, no se inventa.", 13, TINTA, False, False, 0),
], space=3)
_texto(s, 0.6, 6.45, 12.1, 0.4,
       [(f"Base documental: {N_FUENTES} normas oficiales catalogadas  ·  {N_GASES} tipos de gas "
         f"(gas natural, biometano, hidrógeno)  ·  ~22 PDF archivados en local", 12, GRIS, False, False, 0)])
_notes(s, f"Cuatro cifras fijan el alcance: {N_JUR} jurisdicciones, {N_PAR} parámetros, {N_CELDAS} valores "
          f"trazables y CERO cifras inventadas. Detrás de ese cero: {N_VERIF} verificados verbatim y "
          f"{N_NOVER} declarados 'no verificable' porque la norma no los fija. No los rellenamos con "
          "estimaciones: los marcamos y explicamos por qué.")

# ========================= BLOQUE 2 · ARQUITECTURA =========================
slide_seccion("02", "Arquitectura",
              "Cuatro componentes, responsabilidades separadas y una regla: la cifra nunca nace en el modelo.")

# ---------------- 6. ARQUITECTURA — esquema dibujado (16:9) ----------------
s = _slide(); _cabecera(s, "Arquitectura del sistema", nxt(), kicker="Esquema general")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Cuatro componentes. Sigue las flechas: toda cifra procede de la ontología; la IA solo redacta.",
         14, GRIS, False, False, 0)])

# --- 1 · INTERFAZ WEB ---
_rbox(s, 0.45, 3.05, 2.15, 1.85, fill=BLANCO, line=BORDE, line_w=1.25)
_box(s, 0.45, 3.05, 2.15, 0.42, fill=CYAN)
_texto(s, 0.45, 3.09, 2.15, 0.35, [("1 · INTERFAZ WEB", 11.5, BLANCO, True, False, 0)], align=PP_ALIGN.CENTER)
_texto(s, 0.6, 3.58, 1.9, 1.25, [
    ("El usuario pregunta", 13, AZUL, True, False, 0),
    ("index.html", 11, GRIS, False, False, 0),
    ("JavaScript vanilla", 11, GRIS, False, False, 0),
    ("marked · DOMPurify", 11, GRIS, False, False, 0),
], space=2)
_flecha(s, 2.63, 3.83, 0.32, 0.3, "der", CYAN)

# --- 2 · SERVIDOR (contenedor) ---
_rbox(s, 2.98, 1.85, 5.2, 4.35, fill=GRISCL, line=AZUL, line_w=1.5)
_box(s, 2.98, 1.85, 5.2, 0.62, fill=AZUL)
_texto(s, 3.15, 1.9, 4.9, 0.52, [
    ("2 · SERVIDOR DE APLICACIÓN", 13, BLANCO, True, False, 0),
    ("Python · FastAPI · uvicorn · pydantic", 10.5, CYAN, False, False, 0),
], space=0)
# Router
_rbox(s, 3.2, 2.68, 4.75, 0.68, fill=AZUL2, line=None)
_texto(s, 3.2, 2.74, 4.75, 0.56, [
    ("ROUTER DETERMINISTA", 13, BLANCO, True, False, 0),
    ("¿la resuelve el código o hace falta la IA?", 10.5, RGBColor(0xBF, 0xDB, 0xEA), False, False, 0),
], align=PP_ALIGN.CENTER, space=0)
_flecha(s, 4.15, 3.4, 0.26, 0.24, "aba", VERDE)
_flecha(s, 6.55, 3.4, 0.26, 0.24, "aba", NARANJA)
# Ruta A
_rbox(s, 3.2, 3.72, 4.75, 1.05, fill=VERDECL, line=VERDE, line_w=1.25)
_box(s, 3.2, 3.72, 0.09, 1.05, fill=VERDE)
_texto(s, 3.42, 3.79, 4.45, 0.92, [
    ("RUTA A · Consulta cuantitativa   (la mayoría)", 12.5, VERDEOS, True, False, 0),
    ("La resuelve el CÓDIGO. Sin IA.", 11.5, TINTA, False, False, 0),
    ("motor_determinista · conversor_unidades · fuente_oficial", 10, GRIS, False, False, 0),
], space=1)
# Ruta B
_rbox(s, 3.2, 5.0, 4.75, 1.05, fill=NARANJACL, line=NARANJA, line_w=1.25)
_box(s, 3.2, 5.0, 0.09, 1.05, fill=NARANJA)
_texto(s, 3.42, 5.07, 4.45, 0.92, [
    ("RUTA B · Texto abierto", 12.5, NARANJAOS, True, False, 0),
    ("Va al modelo, que PIDE las cifras.", 11.5, TINTA, False, False, 0),
    ("llm_interface · function calling", 10, GRIS, False, False, 0),
], space=1)

_flecha(s, 8.2, 4.1, 0.34, 0.3, "der", VERDE)
_flecha(s, 8.2, 5.38, 0.34, 0.3, "der", NARANJA)

# --- 3 · ONTOLOGÍA (la estrella) ---
_rbox(s, 8.6, 3.35, 4.25, 1.5, fill=AZUL, line=None)
_texto(s, 8.8, 3.45, 3.9, 1.3, [
    ("3 · BASE DE CONOCIMIENTO", 11.5, CYAN, True, False, 0),
    ("Ontología YAML", 17, BLANCO, True, False, 0),
    (f"Las {N_CELDAS} cifras, cada una con su unidad, sus condiciones y su cita oficial.",
     11, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=2)
# Flecha de vuelta (function calling) de la IA a la ontología
_flecha(s, 9.05, 4.95, 0.3, 0.42, "arr", NARANJA)
_texto(s, 9.45, 4.98, 3.4, 0.4,
       [("function calling: el modelo PIDE la cifra, no la inventa", 10.5, NARANJAOS, True, False, 0)],
       anchor=MSO_ANCHOR.MIDDLE)

# --- 4 · IA EXTERNA ---
_rbox(s, 8.6, 5.45, 4.25, 1.0, fill=BLANCO, line=NARANJA, line_w=1.5, dash=True)
_texto(s, 8.8, 5.53, 3.9, 0.85, [
    ("4 · SERVICIO DE IA  (externo · opcional)", 11.5, NARANJAOS, True, False, 0),
    ("OpenAI GPT-4o-mini · temperatura 0 — solo REDACTA, nunca genera cifras.", 11, TINTA, False, False, 0),
], space=1)

# --- Banda inferior: documentos y RAG ---
_box(s, 0.45, 6.42, 12.4, 0.5, fill=AZULCL)
_box(s, 0.45, 6.42, 0.09, 0.5, fill=AZUL2)
_texto(s, 0.7, 6.46, 12.0, 0.42, [
    ("Debajo de todo: los ~22 PDF oficiales (data/raw) y su índice de búsqueda SQLite — el índice guarda TEXTO, "
     "ninguna cifra.", 12, AZUL, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
_notes(s, "Este es el esquema del sistema, y conviene recorrerlo con el dedo. Uno: el usuario pregunta desde la "
          "interfaz web. Dos: la pregunta llega a NUESTRO servidor, y lo primero que hace es pasar por el ROUTER "
          "DETERMINISTA, que decide quién la resuelve. Si es cuantitativa —RUTA A, la mayoría— la resuelve el "
          "código leyendo la ontología, sin IA. Si es de texto abierto —RUTA B— va al modelo. Tres: fíjate en la "
          "flecha que sube desde la IA hasta la ontología: incluso en la ruta B, el modelo no inventa el número, "
          "lo PIDE mediante function calling. Cuatro: la IA es externa y opcional; si cae, el sistema conmuta "
          "a determinista. Y abajo, los PDF y su índice de búsqueda, que no guardan ninguna cifra.")

# --------------------- 7. Los cuatro componentes (tabla) ---------------------
slide_tabla("Los cuatro componentes",
    ["Componente", "Responsabilidad", "Con qué está hecho"],
    [
        ["1 · Interfaz web", "Formular la consulta y mostrar la respuesta con sus citas. Cinco secciones.",
         "index.html — HTML + JavaScript vanilla"],
        ["2 · Servidor de aplicación", "El núcleo: enruta, calcula, accede al dato y custodia las credenciales.",
         "Python · FastAPI · uvicorn · pydantic"],
        ["3 · Base de conocimiento", "La ÚNICA fuente autorizada de cifras: los límites con su contexto y su fuente.",
         "Ontología YAML (PyYAML)"],
        ["4 · Servicio de IA (externo)", "Interpretar la pregunta y REDACTAR el texto. Nunca genera cifras.",
         "API de OpenAI (GPT-4o-mini)"],
    ],
    intro="Cada componente tiene una responsabilidad, y solo una. La separación es deliberada.",
    col_ratios=[2.4, 5.5, 3.4], fsize=13.5, kicker="Arquitectura",
    notas="La separación es lo que hace imposible la alucinación numérica: el mundo determinista (servidor + "
          "ontología) es el único que produce números; el mundo conversacional (la IA) solo redacta. "
          "Ojo con una confusión frecuente: FastAPI y la API de OpenAI no son lo mismo aunque ambas lleven "
          "'API'. FastAPI es el framework de NUESTRO servidor: infraestructura propia y gratuita. La API de "
          "OpenAI es un servicio de terceros, de pago y opcional.")

# ------------------- 8. Las tres capas de datos (esquema) -------------------
s = _slide(); _cabecera(s, "Las tres capas de datos", nxt(), kicker="Arquitectura")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("No hay una única base de datos: hay tres capas con funciones distintas. Y solo UNA guarda cifras.",
         14, GRIS, False, False, 0)])
capas = [
    ("CAPA 1", "Documentos oficiales", AZUL2,
     ["Los ~22 PDF de las normas: BOE, ERSE, GRTgaz, DVGW, Fluxys…",
      "Archivados en local (data/raw) para no depender de webs externas.",
      "Es la FUENTE ÚLTIMA DE VERDAD."], "pdfplumber"),
    ("CAPA 2", "La ontología", VERDE,
     [f"Las {N_CELDAS} cifras extraídas de esos PDF, cada una con su contexto y su cita.",
      "Un único fichero YAML, legible y versionado en git.",
      "De aquí salen TODAS las respuestas."], "PyYAML"),
    ("CAPA 3", "Índice documental (RAG)", NARANJA,
     ["El TEXTO de los PDF troceado en fragmentos con solape.",
      "Sirve para localizar el pasaje en consultas de texto abierto.",
      "NO ALMACENA NINGUNA CIFRA."], "SQLite"),
]
x = 0.6
for etiqueta, tit, color, puntos, herr in capas:
    _rbox(s, x, 1.9, 3.93, 4.45, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, x, 1.9, 3.93, 0.52, fill=color)
    _texto(s, x + 0.18, 1.95, 3.6, 0.42, [(etiqueta, 12, BLANCO, True, False, 0)])
    _texto(s, x + 0.18, 2.55, 3.6, 0.45, [(tit, 17, AZUL, True, False, 0)])
    _texto(s, x + 0.18, 3.1, 3.6, 2.6, [(p, 12.5, TINTA, False, True, 0) for p in puntos], space=9)
    _box(s, x + 0.18, 5.75, 1.7, 0.35, fill=BLANCO, line=color, line_w=1)
    _texto(s, x + 0.18, 5.77, 1.7, 0.3, [(herr, 11, color, True, False, 0)], align=PP_ALIGN.CENTER)
    x += 4.07
_box(s, 0.6, 6.5, 12.13, 0.45, fill=AZULCL)
_texto(s, 0.85, 6.52, 11.8, 0.4,
       [("Las CIFRAS residen solo en la capa 2. La capa 3 es un buscador de texto: no puede producir un número.",
         13, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
_notes(s, "Suele asumirse que hay una gran base de datos única. No es así. Lo importante de esta diapositiva "
          "es el reparto: las cifras viven SOLO en la capa 2, la ontología. La capa 3, el índice documental, "
          "no guarda ningún número: solo sirve para localizar el pasaje pertinente cuando la consulta es de "
          "texto abierto. Y los PDF los guardamos localmente para no depender de que una web externa siga viva.")

# ========================== BLOQUE 3 · ONTOLOGÍA ==========================
slide_seccion("03", "La ontología",
              "El corazón del sistema: la extracción verificada de los PDF oficiales, con todo su contexto.")

# ---------------- 10. ONTOLOGÍA — esquema dibujado (16:9) ----------------
s = _slide(); _cabecera(s, "La ontología: estructura", nxt(), kicker="Ontología")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Un único fichero YAML. Cinco claves. Toda la base de conocimiento del sistema.",
         14, GRIS, False, False, 0)])
# El fichero (izquierda)
_rbox(s, 0.5, 2.1, 3.15, 3.55, fill=AZUL, line=None)
_texto(s, 0.72, 2.3, 2.75, 3.2, [
    ("FICHERO ÚNICO", 11, CYAN, True, False, 0),
    ("ontologia_enagas.yaml", 15, BLANCO, True, False, 0),
    ("data/ontologia/", 11, RGBColor(0x9F, 0xB3, 0xC4), False, False, 0),
    (f"versión {VER_ONT}", 11, RGBColor(0x9F, 0xB3, 0xC4), False, False, 0),
    ("", 6, BLANCO, False, False, 0),
    ("Legible por una persona.", 12, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
    ("Versionado en git junto al código.", 12, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
    ("Auditable celda a celda.", 12, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=4)
# Bus vertical
_box(s, 4.0, 2.25, 0.045, 3.3, fill=BORDE)
ramas = [
    ("ontologia.fuentes_normativas", f"El catálogo de las {N_FUENTES} normas oficiales: id, organismo, publicación, URL y copia local del PDF.", AZUL2),
    ("ontologia.tipos_gas", f"El registro de los {N_GASES} tipos de gas y a qué sección de parámetros apunta cada uno.", AZUL2),
    ("parametros", f"GAS NATURAL — {N_PAR} parámetros × {N_JUR} jurisdicciones = {N_CELDAS} celdas.", VERDE),
    ("parametros_biometano", f"BIOMETANO — {len(PB)} parámetros × 4 jurisdicciones (ES · PT · FR · UE).", VERDE),
    ("parametros_hidrogeno", f"HIDRÓGENO — {len(PH)} parámetros · dominio de RED y dominio de PRODUCTO.", VERDE),
]
y = 2.1
for clave, desc, color in ramas:
    cy = y + 0.31
    _box(s, 4.045, cy - 0.02, 0.45, 0.045, fill=BORDE)
    _rbox(s, 4.55, y, 8.3, 0.62, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, 4.55, y, 0.08, 0.62, fill=color)
    _texto(s, 4.75, y + 0.03, 3.3, 0.56, [(clave, 12.5, color, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE, font=MONO)
    _texto(s, 8.05, y + 0.03, 4.7, 0.56, [(desc, 11.5, TINTA, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.72
# Nota inferior
_box(s, 0.5, 5.9, 12.35, 1.0, fill=AZULCL)
_box(s, 0.5, 5.9, 0.09, 1.0, fill=AZUL)
_texto(s, 0.8, 5.98, 11.9, 0.9, [
    ("Las tres secciones de parámetros comparten EXACTAMENTE el mismo esquema.", 14, AZUL, True, False, 0),
    ("Por eso la ampliación a biometano e hidrógeno no cambió la arquitectura: reutiliza la misma maquinaria "
     "(consulta, comparativa, matriz, normalización ISO 13443 y estados de verificación).", 12.5, GRIS, False, False, 0),
], space=3)
_notes(s, "La ontología es el elemento central. Es un ÚNICO fichero YAML, legible por una persona, con cinco "
          "claves: el catálogo de normas, el registro de tipos de gas y las tres secciones de parámetros —una "
          "por gas—. Lo importante: las tres secciones comparten exactamente el mismo esquema. Por eso "
          "ampliar a biometano e hidrógeno no obligó a cambiar la arquitectura. Y el motor determinista lee "
          "de aquí: el LLM nunca calcula ni inventa valores.")

# --------------------- 11. Anatomía de un valor ---------------------
s = _slide(); _cabecera(s, "Anatomía de un valor", nxt(), kicker="Ontología")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Cada límite NO es solo un número: guarda todo su contexto normativo. Ejemplo real — el O2 de España:",
         14, GRIS, False, False, 0)])
_rbox(s, 0.55, 1.85, 6.55, 3.45, fill=RGBColor(0xF5, 0xF8, 0xFA), line=BORDE, line_w=1.25)
_box(s, 0.55, 1.85, 6.55, 0.42, fill=AZUL2)
_texto(s, 0.75, 1.89, 6.1, 0.35, [("ontologia_enagas.yaml  →  parametros → O2 → limites → ES", 11, BLANCO, False, False, 0)], font=MONO)
_texto(s, 0.8, 2.4, 6.1, 2.8, [
    ("ES:", 12.5, AZUL, True, False, 0),
    ("  fuente: ORDEN_TED_181_2025", 12, TINTA, False, False, 0),
    ("  articulo: \"Tabla 3, apdo. 2.5.2.1 (pág. 27)\"", 12, TINTA, False, False, 0),
    ("  tipo_limite: maximo", 12, TINTA, False, False, 0),
    ("  valor: 0.01", 12, TINTA, False, False, 0),
    ("  unidad: pct_mol", 12, TINTA, False, False, 0),
    ("  expresion_original: \"O2: – / 0,01 % mol\"", 12, AZUL, True, False, 0),
    ("  condiciones_referencia:", 12, TINTA, False, False, 0),
    ("    temperatura_volumen_C: 0", 12, TINTA, False, False, 0),
    ("    presion_bar: 1.01325", 12, TINTA, False, False, 0),
    ("  estado_verificacion: VERIFICADO", 12, VERDEOS, True, False, 0),
], space=3, font=MONO)
# Bloque de refuerzo bajo el YAML (rellena la columna y remata el mensaje)
_rbox(s, 0.55, 5.45, 6.55, 1.45, fill=VERDECL, line=VERDE, line_w=1.25)
_box(s, 0.55, 5.45, 0.09, 1.45, fill=VERDE)
_texto(s, 0.85, 5.55, 6.05, 1.3, [
    (f"Así son las {N_CELDAS} celdas. Todas.", 14, VERDEOS, True, False, 0),
    ("Ninguna es «solo un número»: el valor viaja siempre con su unidad, sus condiciones de referencia, "
     "su cita exacta y el texto literal de la norma del que se extrajo.", 12.5, TINTA, False, False, 0),
], space=3)
campos = [
    ("fuente", "De qué norma sale (enlaza al catálogo)."),
    ("articulo", "Dónde exactamente: tabla, apartado y página."),
    ("tipo_limite", "Máximo, mínimo o rango."),
    ("valor + unidad", "La cifra y la unidad en que se expresa."),
    ("expresion_original", "El TEXTO LITERAL de la norma."),
    ("condiciones_referencia", "Temperatura y presión de referencia."),
    ("estado_verificacion", "La garantía frente a la invención de datos."),
]
y = 1.85
for campo, desc in campos:
    _box(s, 7.45, y, 5.4, 0.5, fill=GRISCL if campos.index((campo, desc)) % 2 == 0 else BLANCO)
    _box(s, 7.45, y, 0.06, 0.5, fill=CYAN)
    _texto(s, 7.62, y + 0.02, 2.15, 0.46, [(campo, 11.5, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE, font=MONO)
    _texto(s, 9.8, y + 0.02, 3.0, 0.46, [(desc, 11.5, TINTA, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.55
_box(s, 7.45, 5.75, 5.4, 0.85, fill=AZULCL)
_texto(s, 7.65, 5.82, 5.05, 0.75, [
    ("Gracias a expresion_original, un auditor puede recomprobar la transcripción SIN abrir el PDF.",
     12.5, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
_notes(s, "Aquí está el valor real del diseño: de cada dato no guardamos solo el número, sino todo su contexto. "
          "El campo clave es 'expresion_original': el texto literal de la norma, tal cual está redactado. Eso "
          "convierte la confianza en VERIFICABILIDAD: no hay que creerse el dato, se puede comprobar en el acto.")

# --------------------- 12. Estados de verificación ---------------------
s = _slide(); _cabecera(s, "Estados de verificación", nxt(), kicker="Ontología")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("La garantía anti-invención. Solo hay dos estados; no existe un punto intermedio.",
         14, GRIS, False, False, 0)])
_rbox(s, 0.6, 1.85, 5.95, 2.35, fill=VERDECL, line=VERDE, line_w=1.25)
_box(s, 0.6, 1.85, 5.95, 0.09, fill=VERDE)
_texto(s, 0.9, 2.05, 5.4, 2.0, [
    (f"{N_VERIF}", 44, VERDEOS, True, False, 0),
    ("VERIFICADO", 17, VERDEOS, True, False, 0),
    ("Cifra contrastada VERBATIM contra su boletín oficial, con artículo y página.", 13, TINTA, False, False, 0),
], space=3)
_rbox(s, 6.78, 1.85, 5.95, 2.35, fill=NARANJACL, line=NARANJA, line_w=1.25)
_box(s, 6.78, 1.85, 5.95, 0.09, fill=NARANJA)
_texto(s, 7.08, 2.05, 5.4, 2.0, [
    (f"{N_NOVER}", 44, NARANJAOS, True, False, 0),
    ("NO VERIFICABLE", 17, NARANJAOS, True, False, 0),
    ("La norma de ese país NO FIJA ese parámetro. No se inventa: se declara el hueco y se explica.",
     13, TINTA, False, False, 0),
], space=3)
_box(s, 0.6, 4.45, 12.13, 1.35, fill=GRISCL)
_box(s, 0.6, 4.45, 0.09, 1.35, fill=AZUL)
_texto(s, 0.9, 4.55, 11.6, 1.2, [
    ("Los huecos no son errores: son honestidad.", 17, AZUL, True, False, 0),
    ("Ejemplo real — DINAMARCA: los límites de O2 y CO2 de su norma corresponden al BIOGÁS DE DISTRIBUCIÓN, "
     "no al gas natural de transporte. Trasladar ese valor sería un error metodológico; por eso, para gas "
     "natural, se marcaron como no verificable en lugar de rellenar el hueco.", 13, TINTA, False, False, 0),
], space=4)
_box(s, 0.6, 6.0, 12.13, 0.9, fill=AZULCL)
_texto(s, 0.9, 6.08, 11.6, 0.8, [
    ("En biometano e hidrógeno existe además VERIFICADO_SECUNDARIO:", 13, AZUL, True, False, 0),
    ("valor tomado de una fuente pública secundaria citada, porque la norma primaria es de pago.",
     12.5, GRIS, False, False, 0),
], space=2)
_notes(s, "Esta es la garantía anti-invención. Dos estados y ninguno intermedio: o la cifra consta en la norma, "
          "o se declara que la norma no la establece. El ejemplo de Dinamarca es el que mejor lo ilustra: era "
          "fácil rellenar el hueco con un número que estaba en la misma norma, pero pertenecía a otro contexto "
          "—biogás de distribución, no transporte—. Preferimos el hueco honesto: informa mejor que un número falso.")

# ======================== BLOQUE 4 · HERRAMIENTAS ========================
slide_seccion("04", "Las herramientas",
              "Con qué está construida la aplicación, pieza a pieza, y qué papel cumple cada una.")

# --------------------- 14. El stack de un vistazo ---------------------
s = _slide(); _cabecera(s, "El stack tecnológico de un vistazo", nxt(), kicker="Herramientas")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Todas las herramientas que usa la aplicación, agrupadas por capa.", 14, GRIS, False, False, 0)])
capas = [
    ("FRONTEND", CYAN, ["HTML + CSS", "JavaScript vanilla", "marked", "DOMPurify", "localStorage"]),
    ("BACKEND", AZUL, ["Python 3.11+", "FastAPI", "uvicorn", "pydantic", "python-dotenv"]),
    ("DATOS Y DOCUMENTOS", VERDE, ["PyYAML", "SQLite", "pdfplumber", "pandas", "openpyxl · xhtml2pdf"]),
    ("IA  (opcional)", NARANJA, ["OpenAI SDK", "GPT-4o-mini", "function calling", "temperatura 0", "sustituible"]),
]
x = 0.6
for titulo, color, items in capas:
    _rbox(s, x, 1.9, 2.95, 3.8, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, x, 1.9, 2.95, 0.5, fill=color)
    _texto(s, x, 1.95, 2.95, 0.42, [(titulo, 12.5, BLANCO, True, False, 0)], align=PP_ALIGN.CENTER)
    _texto(s, x + 0.2, 2.55, 2.6, 3.0, [(i, 13, TINTA, False, True, 0) for i in items], space=10)
    x += 3.11
_box(s, 0.6, 5.9, 12.13, 1.0, fill=AZULCL)
_box(s, 0.6, 5.9, 0.09, 1.0, fill=AZUL)
_texto(s, 0.9, 5.98, 11.7, 0.9, [
    ("Todo el stack es software libre salvo la API de OpenAI — el único componente de pago, y además opcional.",
     14, AZUL, True, False, 0),
    ("Calidad y trazabilidad del propio proyecto: pytest (pruebas automáticas) · git (versiona el código Y la ontología).",
     12.5, GRIS, False, False, 0),
], space=3)
_notes(s, "Este es el mapa completo. Cuatro capas. Lo importante: todo es software libre EXCEPTO la API de "
          "OpenAI, que además es opcional —sin ella el sistema sigue funcionando en modo determinista—. "
          "En las tres diapositivas siguientes vemos el papel exacto de cada pieza.")

# --------------------- 15. Herramientas — Backend ---------------------
slide_tabla("Herramientas — Backend",
    ["Herramienta", "Para qué sirve exactamente en la aplicación"],
    [
        ["Python 3.11+", "Lenguaje de todo el backend y de los scripts de datos, diagramas y documentación."],
        ["FastAPI", "Framework con el que está construido NUESTRO servidor: define los endpoints y valida las peticiones."],
        ["uvicorn", "El servidor que ejecuta FastAPI y atiende el puerto 8000 (lo lanza iniciar_chatbot.bat)."],
        ["pydantic", "Valida y tipa los datos que entran y salen de cada endpoint: evita peticiones malformadas."],
        ["python-dotenv", "Carga la clave de OpenAI desde el entorno, para que nunca esté escrita en el código."],
        ["pytest", f"Ejecuta las pruebas automáticas: comprueba que las {N_CELDAS} celdas resuelven y que nada se rompe."],
    ],
    col_ratios=[2.6, 9.5], fsize=14, kicker="Herramientas",
    notas="Aquí conviene deshacer una confusión: FastAPI y la API de OpenAI no son lo mismo, aunque ambas "
          "lleven 'API'. FastAPI es el framework con el que construimos NUESTRO servidor: infraestructura "
          "propia y gratuita. La API de OpenAI es un servicio de terceros, de pago, que consumimos de forma "
          "puntual y controlada.")

# --------------- 16. Herramientas — Datos y documentos ---------------
slide_tabla("Herramientas — Datos y documentos",
    ["Herramienta", "Para qué sirve exactamente en la aplicación"],
    [
        ["PyYAML", "Lee la ONTOLOGÍA (el fichero .yaml con las cifras verificadas). Es la puerta a la base de conocimiento."],
        ["pdfplumber", "Extrae el TEXTO de los PDF oficiales para poder indexarlos y buscar en ellos."],
        ["sqlite3", "Base de datos ligera que actúa de ÍNDICE del buscador documental (RAG). No guarda ninguna cifra."],
        ["pandas", "Manejo tabular de datos dentro del motor determinista (carga y cruce de tablas)."],
        ["openpyxl", "Genera el informe de la matriz comparativa en EXCEL, con las celdas coloreadas por nivel."],
        ["xhtml2pdf", "Genera el informe de la matriz en PDF, y también la documentación del proyecto."],
        ["cryptography", "Genera el certificado autofirmado para servir por HTTPS (opcional, para producción)."],
    ],
    col_ratios=[2.6, 9.5], fsize=13.5, kicker="Herramientas",
    notas="Aquí está el reparto real del dato. PyYAML abre la ontología, que es de donde salen TODAS las cifras. "
          "pdfplumber y sqlite3 son solo para el buscador documental: el índice NO guarda números. openpyxl y "
          "xhtml2pdf son para exportar informes: serializan los mismos datos que ya están en pantalla, no "
          "generan cifras nuevas.")

# --------------- 17. Herramientas — IA y frontend ---------------
slide_tabla("Herramientas — IA y frontend",
    ["Herramienta", "Capa", "Para qué sirve exactamente en la aplicación"],
    [
        ["OpenAI SDK", "IA", "Cliente para hablar con el modelo. Es el ÚNICO componente de pago, y es opcional."],
        ["GPT-4o-mini", "IA", "El modelo: interpreta la pregunta y REDACTA la respuesta. Temperatura 0. Nunca genera cifras."],
        ["function calling", "IA", "El mecanismo por el que el modelo PIDE los datos a nuestras herramientas en vez de inventarlos."],
        ["HTML + JS vanilla", "Frontend", "La interfaz (index.html). Sin framework: una SPA ligera con cinco secciones."],
        ["marked", "Frontend", "Convierte a HTML el Markdown con el que responde el asistente (tablas, negritas, listas)."],
        ["DOMPurify", "Frontend", "Sanea ese HTML antes de pintarlo: evita la inyección de código en el navegador (XSS)."],
        ["localStorage", "Frontend", "Guarda el historial de la conversación en el navegador; se restaura al recargar."],
    ],
    col_ratios=[2.3, 1.2, 8.6], fsize=13.5, kicker="Herramientas",
    notas="En la capa de IA lo esencial es el 'function calling': es el mecanismo que permite que el modelo, "
          "cuando necesita un número, lo PIDA a nuestras herramientas en lugar de sacarlo de su memoria. Ahí "
          "está técnicamente la garantía anti-alucinación. En el frontend, DOMPurify merece mención: es la "
          "protección contra inyección de código en el navegador.")

# --------------- 18. Módulos propios del proyecto ---------------
slide_tabla("Los módulos propios del proyecto",
    ["Fichero", "Responsabilidad"],
    [
        ["api.py", "El núcleo: endpoints, ROUTER DETERMINISTA y orquestación de la respuesta."],
        ["fuente_oficial.py", "Lee la ontología y devuelve el valor CON SU CITA. La única puerta a las cifras."],
        ["conversor_unidades.py", "Conversión de unidades y factores ISO 13443 (Tabla A.1) para comparar de forma homogénea."],
        ["condiciones_referencia.py", "Gestión de las condiciones de referencia (temperatura y presión) de cada país."],
        ["motor_determinista.py", "Lógica de comparación y de evaluación de cumplimiento, sin IA."],
        ["agente_pdf.py", "Indexación de los PDF y búsqueda documental (RAG) sobre el índice SQLite."],
        ["llm_interface.py", "La frontera con el modelo: define las herramientas que puede invocar y sus salvaguardas."],
        ["busqueda_semantica.py", "Capa de búsqueda semántica: PREPARADA y opcional (desactivada por defecto)."],
    ],
    intro="Código propio: cada fichero, una responsabilidad.",
    col_ratios=[3.0, 9.1], fsize=13, kicker="Herramientas",
    notas="La pieza que hay que retener es fuente_oficial.py: es la ÚNICA puerta a las cifras. Todo —el chat, "
          "la comparativa, la matriz, el análisis de gas— pasa por ahí. Si alguien quiere auditar de dónde "
          "sale un número, ese es el sitio donde mirar.")

# --------------- 19. Endpoints ---------------
slide_tabla("Los servicios que expone la aplicación",
    ["Endpoint", "Qué hace"],
    [
        ["/", "Sirve la interfaz web (index.html)."],
        ["/api/status", "Estado del sistema: si la IA está activa o se opera en modo determinista."],
        ["/api/chat", "Consulta en lenguaje natural. Resuelve también INTERCONEXIONES en cadena entre países."],
        ["/api/parametros", "Lista los parámetros y jurisdicciones disponibles para cada tipo de gas."],
        ["/api/comparar", "Comparación puntual de un parámetro entre España y otro país."],
        ["/api/matriz", "La matriz comparativa completa: todas las jurisdicciones × todos los parámetros."],
        ["/api/analizar-gas", "Valida un gas concreto contra la normativa de cada país: cumple / alerta / no cumple."],
        ["/api/exportar-matriz", "Descarga la comparativa en Excel o PDF para las jurisdicciones seleccionadas."],
    ],
    col_ratios=[3.0, 9.1], fsize=13, kicker="Herramientas",
    notas="Ocho servicios. Merece la pena destacar dos: /api/analizar-gas, que valida un gas real país a país y "
          "marca la ZONA DE ALERTA —cumple, pero a menos del 10 % del límite—; y la detección de "
          "interconexiones dentro de /api/chat, que calcula qué gas puede atravesar una cadena de países e "
          "identifica el CUELLO DE BOTELLA regulatorio.")

# --------------- 20. Motor determinista + ISO 13443 ---------------
s = _slide(); _cabecera(s, "El motor determinista y la normalización", nxt(), kicker="Cómo funciona")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("«Determinista» = ante la misma consulta, siempre la misma respuesta, calculada por código, sin azar ni IA.",
         14, GRIS, False, False, 0)])
_rbox(s, 0.6, 1.85, 5.95, 2.5, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 0.6, 1.85, 5.95, 0.5, fill=AZUL)
_texto(s, 0.78, 1.9, 5.6, 0.42, [("RESUELVE SIN IA — 7 tipos de intención", 14, BLANCO, True, False, 0)])
_texto(s, 0.8, 2.5, 5.55, 1.75, [
    ("El valor de un límite", 12.5, TINTA, False, True, 0),
    ("Si un valor medido cumple", 12.5, TINTA, False, True, 0),
    ("De qué norma procede", 12.5, TINTA, False, True, 0),
    ("Si dos gases son intercambiables", 12.5, TINTA, False, True, 0),
    ("Si un país es más restrictivo que España", 12.5, TINTA, False, True, 0),
    ("La comparación directa entre dos países", 12.5, TINTA, False, True, 0),
    ("La conversión de condiciones", 12.5, TINTA, False, True, 0),
], space=4)
_rbox(s, 6.78, 1.85, 5.95, 2.5, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 6.78, 1.85, 5.95, 0.5, fill=NARANJA)
_texto(s, 6.96, 1.9, 5.6, 0.42, [("EL PROBLEMA DE LA COMPARABILIDAD", 14, BLANCO, True, False, 0)])
_texto(s, 6.98, 2.5, 5.55, 1.75, [
    ("Unos países miden en kWh/m3, otros en MJ/m3 o kcal/m3.", 12.5, TINTA, False, True, 0),
    ("Unos refieren el volumen a 0 °C, otros a 15 o a 25 °C.", 12.5, TINTA, False, True, 0),
    ("Comparar esos valores EN BRUTO sería metodológicamente incorrecto.", 12.5, TINTA, False, True, 0),
    ("Solución: llevar TODO a la base española (0/0) con la norma ISO 13443.", 12.5, AZUL, True, True, 0),
], space=6)
# Tabla de factores
_box(s, 0.6, 4.55, 12.13, 0.45, fill=AZUL)
_texto(s, 0.8, 4.58, 5.0, 0.4, [("Factores literales de la Tabla A.1 · ISO 13443", 13, BLANCO, True, False, 0)],
       anchor=MSO_ANCHOR.MIDDLE)
_texto(s, 8.5, 4.58, 2.0, 0.4, [("PCS", 13, CYAN, True, False, 0)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
_texto(s, 10.6, 4.58, 2.0, 0.4, [("Wobbe", 13, CYAN, True, False, 0)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
factores = [
    ("25/0 → 0/0", "Portugal, Alemania, P. Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Grecia", "1,0026", "1,0026"),
    ("15/15 → 0/0", "Italia, UE, Chequia, Irlanda, Rumanía, Turquía, Reino Unido", "1,0570", "1,0569"),
    ("25/20 → 0/0", "Eslovaquia — par no tabulado: se calcula con las ecuaciones del Anexo B de la norma", "~1,076", "~1,076"),
    ("0/0 → 0/0", "España (base) y Francia — identidad, no hay conversión", "×1", "×1"),
]
y = 5.0
for i, (par, paises, pcs, wob) in enumerate(factores):
    _box(s, 0.6, y, 12.13, 0.42, fill=GRISCL if i % 2 == 0 else BLANCO)
    _texto(s, 0.8, y + 0.01, 1.8, 0.4, [(par, 12, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 2.6, y + 0.01, 5.8, 0.4, [(paises, 11, GRIS, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 8.5, y + 0.01, 2.0, 0.4, [(pcs, 12, TINTA, True, False, 0)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 10.6, y + 0.01, 2.0, 0.4, [(wob, 12, TINTA, True, False, 0)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.44
_texto(s, 0.6, 6.78, 12.13, 0.3,
       [("Estos factores NO se estiman: se toman literalmente de la norma. España es siempre la base de referencia.",
         12, AZUL, True, False, 0)])
_notes(s, "Un punto clave para la credibilidad es la comparabilidad: no basta con tener los números, hay que "
          "poder compararlos. Por eso llevamos todo a la base española aplicando los factores de la ISO 13443, "
          "que no estimamos sino que tomamos literalmente de la norma. Fíjate en la fila de Eslovaquia: su par "
          "de condiciones no está tabulado, así que se calcula con las ECUACIONES DEL ANEXO B de la misma "
          "norma. Sigue siendo un valor derivado de la norma, no un número inventado.")

# --------------- 21. IA y salvaguardas ---------------
slide_2col("La IA y sus salvaguardas",
    ("EL MODELO PUEDE", VERDE, [
        "Interpretar la pregunta y detectar la intención.",
        "Identificar entidades (parámetro, país, gas).",
        "Reformular la consulta.",
        "REDACTAR la respuesta final en lenguaje natural.",
        ("Es la capa de LENGUAJE, no la fuente del dato.", True),
    ]),
    ("EL MODELO NO PUEDE", NARANJA, [
        "Generar límites regulatorios.",
        "Inventar valores.",
        "Deducir conversiones ni calcular equivalencias.",
        "Inferir comparabilidad por su cuenta.",
        ("Para cualquier número invoca una herramienta: consultar · evaluar_cumplimiento · convertir_unidades · "
         "convertir_condiciones_iso13443 · buscar_pdfs", True),
    ]),
    intro="Cuando una consulta sí llega al modelo, opera atada en corto.",
    kicker="Cómo funciona", alto=3.15,
    banda=["Tres salvaguardas más:",
           "1) El SYSTEM_PROMPT le prohíbe inventar cifras, le obliga a citar y limita su ámbito a la calidad "
           "del gas.   2) Temperatura 0 (máxima previsibilidad) y hasta 5 iteraciones de llamadas a herramientas.",
           "3) Si OpenAI no está disponible —sin clave, sin red o por límite—, el sistema conmuta al motor "
           "determinista: EL CHAT NUNCA DEVUELVE ERROR."],
    notas="Hay que ser muy claro: el modelo NO es la fuente del dato, es la capa de lenguaje. Si necesita un "
          "número, lo pide. El SYSTEM_PROMPT le prohíbe inventar cifras, le obliga a citar y le acota el ámbito. "
          "Y si el servicio no está disponible, el sistema conmuta solo a modo determinista: la IA es una "
          "comodidad, no una dependencia.")

# --------------- 22. RAG ---------------
slide_2col("La recuperación documental (RAG)",
    ("1 · INDEXACIÓN", AZUL2, [
        "pdfplumber extrae el texto de los PDF oficiales.",
        "Se trocea en fragmentos CON SOLAPE, con una ventana deslizante sobre el documento completo (no por página).",
        ("Así, una respuesta partida entre dos páginas queda ENTERA dentro de un mismo fragmento, y sigue siendo recuperable.", True),
        "Es incremental: solo se reprocesa lo nuevo o modificado, así que el arranque es casi inmediato.",
    ]),
    ("2 · RECUPERACIÓN", CYAN, [
        "buscar_pdfs() hace una búsqueda LÉXICA (SQLite LIKE sobre el texto normalizado).",
        "Devuelve los fragmentos relevantes con su archivo, su página y un extracto.",
        ("Es léxica, NO vectorial: sin embeddings ni similitud semántica.", True),
        "Decisión consciente: plenamente reproducible y sin depender de servicios externos.",
    ]),
    intro="Para las consultas de texto abierto, la respuesta se fundamenta en los documentos oficiales.",
    kicker="Cómo funciona", alto=3.15,
    banda=["¿Y si hiciera falta búsqueda semántica? Lo medimos antes de decidir.",
           "El estudio de terminología cuantificó cuánto varían los NOMBRES de un mismo parámetro entre normas: "
           "índice de variación 27,4 en gas natural · 9,2 en biometano · 7,3 en hidrógeno (umbral 7,0).",
           "Ese estudio JUSTIFICA una capa semántica multilingüe, que queda preparada y activable, pero "
           "desactivada por defecto por reproducibilidad."],
    notas="Somos transparentes: nuestro RAG es léxico, no semántico. No es una carencia, es una decisión: es "
          "reproducible y no depende de terceros. Y antes de decidirlo lo MEDIMOS, con el estudio de "
          "terminología. Primero medir, luego decidir.")

# --------------- 23. Ampliación: biometano e hidrógeno ---------------
s = _slide(); _cabecera(s, "Ampliación: biometano e hidrógeno", nxt(), kicker="Alcance")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Añadidos como CAPA ADITIVA: se introduce la dimensión «tipo_gas», con gas_natural por defecto. "
         "El gas natural queda intacto.", 14, GRIS, False, False, 0)])
gases = [
    ("GAS NATURAL", AZUL, "parametros", f"{N_JUR} jurisdicciones", f"{N_PAR} parámetros",
     f"{N_VERIF} verificados · {N_NOVER} no verificables"),
    ("BIOMETANO", VERDE, "parametros_biometano", "4 · ES · PT · FR · UE", f"{len(PB)} parámetros",
     "Inyección en red: CH4 mín · CO2 máx · siloxanos"),
    ("HIDRÓGENO", NARANJA, "parametros_hidrogeno", "RED + PRODUCTO", f"{len(PH)} parámetros",
     "Marco aún en construcción: prospección normativa"),
]
x = 0.6
for tit, color, clave, jur, par, nota in gases:
    _rbox(s, x, 1.9, 3.93, 2.75, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, x, 1.9, 3.93, 0.5, fill=color)
    _texto(s, x + 0.18, 1.95, 3.6, 0.42, [(tit, 14, BLANCO, True, False, 0)])
    _texto(s, x + 0.18, 2.52, 3.6, 0.3, [(clave, 11.5, color, True, False, 0)], font=MONO)
    _texto(s, x + 0.18, 2.9, 3.6, 1.65, [
        (jur, 13, TINTA, False, True, 0),
        (par, 13, TINTA, False, True, 0),
        (nota, 11.5, GRIS, False, False, 1),
    ], space=6)
    x += 4.07
# Aviso del dominio del hidrógeno
_box(s, 0.6, 4.85, 12.13, 1.45, fill=NARANJACL)
_box(s, 0.6, 4.85, 0.09, 1.45, fill=NARANJA)
_texto(s, 0.9, 4.93, 11.7, 1.3, [
    ("Hidrógeno — la distinción esencial es de DOMINIO:", 14, NARANJAOS, True, False, 0),
    ("RED (el gasoducto, lo que compete a Enagás): CEN/TS 17977 y recomendación GIE — pureza H2 >= 98 % mol.   "
     "Hoy solo PORTUGAL lo fija como vinculante; España y Francia regulan el blending; la UE lo recomienda.",
     12.5, TINTA, False, False, 0),
    ("PRODUCTO / VEHÍCULO: ISO 14687 Grade D — pureza 99,97 % para pilas de combustible. NO es lo que necesita "
     "un operador de red. La herramienta los mantiene SEPARADOS para no confundirlos.", 12.5, TINTA, False, False, 0),
], space=3)
_box(s, 0.6, 6.45, 12.13, 0.45, fill=AZULCL)
_texto(s, 0.9, 6.47, 11.7, 0.4, [
    ("Mismo motor, mismas garantías, mismas pruebas: la ampliación no degradó nada de lo anterior.",
     13, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
_notes(s, "La ampliación se hizo sin tocar nada de lo anterior: el gas natural sigue funcionando exactamente "
          "igual, y las pruebas automáticas lo confirman. Sobre el hidrógeno hay que subrayar la distinción de "
          "dominio: la calidad del H2 PARA LA RED es distinta de la del H2 como combustible de VEHÍCULO. Son "
          "especificaciones que no se pueden comparar, y la herramienta las mantiene separadas. Y hoy, de las "
          "cuatro jurisdicciones, solo Portugal fija una pureza vinculante del 98 %.")

# --------------- 24. Garantías y cierre ---------------
s = _slide()
_box(s, 0, 0, 13.333, 7.5, fill=AZUL)
_box(s, 0, 1.45, 13.333, 0.05, fill=CYAN)
_texto(s, 0.9, 0.5, 11.5, 0.8, [("Las garantías del sistema", 32, BLANCO, True, False, 0)])
gar = [
    ("Cero cifras inventadas", "Los valores proceden de código y datos verificados, nunca del modelo."),
    ("Trazabilidad completa", "Cada valor cita su norma, su artículo, su página y su enlace."),
    ("Transparencia", "Lo que la norma no fija se declara explícitamente; no se completa."),
    ("Reproducibilidad", "Con el mismo código y los mismos datos, el resultado es idéntico en cualquier entorno."),
    ("Auditabilidad", "La base de conocimiento es consultable: se puede verificar el origen de cada valor."),
]
y = 2.0
for t, d in gar:
    _box(s, 0.9, y, 0.07, 0.78, fill=VERDE)
    _texto(s, 1.25, y - 0.03, 11.3, 0.42, [(t, 18, CYAN, True, False, 0)])
    _texto(s, 1.25, y + 0.33, 11.3, 0.42, [(d, 14, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0)])
    y += 0.92
_box(s, 0.9, 6.6, 11.6, 0.06, fill=VERDE)
_texto(s, 0.9, 6.75, 11.6, 0.5,
       [("La IA redacta el texto. Los números salen siempre de la normativa oficial.", 18, BLANCO, True, False, 0)])
nxt()
_notes(s, "En síntesis: hemos construido una herramienta que compara la calidad regulatoria del gas natural, el "
          "biometano y el hidrógeno entre jurisdicciones, con trazabilidad total y sin cifras inventadas. Las "
          "cifras salen siempre de normativa oficial verificada; la IA solo redacta el texto. Y la ampliación "
          "se ha hecho sin degradar nada de lo anterior. Muchas gracias; quedo a vuestra disposición.")

prs.save(PPTX)
print("PPTX generado:", os.path.relpath(PPTX, RAIZ),
      f"({os.path.getsize(PPTX)//1024} KB, {len(prs.slides._sldIdLst)} diapositivas)")
