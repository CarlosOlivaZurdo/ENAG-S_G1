# -*- coding: utf-8 -*-
"""Genera LA presentación del Comparador Regulatorio de Calidad de Gas (estilo Enagás).

    python docs/generar_presentacion.py

Presentación única y completa, centrada en:
  - la ARQUITECTURA del sistema (con el diagrama),
  - la ONTOLOGÍA (con el diagrama y la anatomía de un valor),
  - TODAS LAS HERRAMIENTAS que usa la aplicación, indicando el papel de cada una.

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

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ONT = os.path.join(RAIZ, "data", "ontologia", "ontologia_enagas.yaml")
PPTX = os.path.join(AQUI, "Presentacion_Comparador_Gas.pptx")
IMG_ARQ = os.path.join(AQUI, "Arquitectura_Esquema_Cajas.png")
IMG_ONT = os.path.join(AQUI, "Ontologia_Estructura.png")

# ----------------------- Datos reales desde la ontología -----------------------
_d = yaml.safe_load(io.open(ONT, encoding="utf-8"))
ONTO = _d["ontologia"]
P = _d["parametros"]
PB = _d.get("parametros_biometano") or {}
PH = _d.get("parametros_hidrogeno") or {}
FUENTES = ONTO["fuentes_normativas"]
CODES = ["ES", "PT", "FR", "IT", "DE", "NL", "BE", "NOR", "PL", "DK", "HU",
         "AT", "CH", "CZ", "GR", "IE", "RO", "SK", "TR", "GB", "UE"]
PARAMS = ["WOBBE", "PCS", "DENS_REL", "S_TOTAL", "H2S_COS", "RSH", "O2", "CO2", "PR_H2O", "PR_HC"]


def _estados(seccion):
    c = collections.Counter()
    for v in seccion.values():
        for lim in (v.get("limites") or {}).values():
            c[(lim or {}).get("estado_verificacion", "?")] += 1
    return c


EGN = _estados({k: P[k] for k in PARAMS})
N_VERIF = EGN.get("VERIFICADO", 0)
N_NOVER = EGN.get("NO_VERIFICABLE_SIN_FUENTE", 0)
N_CELDAS = len(PARAMS) * len(CODES)
N_JUR, N_PAR = len(CODES), len(PARAMS)
N_FUENTES = len(FUENTES)
N_GASES = len(ONTO.get("tipos_gas", []) or [])
VER_ONT = ONTO.get("version", "—")

# ----------------------------- Paleta y utilidades -----------------------------
AZUL = RGBColor(0x01, 0x3A, 0x57)
CYAN = RGBColor(0x00, 0x99, 0xD6)
VERDE = RGBColor(0x6C, 0xB3, 0x3E)
NARANJA = RGBColor(0xE8, 0x8A, 0x1A)
GRIS = RGBColor(0x4A, 0x5B, 0x68)
TINTA = RGBColor(0x1B, 0x2A, 0x38)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRISCL = RGBColor(0xEE, 0xF2, 0xF6)
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


def _box(slide, l, t, w, h, fill=None, line=None, line_w=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = line_w or Pt(1)
    shp.shadow.inherit = False
    return shp


def _text(slide, l, t, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6, font=FUENTE):
    """runs: lista de (texto, size, color, bold, bullet, level)."""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = Pt(4); tf.margin_right = Pt(4); tf.margin_top = Pt(2); tf.margin_bottom = Pt(2)
    for i, r in enumerate(runs):
        txt, size, color, bold, bullet, level = (r + (None,) * 6)[:6]
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space); p.level = level or 0
        run = p.add_run(); run.text = ("• " + txt) if bullet else txt
        run.font.name = font; run.font.size = Pt(size)
        run.font.color.rgb = color; run.font.bold = bool(bold)
    return tb


def _cabecera(slide, titulo, n, sub=None):
    _box(slide, 0, 0, W, Inches(1.05), fill=AZUL)
    _box(slide, 0, Inches(1.05), W, Pt(4), fill=CYAN)
    _text(slide, Inches(0.55), Inches(0.16), Inches(11.5), Inches(0.8),
          [(titulo, 26, BLANCO, True, False, 0)], anchor=MSO_ANCHOR.MIDDLE)
    _text(slide, Inches(0.55), Inches(7.05), Inches(9), Inches(0.35),
          [("Comparador Regulatorio de Calidad de Gas — Enagás", 10, GRIS, False, False, 0)])
    _text(slide, Inches(12.2), Inches(7.05), Inches(0.9), Inches(0.35),
          [(str(n), 10, GRIS, False, False, 0)], align=PP_ALIGN.RIGHT)


N = 0


def nxt():
    global N
    N += 1
    return N


def slide_contenido(titulo, intro=None, bullets=None, notas="", bsize=17):
    s = _slide(); _cabecera(s, titulo, nxt())
    top = 1.45
    if intro:
        _text(s, Inches(0.6), Inches(top), Inches(12.1), Inches(0.9),
              [(intro, 15, GRIS, False, False, 0)])
        top += 0.85
    if bullets:
        runs = []
        for b in bullets:
            if isinstance(b, tuple):
                runs.append((b[0], bsize - 2, GRIS, False, True, 1))
            else:
                runs.append((b, bsize, TINTA, False, True, 0))
        _text(s, Inches(0.7), Inches(top), Inches(11.9), Inches(5.2), runs, space=10)
    if notas:
        _notes(s, notas)
    return s


def slide_tabla(titulo, headers, filas, notas="", intro=None, col_ratios=None, fsize=13, hsize=13):
    s = _slide(); _cabecera(s, titulo, nxt())
    top = 1.5
    if intro:
        _text(s, Inches(0.6), Inches(top), Inches(12.1), Inches(0.6),
              [(intro, 14, GRIS, False, False, 0)])
        top += 0.62
    nrows, ncols = len(filas) + 1, len(headers)
    tw = Inches(12.1)
    gr = s.shapes.add_table(nrows, ncols, Inches(0.6), Inches(top), tw, Inches(0.4)).table
    gr.first_row = False; gr.horz_banding = False
    if col_ratios:
        tot = sum(col_ratios)
        for j, cr in enumerate(col_ratios):
            gr.columns[j].width = int(tw * cr / tot)
    for j, htxt in enumerate(headers):
        c = gr.cell(0, j); c.fill.solid(); c.fill.fore_color.rgb = AZUL
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        c.margin_top = Pt(2); c.margin_bottom = Pt(2)
        p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = htxt
        r.font.name = FUENTE; r.font.size = Pt(hsize); r.font.bold = True; r.font.color.rgb = BLANCO
    for i, fila in enumerate(filas, start=1):
        for j, val in enumerate(fila):
            c = gr.cell(i, j); c.fill.solid()
            c.fill.fore_color.rgb = GRISCL if i % 2 else BLANCO
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_top = Pt(2); c.margin_bottom = Pt(2)
            p = c.text_frame.paragraphs[0]; p.word_wrap = True
            mono = isinstance(val, str) and (val.endswith(".py") or val.startswith("/"))
            run = p.add_run(); run.text = val
            run.font.name = MONO if mono else FUENTE
            run.font.size = Pt(fsize - 1 if mono else fsize)
            run.font.bold = bool(j == 0 and not mono)
            run.font.color.rgb = AZUL if j == 0 else TINTA
    if notas:
        _notes(s, notas)
    return s


def slide_imagen(titulo, img, notas="", intro=None, puntos=None, alto=5.35):
    """Diagrama a la izquierda (escalado por ALTURA para que nunca se salga) y puntos clave a la derecha."""
    s = _slide(); _cabecera(s, titulo, nxt())
    top = 1.4
    if intro:
        _text(s, Inches(0.6), Inches(top), Inches(12.1), Inches(0.45),
              [(intro, 14, GRIS, False, False, 0)])
        top += 0.5
    alto_disp = min(alto, 6.95 - top)  # nunca invadir el pie de página
    if os.path.exists(img):
        s.shapes.add_picture(img, Inches(0.55), Inches(top), height=Inches(alto_disp))
    else:
        _text(s, Inches(0.6), Inches(top), Inches(6), Inches(1),
              [(f"[Falta la imagen: {os.path.basename(img)}]", 14, NARANJA, True, False, 0)])
    if puntos:
        runs = []
        for p in puntos:
            if isinstance(p, tuple):
                runs.append((p[0], 13, GRIS, False, False, 1))
            else:
                runs.append((p, 15, TINTA, False, True, 0))
        _text(s, Inches(7.9), Inches(top), Inches(4.9), Inches(alto_disp), runs, space=11)
    if notas:
        _notes(s, notas)
    return s


# ================================ CONTENIDO ================================

# --- 1. Portada ---
s = _slide()
_box(s, 0, 0, W, H, fill=AZUL)
_box(s, 0, Inches(4.55), W, Pt(5), fill=CYAN)
_box(s, Inches(0.9), Inches(2.0), Inches(0.16), Inches(2.2), fill=VERDE)
_text(s, Inches(1.25), Inches(2.0), Inches(11), Inches(2.3), [
    ("Comparador Regulatorio", 40, BLANCO, True, False, 0),
    ("de Calidad de Gas", 40, BLANCO, True, False, 0),
], space=2)
_text(s, Inches(1.28), Inches(4.75), Inches(11), Inches(1.3), [
    ("Arquitectura, ontología y herramientas del sistema", 20, CYAN, False, False, 0),
    (f"Gas natural · biometano · hidrógeno — {N_JUR} jurisdicciones · {N_PAR} parámetros · "
     f"{N_CELDAS} valores trazables", 15, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
], space=6)
_text(s, Inches(1.28), Inches(6.5), Inches(11), Inches(0.5),
      [(f"Ontología v{VER_ONT} · Presentación técnica", 13, RGBColor(0x9F, 0xB3, 0xC4), False, False, 0)])
_notes(s, "Presentación del sistema. El hilo conductor es doble: CÓMO ESTÁ CONSTRUIDO "
          "(arquitectura, ontología y herramientas) y POR QUÉ ES FIABLE (trazabilidad total y "
          "cero cifras inventadas). Presentar el equipo y pasar al índice.")

# --- 2. Índice ---
slide_contenido("Índice",
    intro="Recorrido de la presentación:",
    bullets=[
        "Contexto, objetivo y cifras del sistema",
        "ARQUITECTURA — los cuatro componentes y el recorrido de una consulta",
        "Las tres capas de datos",
        "ONTOLOGÍA — estructura, anatomía de un valor y estados de verificación",
        "HERRAMIENTAS — stack completo: backend, datos, documentos, IA y frontend",
        "Los módulos propios del código y los endpoints de la API",
        "Motor determinista, normalización ISO 13443, IA y RAG",
        "Ampliación a biometano e hidrógeno · Garantías",
    ],
    notas="Agenda. Tres bloques: primero la ARQUITECTURA (la forma del sistema), luego la ONTOLOGÍA "
          "(el corazón del dato), y luego las HERRAMIENTAS (con qué está hecho, pieza a pieza). "
          "Cerramos con las garantías.")

# --- 3. Contexto y objetivo ---
slide_contenido("Contexto y objetivo",
    intro="El problema y la propuesta de valor.",
    bullets=[
        "Cada país regula la calidad admisible del gas con su propia normativa: Wobbe, PCS, azufre, CO2, puntos de rocío…",
        "La información está dispersa en boletines oficiales distintos, en varios idiomas, con unidades y condiciones de referencia diferentes.",
        "Comparar dos marcos regulatorios a mano es laborioso y propenso a error.",
        f"Solución: un asistente que compara esa calidad entre {N_JUR} jurisdicciones y {N_PAR} parámetros, en lenguaje natural.",
        "Principio de diseño: CERO CIFRAS INVENTADAS. Ningún valor se estima; todos proceden de normativa oficial, con su cita.",
    ],
    notas="El problema es concreto: la información regulatoria está dispersa y no es directamente comparable "
          "(unidades y condiciones distintas). Nuestra solución compara 21 jurisdicciones y 10 parámetros en "
          "lenguaje natural, y su principio de diseño es que no genera ninguna cifra por estimación.")

# --- 4. El sistema en cifras ---
s = _slide(); _cabecera(s, "El sistema en cifras", nxt())
tarjetas = [(str(N_JUR), "jurisdicciones"), (str(N_PAR), "parámetros"),
            (str(N_CELDAS), "valores trazables"), ("0", "cifras inventadas")]
x = 0.6
for num, txt in tarjetas:
    _box(s, Inches(x), Inches(1.9), Inches(2.95), Inches(2.4), fill=GRISCL)
    _box(s, Inches(x), Inches(1.9), Inches(2.95), Pt(6), fill=CYAN)
    _text(s, Inches(x), Inches(2.25), Inches(2.95), Inches(1.2),
          [(num, 54, AZUL, True, False, 0)], align=PP_ALIGN.CENTER)
    _text(s, Inches(x), Inches(3.45), Inches(2.95), Inches(0.6),
          [(txt, 15, GRIS, False, False, 0)], align=PP_ALIGN.CENTER)
    x += 3.11
_text(s, Inches(0.6), Inches(4.75), Inches(12.1), Inches(1.9), [
    (f"Detrás del cero: de los {N_CELDAS} valores, {N_VERIF} están VERIFICADOS literalmente contra su boletín "
     f"oficial y {N_NOVER} se declaran NO VERIFICABLES porque la norma de ese país no fija ese parámetro.",
     17, TINTA, False, False, 0),
    ("No se rellenan con estimaciones: se marcan y se explica el motivo. No hay estado intermedio.",
     17, TINTA, False, False, 0),
    (f"Base documental: {N_FUENTES} normas oficiales catalogadas · {N_GASES} tipos de gas "
     f"(gas natural, biometano, hidrógeno).", 15, GRIS, False, False, 0),
], space=10)
_notes(s, f"Cuatro cifras fijan el alcance: {N_JUR} jurisdicciones, {N_PAR} parámetros, {N_CELDAS} valores "
          f"trazables y CERO cifras inventadas. Detrás de ese cero está lo importante: {N_VERIF} verificados "
          f"verbatim y {N_NOVER} declarados 'no verificable' porque la norma no los fija. Esa disciplina es "
          "la que sostiene todo el proyecto.")

# ============================== ARQUITECTURA ==============================

# --- 5. Arquitectura: el diagrama ---
slide_imagen("Arquitectura del sistema", IMG_ARQ,
    intro="Cuatro componentes con responsabilidades bien delimitadas.",
    puntos=[
        "Interfaz web — formula la consulta.",
        ("index.html · JavaScript vanilla", True),
        "Servidor de aplicación — el núcleo: decide, calcula y accede al dato.",
        ("Python · FastAPI · uvicorn", True),
        "Base de conocimiento — las cifras verificadas y sus fuentes.",
        ("Ontología YAML", True),
        "Servicio de IA — externo y acotado: solo redacta.",
        ("OpenAI · opcional", True),
        "Los DATOS y los CÁLCULOS son propios. La IA es un proveedor auxiliar bajo control.",
    ],
    notas="Este es el esquema del sistema. Cuatro cajas: la INTERFAZ WEB, donde se formula la consulta; "
          "el SERVIDOR DE APLICACIÓN (FastAPI), que concentra la lógica y decide cómo resolver cada pregunta; "
          "la BASE DE CONOCIMIENTO (la ontología), con los datos verificados y sus fuentes; y el SERVICIO DE "
          "IA, externo, usado de forma acotada. El mensaje clave: los DATOS y los CÁLCULOS son propios; "
          "la IA es un proveedor auxiliar bajo control.")

# --- 6. Los cuatro componentes ---
slide_tabla("Los cuatro componentes",
    ["Componente", "Responsabilidad", "Con qué está hecho"],
    [
        ["Interfaz web", "Formular la consulta y mostrar la respuesta con sus citas. Cinco secciones.",
         "index.html — HTML + JavaScript vanilla"],
        ["Servidor de aplicación", "El núcleo: router determinista, cálculos exactos, acceso al dato y custodia de credenciales.",
         "Python + FastAPI + uvicorn"],
        ["Base de conocimiento", "La ÚNICA fuente autorizada de cifras: los límites con su contexto y su fuente.",
         "Ontología YAML (PyYAML)"],
        ["Servicio de IA (externo)", "Solo interpretar la pregunta y REDACTAR el texto. Nunca genera cifras.",
         "API de OpenAI (GPT-4o-mini)"],
    ],
    col_ratios=[2.2, 5.2, 3.2], fsize=13,
    notas="Cada componente tiene una responsabilidad y una sola. La separación es deliberada: el mundo "
          "determinista (servidor + ontología) es el único que produce números; el mundo conversacional "
          "(la IA) solo redacta. Esa separación es lo que hace imposible la alucinación numérica.")

# --- 7. Recorrido de una consulta ---
s = _slide(); _cabecera(s, "Recorrido de una consulta", nxt())
_text(s, Inches(0.6), Inches(1.4), Inches(12.1), Inches(0.5),
      [("El router determinista decide, para cada pregunta, quién la resuelve.", 15, GRIS, False, False, 0)])
# Caja 1: usuario
_box(s, Inches(0.6), Inches(2.15), Inches(2.3), Inches(1.0), fill=GRISCL)
_box(s, Inches(0.6), Inches(2.15), Inches(2.3), Pt(5), fill=CYAN)
_text(s, Inches(0.6), Inches(2.35), Inches(2.3), Inches(0.7),
      [("Pregunta", 15, AZUL, True, False, 0), ("index.html", 11, GRIS, False, False, 0)],
      align=PP_ALIGN.CENTER, space=1)
# Caja 2: router
_box(s, Inches(3.35), Inches(2.15), Inches(2.6), Inches(1.0), fill=AZUL)
_text(s, Inches(3.35), Inches(2.3), Inches(2.6), Inches(0.8),
      [("Router determinista", 14, BLANCO, True, False, 0), ("api.py", 11, CYAN, False, False, 0)],
      align=PP_ALIGN.CENTER, space=1)
# Rama A (determinista)
_box(s, Inches(6.5), Inches(1.75), Inches(6.2), Inches(1.75), fill=RGBColor(0xE8, 0xF4, 0xE2))
_box(s, Inches(6.5), Inches(1.75), Pt(6), Inches(1.75), fill=VERDE)
_text(s, Inches(6.75), Inches(1.9), Inches(5.8), Inches(1.5), [
    ("RUTA A — Consulta cuantitativa  (la mayoría)", 15, RGBColor(0x3E, 0x6B, 0x22), True, False, 0),
    ("La resuelve el CÓDIGO leyendo la ontología. Sin IA.", 13, TINTA, False, False, 0),
    ("Un límite · cumplimiento · comparación · conversión", 12, GRIS, False, False, 0),
], space=3)
# Rama B (IA)
_box(s, Inches(6.5), Inches(3.75), Inches(6.2), Inches(1.75), fill=RGBColor(0xFD, 0xF0, 0xDF))
_box(s, Inches(6.5), Inches(3.75), Pt(6), Inches(1.75), fill=NARANJA)
_text(s, Inches(6.75), Inches(3.9), Inches(5.8), Inches(1.5), [
    ("RUTA B — Texto abierto", 15, RGBColor(0xA5, 0x61, 0x0E), True, False, 0),
    ("Va al LLM, que PIDE las cifras a las herramientas.", 13, TINTA, False, False, 0),
    ("El LLM redacta; los números siguen saliendo de la ontología.", 12, GRIS, False, False, 0),
], space=3)
_text(s, Inches(0.6), Inches(5.85), Inches(12.1), Inches(1.1), [
    ("En ambas rutas la cifra sale SIEMPRE de la ontología. El LLM nunca la produce: la solicita.",
     16, AZUL, True, False, 0),
    ("Si el servicio de IA no está disponible, el sistema conmuta automáticamente al motor determinista: el chat nunca falla.",
     14, GRIS, False, False, 0),
], space=6)
_notes(s, "Toda consulta pasa primero por el router. Si es cuantitativa —un límite, un cumplimiento, una "
          "comparación, una conversión— la resuelve el código leyendo la ontología, sin IA y sin posibilidad "
          "de error. Si es de texto abierto, va al LLM, pero incluso ahí el LLM no inventa: llama a las "
          "herramientas, que leen la ontología. Y si OpenAI cae, conmutamos a determinista. La cifra siempre "
          "viene del mismo sitio.")

# --- 8. Las tres capas de datos ---
slide_tabla("Las tres capas de datos",
    ["Capa", "Contenido", "Función", "Herramienta"],
    [
        ["1. Documentos oficiales", "Los ~22 PDF de las normas (BOE, ERSE, GRTgaz, DVGW, Fluxys…), guardados en local",
         "Fuente última de verdad", "data/raw/"],
        ["2. Ontología", f"Las {N_CELDAS} cifras extraídas de esos PDF, con su contexto y su cita",
         "De aquí salen TODAS las respuestas", "YAML + PyYAML"],
        ["3. Índice documental (RAG)", "El TEXTO de los PDF troceado en fragmentos con solape",
         "Buscador interno para texto abierto", "SQLite + pdfplumber"],
    ],
    intro="No hay una única base de datos: hay tres capas con funciones distintas.",
    col_ratios=[2.3, 4.4, 3.0, 2.0], fsize=12,
    notas="Suele asumirse que hay una gran base de datos única. No es así. Las CIFRAS viven SOLO en la capa 2, "
          "la ontología. La capa 3, el índice documental, no guarda ningún número: solo sirve para localizar el "
          "pasaje pertinente en las consultas de texto abierto. Y los PDF los guardamos localmente para no "
          "depender de que una web externa siga disponible.")

# ================================ ONTOLOGÍA ================================

# --- 9. La ontología: el diagrama ---
slide_imagen("La ontología: estructura", IMG_ONT,
    intro="El corazón del sistema: la base de conocimiento verificada.",
    puntos=[
        f"Un único fichero YAML, legible por una persona: {N_CELDAS} cifras de gas natural con su contexto.",
        f"Un catálogo de {N_FUENTES} normas oficiales: cada valor enlaza con la suya.",
        f"Tres secciones de parámetros ({N_GASES} tipos de gas) con EXACTAMENTE el mismo esquema.",
        "El motor determinista lee de aquí. El LLM nunca calcula ni inventa valores.",
        "¿Por qué YAML y no una base de datos? Porque a esta escala es más AUDITABLE y TRAZABLE, y se versiona en git junto al código.",
    ],
    notas="La ontología es el elemento central. Es la extracción verificada de los PDF oficiales, en un "
          "formato estructurado y legible por una persona. El motor determinista lee de aquí; el LLM nunca "
          "calcula ni inventa valores. Recorrer el diagrama: el catálogo de fuentes, los tipos de gas y las "
          "tres secciones de parámetros.")

# --- 10. Qué contiene la ontología ---
slide_tabla("Qué contiene la ontología",
    ["Clave del fichero", "Contenido"],
    [
        ["ontologia.fuentes_normativas", f"El catálogo de las {N_FUENTES} normas oficiales: id, nombre, organismo, publicación, URL (cita) y PDF (copia local)."],
        ["ontologia.tipos_gas", f"El registro de los {N_GASES} tipos de gas y a qué sección de parámetros apunta cada uno."],
        ["parametros", f"GAS NATURAL: los {N_PAR} parámetros, cada uno con un bloque 'limites:' con una entrada por país (×{N_JUR})."],
        ["parametros_biometano", f"BIOMETANO: {len(PB)} parámetros, con límites por jurisdicción (España, Portugal, Francia, UE)."],
        ["parametros_hidrogeno", f"HIDRÓGENO: {len(PH)} parámetros, con límites por jurisdicción (dominio de red y de producto)."],
    ],
    intro="Un único fichero: data/ontologia/ontologia_enagas.yaml",
    col_ratios=[3.2, 8.9], fsize=13,
    notas="Las tres secciones de parámetros comparten EXACTAMENTE el mismo esquema; solo cambian el conjunto "
          "de jurisdicciones y las fuentes. Por eso la ampliación a biometano e hidrógeno no cambió la "
          "arquitectura: se reutiliza la misma maquinaria.")

# --- 11. Anatomía de un valor ---
s = _slide(); _cabecera(s, "Anatomía de un valor", nxt())
_text(s, Inches(0.6), Inches(1.4), Inches(12.1), Inches(0.5),
      [("Cada límite NO es solo un número: guarda todo su contexto normativo. Ejemplo real — el O2 de España:",
        15, GRIS, False, False, 0)])
_box(s, Inches(0.6), Inches(2.0), Inches(6.9), Inches(3.5), fill=RGBColor(0xF5, 0xF8, 0xFA),
     line=RGBColor(0xDD, 0xE4, 0xEA))
_text(s, Inches(0.75), Inches(2.15), Inches(6.6), Inches(3.2), [
    ("ES:", 13, AZUL, True, False, 0),
    ("  fuente: ORDEN_TED_181_2025", 12, TINTA, False, False, 0),
    ("  articulo: \"Tabla 3, apdo. 2.5.2.1 (pág. 27)\"", 12, TINTA, False, False, 0),
    ("  tipo_limite: maximo", 12, TINTA, False, False, 0),
    ("  valor: 0.01", 12, TINTA, False, False, 0),
    ("  unidad: pct_mol", 12, TINTA, False, False, 0),
    ("  expresion_original: \"O2: – / 0,01 % mol\"", 12, TINTA, False, False, 0),
    ("  condiciones_referencia:", 12, TINTA, False, False, 0),
    ("    temperatura_volumen_C: 0", 12, TINTA, False, False, 0),
    ("    presion_bar: 1.01325", 12, TINTA, False, False, 0),
    ("  estado_verificacion: VERIFICADO", 12, VERDE, True, False, 0),
], space=2, font=MONO)
_text(s, Inches(7.75), Inches(2.0), Inches(4.95), Inches(3.6), [
    ("fuente — de qué norma sale (enlaza al catálogo).", 14, TINTA, False, True, 0),
    ("articulo — dónde exactamente: tabla, apartado, página.", 14, TINTA, False, True, 0),
    ("tipo_limite — máximo, mínimo o rango.", 14, TINTA, False, True, 0),
    ("valor + unidad — la cifra y su unidad.", 14, TINTA, False, True, 0),
    ("expresion_original — el TEXTO LITERAL de la norma.", 14, AZUL, True, True, 0),
    ("condiciones_referencia — T y P de referencia.", 14, TINTA, False, True, 0),
    ("estado_verificacion — la garantía anti-invención.", 14, AZUL, True, True, 0),
], space=9)
_text(s, Inches(0.6), Inches(5.8), Inches(12.1), Inches(1.0), [
    ("Gracias a 'expresion_original', cualquier auditor puede recomprobar la transcripción sin abrir el PDF.",
     16, AZUL, True, False, 0),
], space=4)
_notes(s, "Aquí está el valor real del diseño: de cada dato no guardamos solo el número, sino todo su contexto. "
          "El campo clave es 'expresion_original': el texto literal de la norma, tal cual está redactado. "
          "Eso convierte la confianza en verificabilidad: no hay que creerse el dato, se puede comprobar.")

# --- 12. Estados de verificación ---
s = _slide(); _cabecera(s, "Estados de verificación", nxt())
_text(s, Inches(0.6), Inches(1.4), Inches(12.1), Inches(0.5),
      [("La garantía anti-invención. Solo hay dos estados; no existe un intermedio.", 15, GRIS, False, False, 0)])
_box(s, Inches(0.6), Inches(2.1), Inches(5.9), Inches(2.3), fill=RGBColor(0xE8, 0xF4, 0xE2))
_box(s, Inches(0.6), Inches(2.1), Inches(5.9), Pt(6), fill=VERDE)
_text(s, Inches(0.85), Inches(2.35), Inches(5.5), Inches(2.0), [
    (f"{N_VERIF}   VERIFICADO", 26, RGBColor(0x3E, 0x6B, 0x22), True, False, 0),
    ("Cifra contrastada VERBATIM contra su boletín oficial.", 14, TINTA, False, False, 0),
], space=8)
_box(s, Inches(6.85), Inches(2.1), Inches(5.85), Inches(2.3), fill=RGBColor(0xFD, 0xF0, 0xDF))
_box(s, Inches(6.85), Inches(2.1), Inches(5.85), Pt(6), fill=NARANJA)
_text(s, Inches(7.1), Inches(2.35), Inches(5.45), Inches(2.0), [
    (f"{N_NOVER}   NO VERIFICABLE", 26, RGBColor(0xA5, 0x61, 0x0E), True, False, 0),
    ("La norma de ese país NO FIJA ese parámetro. No se inventa: se declara el hueco y se explica.",
     14, TINTA, False, False, 0),
], space=8)
_text(s, Inches(0.6), Inches(4.75), Inches(12.1), Inches(2.0), [
    ("Los huecos no son errores: son honestidad.", 18, AZUL, True, False, 0),
    ("Ejemplo real — Dinamarca: los límites de O2 y CO2 de su norma corresponden al BIOGÁS DE DISTRIBUCIÓN, "
     "no al gas natural de transporte. Trasladar ese valor sería un error metodológico; por eso, para gas "
     "natural, se marcaron como no verificable.", 15, TINTA, False, False, 0),
    ("(En biometano e hidrógeno existe además VERIFICADO_SECUNDARIO: valor tomado de fuente pública "
     "secundaria porque la norma primaria es de pago.)", 13, GRIS, False, False, 0),
], space=9)
_notes(s, "Esta diapositiva es la garantía anti-invención. Dos estados y ninguno intermedio: o la cifra consta "
          "en la norma, o se declara que la norma no la establece. El ejemplo de Dinamarca es el que mejor lo "
          "ilustra: era fácil rellenar el hueco con un número de la misma norma, pero era de otro contexto "
          "(biogás de distribución, no transporte). Preferimos el hueco honesto.")

# ============================== HERRAMIENTAS ==============================

# --- 13. El stack de un vistazo ---
s = _slide(); _cabecera(s, "El stack tecnológico de un vistazo", nxt())
_text(s, Inches(0.6), Inches(1.4), Inches(12.1), Inches(0.5),
      [("Todas las herramientas que usa la aplicación, agrupadas por capa.", 15, GRIS, False, False, 0)])
capas = [
    ("FRONTEND", CYAN, ["HTML + CSS", "JavaScript vanilla", "marked (Markdown)", "DOMPurify (saneado)", "localStorage"]),
    ("BACKEND", AZUL, ["Python 3.11+", "FastAPI", "uvicorn", "pydantic", "python-dotenv"]),
    ("DATOS Y DOCUMENTOS", VERDE, ["PyYAML (ontología)", "SQLite (índice RAG)", "pdfplumber (PDF)", "pandas", "openpyxl · xhtml2pdf"]),
    ("IA (opcional)", NARANJA, ["OpenAI SDK", "GPT-4o-mini", "function calling", "temperatura 0", "— sustituible —"]),
]
x = 0.6
for titulo, color, items in capas:
    _box(s, Inches(x), Inches(2.05), Inches(2.95), Inches(3.6), fill=GRISCL)
    _box(s, Inches(x), Inches(2.05), Inches(2.95), Inches(0.5), fill=color)
    _text(s, Inches(x), Inches(2.11), Inches(2.95), Inches(0.4),
          [(titulo, 13, BLANCO, True, False, 0)], align=PP_ALIGN.CENTER)
    _text(s, Inches(x + 0.15), Inches(2.7), Inches(2.65), Inches(2.8),
          [(i, 13, TINTA, False, True, 0) for i in items], space=8)
    x += 3.11
_text(s, Inches(0.6), Inches(5.9), Inches(12.1), Inches(1.0), [
    ("Todo el stack es software libre salvo la API de OpenAI, que es el único componente de pago — y es opcional.",
     15, AZUL, True, False, 0),
    ("Calidad: pytest (pruebas automáticas) · git (versionado del código y de la ontología).", 14, GRIS, False, False, 0),
], space=5)
_notes(s, "Este es el mapa completo de herramientas. Cuatro capas. Lo importante: todo es software libre "
          "excepto la API de OpenAI, que además es OPCIONAL: sin ella el sistema sigue funcionando en modo "
          "determinista. En las siguientes diapositivas vemos el papel exacto de cada pieza.")

# --- 14. Herramientas del backend ---
slide_tabla("Herramientas — Backend",
    ["Herramienta", "Para qué sirve exactamente en la aplicación"],
    [
        ["Python 3.11+", "Lenguaje de todo el backend y de los scripts de datos, diagramas y documentación."],
        ["FastAPI", "Framework con el que está construido NUESTRO servidor: define los endpoints y valida las peticiones."],
        ["uvicorn", "El servidor que ejecuta FastAPI y atiende el puerto 8000 (lo lanza iniciar_chatbot.bat)."],
        ["pydantic", "Valida y tipa los datos que entran y salen de cada endpoint (evita peticiones malformadas)."],
        ["python-dotenv", "Carga la clave de OpenAI desde el entorno / .env, para que nunca esté escrita en el código."],
        ["pytest", "Ejecuta las pruebas automáticas: comprueba que las 210 celdas resuelven y que nada se rompe."],
    ],
    col_ratios=[2.6, 9.5], fsize=13,
    notas="Ojo con una confusión frecuente: FastAPI y la API de OpenAI no son lo mismo aunque ambas lleven "
          "'API'. FastAPI es el framework con el que construimos NUESTRO servidor: es infraestructura propia y "
          "gratuita. La API de OpenAI es un servicio de terceros, de pago, que consumimos puntualmente.")

# --- 15. Herramientas de datos y documentos ---
slide_tabla("Herramientas — Datos y documentos",
    ["Herramienta", "Para qué sirve exactamente en la aplicación"],
    [
        ["PyYAML", "Lee la ONTOLOGÍA (el fichero .yaml con las cifras verificadas). Es la puerta a la base de conocimiento."],
        ["pdfplumber", "Extrae el TEXTO de los PDF oficiales para poder indexarlos y buscar en ellos."],
        ["sqlite3", "Base de datos ligera que actúa de ÍNDICE del buscador documental (RAG). No guarda ninguna cifra."],
        ["pandas", "Manejo tabular de datos en el motor determinista (carga y cruce de tablas)."],
        ["openpyxl", "Genera el informe de la matriz comparativa en EXCEL, con las celdas coloreadas por nivel."],
        ["xhtml2pdf", "Genera el informe de la matriz en PDF, y también la documentación del proyecto."],
        ["cryptography", "Genera el certificado autofirmado para servir por HTTPS (opcional, para producción)."],
    ],
    col_ratios=[2.6, 9.5], fsize=12.5,
    notas="Aquí está el reparto real del dato. PyYAML abre la ontología, que es de donde salen TODAS las cifras. "
          "pdfplumber y sqlite3 son solo para el buscador documental: el índice NO guarda números. openpyxl y "
          "xhtml2pdf son para exportar informes: serializan los mismos datos que ya están en pantalla, no "
          "generan cifras nuevas.")

# --- 16. Herramientas de IA y frontend ---
slide_tabla("Herramientas — IA y frontend",
    ["Herramienta", "Capa", "Para qué sirve exactamente en la aplicación"],
    [
        ["OpenAI SDK", "IA", "Cliente para hablar con el modelo. Es el ÚNICO componente de pago, y es opcional."],
        ["GPT-4o-mini", "IA", "El modelo. Interpreta la pregunta y REDACTA la respuesta. Temperatura 0. Nunca genera cifras."],
        ["function calling", "IA", "El mecanismo por el que el modelo PIDE los datos a nuestras herramientas en vez de inventarlos."],
        ["HTML + JS vanilla", "Frontend", "La interfaz (index.html). Sin framework: una SPA ligera con cinco secciones."],
        ["marked", "Frontend", "Convierte a HTML el Markdown con el que responde el asistente (tablas, negritas, listas)."],
        ["DOMPurify", "Frontend", "Sanea ese HTML antes de pintarlo: evita la inyección de código en el navegador (XSS)."],
        ["localStorage", "Frontend", "Guarda el historial de la conversación en el navegador; se restaura al recargar."],
    ],
    col_ratios=[2.3, 1.3, 8.5], fsize=12.5,
    notas="En la capa de IA lo esencial es el 'function calling': es el mecanismo que permite que el modelo, "
          "cuando necesita un número, lo PIDA a nuestras herramientas en lugar de sacarlo de su memoria. "
          "Ahí está técnicamente la garantía anti-alucinación. En el frontend, DOMPurify merece una mención: "
          "es la protección contra inyección de código en el navegador.")

# --- 17. Módulos propios del código ---
slide_tabla("Los módulos propios del proyecto",
    ["Fichero", "Responsabilidad"],
    [
        ["api.py", "El núcleo: endpoints, ROUTER DETERMINISTA y orquestación de la respuesta."],
        ["fuente_oficial.py", "Lee la ontología y devuelve el valor CON SU CITA. La única puerta a las cifras."],
        ["conversor_unidades.py", "Conversión de unidades y factores ISO 13443 (tabla A.1) para comparar de forma homogénea."],
        ["condiciones_referencia.py", "Gestión de las condiciones de referencia (temperatura y presión) de cada país."],
        ["motor_determinista.py", "Lógica de comparación y de evaluación de cumplimiento, sin IA."],
        ["agente_pdf.py", "Indexación de los PDF y búsqueda documental (RAG) sobre el índice SQLite."],
        ["llm_interface.py", "La frontera con el LLM: define las herramientas que puede invocar y sus salvaguardas."],
        ["busqueda_semantica.py", "Capa de búsqueda semántica, PREPARADA y opcional (desactivada por defecto)."],
    ],
    intro="Código propio: cada fichero, una responsabilidad.",
    col_ratios=[3.0, 9.1], fsize=12.5,
    notas="Este es el código propio. La pieza que hay que retener es fuente_oficial.py: es la ÚNICA puerta a "
          "las cifras. Todo —el chat, la comparativa, la matriz, el análisis de gas— pasa por ahí. Si alguien "
          "quiere auditar de dónde sale un número, ese es el sitio.")

# --- 18. Endpoints ---
slide_tabla("Los servicios que expone la aplicación (endpoints)",
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
    col_ratios=[3.0, 9.1], fsize=12.5,
    notas="Ocho servicios. Merece la pena destacar dos: /api/analizar-gas, que valida un gas real país a país "
          "y marca la zona de alerta (cumple, pero a menos del 10 % del límite); y la detección de "
          "interconexiones dentro de /api/chat, que calcula qué gas puede atravesar una cadena de países "
          "e identifica el cuello de botella regulatorio.")

# --- 19. Motor determinista y normalización ---
slide_contenido("El motor determinista y la normalización (ISO 13443)",
    intro="Determinista = ante la misma consulta, siempre la misma respuesta, por código, sin azar ni IA.",
    bullets=[
        "El motor resuelve SIN IA siete tipos de intención: valor de un límite · cumplimiento de un valor medido · norma de origen · intercambiabilidad · restrictividad frente a España · comparación directa · conversión de condiciones.",
        "Problema: cada país usa unidades y condiciones distintas (kWh/m3 o MJ/m3; referidos a 0, 15 o 25 °C). Compararlos en bruto sería metodológicamente incorrecto.",
        "Solución: todos los valores se llevan a la BASE ESPAÑOLA (0/0) con los factores literales de la Tabla A.1 de la norma ISO 13443.",
        ("25/0 → 0/0 = 1,0026   ·   15/15 → 0/0 = 1,0570 (PCS) / 1,0569 (Wobbe)   ·   0/0 = identidad", True),
        "Esos factores NO se estiman: se toman de la norma. Los valores derivados se muestran con 2 decimales, sin falsa precisión.",
    ],
    bsize=15,
    notas="Un punto clave para la credibilidad es la comparabilidad. No basta con tener los números: hay que "
          "poder compararlos. Por eso llevamos todo a la base española aplicando los factores de la ISO 13443, "
          "que no estimamos, sino que tomamos literalmente de la norma. España es siempre la referencia.")

# --- 20. IA y salvaguardas ---
slide_contenido("La IA y sus salvaguardas",
    intro="Cuando una consulta sí llega al modelo, opera atada en corto.",
    bullets=[
        "PUEDE: interpretar la pregunta, detectar la intención, reformular y REDACTAR la respuesta.",
        "NO PUEDE: generar límites, inventar valores, deducir conversiones ni inferir comparabilidad.",
        "Para cualquier número invoca una herramienta: consultar · evaluar_cumplimiento · convertir_unidades · convertir_condiciones_iso13443 · buscar_pdfs.",
        "El SYSTEM_PROMPT le prohíbe inventar cifras, le obliga a citar y le acota el ámbito a la calidad del gas.",
        "Temperatura 0 (máxima previsibilidad) y hasta 5 iteraciones de llamadas a herramientas.",
        "Tolerancia a fallos: si OpenAI no está disponible, conmuta al motor determinista. El chat NUNCA devuelve error.",
    ],
    bsize=15,
    notas="Aquí conviene ser muy claro: el modelo no es la fuente del dato, es la capa de lenguaje. Si necesita "
          "un número, lo pide. Y si el servicio no está disponible —sin clave, sin red o por límite de uso—, el "
          "sistema conmuta solo a modo determinista. Es decir: la IA es una comodidad, no una dependencia.")

# --- 21. RAG ---
slide_contenido("La recuperación documental (RAG)",
    intro="Para las consultas de texto abierto, la respuesta se fundamenta en los documentos oficiales.",
    bullets=[
        "INDEXACIÓN: pdfplumber extrae el texto de los PDF y lo trocea en fragmentos CON SOLAPE mediante una ventana deslizante sobre el documento completo (no por página).",
        ("Así, una respuesta partida entre dos páginas queda entera dentro de un mismo fragmento y sigue siendo recuperable.", True),
        ("La indexación es incremental: solo se reprocesa lo nuevo o modificado, por lo que el arranque es casi inmediato.", True),
        "RECUPERACIÓN: buscar_pdfs() hace una búsqueda LÉXICA (SQLite LIKE) y devuelve los fragmentos con su archivo, página y extracto.",
        "Es léxica, NO vectorial. Decisión consciente: es plenamente reproducible y no depende de servicios externos.",
        "La capa semántica multilingüe está PREPARADA y justificada por el estudio de terminología (índice de variación 27,4 en gas natural), pero desactivada por defecto.",
    ],
    bsize=14,
    notas="Somos transparentes: nuestro RAG es léxico, no semántico. No es una carencia, es una decisión: es "
          "reproducible y no depende de terceros. Y antes de decidirlo lo MEDIMOS, con el estudio de "
          "terminología. La capa semántica queda preparada y activable si algún día compensa. Primero medir, "
          "luego decidir.")

# --- 22. Ampliación: biometano e hidrógeno ---
slide_tabla("Ampliación: biometano e hidrógeno",
    ["Tipo de gas", "Sección de la ontología", "Jurisdicciones", "Parámetros"],
    [
        ["Gas natural", "parametros", f"{N_JUR} (España … UE)", str(N_PAR)],
        ["Biometano", "parametros_biometano", "4 · España · Portugal · Francia · UE", str(len(PB))],
        ["Hidrógeno", "parametros_hidrogeno", "RED (CEN · GIE/UE · ES · FR · PT) + producto (ISO 14687)", str(len(PH))],
    ],
    intro="Añadidos como CAPA ADITIVA: se introduce la dimensión 'tipo_gas', con gas_natural por defecto. El gas natural queda intacto.",
    col_ratios=[2.0, 3.3, 5.3, 1.5], fsize=13,
    notas="La ampliación se hizo sin tocar nada de lo anterior: el gas natural sigue funcionando exactamente "
          "igual, y las pruebas automáticas lo confirman. Sobre el hidrógeno hay que subrayar una distinción: "
          "la calidad del H2 PARA LA RED (el gasoducto, lo que compete a Enagás: CEN/TS 17977 y recomendación "
          "GIE) es distinta de la del H2 como combustible de VEHÍCULO (ISO 14687). La herramienta las mantiene "
          "separadas. Y hoy solo Portugal fija una pureza vinculante del 98 %.")

# --- 23. Garantías y cierre ---
s = _slide()
_box(s, 0, 0, W, H, fill=AZUL)
_box(s, 0, Inches(1.35), W, Pt(4), fill=CYAN)
_text(s, Inches(0.9), Inches(0.45), Inches(11.5), Inches(0.8),
      [("Las garantías del sistema", 30, BLANCO, True, False, 0)])
gar = [
    ("Cero cifras inventadas", "Los valores proceden de código y datos verificados, nunca del modelo."),
    ("Trazabilidad completa", "Cada valor cita norma, artículo, página y enlace."),
    ("Transparencia", "Lo que la norma no fija se declara; no se completa."),
    ("Reproducibilidad", "Con el mismo código y datos, el resultado es idéntico en cualquier entorno."),
    ("Auditabilidad", "La base de conocimiento es consultable: se puede verificar el origen de cada valor."),
]
y = 1.95
for t, d in gar:
    _box(s, Inches(0.9), Inches(y), Pt(6), Inches(0.72), fill=VERDE)
    _text(s, Inches(1.2), Inches(y - 0.04), Inches(11.4), Inches(0.8), [
        (t + " — ", 17, CYAN, True, False, 0),
    ], space=0)
    _text(s, Inches(1.2), Inches(y + 0.26), Inches(11.4), Inches(0.5), [
        (d, 14, RGBColor(0xC9, 0xD6, 0xE0), False, False, 0),
    ], space=0)
    y += 0.92
_text(s, Inches(0.9), Inches(6.7), Inches(11.5), Inches(0.6),
      [("La IA redacta el texto. Los números salen siempre de la normativa oficial.", 17, BLANCO, True, False, 0)])
_notes(s, "En síntesis: hemos construido una herramienta que compara la calidad regulatoria del gas natural, el "
          "biometano y el hidrógeno entre jurisdicciones, con trazabilidad total y sin cifras inventadas. Las "
          "cifras salen siempre de normativa oficial verificada; la IA solo redacta el texto. Muchas gracias; "
          "quedo a vuestra disposición para las preguntas.")

prs.save(PPTX)
print("PPTX generado:", os.path.relpath(PPTX, RAIZ),
      f"({os.path.getsize(PPTX)//1024} KB, {len(prs.slides.__iter__.__self__._sldIdLst)} diapositivas)")
