"""Esquema de cajas de la ESTRUCTURA de la ontologia (ontologia_enagas.yaml).
Mismo estilo/motor que el diagrama de arquitectura. Salidas: PNG (2x) + SVG.
"""
import os, math
from PIL import Image, ImageDraw, ImageFont

PNG = os.path.join("docs", "Ontologia_Estructura.png")
SVG = os.path.join("docs", "Ontologia_Estructura.svg")
W, H = 1300, 1010

AZUL="#013a57"; CIAN="#0099d6"; VERDE="#5a9e2f"; NARANJA="#d98326"; GRIS="#9aa7b3"
TINTA="#1b2a38"; ROJO="#b03a2e"
AZUL_BG="#eaf6fc"; VERDE_BG="#eef7e7"; NARAN_BG="#fdf2e6"; GRIS_BG="#eef2f6"; FLECHA="#44515c"

FONTS = {
    "title":("arialbd.ttf",26), "header":("arialbd.ttf",15), "body":("arial.ttf",13),
    "bodybold":("arialbd.ttf",13), "small":("arial.ttf",11.5), "tiny":("arial.ttf",10.5),
    "mono":("consola.ttf",11), "monob":("consolab.ttf",11),
}

def _fontfile(name):
    p = os.path.join("C:\\Windows\\Fonts", name)
    return p if os.path.exists(p) else None

def _font(name, size):
    p = _fontfile(name)
    return ImageFont.truetype(p, int(size)) if p else ImageFont.load_default()

