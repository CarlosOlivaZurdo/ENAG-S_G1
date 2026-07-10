# -*- coding: utf-8 -*-
"""Genera las DOS presentaciones en PDF del proyecto (estilo Enagás).

    python docs/generar_presentaciones.py

Salida:
    docs/Presentacion_7min.pdf   — versión ejecutiva (8 diapositivas ≈ 7 min)
    docs/Presentacion_15min.pdf  — versión completa (17 diapositivas ≈ 15 min)

Cubre TODO el proyecto: comparador de gas natural (21 jurisdicciones × 10 parámetros)
y la ampliación a biometano e hidrógeno (dominio de red). Diapositivas 16:9 dibujadas
con reportlab; tipografía Calibri incrustada (acentos, subíndices, ≤, µ, →).
Los guiones del ponente van en Guion_Presentacion_7min.md y _15min.md.
"""
import os
import re
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

AQUI = os.path.dirname(os.path.abspath(__file__))
WINF = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# --- Tipografía (Calibri incrustada) -----------------------------------------
F, FB = "Calibri", "Calibri-Bold"
pdfmetrics.registerFont(TTFont(F, os.path.join(WINF, "calibri.ttf")))
pdfmetrics.registerFont(TTFont(FB, os.path.join(WINF, "calibrib.ttf")))

# --- Paleta Enagás -----------------------------------------------------------
AZUL   = HexColor("#013A57")
CYAN   = HexColor("#0099D6")
VERDE  = HexColor("#6CB33E")
GRIS   = HexColor("#4A5B68")
TINTA  = HexColor("#1B2A38")
BLANCO = HexColor("#FFFFFF")
GRISCL = HexColor("#EEF2F6")
CLARO  = HexColor("#C9D6E0")
AMBAR  = HexColor("#E8A33D")

W, H = 960, 540  # 16:9 en puntos


# =========================== primitivas de texto =============================
def _tokens(text):
    """Divide el texto en palabras (word, negrita, espacio_delante) conservando
    el marcador **negrita** y los espacios reales (sin espacio antes de la puntuación)."""
    chars = []
    for part in re.split(r"(\*\*.*?\*\*)", text):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        for ch in (part[2:-2] if bold else part):
            chars.append((ch, bold))
    out, cur, cur_bold, sb, pending = [], "", False, False, False
    for ch, bold in chars:
        if ch == " ":
            if cur:
                out.append((cur, cur_bold, sb)); cur = ""
            pending = True
            continue
        if not cur:
            cur_bold, sb, pending = bold, pending, False
        cur += ch
    if cur:
        out.append((cur, cur_bold, sb))
    return out


def _layout(tokens, max_w, size, force_bold=False):
    """Reparte tokens en líneas que caben en max_w."""
    lines, cur, cur_w = [], [], 0.0
    sp = stringWidth(" ", F, size)
    for word, bold, spb in tokens:
        fnt = FB if (bold or force_bold) else F
        ww = stringWidth(word, fnt, size)
        gap = sp if (cur and spb) else 0
        add = ww + gap
        if cur and cur_w + add > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
            add = ww
        cur.append((word, bold, spb))
        cur_w += add
    if cur:
        lines.append(cur)
    return lines or [[]]


def _draw_line(c, x, y, line, size, color, force_bold=False):
    sp = stringWidth(" ", F, size)
    cx = x
    for i, (word, bold, spb) in enumerate(line):
        fnt = FB if (bold or force_bold) else F
        if i > 0 and spb:
            cx += sp
        c.setFont(fnt, size)
        c.setFillColor(color)
        c.drawString(cx, y, word)
        cx += stringWidth(word, fnt, size)


def _para(c, x, y, max_w, text, size, color, leading=None, force_bold=False):
    """Dibuja un párrafo con ajuste de línea; devuelve la y tras el párrafo."""
    leading = leading or size + 4
    for line in _layout(_tokens(text), max_w, size, force_bold):
        _draw_line(c, x, y, line, size, color, force_bold)
        y -= leading
    return y


