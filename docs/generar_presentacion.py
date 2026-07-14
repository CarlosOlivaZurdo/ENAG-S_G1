# -*- coding: utf-8 -*-
"""Genera LA presentación del Comparador Regulatorio de Calidad de Gas (estilo Enagás).

    python docs/generar_presentacion.py

Presentación breve (10 diapositivas), centrada en:
  - la ARQUITECTURA del sistema (esquema DIBUJADO en la propia diapositiva, apaisado),
  - la ONTOLOGÍA (esquema DIBUJADO: el fichero y sus cinco claves),
  - y las garantías (cero cifras inventadas, trazabilidad).

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
from pptx.util import Inches, Pt
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
    ty = 0.16
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


# ============================== CONTENIDO (10) ==============================

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
    ("Arquitectura, ontología y garantías del sistema", 21, CYAN, False, False, 0),
    (f"Gas natural · biometano · hidrógeno   |   {N_JUR} jurisdicciones · {N_PAR} parámetros · "
     f"{N_CELDAS} valores trazables", 15, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=7)
_texto(s, 1.38, 6.55, 11, 0.4,
       [(f"Ontología v{VER_ONT}  ·  Presentación técnica", 12, RGBColor(0x8F, 0xA6, 0xB8), False, False, 0)])
_notes(s, "El hilo conductor es doble: CÓMO ESTÁ CONSTRUIDO (arquitectura y ontología) y POR QUÉ ES FIABLE "
          "(trazabilidad total y cero cifras inventadas).")

# --------------------- 2. Contexto, objetivo y alcance ---------------------
s = _slide(); _cabecera(s, "Contexto, objetivo y alcance", nxt())
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("El problema es concreto; la propuesta de valor, también.", 14, GRIS, False, False, 0)])
_rbox(s, 0.6, 1.75, 5.9, 2.35, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 0.6, 1.75, 5.9, 0.5, fill=NARANJA)
_texto(s, 0.78, 1.8, 5.5, 0.42, [("EL PROBLEMA", 14, BLANCO, True, False, 0)])
_texto(s, 0.8, 2.4, 5.5, 1.6, [
    ("Cada país regula la calidad del gas con SU PROPIA normativa, dispersa y en varios idiomas.",
     13, TINTA, False, True, 0),
    ("Las unidades y las condiciones de referencia NO coinciden: unos miden a 0 °C, otros a 15 o a 25 °C.",
     13, TINTA, False, True, 0),
    ("Compararlas a mano es lento y propenso a error.", 13, TINTA, False, True, 0),
], space=7)
_rbox(s, 6.85, 1.75, 5.9, 2.35, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 6.85, 1.75, 5.9, 0.5, fill=VERDE)
_texto(s, 7.03, 1.8, 5.5, 0.42, [("LA SOLUCIÓN", 14, BLANCO, True, False, 0)])
_texto(s, 7.05, 2.4, 5.5, 1.6, [
    (f"Un asistente que compara {N_JUR} jurisdicciones y {N_PAR} parámetros, en lenguaje natural.",
     13, TINTA, False, True, 0),
    ("Normaliza unidades y condiciones (ISO 13443) ANTES de comparar, y cita la fuente de cada cifra.",
     13, TINTA, False, True, 0),
    ("Principio de diseño: CERO CIFRAS INVENTADAS.", 13, AZUL, True, True, 0),
], space=7)
for num, txt, color, x in ((str(N_JUR), "jurisdicciones", CYAN, 0.6),
                           (str(N_PAR), "parámetros", CYAN, 3.71),
                           (str(N_CELDAS), "valores trazables", CYAN, 6.82),
                           ("0", "cifras inventadas", VERDE, 9.93)):
    _box(s, x, 4.3, 2.95, 1.6, fill=GRISCL)
    _box(s, x, 4.3, 2.95, 0.08, fill=color)
    _texto(s, x, 4.5, 2.95, 0.85, [(num, 40, AZUL, True, False, 0)], align=PP_ALIGN.CENTER)
    _texto(s, x, 5.4, 2.95, 0.45, [(txt, 13, GRIS, False, False, 0)], align=PP_ALIGN.CENTER)
_box(s, 0.6, 6.05, 12.13, 0.85, fill=AZULCL)
_box(s, 0.6, 6.05, 0.09, 0.85, fill=AZUL)
_texto(s, 0.9, 6.12, 11.7, 0.75, [
    (f"Detrás de ese cero: {N_VERIF} valores VERIFICADOS verbatim contra su boletín oficial y "
     f"{N_NOVER} declarados NO VERIFICABLES.", 14, AZUL, True, False, 0),
    ("Cuando la norma de un país no fija un parámetro, no lo rellenamos con una estimación: lo marcamos y "
     "explicamos por qué.", 12.5, GRIS, False, False, 0),
], space=3)
_notes(s, "El problema: la información regulatoria está dispersa y, sobre todo, NO ES DIRECTAMENTE COMPARABLE, "
          "porque cada país usa unidades y condiciones distintas. Cuatro cifras fijan el alcance: "
          f"{N_JUR} jurisdicciones, {N_PAR} parámetros, {N_CELDAS} valores trazables y CERO cifras inventadas. "
          f"Detrás de ese cero: {N_VERIF} verificados verbatim y {N_NOVER} declarados 'no verificable' porque "
          "la norma de ese país no los fija.")

# ------------- 3. ARQUITECTURA — esquema dibujado (16:9) -------------
s = _slide(); _cabecera(s, "Arquitectura del sistema", nxt(), kicker="Cómo está construido")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Cuatro componentes. Sigue las flechas: toda cifra procede de la ontología; la IA solo redacta.",
         14, GRIS, False, False, 0)])
# 1 · Interfaz web
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
# 2 · Servidor (contenedor)
_rbox(s, 2.98, 1.85, 5.2, 4.35, fill=GRISCL, line=AZUL, line_w=1.5)
_box(s, 2.98, 1.85, 5.2, 0.62, fill=AZUL)
_texto(s, 3.15, 1.9, 4.9, 0.52, [
    ("2 · SERVIDOR DE APLICACIÓN", 13, BLANCO, True, False, 0),
    ("Python · FastAPI · uvicorn · pydantic", 10.5, CYAN, False, False, 0),
], space=0)
_rbox(s, 3.2, 2.68, 4.75, 0.68, fill=AZUL2, line=None)
_texto(s, 3.2, 2.74, 4.75, 0.56, [
    ("ROUTER DETERMINISTA", 13, BLANCO, True, False, 0),
    ("¿la resuelve el código o hace falta la IA?", 10.5, RGBColor(0xBF, 0xDB, 0xEA), False, False, 0),
], align=PP_ALIGN.CENTER, space=0)
_flecha(s, 4.15, 3.4, 0.26, 0.24, "aba", VERDE)
_flecha(s, 6.55, 3.4, 0.26, 0.24, "aba", NARANJA)
_rbox(s, 3.2, 3.72, 4.75, 1.05, fill=VERDECL, line=VERDE, line_w=1.25)
_box(s, 3.2, 3.72, 0.09, 1.05, fill=VERDE)
_texto(s, 3.42, 3.79, 4.45, 0.92, [
    ("RUTA A · Consulta cuantitativa   (la mayoría)", 12.5, VERDEOS, True, False, 0),
    ("La resuelve el CÓDIGO. Sin IA.", 11.5, TINTA, False, False, 0),
    ("fuente_oficial · conversor_unidades · condiciones_referencia", 10, GRIS, False, False, 0),
], space=1)
_rbox(s, 3.2, 5.0, 4.75, 1.05, fill=NARANJACL, line=NARANJA, line_w=1.25)
_box(s, 3.2, 5.0, 0.09, 1.05, fill=NARANJA)
_texto(s, 3.42, 5.07, 4.45, 0.92, [
    ("RUTA B · Texto abierto", 12.5, NARANJAOS, True, False, 0),
    ("Va al modelo, que PIDE las cifras.", 11.5, TINTA, False, False, 0),
    ("llm_interface · function calling", 10, GRIS, False, False, 0),
], space=1)
_flecha(s, 8.2, 4.1, 0.34, 0.3, "der", VERDE)
_flecha(s, 8.2, 5.38, 0.34, 0.3, "der", NARANJA)
# 3 · Ontología
_rbox(s, 8.6, 3.35, 4.25, 1.5, fill=AZUL, line=None)
_texto(s, 8.8, 3.45, 3.9, 1.3, [
    ("3 · BASE DE CONOCIMIENTO", 11.5, CYAN, True, False, 0),
    ("Ontología YAML", 17, BLANCO, True, False, 0),
    (f"Las {N_CELDAS} cifras, cada una con su unidad, sus condiciones y su cita oficial.",
     11, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=2)
_flecha(s, 9.05, 4.95, 0.3, 0.42, "arr", NARANJA)
_texto(s, 9.45, 4.98, 3.4, 0.4,
       [("function calling: el modelo PIDE la cifra, no la inventa", 10.5, NARANJAOS, True, False, 0)],
       anchor=MSO_ANCHOR.MIDDLE)
# 4 · IA externa
_rbox(s, 8.6, 5.45, 4.25, 1.0, fill=BLANCO, line=NARANJA, line_w=1.5, dash=True)
_texto(s, 8.8, 5.53, 3.9, 0.85, [
    ("4 · SERVICIO DE IA  (externo · opcional)", 11.5, NARANJAOS, True, False, 0),
    ("OpenAI GPT-4o-mini · temperatura 0 — solo REDACTA, nunca genera cifras.", 11, TINTA, False, False, 0),
], space=1)
_box(s, 0.45, 6.42, 12.4, 0.5, fill=AZULCL)
_box(s, 0.45, 6.42, 0.09, 0.5, fill=AZUL2)
_texto(s, 0.7, 6.46, 12.0, 0.42, [
    ("Debajo de todo: los ~22 PDF oficiales (data/raw) y su índice de búsqueda SQLite — el índice guarda TEXTO, "
     "ninguna cifra.", 12, AZUL, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
_notes(s, "Recorred el esquema con el dedo. Uno: el usuario pregunta desde la interfaz web. Dos: la pregunta "
          "llega a NUESTRO servidor, y lo primero que hace es pasar por el ROUTER DETERMINISTA, que decide "
          "quién la resuelve. Si es cuantitativa —RUTA A, la mayoría— la resuelve el código leyendo la "
          "ontología, sin IA y sin posibilidad de error. Si es de texto abierto —RUTA B— va al modelo. Tres, y "
          "es lo importante: fijaos en la flecha que SUBE desde la IA hasta la ontología. Incluso en la ruta B "
          "el modelo no inventa el número: lo PIDE mediante function calling. Cuatro: la IA es externa y "
          "opcional; si cae, el sistema conmuta a determinista y el chat nunca falla.")

# --------------- 4. Las tres capas de datos (+ el stack) ---------------
s = _slide(); _cabecera(s, "Las tres capas de datos", nxt(), kicker="Cómo está construido")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("No hay una única base de datos: hay tres capas con funciones distintas. Y solo UNA guarda cifras.",
         14, GRIS, False, False, 0)])
capas = [
    ("CAPA 1", "Documentos oficiales", AZUL2,
     ["Los ~22 PDF de las normas: BOE, ERSE, GRTgaz, DVGW, Fluxys…",
      "Archivados en local para no depender de webs externas.",
      "Es la FUENTE ÚLTIMA DE VERDAD."], "pdfplumber"),
    ("CAPA 2", "La ontología", VERDE,
     [f"Las {N_CELDAS} cifras extraídas de esos PDF, con su contexto y su cita.",
      "Un único fichero YAML, legible y versionado en git.",
      "De aquí salen TODAS las respuestas."], "PyYAML"),
    ("CAPA 3", "Índice documental (RAG)", NARANJA,
     ["El TEXTO de los PDF troceado en fragmentos con solape.",
      "Localiza el pasaje en las consultas de texto abierto.",
      "NO ALMACENA NINGUNA CIFRA."], "SQLite"),
]
x = 0.6
for etiqueta, tit, color, puntos, herr in capas:
    _rbox(s, x, 1.85, 3.93, 3.35, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, x, 1.85, 3.93, 0.5, fill=color)
    _texto(s, x + 0.18, 1.9, 3.6, 0.42, [(etiqueta, 12, BLANCO, True, False, 0)])
    _texto(s, x + 0.18, 2.48, 3.6, 0.42, [(tit, 16, AZUL, True, False, 0)])
    _texto(s, x + 0.18, 2.98, 3.6, 1.7, [(p, 12, TINTA, False, True, 0) for p in puntos], space=7)
    _box(s, x + 0.18, 4.68, 1.6, 0.33, fill=BLANCO, line=color, line_w=1)
    _texto(s, x + 0.18, 4.7, 1.6, 0.29, [(herr, 11, color, True, False, 0)], align=PP_ALIGN.CENTER)
    x += 4.07
_box(s, 0.6, 5.35, 12.13, 0.62, fill=GRISCL)
_box(s, 0.6, 5.35, 0.09, 0.62, fill=CYAN)
_texto(s, 0.9, 5.38, 11.7, 0.56, [
    ("El stack completo", 11.5, CYAN, True, False, 0),
    ("Frontend: JavaScript vanilla · marked · DOMPurify    |    Backend: Python · FastAPI · uvicorn · pydantic"
     "    |    Datos: PyYAML · pdfplumber · SQLite    |    Informes: openpyxl · xhtml2pdf    |    "
     "IA (opcional): OpenAI GPT-4o-mini", 11, TINTA, False, False, 0),
], space=1)
_box(s, 0.6, 6.1, 12.13, 0.8, fill=AZULCL)
_box(s, 0.6, 6.1, 0.09, 0.8, fill=AZUL)
_texto(s, 0.9, 6.16, 11.7, 0.72, [
    ("Las CIFRAS residen solo en la capa 2. La capa 3 es un buscador de texto: no puede producir un número.",
     14, AZUL, True, False, 0),
    ("Todo el stack es software libre salvo la API de OpenAI — el único componente de pago, y además opcional.",
     12, GRIS, False, False, 0),
], space=2)
_notes(s, "Suele asumirse que hay una gran base de datos única. No es así. Lo importante es el reparto: las "
          "cifras viven SOLO en la capa 2, la ontología. La capa 3, el índice documental, no guarda ningún "
          "número: solo localiza el pasaje pertinente en las consultas de texto abierto. Y los PDF los "
          "guardamos en local para no depender de que una web externa siga viva. Sobre el stack: todo es "
          "software libre excepto la API de OpenAI, que además es opcional. Si os preguntan por pint, PyPDF2, "
          "pandas o cryptography: están declarados en requirements pero HOY NO SE USAN, y lo sabemos.")

# ------------- 5. ONTOLOGÍA — esquema dibujado (16:9) -------------
s = _slide(); _cabecera(s, "La ontología: estructura", nxt(), kicker="El corazón del dato")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Un único fichero YAML. Cinco claves. Toda la base de conocimiento del sistema.",
         14, GRIS, False, False, 0)])
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
_box(s, 4.0, 2.25, 0.045, 3.3, fill=BORDE)
ramas = [
    ("ontologia.fuentes_normativas",
     f"El catálogo de las {N_FUENTES} normas oficiales: id, organismo, publicación, URL y copia local del PDF.", AZUL2),
    ("ontologia.tipos_gas",
     f"El registro de los {N_GASES} tipos de gas y a qué sección de parámetros apunta cada uno.", AZUL2),
    ("parametros",
     f"GAS NATURAL — {N_PAR} parámetros × {N_JUR} jurisdicciones = {N_CELDAS} celdas.", VERDE),
    ("parametros_biometano",
     f"BIOMETANO — {len(PB)} parámetros × 4 jurisdicciones (ES · PT · FR · UE).", VERDE),
    ("parametros_hidrogeno",
     f"HIDRÓGENO — {len(PH)} parámetros · dominio de RED y dominio de PRODUCTO.", VERDE),
]
y = 2.1
for clave, desc, color in ramas:
    _box(s, 4.045, y + 0.29, 0.45, 0.045, fill=BORDE)
    _rbox(s, 4.55, y, 8.3, 0.62, fill=GRISCL, line=BORDE, line_w=1)
    _box(s, 4.55, y, 0.08, 0.62, fill=color)
    _texto(s, 4.75, y + 0.03, 3.3, 0.56, [(clave, 12.5, color, True, False, 0)],
           anchor=MSO_ANCHOR.MIDDLE, font=MONO)
    _texto(s, 8.05, y + 0.03, 4.7, 0.56, [(desc, 11.5, TINTA, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    y += 0.72
_box(s, 0.5, 5.9, 12.35, 1.0, fill=AZULCL)
_box(s, 0.5, 5.9, 0.09, 1.0, fill=AZUL)
_texto(s, 0.8, 5.98, 11.9, 0.9, [
    ("Las tres secciones de parámetros comparten EXACTAMENTE el mismo esquema.", 14, AZUL, True, False, 0),
    ("Por eso la ampliación a biometano e hidrógeno no cambió la arquitectura: reutiliza la misma maquinaria "
     "(consulta, comparativa, matriz, normalización ISO 13443 y estados de verificación).",
     12.5, GRIS, False, False, 0),
], space=3)
_notes(s, "La ontología es el elemento central: un ÚNICO fichero YAML, legible por una persona, con cinco "
          "claves —el catálogo de normas, el registro de tipos de gas y las tres secciones de parámetros, una "
          "por gas—. Lo importante: las tres secciones comparten exactamente el mismo esquema; por eso ampliar "
          "a biometano e hidrógeno no obligó a cambiar la arquitectura. El motor determinista lee de aquí; el "
          "modelo nunca calcula ni inventa valores. Y usamos YAML en vez de una base de datos porque a esta "
          "escala es más AUDITABLE y TRAZABLE, y se versiona en git junto al código.")

# --------------- 6. Anatomía de un valor y su garantía ---------------
s = _slide(); _cabecera(s, "Anatomía de un valor, y la garantía", nxt(), kicker="El corazón del dato")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Cada límite NO es solo un número: guarda todo su contexto normativo. Ejemplo real — el O2 de España:",
         14, GRIS, False, False, 0)])
_rbox(s, 0.55, 1.8, 6.35, 3.7, fill=RGBColor(0xF5, 0xF8, 0xFA), line=BORDE, line_w=1.25)
_box(s, 0.55, 1.8, 6.35, 0.4, fill=AZUL2)
_texto(s, 0.72, 1.83, 6.0, 0.34,
       [("parametros -> O2 -> limites -> ES", 10.5, BLANCO, False, False, 0)], font=MONO)
_texto(s, 0.78, 2.3, 6.0, 3.1, [
    ("ES:", 12, AZUL, True, False, 0),
    ("  fuente: ORDEN_TED_181_2025", 11.5, TINTA, False, False, 0),
    ('  articulo: "Tabla 3, apdo. 2.5.2.1 (pág. 27)"', 11.5, TINTA, False, False, 0),
    ("  tipo_limite: maximo", 11.5, TINTA, False, False, 0),
    ("  valor: 0.01", 11.5, TINTA, False, False, 0),
    ("  unidad: pct_mol", 11.5, TINTA, False, False, 0),
    ('  expresion_original: "O2: – / 0,01 % mol"', 11.5, AZUL, True, False, 0),
    ("  condiciones_referencia:", 11.5, TINTA, False, False, 0),
    ("    temperatura_volumen_C: 0", 11.5, TINTA, False, False, 0),
    ("    presion_bar: 1.01325", 11.5, TINTA, False, False, 0),
    ("  estado_verificacion: VERIFICADO", 11.5, VERDEOS, True, False, 0),
], space=3, font=MONO)
_rbox(s, 7.15, 1.8, 5.65, 1.75, fill=VERDECL, line=VERDE, line_w=1.25)
_box(s, 7.15, 1.8, 0.09, 1.75, fill=VERDE)
_texto(s, 7.45, 1.95, 5.2, 1.5, [
    (f"{N_VERIF}   VERIFICADO", 20, VERDEOS, True, False, 0),
    ("Cifra contrastada VERBATIM contra su boletín oficial, con artículo y página.",
     12.5, TINTA, False, False, 0),
], space=4)
_rbox(s, 7.15, 3.75, 5.65, 1.75, fill=NARANJACL, line=NARANJA, line_w=1.25)
_box(s, 7.15, 3.75, 0.09, 1.75, fill=NARANJA)
_texto(s, 7.45, 3.9, 5.2, 1.5, [
    (f"{N_NOVER}   NO VERIFICABLE", 20, NARANJAOS, True, False, 0),
    ("La norma de ese país NO FIJA ese parámetro. No se inventa: se declara el hueco y se explica.",
     12.5, TINTA, False, False, 0),
], space=4)
_box(s, 0.55, 5.7, 12.27, 1.2, fill=AZULCL)
_box(s, 0.55, 5.7, 0.09, 1.2, fill=AZUL)
_texto(s, 0.85, 5.77, 11.85, 1.1, [
    ("Solo hay dos estados, y ningún intermedio. Los huecos no son errores: son honestidad.",
     14, AZUL, True, False, 0),
    ("Ejemplo real — DINAMARCA: los límites de O2 y CO2 de su norma corresponden al BIOGÁS DE DISTRIBUCIÓN, no "
     "al gas natural de transporte. Trasladar ese valor sería un error metodológico; por eso se marcaron como "
     "no verificable.", 12.5, TINTA, False, False, 0),
    ("Gracias a expresion_original (el texto literal de la norma), un auditor puede recomprobar cualquier celda "
     "SIN abrir el PDF.", 12.5, GRIS, False, False, 0),
], space=2)
_notes(s, "Aquí está el valor real del diseño: de cada dato no guardamos solo el número, sino todo su contexto. "
          "El campo clave es 'expresion_original': el texto literal de la norma, tal cual está redactado. Eso "
          "convierte la confianza en VERIFICABILIDAD. A la derecha, la garantía anti-invención: dos estados y "
          "ninguno intermedio. El ejemplo de Dinamarca es el que mejor lo ilustra: era fácil rellenar el hueco "
          "con un número que estaba en la misma norma, pero pertenecía a otro contexto —biogás de "
          "distribución, no transporte—. Preferimos el hueco honesto: informa mejor que un número falso.")

# --------------- 7. Motor determinista + ISO 13443 ---------------
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
_box(s, 0.6, 4.55, 12.13, 0.45, fill=AZUL)
_texto(s, 0.8, 4.58, 5.0, 0.4, [("Factores literales de la Tabla A.1 · ISO 13443", 13, BLANCO, True, False, 0)],
       anchor=MSO_ANCHOR.MIDDLE)
_texto(s, 8.5, 4.58, 2.0, 0.4, [("PCS", 13, CYAN, True, False, 0)],
       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
_texto(s, 10.6, 4.58, 2.0, 0.4, [("Wobbe", 13, CYAN, True, False, 0)],
       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
factores = [
    ("25/0 → 0/0", "Portugal, Alemania, P. Bajos, Bélgica, Noruega, Polonia, Dinamarca, Hungría, Austria, Suiza, Grecia", "1,0026", "1,0026"),
    ("15/15 → 0/0", "Italia, UE, Chequia, Irlanda, Rumanía, Turquía, Reino Unido", "1,0570", "1,0569"),
    ("25/20 → 0/0", "Eslovaquia — par no tabulado: se calcula con las ecuaciones del Anexo B de la norma", "≈1,076", "≈1,076"),
    ("0/0 → 0/0", "España (base) y Francia — identidad, no hay conversión", "×1", "×1"),
]
y = 5.0
for i, (par, paises, pcs, wob) in enumerate(factores):
    _box(s, 0.6, y, 12.13, 0.42, fill=GRISCL if i % 2 == 0 else BLANCO)
    _texto(s, 0.8, y + 0.01, 1.8, 0.4, [(par, 12, AZUL, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 2.6, y + 0.01, 5.8, 0.4, [(paises, 11, GRIS, False, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 8.5, y + 0.01, 2.0, 0.4, [(pcs, 12, TINTA, True, False, 0)],
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    _texto(s, 10.6, y + 0.01, 2.0, 0.4, [(wob, 12, TINTA, True, False, 0)],
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.44
_texto(s, 0.6, 6.78, 12.13, 0.3,
       [("Estos factores NO se estiman: se toman literalmente de la norma. España es siempre la base de referencia.",
         12, AZUL, True, False, 0)])
_notes(s, "Un punto clave para la credibilidad es la comparabilidad: no basta con tener los números, hay que "
          "poder compararlos. Por eso llevamos todo a la base española aplicando los factores de la ISO 13443, "
          "que no estimamos sino que tomamos literalmente de la norma. Fijaos en la fila de Eslovaquia: su par "
          "de condiciones no está tabulado, así que se calcula con las ECUACIONES DEL ANEXO B de la misma "
          "norma. Sigue siendo un valor derivado de la norma, no un número inventado. Es la pregunta fina que "
          "os pueden hacer.")

# --------------- 8. La IA, sus salvaguardas y el RAG ---------------
s = _slide(); _cabecera(s, "La IA, sus salvaguardas y el RAG", nxt(), kicker="Cómo funciona")
_texto(s, 0.6, 1.35, 12.2, 0.35,
       [("Cuando una consulta sí llega al modelo, opera atada en corto.", 14, GRIS, False, False, 0)])
_rbox(s, 0.6, 1.8, 5.9, 3.7, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 0.6, 1.8, 5.9, 0.5, fill=VERDE)
_texto(s, 0.78, 1.85, 5.5, 0.42, [("QUÉ PUEDE Y QUÉ NO PUEDE EL MODELO", 14, BLANCO, True, False, 0)])
_texto(s, 0.8, 2.45, 5.5, 2.9, [
    ("PUEDE: interpretar la pregunta, detectar la intención y REDACTAR la respuesta.",
     13, TINTA, False, True, 0),
    ("NO PUEDE: generar límites, inventar valores, deducir conversiones ni inferir comparabilidad.",
     13, AZUL, True, True, 0),
    ("Para cualquier número invoca una herramienta: consultar · evaluar_cumplimiento · convertir_unidades · buscar_pdfs.",
     13, TINTA, False, True, 0),
    ("El SYSTEM_PROMPT le prohíbe inventar cifras, le obliga a citar y acota su ámbito. Temperatura 0.",
     13, TINTA, False, True, 0),
], space=9)
_rbox(s, 6.85, 1.8, 5.9, 3.7, fill=GRISCL, line=BORDE, line_w=1)
_box(s, 6.85, 1.8, 5.9, 0.5, fill=CYAN)
_texto(s, 7.03, 1.85, 5.5, 0.42, [("LA RECUPERACIÓN DOCUMENTAL (RAG)", 14, BLANCO, True, False, 0)])
_texto(s, 7.05, 2.45, 5.5, 2.9, [
    ("INDEXACIÓN: pdfplumber extrae el texto y lo trocea en fragmentos CON SOLAPE (ventana deslizante, no por página).",
     13, TINTA, False, True, 0),
    ("Así, una respuesta partida entre dos páginas queda ENTERA dentro de un mismo fragmento.",
     13, TINTA, False, True, 0),
    ("RECUPERACIÓN: búsqueda LÉXICA (SQLite LIKE); devuelve archivo, página y extracto.",
     13, TINTA, False, True, 0),
    ("Es léxica, NO vectorial. Decisión consciente: reproducible y sin depender de terceros.",
     13, AZUL, True, True, 0),
], space=9)
_box(s, 0.6, 5.7, 12.15, 1.2, fill=AZULCL)
_box(s, 0.6, 5.7, 0.09, 1.2, fill=AZUL)
_texto(s, 0.9, 5.77, 11.75, 1.1, [
    ("La salvaguarda que lo cierra todo: si OpenAI no está disponible —sin clave, sin red o por límite—, el "
     "sistema conmuta al motor determinista. EL CHAT NUNCA DEVUELVE ERROR.", 14, AZUL, True, False, 0),
    ("¿Y una búsqueda semántica? Lo medimos antes de decidir: el estudio de terminología dio un índice de "
     "variación de 27,4 en gas natural. La capa semántica queda preparada y activable, pero desactivada por "
     "defecto por reproducibilidad.", 12.5, GRIS, False, False, 0),
], space=3)
_notes(s, "Hay que ser muy claro: el modelo NO es la fuente del dato, es la capa de lenguaje. Si necesita un "
          "número, lo pide. Sobre el RAG somos transparentes: es léxico, no semántico. No es una carencia, es "
          "una decisión: es reproducible y no depende de terceros. Y antes de decidirlo lo MEDIMOS, con el "
          "estudio de terminología. Primero medir, luego decidir. La salvaguarda de abajo es la más "
          "importante: la IA es una comodidad, no una dependencia.")

# --------------- 9. Ampliación: biometano e hidrógeno ---------------
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
_box(s, 0.6, 4.85, 12.13, 1.45, fill=NARANJACL)
_box(s, 0.6, 4.85, 0.09, 1.45, fill=NARANJA)
_texto(s, 0.9, 4.93, 11.7, 1.3, [
    ("Hidrógeno — la distinción esencial es de DOMINIO:", 14, NARANJAOS, True, False, 0),
    ("RED (el gasoducto, lo que compete a Enagás): CEN/TS 17977 y recomendación GIE — pureza H2 >= 98 % mol.   "
     "Hoy solo PORTUGAL lo fija como vinculante; España y Francia regulan el blending; la UE lo recomienda.",
     12.5, TINTA, False, False, 0),
    ("PRODUCTO / VEHÍCULO: ISO 14687 Grade D — pureza 99,97 % para pilas de combustible. NO es lo que necesita "
     "un operador de red. La herramienta los mantiene SEPARADOS para no confundirlos.",
     12.5, TINTA, False, False, 0),
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

# --------------- 10. Garantías y cierre ---------------
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
       [("La IA redacta el texto. Los números salen siempre de la normativa oficial.",
         18, BLANCO, True, False, 0)])
nxt()
_notes(s, "En síntesis: una herramienta que compara la calidad regulatoria del gas natural, el biometano y el "
          "hidrógeno entre jurisdicciones, con trazabilidad total y sin cifras inventadas. Las cifras salen "
          "siempre de normativa oficial verificada; la IA solo redacta el texto. Muchas gracias; quedo a "
          "vuestra disposición para las preguntas.")

prs.save(PPTX)
print("PPTX generado:", os.path.relpath(PPTX, RAIZ),
      f"({os.path.getsize(PPTX)//1024} KB, {len(prs.slides._sldIdLst)} diapositivas)")
