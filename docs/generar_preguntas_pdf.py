# -*- coding: utf-8 -*-
"""Genera el PDF de 'Preguntas y respuestas para la defensa del proyecto' (estilo Enagás).

    python docs/generar_preguntas_pdf.py

Lee docs/Preguntas_Respuestas_Defensa.md (revisado a mano) y produce el .pdf con el mismo
aspecto que Documentacion_Comparador_Gas.pdf. No genera contenido: solo maqueta el MD.
"""
import os
import markdown
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

AQUI = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(AQUI, "Preguntas_Respuestas_Defensa.md")
PDF = os.path.join(AQUI, "Preguntas_Respuestas_Defensa.pdf")

texto = open(MD, encoding="utf-8").read()

# xhtml2pdf/los TTF no renderizan subíndices, flechas ni emoji: se sustituyen por equivalentes.
_REEMP = {
    "₂": "2", "₃": "3", "₁": "1", "₀": "0", "·": "-", "→": "->", "×": "x",
    "↔": "<->", "≤": "<=", "≥": ">=", "≈": "~", "🔴": "[!]",
}
for a, b in _REEMP.items():
    texto = texto.replace(a, b)

cuerpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists"])


def _f(*n):
    for x in n:
        r = os.path.join("C:\\Windows\\Fonts", x)
        if os.path.exists(r):
            return r.replace("\\", "/")
    return None


arial = _f("arial.ttf"); arialbd = _f("arialbd.ttf"); mono = _f("consola.ttf", "cour.ttf")
fc, fm = "Helvetica", "Courier"
if arial:
    pdfmetrics.registerFont(TTFont("Cuerpo", arial))
    if arialbd:
        pdfmetrics.registerFont(TTFont("Cuerpo-Bold", arialbd))
        pdfmetrics.registerFontFamily("Cuerpo", normal="Cuerpo", bold="Cuerpo-Bold")
    fc = "Cuerpo"
if mono:
    pdfmetrics.registerFont(TTFont("Mono", mono)); fm = "Mono"

css = f"""
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
"""
html = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{cuerpo}</body></html>'
with open(PDF, "wb") as fh:
    res = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
if res.err:
    raise SystemExit(f"Error generando el PDF ({res.err}).")
print("PDF generado:", os.path.relpath(PDF, os.path.dirname(AQUI)), f"({os.path.getsize(PDF)//1024} KB)")