# =========================== armazón de diapositiva ==========================
def _chrome(c, titulo, n, total):
    c.setFillColor(AZUL); c.rect(0, H - 74, W, 74, fill=1, stroke=0)
    c.setFillColor(CYAN); c.rect(0, H - 78, W, 4, fill=1, stroke=0)
    c.setFont(FB, 22); c.setFillColor(BLANCO)
    c.drawString(40, H - 50, titulo)
    c.setFont(F, 8.5); c.setFillColor(GRIS)
    c.drawString(40, 16, "Comparador Regulatorio de Calidad de Gas · Gas natural · Biometano · Hidrógeno — Enagás")
    c.drawRightString(W - 40, 16, f"{n} / {total}")


def _dot(c, x, y, color=CYAN, r=2.4):
    c.setFillColor(color)
    c.circle(x, y, r, fill=1, stroke=0)


def slide_bullets(c, titulo, n, total, intro=None, bullets=None, notas=None, size=13.5, gap=9):
    _chrome(c, titulo, n, total)
    y = H - 108
    if intro:
        y = _para(c, 45, y, W - 90, intro, 13, GRIS, leading=18)
        y -= 10
    for b in (bullets or []):
        sub = False
        if isinstance(b, tuple):
            b, sub = b
        bx = 45 + (26 if sub else 0)
        bw = (W - 90) - (26 if sub else 0) - 16
        s = size - 1.5 if sub else size
        col = GRIS if sub else TINTA
        lines = _layout(_tokens(b), bw, s)
        _dot(c, bx + 4, y + s * 0.30, GRIS if sub else CYAN, r=2.0 if sub else 2.6)
        for i, line in enumerate(lines):
            _draw_line(c, bx + 15, y, line, s, col)
            y -= s + 4
        y -= gap
    return y


def slide_table(c, titulo, n, total, headers, rows, intro=None, ratios=None,
                fsize=10.8, hsize=11.5, top=None):
    _chrome(c, titulo, n, total)
    y = H - 108
    if intro:
        y = _para(c, 45, y, W - 90, intro, 13, GRIS, leading=18)
        y -= 12
    x0, tw = 45, W - 90
    ncol = len(headers)
    ratios = ratios or [1] * ncol
    widths = [tw * r / sum(ratios) for r in ratios]
    pad = 7
    top = y if top is None else top

    hlines = [_layout(_tokens(h), widths[j] - 2 * pad, hsize, force_bold=True) for j, h in enumerate(headers)]
    hh = max(len(l) for l in hlines) * (hsize + 3) + 2 * pad
    c.setFillColor(AZUL); c.rect(x0, top - hh, tw, hh, fill=1, stroke=0)
    cx = x0
    for j, lines in enumerate(hlines):
        yb = top - pad - hsize
        for line in lines:
            _draw_line(c, cx + pad, yb, line, hsize, BLANCO, force_bold=True)
            yb -= hsize + 3
        cx += widths[j]
    y = top - hh
    for i, row in enumerate(rows):
        clines = [_layout(_tokens(str(cell)), widths[j] - 2 * pad, fsize) for j, cell in enumerate(row)]
        rh = max(len(l) for l in clines) * (fsize + 3) + 2 * pad
        c.setFillColor(GRISCL if i % 2 == 0 else BLANCO)
        c.rect(x0, y - rh, tw, rh, fill=1, stroke=0)
        cx = x0
        for j, lines in enumerate(clines):
            yb = y - pad - fsize
            for line in lines:
                _draw_line(c, cx + pad, yb, line, fsize, TINTA)
                yb -= fsize + 3
            cx += widths[j]
        y -= rh
    c.setStrokeColor(CLARO); c.setLineWidth(0.5)
    c.rect(x0, y, tw, top - y, fill=0, stroke=1)
    return y