# --------------------------------------------------------------- LAYOUT
BOXES = [
    # raiz
    dict(x=450, y=64, w=400, h=46, fill=AZUL, stroke=AZUL, header=None,
         body=[("ontologia_enagas.yaml   ·   PyYAML (fuente de verdad)", "bodybold", "#ffffff")], align="center"),

    # 4 claves de primer nivel
    dict(x=64, y=158, w=262, h=64, fill=AZUL_BG, stroke=CIAN, header=None,
         body=[("1 · ontologia:", "bodybold", AZUL),
               ("fuentes_normativas[]  (las normas)", "small", TINTA)], align="center"),
    dict(x=360, y=158, w=262, h=64, fill=AZUL_BG, stroke=CIAN, header=None,
         body=[("2 · parametros:", "bodybold", AZUL),
               ("los 10 índices de calidad", "small", TINTA)], align="center"),
    dict(x=656, y=158, w=240, h=64, fill=AZUL_BG, stroke=CIAN, header=None,
         body=[("3 · unidades · flags", "bodybold", AZUL),
               ("catálogos auxiliares", "small", TINTA)], align="center"),
    dict(x=930, y=158, w=306, h=64, fill=NARAN_BG, stroke=NARANJA, header=None,
         body=[("4 · orquestador · motor_reglas · rag", "bodybold", "#9a5a12"),
               ("diseño / parte aspiracional", "small", TINTA)], align="center"),

    # --- rama A: una FUENTE NORMATIVA
    dict(x=64, y=300, w=336, h=236, fill="#f5f8fa", stroke=CIAN,
         header="FUENTE NORMATIVA  ·  fuentes_normativas[]",
         hfill=CIAN, hcolor="#ffffff",
         body=[("id:  p. ej. NORM_PL_GAZSYSTEM", "body", AZUL),
               ("nombre · organismo · publicacion", "small", TINTA),
               ("url:  cita en pantalla + descarga PDF", "small", TINTA),
               ("pdf:  copia local (data/raw/)", "small", TINTA),
               ("tabla_calidad · ambito", "small", TINTA),
               ("condiciones_referencia", "small", TINTA),
               ("← fuente ÚNICA: el campo url lo usan", "tiny", "#5d7082"),
               ("a la vez la cita y actualizar_fuentes.py", "tiny", "#5d7082")], align="left"),

    # --- rama B: parametro -> limites -> limite
    dict(x=470, y=300, w=380, h=96, fill=AZUL_BG, stroke=CIAN,
         header="parametros:  los 10 índices",
         hfill=AZUL, hcolor="#ffffff",
         body=[("Wobbe · PCS · densidad rel. · S total · H₂S+COS", "small", TINTA),
               ("RSH · O₂ · CO₂ · rocío H₂O · rocío HC", "small", TINTA),
               ("(c/u: nombre_completo · símbolo · grupo · unidad)", "tiny", "#5d7082")], align="center"),

    dict(x=470, y=426, w=380, h=66, fill=AZUL_BG, stroke=CIAN,
         header="limites:  un bloque por PAÍS  (×12)",
         hfill=AZUL, hcolor="#ffffff",
         body=[("ES · PT · FR · IT · DE · NL · BE · NOR · PL · DK · HU · UE", "bodybold", AZUL)], align="center"),

    dict(x=470, y=522, w=476, h=360, fill="#ffffff", stroke=AZUL,
         header="cada LÍMITE  (un parámetro en un país)",
         hfill=AZUL, hcolor="#ffffff",
         body=[("tipo_limite:  rango · maximo · minimo", "body", TINTA),
               ("valor    |    valor_min · valor_max", "body", TINTA),
               ("unidad:  kWh/m³ · MJ/m³ · mg/Nm³ · % mol · ppm · °C", "small", TINTA),
               ("condiciones_referencia:  combustión/volumen ·", "small", TINTA),
               ("                         presión · notación", "small", TINTA),
               ("expresion_original:  «texto LITERAL de la norma»", "small", TINTA),
               ("estado_verificacion:  VERIFICADO  /", "bodybold", VERDE),
               ("                      NO_VERIFICABLE_SIN_FUENTE", "bodybold", ROJO),
               ("fuente:  → id de la fuente normativa", "bodybold", CIAN),
               ("articulo:  artículo/sección + página", "small", TINTA),
               ("nota:  matices / «comentarios de la tabla»", "bodybold", NARANJA)], align="left"),

    # --- ejemplo real (monospace)
    dict(x=968, y=522, w=268, h=360, fill=GRIS_BG, stroke=GRIS,
         header="EJEMPLO real — PL · Wobbe",
         hfill="#6b7884", hcolor="#ffffff",
         body=[("PL:", "monob", AZUL),
               ("  tipo_limite: rango", "mono", TINTA),
               ("  valor_min: 45.0", "mono", TINTA),
               ("  valor_max: 56.9", "mono", TINTA),
               ("  unidad: MJ_per_nm3", "mono", TINTA),
               ("  condiciones_referencia:", "mono", TINTA),
               ("    {25/0 · 1.01325 bar}", "mono", TINTA),
               ("  expresion_original:", "mono", TINTA),
               ('    "Liczba Wobbego', "mono", "#5d7082"),
               ('     (grupa E):45,0-56,9"', "mono", "#5d7082"),
               ("  estado_verificacion:", "mono", TINTA),
               ("    VERIFICADO", "monob", VERDE),
               ("  fuente:", "mono", TINTA),
               ("    NORM_PL_GAZSYSTEM", "mono", CIAN),
               ('  nota: "Gas grupo E..."', "mono", NARANJA)], align="left"),
]

ARROWS = [
    dict(x1=600, y1=110, x2=195, y2=158, label="", anc="lm"),
    dict(x1=620, y1=110, x2=491, y2=158, label="", anc="lm"),
    dict(x1=660, y1=110, x2=776, y2=158, label="", anc="lm"),
    dict(x1=690, y1=110, x2=1060, y2=158, label="", anc="lm"),
    dict(x1=195, y1=222, x2=210, y2=300, label="", anc="lm"),
    dict(x1=560, y1=222, x2=620, y2=300, label="", anc="lm"),
    dict(x1=660, y1=396, x2=660, y2=426, label="", anc="lm"),
    dict(x1=660, y1=492, x2=680, y2=522, label="", anc="lm"),
    dict(x1=946, y1=590, x2=968, y2=590, label="instancia", ldx=0, ldy=-12, anc="cb"),
    # cross-link: el campo "fuente" del limite referencia un id de fuentes_normativas
    dict(x1=470, y1=738, x2=402, y2=430, label="fuente → id", ldx=-2, ldy=0, anc="rm", dashed=True),
]

