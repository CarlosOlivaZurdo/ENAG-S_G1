"""Genera el diagrama de bloques de la arquitectura (PNG + SVG), estilo limpio Enagás.

Una sola definicion de layout -> dos renderizadores (PIL para PNG, texto para SVG),
para que ambas salidas sean identicas. Cajas pastel sin barra de cabecera: el titulo
de cada bloque va como primera linea en color, y las flechas llevan su etiqueta.

Cotejado con el codigo (api.py, llm_interface.py, fuente_oficial.py, agente_pdf.py):
- Router determinista real: _validate_measurement_gate() en api.py.
- Motor determinista = fuente_oficial.py + conversor_unidades.py + condiciones_referencia.py
  (motor_determinista.py se elimino; su logica quedo en esos tres).
- Tools reales del LLM: consultar_norma, evaluar_cumplimiento, convertir_unidades,
  convertir_condiciones_referencia, buscar_pdfs.
- RAG: indice lexico SQLite LIKE (no vectorial).
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

PNG = os.path.join("docs", "Arquitectura_Esquema_Cajas.png")
SVG = os.path.join("docs", "Arquitectura_Esquema_Cajas.svg")

W, H = 1240, 930

# --- Paleta ---
AZUL = "#013a57"
NAVY = "#0a2c40"
GRIS = "#5a6b78"
GRIST = "#8a97a3"
FLECHA = "#5a6672"
# fills pastel / bordes / titulos por bloque
C_AZUL = ("#e8f1fb", "#2b6cb0", "#013a57")   # navegador
C_GRIS = ("#eef1f4", "#93a1ad", "#1b2a38")   # backend / documentos
C_VERDE = ("#e7f4e4", "#5a9e2f", "#3e6b22")  # determinista / ontologia
C_NARAN = ("#fdf0e0", "#d98326", "#a5610e")  # LLM
C_ROJO = ("#fbeceb", "#c0563f", "#9b3a28")   # RAG

FONTS = {
    "h": ("arialbd.ttf", 17),    # titulo de bloque
    "b": ("arial.ttf", 13),      # cuerpo
    "bb": ("arialbd.ttf", 13),
    "s": ("arial.ttf", 12),      # subtitulo / detalle
    "mono": ("consola.ttf", 12),
    "lab": ("arial.ttf", 12),    # etiquetas de flecha
}


def _font(name, size):
    p = os.path.join("C:\\Windows\\Fonts", name)
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


# ------------------------------------------------------------------ LAYOUT
# Cada bloque: x,y,w,h, (fill,stroke,titlecol), lineas=[(texto, fontkey, color)]
# La 1a linea se pinta con el color del titulo; el bloque se centra verticalmente.
BOXES = [
    dict(x=120, y=60, w=1000, h=92, c=C_AZUL, lines=[
        ("1 · Navegador — index.html   (SPA en JavaScript puro)", "h", None),
        ("Consulta libre (chat)  ·  Comparativa GN / biometano / H2  ·  Analizar gas", "s", "#2b6cb0"),
    ]),
    dict(x=120, y=210, w=1000, h=132, c=C_GRIS, lines=[
        ("2 · Backend — api.py   (FastAPI + uvicorn)", "h", None),
        ("/api/status · /api/chat · /api/parametros · /api/comparar · /api/matriz · /api/analizar-gas · /api/exportar-matriz", "s", GRIS),
        ("ROUTER DETERMINISTA  ·  _validate_measurement_gate()", "bb", AZUL),
        ("cumplimiento · límite · fuente · intercambiabilidad · interconexión · comparación · condiciones", "s", GRIST),
    ]),
    dict(x=120, y=430, w=440, h=150, c=C_VERDE, lines=[
        ("3 · Motor determinista", "h", None),
        ("fuente_oficial.py", "b", NAVY),
        ("conversor_unidades.py   (ISO 13443 · Tabla A.1)", "b", NAVY),
        ("condiciones_referencia.py", "b", NAVY),
    ]),
    dict(x=680, y=430, w=440, h=150, c=C_NARAN, lines=[
        ("4 · Capa LLM — OpenAI gpt-4o-mini", "h", None),
        ("function-calling · temperature 0 · no inventa cifras", "s", NAVY),
        ("tools: consultar_norma · evaluar_cumplimiento", "b", NAVY),
        ("convertir_unidades / condiciones · buscar_pdfs", "b", NAVY),
    ]),
    dict(x=120, y=650, w=440, h=118, c=C_VERDE, lines=[
        ("5 · Ontología (YAML) — fuente de verdad", "h", None),
        ("ontologia_enagas.yaml   ·   tipo_gas", "bb", NAVY),
        ("cada cifra con su unidad, condiciones, cita y estado", "s", GRIS),
    ]),
    dict(x=680, y=650, w=440, h=118, c=C_ROJO, lines=[
        ("6 · RAG — agente_pdf.py + SQLite", "h", None),
        ("índice LÉXICO   (SQLite LIKE · no vectorial)", "b", NAVY),
        ("data/pdf_database.sqlite3", "s", GRIS),
    ]),
    dict(x=120, y=812, w=1000, h=72, c=C_GRIS, lines=[
        ("7 · Documentos oficiales — data/raw/*.pdf", "h", None),
        ("BOE · ERSE · GRTgaz · Snam · Fluxys · EN 16726 · …", "s", GRIS),
    ]),
]

# Flechas: x1,y1,x2,y2, etiqueta, dx, dy, anchor(l/r/c + m/b)
ARROWS = [
    (620, 152, 620, 208, "HTTP / JSON  (sin caché)", 12, -8, "lm"),
    (340, 342, 340, 428, "modo «determinista»", -10, 0, "rm"),
    (900, 342, 900, 428, "None  →  modo «ia»", 12, 0, "lm"),
    (680, 505, 562, 505, "function-calling", 0, -12, "cb"),
    (340, 580, 340, 648, "lee", 10, 0, "lm"),
    (900, 580, 900, 648, "buscar_pdfs", 10, 0, "lm"),
    (340, 812, 340, 770, "extracción verificada", 10, 0, "lm"),
    (900, 812, 900, 770, "indexa (pdfplumber)", 10, 0, "lm"),
]

FOOT = ("Las herramientas del LLM leen la ONTOLOGÍA verificada (extraída de los PDF oficiales); "
        "el LLM nunca genera cifras. Si la IA no está disponible, todo se resuelve en modo determinista.")


# ------------------------------------------------------------------ PIL (PNG)
def render_png(scale=2):
    img = Image.new("RGB", (W * scale, H * scale), "#ffffff")
    d = ImageDraw.Draw(img)
    fc = {k: _font(v[0], v[1] * scale) for k, v in FONTS.items()}

    def S(v):
        return int(v * scale)

    def line_h(fk):
        b = d.textbbox((0, 0), "Ag", font=fc[fk])
        return b[3] - b[1]

    for bx in BOXES:
        x, y, w, h = S(bx["x"]), S(bx["y"]), S(bx["w"]), S(bx["h"])
        fill, stroke, tcol = bx["c"]
        d.rounded_rectangle([x, y, x + w, y + h], radius=S(12), fill=fill,
                            outline=stroke, width=max(2, scale))
        gap = S(7)
        total = sum(line_h(fk) for _, fk, _ in bx["lines"]) + gap * (len(bx["lines"]) - 1)
        cy = y + (h - total) // 2
        for i, (txt, fk, col) in enumerate(bx["lines"]):
            color = tcol if i == 0 else (col or NAVY)
            tb = d.textbbox((0, 0), txt, font=fc[fk])
            tw = tb[2] - tb[0]
            d.text((x + (w - tw) / 2, cy), txt, font=fc[fk], fill=color)
            cy += line_h(fk) + gap

    for (x1, y1, x2, y2, label, ldx, ldy, anc) in ARROWS:
        X1, Y1, X2, Y2 = S(x1), S(y1), S(x2), S(y2)
        d.line([X1, Y1, X2, Y2], fill=FLECHA, width=max(2, scale * 2))
        ang = math.atan2(Y2 - Y1, X2 - X1)
        ah = S(10)
        p1 = (X2 - ah * math.cos(ang - 0.5), Y2 - ah * math.sin(ang - 0.5))
        p2 = (X2 - ah * math.cos(ang + 0.5), Y2 - ah * math.sin(ang + 0.5))
        d.polygon([(X2, Y2), p1, p2], fill=FLECHA)
        if label:
            lf = fc["lab"]
            lb = d.textbbox((0, 0), label, font=lf)
            lw, lh = lb[2] - lb[0], lb[3] - lb[1]
            mx, my = (X1 + X2) / 2 + S(ldx), (Y1 + Y2) / 2 + S(ldy)
            if "r" in anc:
                mx -= lw
            if "c" in anc:
                mx -= lw / 2
            if "b" in anc:
                my -= lh
            if "m" in anc:
                my -= lh / 2
            d.rectangle([mx - S(4), my - S(3), mx + lw + S(4), my + lh + S(4)], fill="#ffffff")
            d.text((mx, my), label, font=lf, fill=FLECHA)

    d.text((S(120), S(H - 24)), FOOT, font=fc["s"], fill=GRIST)
    img.save(PNG)
    return PNG


# ------------------------------------------------------------------ SVG
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg():
    fam = "Arial, Helvetica, sans-serif"
    px = {"h": 17, "b": 13, "bb": 13, "s": 12, "mono": 12, "lab": 12}
    bold = {"h", "bb"}
    lh = {k: v + 7 for k, v in px.items()}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{fam}">']
    s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    s.append('<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="7" refY="3" '
             f'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{FLECHA}"/></marker></defs>')

    def txt(x, y, t, fk, col, anchor="middle"):
        fw = ' font-weight="bold"' if fk in bold else ''
        return (f'<text x="{x}" y="{y}" font-size="{px[fk]}"{fw} fill="{col}" '
                f'text-anchor="{anchor}">{esc(t)}</text>')

    for bx in BOXES:
        x, y, w, h = bx["x"], bx["y"], bx["w"], bx["h"]
        fill, stroke, tcol = bx["c"]
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        total = sum(lh[fk] for _, fk, _ in bx["lines"])
        cy = y + (h - total) / 2 + px[bx["lines"][0][1]]
        for i, (t, fk, col) in enumerate(bx["lines"]):
            color = tcol if i == 0 else (col or NAVY)
            s.append(txt(x + w / 2, cy, t, fk, color, "middle"))
            cy += lh[fk]

    for (x1, y1, x2, y2, label, ldx, ldy, anc) in ARROWS:
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{FLECHA}" '
                 f'stroke-width="2.2" marker-end="url(#ah)"/>')
        if label:
            mx, my = (x1 + x2) / 2 + ldx, (y1 + y2) / 2 + ldy
            anchor = "start"
            if "r" in anc:
                anchor = "end"
            if "c" in anc:
                anchor = "middle"
            wapx = len(label) * 6 + 8
            rx = mx - (wapx if "r" in anc else (wapx / 2 if "c" in anc else 0)) - 4
            s.append(f'<rect x="{rx}" y="{my-11}" width="{wapx}" height="16" fill="#ffffff" opacity="0.95"/>')
            s.append(txt(mx, my, label, "lab", FLECHA, anchor))

    s.append(txt(120, H - 16, FOOT, "s", GRIST, "start"))
    s.append('</svg>')
    open(SVG, "w", encoding="utf-8").write("\n".join(s))
    return SVG


if __name__ == "__main__":
    p = render_png()
    v = render_svg()
    print("PNG:", p, os.path.getsize(p) // 1024, "KB")
    print("SVG:", v, os.path.getsize(v) // 1024, "KB")
