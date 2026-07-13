"""Genera el esquema de cajas de la arquitectura (PNG + SVG) con colores Enagas.

Una sola definicion de layout -> dos renderizadores (PIL para PNG, texto para SVG),
para que ambas salidas sean identicas.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
PNG = os.path.join("docs", "Arquitectura_Esquema_Cajas.png")
SVG = os.path.join("docs", "Arquitectura_Esquema_Cajas.svg")

W, H = 1240, 950

# --- Colores Enagas ---
AZUL   = "#013a57"   # azul corporativo profundo
CIAN   = "#0099d6"   # cian acento
VERDE  = "#5a9e2f"   # verde (fuente de verdad)
NARANJA= "#d98326"   # calido (lado no determinista / LLM)
GRIS   = "#9aa7b3"
TINTA  = "#1b2a38"
AZUL_BG  = "#eaf6fc"
VERDE_BG = "#eef7e7"
NARAN_BG = "#fdf2e6"
GRIS_BG  = "#eef2f6"
FLECHA   = "#44515c"

def _font(name, size):
    for f in (name,):
        p = os.path.join("C:\\Windows\\Fonts", f)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

FONTS = {
    "title":    ("arialbd.ttf", 27),
    "header":   ("arialbd.ttf", 15),
    "body":     ("arial.ttf",   13),
    "bodybold": ("arialbd.ttf", 13),
    "small":    ("arial.ttf",   11),
    "smallit":  ("ariali.ttf",  11),
}

# ------------------------------------------------------------------ LAYOUT
# Cada caja: x,y,w,h, fill, stroke, header(text), header_fill, header_color,
#            body=[(texto, fontkey, color)], align
BOXES = [
    dict(x=120, y=70, w=1000, h=118, fill=AZUL_BG, stroke=CIAN,
         header="1 · NAVEGADOR  —  index.html  (SPA en JavaScript puro · identidad Enagás)",
         hfill=AZUL, hcolor="#ffffff", body=[], align="center"),
    # sub-cajas del navegador (3 pestañas)
    dict(x=150, y=120, w=300, h=52, fill="#ffffff", stroke=CIAN, header=None,
         body=[("CONSULTA LIBRE  (chat)", "bodybold", AZUL)], align="center"),
    dict(x=470, y=120, w=300, h=52, fill="#ffffff", stroke=CIAN, header=None,
         body=[("COMPARATIVA  ·  GN · biometano · H2", "bodybold", AZUL)], align="center"),
    dict(x=790, y=120, w=300, h=52, fill="#ffffff", stroke=CIAN, header=None,
         body=[("ANALIZAR GAS", "bodybold", AZUL)], align="center"),

    dict(x=120, y=232, w=1000, h=172, fill="#f5f8fa", stroke=AZUL,
         header="2 · BACKEND  —  api.py  (FastAPI + uvicorn)",
         hfill=AZUL, hcolor="#ffffff",
         body=[("Endpoints:  /  ·  /api/status  ·  /api/chat  ·  /api/parametros  ·  /api/comparar  ·  /api/matriz  ·  /api/analizar-gas  ·  /api/exportar-matriz",
                "small", TINTA)], align="center"),
    # router dentro del backend
    dict(x=150, y=305, w=940, h=88, fill=AZUL, stroke=AZUL, header=None,
         body=[("ROUTER DETERMINISTA   ·   _validate_measurement_gate()", "bodybold", "#ffffff"),
               ("cumplimiento · límite · fuente · intercambiabilidad · interconexión/cadena · comparación · condiciones",
                "small", "#cfe8f6")], align="center"),

    dict(x=120, y=472, w=420, h=150, fill=AZUL_BG, stroke=CIAN,
         header="3 · MOTOR DETERMINISTA",
         hfill=CIAN, hcolor="#ffffff",
         body=[("fuente_oficial.py", "body", TINTA),
               ("conversor_unidades.py  (ISO 13443 · Tabla A.1)", "body", TINTA),
               ("condiciones_referencia.py", "body", TINTA)], align="center"),

    dict(x=700, y=472, w=420, h=150, fill=NARAN_BG, stroke=NARANJA,
         header="4 · CAPA LLM  —  OpenAI gpt-4o-mini",
         hfill=NARANJA, hcolor="#ffffff",
         body=[("function-calling · temperature 0 · no inventa cifras", "small", TINTA),
               ("tools:  consultar_excel*,  evaluar_cumplimiento,", "body", TINTA),
               ("convertir_unidades / condiciones,  buscar_pdfs", "body", TINTA)], align="center"),

    dict(x=120, y=668, w=420, h=108, fill=VERDE_BG, stroke=VERDE,
         header="5 · ONTOLOGÍA (YAML)  —  FUENTE DE VERDAD",
         hfill=VERDE, hcolor="#ffffff",
         body=[("ontologia_enagas.yaml   ·   tipo_gas", "bodybold", AZUL),
               ("gas natural 10×21 · biometano · hidrógeno + cita + estado", "small", TINTA)], align="center"),

    dict(x=700, y=668, w=420, h=108, fill=NARAN_BG, stroke=NARANJA,
         header="6 · RAG  —  agente_pdf.py + SQLite",
         hfill=NARANJA, hcolor="#ffffff",
         body=[("índice LÉXICO  (SQLite LIKE · no vectorial)", "body", TINTA),
               ("data/pdf_database.sqlite3", "small", TINTA)], align="center"),

    dict(x=120, y=820, w=1000, h=72, fill=GRIS_BG, stroke=GRIS,
         header="7 · DOCUMENTOS OFICIALES  —  data/raw/*.pdf",
         hfill="#6b7884", hcolor="#ffffff",
         body=[("Snam · DVGW · Fluxys · Gassled · GAZ-SYSTEM · EN 16726 · …", "small", TINTA)], align="center"),
]

# Flechas: x1,y1,x2,y2, label, label_dx, label_dy, label_anchor
ARROWS = [
    (620, 188, 620, 230, "HTTP / JSON  (sin caché)", 12, -10, "lm"),
    (330, 393, 330, 471, "modo «determinista»", -8, 0, "rm"),
    (910, 393, 910, 471, "None  →  modo «ia»", 10, 0, "lm"),
    (700, 545, 542, 545, "llama a las funciones", 0, -12, "cb"),
    (330, 622, 330, 667, "lee", 10, 0, "lm"),
    (910, 622, 910, 667, "buscar_pdfs", 10, 0, "lm"),
    (330, 820, 330, 777, "extracción a mano", 10, 0, "lm"),
    (910, 820, 910, 777, "indexa (pdfplumber)", 10, 0, "lm"),
]

FOOT = "* consultar_excel: nombre histórico; hoy lee la ONTOLOGÍA, no Excel."

# ------------------------------------------------------------------ PIL (PNG)
def render_png(scale=2):
    img = Image.new("RGB", (W*scale, H*scale), "#ffffff")
    d = ImageDraw.Draw(img)
    fcache = {k: _font(v[0], v[1]*scale) for k, v in FONTS.items()}

    def S(v): return v*scale

    # titulo
    title = "Arquitectura del Comparador Regulatorio de Calidad de Gas — Enagás"
    tb = d.textbbox((0, 0), title, font=fcache["title"])
    d.text(((W*scale-(tb[2]-tb[0]))/2, S(26)), title, font=fcache["title"], fill=AZUL)

    for b in BOXES:
        x, y, w, h = S(b["x"]), S(b["y"]), S(b["w"]), S(b["h"])
        d.rounded_rectangle([x, y, x+w, y+h], radius=S(10), fill=b["fill"],
                            outline=b["stroke"], width=max(1, scale))
        cy = y + S(8)
        if b["header"]:
            hh = S(30)
            d.rounded_rectangle([x, y, x+w, y+hh], radius=S(10), fill=b["hfill"])
            d.rectangle([x, y+S(15), x+w, y+hh], fill=b["hfill"])
            hb = d.textbbox((0, 0), b["header"], font=fcache["header"])
            d.text((x+(w-(hb[2]-hb[0]))/2, y+(hh-(hb[3]-hb[1]))/2-S(2)),
                   b["header"], font=fcache["header"], fill=b["hcolor"])
            cy = y + hh + S(9)
        for (txt, fk, col) in b["body"]:
            fb = d.textbbox((0, 0), txt, font=fcache[fk])
            tw = fb[2]-fb[0]
            tx = x+(w-tw)/2 if b["align"] == "center" else x+S(16)
            d.text((tx, cy), txt, font=fcache[fk], fill=col)
            cy += (fb[3]-fb[1]) + S(8)

    # flechas
    for (x1, y1, x2, y2, label, ldx, ldy, anc) in ARROWS:
        X1, Y1, X2, Y2 = S(x1), S(y1), S(x2), S(y2)
        d.line([X1, Y1, X2, Y2], fill=FLECHA, width=max(2, scale*2))
        import math
        ang = math.atan2(Y2-Y1, X2-X1)
        ah = S(9)
        p1 = (X2-ah*math.cos(ang-0.5), Y2-ah*math.sin(ang-0.5))
        p2 = (X2-ah*math.cos(ang+0.5), Y2-ah*math.sin(ang+0.5))
        d.polygon([(X2, Y2), p1, p2], fill=FLECHA)
        if label:
            lf = fcache["small"]
            lb = d.textbbox((0, 0), label, font=lf)
            lw, lh = lb[2]-lb[0], lb[3]-lb[1]
            mx, my = (X1+X2)/2 + S(ldx), (Y1+Y2)/2 + S(ldy)
            if "r" in anc: mx -= lw
            if "c" in anc: mx -= lw/2
            if "b" in anc: my -= lh
            if "m" in anc: my -= lh/2
            d.rectangle([mx-S(3), my-S(2), mx+lw+S(3), my+lh+S(3)], fill="#ffffff")
            d.text((mx, my), label, font=lf, fill=FLECHA)

    ff = fcache["small"]
    d.text((S(120), S(906)), FOOT, font=ff, fill="#6b7884")
    img.save(PNG)
    return PNG

# ------------------------------------------------------------------ SVG
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_svg():
    fam = "Arial, Helvetica, sans-serif"
    px = {"title": 27, "header": 15, "body": 13, "bodybold": 13, "small": 11, "smallit": 11}
    bold = {"title", "header", "bodybold"}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{fam}">']
    s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    s.append('<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" '
             'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="%s"/></marker></defs>' % FLECHA)

    title = "Arquitectura del Comparador Regulatorio de Calidad de Gas — Enagás"
    s.append(f'<text x="{W/2}" y="48" text-anchor="middle" font-size="27" '
             f'font-weight="bold" fill="{AZUL}">{esc(title)}</text>')

    def txt(x, y, t, fk, col, anchor="middle"):
        fw = ' font-weight="bold"' if fk in bold else ''
        return (f'<text x="{x}" y="{y}" font-size="{px[fk]}"{fw} fill="{col}" '
                f'text-anchor="{anchor}">{esc(t)}</text>')

    for b in BOXES:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
                 f'fill="{b["fill"]}" stroke="{b["stroke"]}" stroke-width="1.5"/>')
        cy = y + 22
        if b["header"]:
            s.append(f'<path d="M{x+10},{y} h{w-20} a10,10 0 0 1 10,10 v20 h{-w} v-20 '
                     f'a10,10 0 0 1 10,-10 z" fill="{b["hfill"]}"/>')
            s.append(txt(x+w/2, y+20, b["header"], "header", b["hcolor"]))
            cy = y + 30 + 19
        for (t, fk, col) in b["body"]:
            if b["align"] == "center":
                s.append(txt(x+w/2, cy, t, fk, col, "middle"))
            else:
                s.append(txt(x+16, cy, t, fk, col, "start"))
            cy += px[fk] + 9

    for (x1, y1, x2, y2, label, ldx, ldy, anc) in ARROWS:
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{FLECHA}" '
                 f'stroke-width="2.2" marker-end="url(#ah)"/>')
        if label:
            mx, my = (x1+x2)/2 + ldx, (y1+y2)/2 + ldy
            anchor = "start"
            if "r" in anc: anchor = "end"
            if "c" in anc: anchor = "middle"
            s.append(f'<rect x="{mx-3}" y="{my-11}" width="{len(label)*6+6}" height="15" '
                     f'fill="#ffffff" opacity="0.95"/>')
            s.append(txt(mx, my, label, "small", FLECHA, anchor))

    s.append(txt(120, 912, FOOT, "small", "#6b7884", "start"))
    s.append('</svg>')
    open(SVG, "w", encoding="utf-8").write("\n".join(s))
    return SVG

if __name__ == "__main__":
    p = render_png()
    v = render_svg()
    print("PNG:", p, os.path.getsize(p)//1024, "KB")
    print("SVG:", v, os.path.getsize(v)//1024, "KB")