FOOT1 = "VERIFICADO = consta en fuente oficial.   NO_VERIFICABLE_SIN_FUENTE = no se inventa (se deja en blanco)."
FOOT2 = "El motor determinista LEE de aquí. Cada límite es trazable a su fuente: documento · artículo · página · URL."

# --------------------------------------------------------------- helpers PIL
def _dashed(d, x1, y1, x2, y2, color, w, dash=8, gap=6):
    L = math.hypot(x2-x1, y2-y1)
    if L == 0: return
    dx, dy = (x2-x1)/L, (y2-y1)/L
    pos = 0
    while pos < L:
        a = pos; b = min(pos+dash, L)
        d.line([x1+dx*a, y1+dy*a, x1+dx*b, y1+dy*b], fill=color, width=w)
        pos += dash+gap

def _arrowhead(d, x1, y1, x2, y2, color, ah):
    ang = math.atan2(y2-y1, x2-x1)
    p1 = (x2-ah*math.cos(ang-0.5), y2-ah*math.sin(ang-0.5))
    p2 = (x2-ah*math.cos(ang+0.5), y2-ah*math.sin(ang+0.5))
    d.polygon([(x2, y2), p1, p2], fill=color)

def render_png(scale=2):
    img = Image.new("RGB", (W*scale, H*scale), "#ffffff")
    d = ImageDraw.Draw(img)
    fc = {k: _font(v[0], v[1]*scale) for k, v in FONTS.items()}
    S = lambda v: v*scale

    title = "Estructura de la Ontología — ontologia_enagas.yaml"
    tb = d.textbbox((0, 0), title, font=fc["title"])
    d.text(((W*scale-(tb[2]-tb[0]))/2, S(22)), title, font=fc["title"], fill=AZUL)

    for b in BOXES:
        x, y, w, h = S(b["x"]), S(b["y"]), S(b["w"]), S(b["h"])
        d.rounded_rectangle([x, y, x+w, y+h], radius=S(9), fill=b["fill"],
                            outline=b["stroke"], width=max(1, scale))
        cy = y + S(8)
        if b.get("header"):
            hh = S(28)
            d.rounded_rectangle([x, y, x+w, y+hh], radius=S(9), fill=b["hfill"])
            d.rectangle([x, y+S(14), x+w, y+hh], fill=b["hfill"])
            hb = d.textbbox((0, 0), b["header"], font=fc["header"])
            d.text((x+(w-(hb[2]-hb[0]))/2, y+(hh-(hb[3]-hb[1]))/2-S(2)), b["header"], font=fc["header"], fill=b["hcolor"])
            cy = y + hh + S(7)
        for (txt, fk, col) in b["body"]:
            fb = d.textbbox((0, 0), txt, font=fc[fk])
            tx = x+(w-(fb[2]-fb[0]))/2 if b["align"] == "center" else x+S(14)
            d.text((tx, cy), txt, font=fc[fk], fill=col)
            cy += (fb[3]-fb[1]) + S(7)

    for a in ARROWS:
        X1, Y1, X2, Y2 = S(a["x1"]), S(a["y1"]), S(a["x2"]), S(a["y2"])
        wln = max(2, scale*2)
        if a.get("dashed"):
            _dashed(d, X1, Y1, X2, Y2, FLECHA, wln, dash=S(8), gap=S(5))
        else:
            d.line([X1, Y1, X2, Y2], fill=FLECHA, width=wln)
        _arrowhead(d, X1, Y1, X2, Y2, FLECHA, S(9))
        if a.get("label"):
            lf = fc["tiny"]; lb = d.textbbox((0, 0), a["label"], font=lf)
            lw, lh = lb[2]-lb[0], lb[3]-lb[1]
            mx, my = (X1+X2)/2+S(a.get("ldx", 0)), (Y1+Y2)/2+S(a.get("ldy", 0))
            anc = a.get("anc", "lm")
            if "r" in anc: mx -= lw
            if "c" in anc: mx -= lw/2
            if "b" in anc: my -= lh
            if "m" in anc: my -= lh/2
            d.rectangle([mx-S(3), my-S(2), mx+lw+S(3), my+lh+S(3)], fill="#ffffff")
            d.text((mx, my), a["label"], font=lf, fill=FLECHA)

    d.text((S(64), S(916)), FOOT1, font=fc["small"], fill="#3a4754")
    d.text((S(64), S(940)), FOOT2, font=fc["small"], fill="#3a4754")
    img.save(PNG)
    return PNG