def slide_portada(c, titulo1, titulo2, subtitulo, detalle, etiqueta):
    c.setFillColor(AZUL); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(CYAN); c.rect(0, 188, W, 5, fill=1, stroke=0)
    c.setFillColor(VERDE); c.rect(65, 305, 12, 150, fill=1, stroke=0)
    c.setFont(FB, 39); c.setFillColor(BLANCO)
    c.drawString(95, 405, titulo1)
    c.drawString(95, 355, titulo2)
    c.setFont(F, 19); c.setFillColor(CYAN)
    c.drawString(96, 150, subtitulo)
    c.setFont(F, 14); c.setFillColor(CLARO)
    c.drawString(96, 118, detalle)
    c.setFont(F, 12); c.setFillColor(HexColor("#9FB3C4"))
    c.drawString(96, 60, etiqueta)


def slide_cierre(c, lineas, pie):
    c.setFillColor(AZUL); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(VERDE); c.rect(65, 250, 12, 190, fill=1, stroke=0)
    c.setFont(FB, 20); c.setFillColor(CYAN)
    c.drawString(100, 400, "En síntesis")
    c.setFont(FB, 25); c.setFillColor(BLANCO)
    y = 355
    for ln in lineas:
        c.drawString(100, y, ln); y -= 40
    c.setFont(F, 14); c.setFillColor(CLARO)
    _para(c, 101, 165, W - 200, pie, 14, CLARO, leading=20)


def slide_cifras(c, n, total):
    _chrome(c, "El sistema en cifras", n, total)
    tarjetas = [("21", "jurisdicciones"), ("10", "parámetros de calidad"),
                ("210", "valores verificables"), ("0", "cifras inventadas")]
    x = 45
    cw, gapx = 208, 15
    for num, txt in tarjetas:
        c.setFillColor(GRISCL); c.rect(x, 250, cw, 170, fill=1, stroke=0)
        c.setFillColor(CYAN); c.rect(x, 414, cw, 6, fill=1, stroke=0)
        c.setFont(FB, 52); c.setFillColor(AZUL)
        c.drawCentredString(x + cw / 2, 320, num)
        c.setFont(F, 14); c.setFillColor(GRIS)
        c.drawCentredString(x + cw / 2, 275, txt)
        x += cw + gapx
    c.setFont(FB, 14.5); c.setFillColor(TINTA)
    c.drawCentredString(W / 2, 205,
                        "Gas natural: 176 valores VERIFICADOS y 34 NO VERIFICABLES (la norma no los fija) — nunca inventados.")
    c.setFont(F, 13); c.setFillColor(GRIS)
    c.drawCentredString(W / 2, 178,
                        "Ampliación a biometano e hidrógeno (dominio de red): España · Portugal · Francia · UE, con la misma disciplina.")


def slide_arquitectura(c, n, total):
    _chrome(c, "Arquitectura general", n, total)
    c.setFont(F, 13); c.setFillColor(GRIS)
    c.drawString(45, H - 108, "Cuatro componentes con responsabilidades bien delimitadas.")

    def comp(x, yb, w, h, tit, sub, fill, tcol=BLANCO):
        c.setFillColor(fill); c.rect(x, yb, w, h, fill=1, stroke=0)
        c.setFont(FB, 15); c.setFillColor(tcol)
        c.drawCentredString(x + w / 2, yb + h - 26, tit)
        c.setFont(F, 11); c.setFillColor(tcol)
        _para_center(c, x + 8, yb + h - 46, w - 16, sub, 11, tcol)

    def flecha(xc, y_top, y_bot):
        c.setStrokeColor(CYAN); c.setLineWidth(3)
        c.line(xc, y_top, xc, y_bot + 6)
        c.setFillColor(CYAN)
        p = c.beginPath()
        p.moveTo(xc - 6, y_bot + 8); p.lineTo(xc + 6, y_bot + 8); p.lineTo(xc, y_bot); p.close()
        c.drawPath(p, fill=1, stroke=0)

    comp(345, 350, 270, 58, "INTERFAZ WEB", "El usuario formula su consulta", CYAN)
    flecha(480, 350, 320)
    comp(300, 250, 360, 62, "SERVIDOR DE APLICACIÓN", "FastAPI · recibe, aplica la lógica y orquesta", AZUL)
    flecha(360, 250, 210); flecha(600, 250, 210)
    comp(80, 118, 300, 80, "BASE DE CONOCIMIENTO", "Ontología: valores verificados + sus fuentes", VERDE)
    comp(580, 118, 300, 80, "SERVICIO DE IA (externo)", "OpenAI: solo texto abierto · no genera cifras", GRIS)


