"""Genera el PDF de la arquitectura a partir del Markdown.

    python docs/generar_pdf.py

Markdown -> HTML (lib `markdown`) -> PDF (xhtml2pdf/pisa). Usa fuentes de Windows
para que los símbolos (→, ≤, º, ², ·) y las tablas se vean bien.
"""
import os
import markdown
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

AQUI = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(AQUI, "Arquitectura_Comparador_Gas.md")
PDF = os.path.join(AQUI, "Arquitectura_Comparador_Gas.pdf")

# Subíndices/exóticos que algunas fuentes no traen -> equivalentes legibles.
_REEMPLAZOS = {"₂": "2", "₃": "3", "₁": "1", "₀": "0"}


def _fuente(*nombres):
    for n in nombres:
        ruta = os.path.join("C:\\Windows\\Fonts", n)
        if os.path.exists(ruta):
            return ruta.replace("\\", "/")
    return None


def main():
    texto = open(MD, encoding="utf-8").read()
    for a, b in _REEMPLAZOS.items():
        texto = texto.replace(a, b)

    cuerpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists"])

    # Registrar fuentes Unicode directamente en reportlab (más fiable que @font-face).
    arial = _fuente("arial.ttf")
    arialbd = _fuente("arialbd.ttf")
    mono = _fuente("consola.ttf", "cour.ttf")
    fam_cuerpo, fam_mono = "Helvetica", "Courier"
    if arial:
        pdfmetrics.registerFont(TTFont("Cuerpo", arial))
        if arialbd:
            pdfmetrics.registerFont(TTFont("Cuerpo-Bold", arialbd))
            pdfmetrics.registerFontFamily("Cuerpo", normal="Cuerpo", bold="Cuerpo-Bold")
        fam_cuerpo = "Cuerpo"
    if mono:
        pdfmetrics.registerFont(TTFont("Mono", mono))
        fam_mono = "Mono"

    css = f"""
    @page {{ size: A4; margin: 1.8cm 1.6cm; }}
    body {{ font-family: "{fam_cuerpo}"; font-size: 10.5px; color: #1b2a38; line-height: 1.45; }}
    h1 {{ color: #013a57; font-size: 19px; border-bottom: 2px solid #0099d6; padding-bottom: 4px; }}
    h2 {{ color: #013a57; font-size: 14.5px; margin-top: 16px; border-bottom: 1px solid #dde4ea; padding-bottom: 2px; }}
    h3 {{ color: #0077ab; font-size: 12px; margin-top: 11px; }}
    p, li {{ font-size: 10.5px; }}
    em {{ color: #5d7082; }}
    code {{ font-family: "{fam_mono}"; background: #eef2f6; font-size: 9px; }}
    pre {{ font-family: "{fam_mono}"; background: #f5f8fa; border: 1px solid #dde4ea;
          padding: 8px; font-size: 7.6px; line-height: 1.15; }}
    table {{ border-collapse: collapse; width: 100%; margin: 6px 0; }}
    th {{ background: #013a57; color: #fff; font-size: 9px; text-align: left; padding: 5px 7px; }}
    td {{ border: 1px solid #dde4ea; font-size: 9.5px; padding: 5px 7px; vertical-align: top; }}
    tr:nth-child(even) td {{ background: #f5f8fa; }}
    blockquote {{ background: #eef7fc; border-left: 3px solid #0099d6; margin: 6px 0;
                 padding: 5px 10px; color: #0a4e74; font-size: 9.8px; }}
    hr {{ border: 0; border-top: 1px solid #dde4ea; }}
    strong {{ color: #013a57; }}
    """

    html = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{cuerpo}</body></html>'

    with open(PDF, "wb") as fh:
        res = pisa.CreatePDF(html, dest=fh, encoding="utf-8")
    if res.err:
        raise SystemExit(f"Error generando el PDF ({res.err}).")
    print(f"PDF generado: {os.path.relpath(PDF, AQUI)}  ({os.path.getsize(PDF)//1024} KB)")


if __name__ == "__main__":
    main()