# --------------------------------------------------------------- SVG
def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_svg():
    px = {k: v[1] for k, v in FONTS.items()}
    bold = {"title", "header", "bodybold", "monob"}
    mono = {"mono", "monob"}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Arial, Helvetica, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
         f'<path d="M0,0 L7,3 L0,6 Z" fill="{FLECHA}"/></marker></defs>']
    s.append(f'<text x="{W/2}" y="44" text-anchor="middle" font-size="26" font-weight="bold" '
             f'fill="{AZUL}">{esc("Estructura de la Ontología — ontologia_enagas.yaml")}</text>')

    def txt(x, y, t, fk, col, anchor="middle"):
        fw = ' font-weight="bold"' if fk in bold else ''
        ff = ' font-family="Consolas, monospace"' if fk in mono else ''
        return (f'<text x="{x}" y="{y}" font-size="{px[fk]}"{fw}{ff} fill="{col}" '
                f'text-anchor="{anchor}">{esc(t)}</text>')

    for b in BOXES:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{b["fill"]}" '
                 f'stroke="{b["stroke"]}" stroke-width="1.5"/>')
        cy = y + 20
        if b.get("header"):
            s.append(f'<path d="M{x+9},{y} h{w-18} a9,9 0 0 1 9,9 v19 h{-w} v-19 a9,9 0 0 1 9,-9 z" fill="{b["hfill"]}"/>')
            s.append(txt(x+w/2, y+19, b["header"], "header", b["hcolor"]))
            cy = y + 28 + 16
        for (t, fk, col) in b["body"]:
            if b["align"] == "center":
                s.append(txt(x+w/2, cy, t, fk, col, "middle"))
            else:
                s.append(txt(x+14, cy, t, fk, col, "start"))
            cy += px[fk] + 7

    for a in ARROWS:
        dash = ' stroke-dasharray="7,5"' if a.get("dashed") else ''
        s.append(f'<line x1="{a["x1"]}" y1="{a["y1"]}" x2="{a["x2"]}" y2="{a["y2"]}" '
                 f'stroke="{FLECHA}" stroke-width="2.2"{dash} marker-end="url(#ah)"/>')
        if a.get("label"):
            mx, my = (a["x1"]+a["x2"])/2+a.get("ldx", 0), (a["y1"]+a["y2"])/2+a.get("ldy", 0)
            anc = a.get("anc", "lm"); anchor = "start"
            if "r" in anc: anchor = "end"
            if "c" in anc: anchor = "middle"
            s.append(f'<rect x="{mx-(len(a["label"])*5.5 if anchor=="end" else 3)}" y="{my-11}" '
                     f'width="{len(a["label"])*6+6}" height="15" fill="#ffffff" opacity="0.95"/>')
            s.append(txt(mx, my, a["label"], "tiny", FLECHA, anchor))

    s.append(txt(64, 920, FOOT1, "small", "#3a4754", "start"))
    s.append(txt(64, 944, FOOT2, "small", "#3a4754", "start"))
    s.append('</svg>')
    open(SVG, "w", encoding="utf-8").write("\n".join(s))
    return SVG

if __name__ == "__main__":
    print("PNG:", render_png(), os.path.getsize(PNG)//1024, "KB")
    print("SVG:", render_svg(), os.path.getsize(SVG)//1024, "KB")