def _para_center(c, x, y, w, text, size, color, leading=None):
    leading = leading or size + 3
    sp = stringWidth(" ", F, size)
    for line in _layout(_tokens(text), w, size):
        total_w = 0
        for i, (word, bold, spb) in enumerate(line):
            total_w += stringWidth(word, FB if bold else F, size)
            if i > 0 and spb:
                total_w += sp
        _draw_line(c, x + (w - total_w) / 2, y, line, size, color)
        y -= leading
    return y


def slide_estados(c, n, total):
    _chrome(c, "Estados de verificación", n, total)
    c.setFont(F, 13); c.setFillColor(GRIS)
    c.drawString(45, H - 108, "La garantía frente a la invención de datos: cada cifra está en uno de dos estados.")
    # tarjeta verde
    c.setFillColor(GRISCL); c.rect(50, 200, 415, 200, fill=1, stroke=0)
    c.setFillColor(VERDE); c.rect(50, 394, 415, 6, fill=1, stroke=0)
    c.setFont(FB, 21); c.setFillColor(AZUL); c.drawString(72, 355, "VERIFICADO")
    c.setFont(FB, 14); c.setFillColor(VERDE); c.drawString(72, 328, "176 valores (gas natural)")
    _para(c, 72, 300, 370, "Cifra contrastada literalmente (verbatim) contra su boletín oficial.", 13.5, TINTA, leading=19)
    # tarjeta cian
    c.setFillColor(GRISCL); c.rect(495, 200, 415, 200, fill=1, stroke=0)
    c.setFillColor(CYAN); c.rect(495, 394, 415, 6, fill=1, stroke=0)
    c.setFont(FB, 21); c.setFillColor(AZUL); c.drawString(517, 355, "NO VERIFICABLE")
    c.setFont(FB, 14); c.setFillColor(CYAN); c.drawString(517, 328, "34 valores")
    _para(c, 517, 300, 370, "La norma de esa jurisdicción no fija ese parámetro. No se estima: se marca y se explica.", 13.5, TINTA, leading=19)
    c.setFont(FB, 13.5); c.setFillColor(TINTA)
    c.drawCentredString(W / 2, 150, "No hay estado intermedio: el valor consta en la norma, o se declara que la norma no lo establece.")


# ================================ 7 MINUTOS ==================================
def build_7min(path):
    c = canvas.Canvas(path, pagesize=(W, H))
    T = 8

    slide_portada(c,
                  "Comparador Regulatorio de",
                  "Calidad de Gas",
                  "Gas natural · Biometano · Hidrógeno",
                  "Comparativa regulatoria trazable entre jurisdicciones — sin cifras inventadas",
                  "Presentación ejecutiva · 7 minutos")
    c.showPage()

    slide_bullets(c, "El problema", 2, T,
                  intro="Comparar la calidad regulatoria del gas entre países es hoy manual y arriesgado.",
                  bullets=[
                      "Cada país regula la calidad admisible con **su propia normativa**: poder calorífico, índice de Wobbe, azufre, CO₂, puntos de rocío…",
                      "Están **dispersas** en boletines oficiales distintos, en varios idiomas y con **unidades y condiciones de referencia diferentes**.",
                      "Compararlas a mano es **laborioso y propenso a error**.",
                      "Y ahora se suman **biometano e hidrógeno**, con marcos regulatorios aún en construcción.",
                  ])
    c.showPage()

    slide_cifras(c, 3, T)
    c.showPage()

    slide_arquitectura(c, 4, T)
    c.showPage()

    slide_bullets(c, "El principio: cero cifras inventadas", 5, T,
                  intro="El sistema combina dos mundos separados a propósito.",
                  bullets=[
                      "**Mundo determinista** (código + ontología): la **única** fuente de cifras, límites, conversiones y comparaciones. Nunca improvisa un número.",
                      "**Mundo conversacional** (IA): interpreta la pregunta y **redacta**, pero tiene **prohibido generar cifras**; las obtiene llamando a herramientas deterministas.",
                      "Regla: **determinista-primero, IA-como-respaldo**. Lo cuantitativo lo resuelve el código; solo el texto abierto pasa a la IA.",
                      ("Cada valor cita norma, artículo, página y enlace: trazabilidad completa.", True),
                  ])
    c.showPage()

    slide_bullets(c, "Qué puede hacer el sistema", 6, T,
                  intro="Cinco secciones, todas con la misma garantía de cero cifras inventadas:",
                  bullets=[
                      "**Consulta libre** (chat en lenguaje natural), con **análisis de interconexión en cadena**: para una ruta (p. ej. España-Francia-Alemania) halla el **cuello de botella** regulatorio y avisa de incompatibilidades.",
                      "**Comparativa**: parámetro a parámetro entre países y **matriz** (heatmap) países × parámetros, con **exportación a Excel/PDF**.",
                      "**Analizar gas**: se introduce la composición de un gas y responde, país a país, si **cumple / alerta / no cumple**, con la cita de cada límite.",
                      "**Comparativa de biometano** y **Comparativa de hidrógeno**: el mismo motor, para los dos gases nuevos.",
                  ], size=13)
    c.showPage()

    slide_table(c, "Ampliación: biometano e hidrógeno", 7, T,
                headers=["Gas", "Jurisdicciones", "Parámetros clave", "Fuentes normativas"],
                rows=[
                    ["**Biometano**", "España · Portugal · Francia · UE",
                     "CH₄ mínimo · CO₂ · siloxanos (+ impurezas)",
                     "EN 16723-1 · EN 16726 · Reg. (UE) 2024/1789 · Orden TED/181/2025 · GRTgaz · RQS (PT)"],
                    ["**Hidrógeno**", "Dominio de RED (TSO) + producto",
                     "Pureza H₂ · O₂ · trazas de compresores",
                     "CEN/TS 17977 · GIE (recom.) · RQS Anexo XII (PT, 98 % vinculante) · ISO 14687 (vehículo)"],
                ],
                intro="Se añade como capa aditiva: el gas natural queda intacto (mismo motor, misma disciplina de verificación).",
                ratios=[1.3, 2.4, 2.6, 4.2], fsize=10.5)
    c.setFont(F, 11.5); c.setFillColor(GRIS)
    c.drawString(45, 96, "Distinción clave: calidad de RED (gasoducto: CEN/TS 17977, GIE, ≥98 %) frente a producto de VEHÍCULO (ISO 14687, 99,97 %).")
    c.drawString(45, 76, "Un estudio de terminología (índice de variación) justifica una capa de búsqueda semántica, que se deja preparada y opt-in.")
    c.showPage()

    slide_cierre(c,
                 ["Compara la calidad regulatoria del gas natural,",
                  "biometano e hidrógeno con trazabilidad total",
                  "y sin cifras inventadas."],
                 "Las cifras salen de normativa oficial verificada. La IA solo redacta texto; nunca inventa un número.")
    c.showPage()
    c.save()
    return path


# ================================ 15 MINUTOS =================================
def build_15min(path):
    c = canvas.Canvas(path, pagesize=(W, H))
    T = 17

    slide_portada(c,
                  "Comparador Regulatorio de",
                  "Calidad de Gas",
                  "Gas natural · Biometano · Hidrógeno",
                  "Arquitectura, funcionamiento y garantías — comparativa entre jurisdicciones",
                  "Presentación completa · 15 minutos")
    c.showPage()

    slide_bullets(c, "Índice", 2, T,
                  intro="Recorrido de la presentación:",
                  bullets=[
                      "Contexto y objetivo · el sistema en cifras",
                      "Arquitectura general y funcionalidades",
                      "Las tres capas de datos y la ontología (base de conocimiento)",
                      "Estados de verificación · FastAPI frente a la API de OpenAI",
                      "El motor determinista y la normalización (ISO 13443)",
                      "La inteligencia artificial (con salvaguardas) y la recuperación documental (RAG)",
                      "Ampliación a biometano e hidrógeno · estudio de terminología",
                      "Metodología, verificación y garantías",
                  ], size=13.5, gap=7)
    c.showPage()

    slide_bullets(c, "Contexto y objetivo", 3, T,
                  intro="El problema y la propuesta de valor.",
                  bullets=[
                      "Cada país regula la calidad admisible del gas con **su propia normativa** (poder calorífico, Wobbe, azufre, CO₂, puntos de rocío…).",
                      "Está **dispersa**, en varios idiomas y con **unidades y condiciones de referencia distintas**; compararla a mano es costoso y arriesgado.",
                      "**Solución:** un asistente que compara esa calidad entre **21 jurisdicciones y 10 parámetros**, en lenguaje natural.",
                      "**Principio de diseño:** ausencia de cifras no verificadas; todo valor procede de normativa oficial, con su cita.",
                      "Ampliado a **biometano e hidrógeno**, manteniendo el gas natural intacto.",
                  ])
    c.showPage()

    slide_cifras(c, 4, T)
    c.showPage()

    slide_arquitectura(c, 5, T)
    c.showPage()

    slide_bullets(c, "Funcionalidades", 6, T,
                  intro="Cinco secciones, todas con la misma garantía de cero cifras inventadas:",
                  bullets=[
                      "**Consulta libre** (chat): límites, cumplimiento, fuentes y comparaciones en lenguaje natural. Incluye **interconexión en cadena**: para una ruta de varios países halla el **cuello de botella** regulatorio y avisa de incompatibilidades.",
                      "**Comparativa**: comparación puntual de un parámetro entre países y **matriz** (heatmap) países × parámetros, con **exportación a Excel/PDF** de las jurisdicciones elegidas.",
                      "**Analizar gas**: composición de un gas concreto → respuesta país a país (**cumple / alerta / no cumple**) con la cita de cada límite.",
                      "**Comparativa de biometano** y de **hidrógeno**: el mismo motor y la misma presentación, para los gases nuevos.",
                  ], size=12.5, gap=8)
    c.showPage()

    slide_table(c, "Las tres capas de datos", 7, T,
                headers=["Capa", "Contenido", "Función"],
                rows=[
                    ["**1. Documentos oficiales**", "Los PDF de las normas (BOE, ERSE, DVGW, Fluxys, National Grid, ERSE-RQS…)", "Fuente primaria y última de verdad"],
                    ["**2. Ontología**", "Fichero estructurado con las cifras extraídas de esos PDF, con su contexto", "Repositorio del que salen las respuestas"],
                    ["**3. Índice documental (RAG)**", "Índice del texto de los PDF, segmentado en fragmentos con solape", "Buscador interno para consultas abiertas"],
                ],
                intro="No hay una única base de datos gigante: la información se organiza en tres capas con funciones distintas.",
                ratios=[2.2, 4.3, 3.1])
    c.showPage()

    slide_bullets(c, "La base de conocimiento (ontología)", 8, T,
                  intro="El elemento central. De cada valor se registra su cifra y todo su contexto normativo:",
                  bullets=[
                      "El **valor** (o su rango) y la **unidad**.",
                      "Las **condiciones de referencia** (a qué temperatura y presión se mide).",
                      "El **texto literal** de la norma, tal como está redactado.",
                      "La **cita completa**: norma, artículo, página y enlace.",
                      "Una **nota** aclaratoria con los matices, y el **estado de verificación**.",
                      ("Se usa un fichero YAML (legible y auditable) en lugar de una base de datos relacional: a esta escala es más trazable y se versiona junto al código.", True),
                  ])
    c.showPage()

    slide_estados(c, 9, T)
    c.showPage()

    slide_table(c, "FastAPI y la API de OpenAI: son cosas distintas", 10, T,
                headers=["", "FastAPI", "API de OpenAI"],
                rows=[
                    ["**Naturaleza**", "Framework para construir NUESTRO servidor", "Servicio externo que consumimos"],
                    ["**Titularidad**", "Propia (es nuestro backend)", "De OpenAI (somos cliente)"],
                    ["**Coste**", "Sin coste (código abierto)", "De pago, por uso"],
                    ["**Papel**", "Núcleo de la aplicación", "Proveedor auxiliar, invocado de forma controlada"],
                ],
                intro="Ambos incluyen el término «API», pero son componentes de niveles distintos.",
                ratios=[1.5, 4.0, 4.0])
    c.showPage()

    slide_bullets(c, "El motor determinista", 11, T,
                  intro="Toda consulta pasa primero por un enrutado que decide cómo resolverla. «Determinista» = misma consulta, misma respuesta, por código, sin IA.",
                  bullets=[
                      "Consultas **cuantitativas** (un límite, un cumplimiento, una comparación, una conversión): las resuelve el **código leyendo la ontología**. Sin IA, sin posibilidad de generar un valor incorrecto.",
                      "Consultas de **texto abierto** («¿en qué consiste el índice de Wobbe?»): se derivan al servicio de IA.",
                      "Resuelve **sin IA** siete tipos de intención: valor de un límite, cumplimiento, fuente, intercambiabilidad, restrictividad frente a España, comparación directa y conversión de condiciones.",
                      ("En la práctica, la mayoría de consultas se resuelven sin recurrir a la IA.", True),
                  ])
    c.showPage()

    slide_bullets(c, "Normalización de condiciones (ISO 13443)", 12, T,
                  intro="Para comparar de forma rigurosa: cada país usa unidades y condiciones de referencia distintas.",
                  bullets=[
                      "Unos expresan en **kWh/m³**, otros en **MJ/m³** o kcal/m³; unos miden a **0 °C**, otros a **15** o a **25 °C**.",
                      "Comparar los valores en bruto sería incorrecto (como comparar millas con kilómetros).",
                      "Todos los valores se llevan a la **base española** con los **factores literales de la norma ISO 13443** (Tabla A.1), ya implementados y verificados.",
                      "**España** es siempre la base de referencia de la comparación.",
                      ("Los valores derivados se muestran con 2 decimales (sin falsa precisión); los originales, con su precisión de origen.", True),
                  ])
    c.showPage()

    slide_bullets(c, "La inteligencia artificial y sus salvaguardas", 13, T,
                  intro="Cuando una consulta se deriva al servicio de IA, este opera bajo restricciones estrictas:",
                  bullets=[
                      "Tiene **prohibido generar cifras**: si necesita un dato, lo pide a las herramientas internas, que lo obtienen de la ontología.",
                      "Debe **citar** los documentos oficiales, y su ámbito se limita a la calidad del gas.",
                      "Si el servicio de IA no está disponible, el sistema **conmuta automáticamente al modo determinista**: nunca se interrumpe.",
                      ("Modelo: OpenAI GPT-4o-mini, temperatura 0 (máxima previsibilidad), con llamadas a herramientas (function calling).", True),
                  ])
    c.showPage()

    slide_bullets(c, "Recuperación documental (RAG) y terminología", 14, T,
                  intro="Para el texto abierto, la respuesta se fundamenta en los documentos oficiales, no en el conocimiento general del modelo.",
                  bullets=[
                      "**Indexación:** se procesan los PDF, se extrae el texto y se trocea en **fragmentos con solape** (ventana continua que cruza el salto de página); indexación **incremental**.",
                      "**Recuperación:** búsqueda **léxica** (por términos) que devuelve los fragmentos pertinentes con archivo y página; reproducible, sin caja negra externa.",
                      "**Estudio de terminología:** se mide la variación de nombres entre normas (**índice de variación**: 27,4 en gas natural, 9,2 en biometano, 7,3 en hidrógeno; umbral 7,0).",
                      ("El estudio justifica una capa de búsqueda semántica (multilingüe), que se deja preparada y opt-in.", True),
                  ], size=13)
    c.showPage()

    slide_table(c, "Ampliación: biometano e hidrógeno", 15, T,
                headers=["Gas", "Jurisdicciones", "Parámetros clave", "Fuentes normativas"],
                rows=[
                    ["**Biometano**", "España · Portugal · Francia · UE",
                     "CH₄ mínimo · CO₂ · siloxanos (+ O₂, azufre, NH₃, aminas)",
                     "EN 16723-1 · EN 16726 · Reg. (UE) 2024/1789 · Orden TED/181/2025 · GRTgaz/GRDF · RQS Anexo XI"],
                    ["**Hidrógeno**", "Dominio de RED (TSO) + producto",
                     "Pureza H₂ · O₂ · trazas de compresores",
                     "CEN/TS 17977 · GIE (recomendación) · RQS Anexo XII (PT, 98 % vinculante) · ISO 14687 (vehículo)"],
                ],
                intro="Capa aditiva: el gas natural queda byte a byte intacto (mismo motor, misma disciplina). 14/14 pruebas en verde.",
                ratios=[1.2, 2.3, 2.9, 4.3], fsize=10.3)
    c.setFont(F, 11.5); c.setFillColor(GRIS)
    c.drawString(45, 92, "Distinción clave de dominio: calidad de RED (gasoducto: CEN/TS 17977, GIE, ≥98 %) frente a producto de VEHÍCULO (ISO 14687, 99,97 %).")
    c.drawString(45, 72, "Solo Portugal (RQS) fija hoy una pureza de H₂ vinculante (≥98 %); España y Francia regulan el blending; la UE lo recomienda vía GIE.")
    c.showPage()

    slide_bullets(c, "Metodología, verificación y garantías", 16, T,
                  intro="La fiabilidad es consecuencia del rigor del proceso de carga. Para cada jurisdicción:",
                  bullets=[
                      "Se identificó la **norma oficial vigente**, se **archivó el documento** localmente y se **transcribió cada cifra literalmente**.",
                      "Se **verificó una a una** contra el documento; lo que la norma **no fija, no se completa** (se marca «no verificable», con su justificación).",
                      "**Controles automáticos**: comprueban que las celdas se resuelven, que los enlaces funcionan y que no hay incoherencias.",
                      ("Garantías: cero cifras inventadas · trazabilidad completa · transparencia · reproducibilidad · auditabilidad.", True),
                  ])
    c.showPage()

    slide_cierre(c,
                 ["Compara la calidad regulatoria del gas natural,",
                  "biometano e hidrógeno entre jurisdicciones,",
                  "con trazabilidad total y sin cifras inventadas."],
                 "Las cifras salen de normativa oficial verificada. La IA solo redacta texto; nunca inventa un número. El gas natural permanece intacto tras la ampliación.")
    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    p7 = build_7min(os.path.join(AQUI, "Presentacion_7min.pdf"))
    p15 = build_15min(os.path.join(AQUI, "Presentacion_15min.pdf"))
    for p in (p7, p15):
        print(f"PDF generado: {os.path.relpath(p, os.path.dirname(AQUI))}  ({os.path.getsize(p)//1024} KB)")
