# -*- coding: utf-8 -*-
"""
Genera el documento Word con los valores VERIFICADOS de calidad del gas natural
para el proyecto ENAGÁS Reto 5 (revisión 2026-06).

Fuente de contenido: ENAG-S_G1/data/ontologia/ontologia_enagas.yaml
Salida: ENAG-S_G1/docs/Calidad_Gas_Valores_Verificados.docx

Uso:
    python -m pip install python-docx
    python ENAG-S_G1/docs/generar_docx.py
"""

import os

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# --------------------------------------------------------------------------- #
# Paleta de color y utilidades de estilo
# --------------------------------------------------------------------------- #
AZUL_ENAGAS = RGBColor(0x00, 0x3D, 0x6B)
AZUL_CLARO = RGBColor(0x1F, 0x6F, 0xB2)
GRIS = RGBColor(0x55, 0x55, 0x55)
VERDE = RGBColor(0x1E, 0x7A, 0x34)
ROJO = RGBColor(0xB0, 0x2A, 0x2A)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)


def set_cell_background(cell, hex_color):
    """Aplica un color de fondo a una celda de tabla."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=9, align="left",
                  italic=False):
    """Escribe texto formateado dentro de una celda (sustituye el contenido)."""
    cell.text = ""
    p = cell.paragraphs[0]
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    return p


def add_run(paragraph, text, bold=False, italic=False, color=None, size=None):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    if size is not None:
        run.font.size = Pt(size)
    return run


def style_header_row(row, fill="003D6B"):
    for cell in row.cells:
        set_cell_background(cell, fill)
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = BLANCO
                r.bold = True


# --------------------------------------------------------------------------- #
# Construcción del documento
# --------------------------------------------------------------------------- #
def build():
    doc = Document()

    # Estilo base
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # ---------------------------------------------------------------- #
    # PORTADA / TÍTULO
    # ---------------------------------------------------------------- #
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(title,
            "Especificaciones de Calidad del Gas Natural",
            bold=True, color=AZUL_ENAGAS, size=20)
    title2 = doc.add_paragraph()
    title2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(title2, "Valores Verificados (ES vs UE)",
            bold=True, color=AZUL_CLARO, size=16)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(sub,
            "Conjunto de datos corregido y verificado — revisión 2026-06",
            italic=True, color=GRIS, size=11)
    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(sub2, "Proyecto ENAGÁS Reto 5", italic=True, color=GRIS, size=11)

    sub3 = doc.add_paragraph()
    sub3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(sub3,
            "Parámetros cubiertos: O₂ · H₂S · PCS   |   "
            "Fuentes oficiales: BOE · Enagás/PD-01 · EUR-Lex",
            color=GRIS, size=9.5)

    doc.add_paragraph()

    # ---------------------------------------------------------------- #
    # 1. INTRODUCCIÓN / ALCANCE
    # ---------------------------------------------------------------- #
    doc.add_heading("1. Introducción y alcance", level=1)
    p = doc.add_paragraph()
    add_run(p,
            "Este documento recoge los valores oficialmente verificados de las "
            "especificaciones de calidad del gas natural para tres parámetros "
            "clave —oxígeno (O₂), sulfuro de hidrógeno (H₂S) y poder calorífico "
            "superior (PCS)— comparando la normativa española con la europea. "
            "Constituye el conjunto de datos corregido (revisión 2026-06) que "
            "sustituye a las cifras erróneas del dataset original del proyecto "
            "ENAGÁS Reto 5.")
    p = doc.add_paragraph()
    add_run(p, "Metodología de verificación. ", bold=True)
    add_run(p,
            "Los valores españoles se han contrastado contra el Protocolo de "
            "Detalle PD-01 («Medición, Calidad y Odorización de Gas»), apartado "
            "5.2, Tabla 3, publicado en el BOE y reproducido por Enagás. Los "
            "valores europeos se han contrastado contra el Reglamento (UE) "
            "2015/703 (Network Code on Interoperability — NC INT) en EUR-Lex. "
            "Toda cifra incluida es trazable a su documento, artículo o tabla de "
            "origen; cuando una fuente no fija un valor numérico, así se indica "
            "explícitamente y no se inventa ninguna cifra.")

    p = doc.add_paragraph()
    add_run(p, "Conclusión normativa clave. ", bold=True)
    add_run(p,
            "El Reglamento (UE) 2015/703 NO fija límites numéricos de O₂, H₂S ni "
            "un rango de PCS: únicamente armoniza unidades, condiciones de "
            "referencia y la obligación de monitorizar el índice de Wobbe y el "
            "PCS. Los límites de calidad se delegan a la normativa nacional y a "
            "los acuerdos bilaterales entre gestores de red (TSOs); la norma "
            "EN 16726 es una referencia técnica no vinculante.")

    # ---------------------------------------------------------------- #
    # 2. TABLA RESUMEN PRINCIPAL
    # ---------------------------------------------------------------- #
    doc.add_heading("2. Tabla resumen de valores verificados", level=1)

    cols = ["Parámetro", "Jurisdicción", "Valor verificado", "Unidad",
            "Condiciones de referencia", "Fuente (documento + artículo/tabla)",
            "Estado de verificación"]

    main_rows = [
        ["O₂ (Oxígeno)", "España (ES)", "0,01 (máximo)", "% mol",
         "V(0 ºC, 1,01325 bar)",
         "PD-01, apdo. 5.2, Tabla 3 (NGTS-06)",
         "VERIFICADO"],
        ["O₂ (Oxígeno)", "Unión Europea (UE)", "No fija límite", "—",
         "—",
         "Reglamento (UE) 2015/703 — no establece límite de O₂",
         "NO_VERIFICABLE_SIN_FUENTE"],
        ["H₂S (Sulfuro de hidrógeno)", "España (ES)",
         "15 (máximo) — «H₂S + COS (como S)»", "mg/Nm³",
         "V(0 ºC, 1,01325 bar)",
         "PD-01, apdo. 5.2, Tabla 3 (fila «H₂S + COS (como S)»)",
         "VERIFICADO"],
        ["H₂S (Sulfuro de hidrógeno)", "Unión Europea (UE)", "No fija límite",
         "—", "—",
         "Reglamento (UE) 2015/703 — no establece límite de H₂S",
         "NO_VERIFICABLE_SIN_FUENTE"],
        ["PCS (Poder Calorífico Superior)", "España (ES)",
         "10,26 – 13,26  (= 36,94 – 47,74 MJ/Nm³)", "kWh/Nm³",
         "@0/0 — combustión 0 ºC, V(0 ºC, 1,01325 bar)",
         "PD-01, apdo. 5.2, Tabla 3 (fila «PCS»)",
         "VERIFICADO"],
        ["PCS (Poder Calorífico Superior)", "Unión Europea (UE)",
         "No fija rango numérico", "—",
         "@25/0 — sólo condiciones de reporte (art. 13)",
         "Reglamento (UE) 2015/703, art. 13 (unidades/condiciones) y art. 16 "
         "(monitorización)",
         "NO_VERIFICABLE_SIN_FUENTE"],
    ]

    table = doc.add_table(rows=1, cols=len(cols))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, c in enumerate(cols):
        set_cell_text(hdr.cells[i], c, bold=True, color=BLANCO, size=8.5,
                      align="center")
    style_header_row(hdr)

    for r in main_rows:
        cells = table.add_row().cells
        estado = r[6]
        for i, val in enumerate(r):
            color = None
            bold = False
            if i == 6:  # estado
                if estado == "VERIFICADO":
                    color = VERDE
                else:
                    color = ROJO
                bold = True
            set_cell_text(cells[i], val, bold=bold, color=color, size=8.5)
        # tinte de fila por jurisdicción
        fill = "EAF2FB" if r[1].startswith("España") else "FBEFEF"
        for c in cells:
            set_cell_background(c, fill)
            # re-aplicar color del estado tras el fondo
        # reaplicar color de estado
        if estado == "VERIFICADO":
            set_cell_text(cells[6], estado, bold=True, color=VERDE, size=8.5)
        else:
            set_cell_text(cells[6], estado, bold=True, color=ROJO, size=8.5)

    # ancho de columnas aproximado
    widths = [1.25, 1.0, 1.55, 0.6, 1.55, 1.9, 1.25]
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)

    # ---------------------------------------------------------------- #
    # 3. CORRECCIONES APLICADAS
    # ---------------------------------------------------------------- #
    doc.add_heading("3. Correcciones aplicadas", level=1)
    p = doc.add_paragraph()
    add_run(p,
            "La tabla siguiente documenta, en formato antes → después, los "
            "errores detectados en el dataset original y su corrección "
            "verificada.")

    corr_cols = ["Parámetro / aspecto", "Valor original (ERRÓNEO)",
                 "Valor corregido (VERIFICADO)", "Explicación"]
    corr_rows = [
        ["H₂S (ES) — límite",
         "5 mg/Nm³",
         "15 mg/Nm³ — «H₂S + COS (como S)»",
         "El valor original era incorrecto. El límite oficial de la Tabla 3 del "
         "PD-01 es 15 mg/Nm³ para la suma de H₂S y COS expresada como azufre. "
         "Parámetros relacionados: azufre total ≤ 50 mg/Nm³; mercaptanos "
         "RSH (como S) ≤ 17 mg/Nm³."],
        ["PCS (ES) — rango",
         "34,12 – 38,77 MJ/Nm³",
         "10,26 – 13,26 kWh/Nm³ (= 36,94 – 47,74 MJ/Nm³)",
         "El rango original era incorrecto. La Tabla 3 del PD-01 expresa el PCS "
         "en kWh/Nm³; su equivalente exacto en MJ se obtiene multiplicando por "
         "3,6."],
        ["PCS (ES) — condiciones de referencia",
         "@25/0 (combustión 25 ºC, volumen 0 ºC)",
         "@0/0 (combustión 0 ºC, volumen 0 ºC)",
         "El PD-01 fija el PCS en base volumétrica a [0 ºC combustión, "
         "V(0 ºC, 1,01325 bar)]. La UE, en cambio, reporta a @25/0 (art. 13 del "
         "Reglamento 2015/703); coincide el volumen (0 ºC) pero difiere la "
         "temperatura de combustión."],
        ["O₂ (ES) — unidad",
         "% vol",
         "% mol",
         "La Tabla 3 del PD-01 expresa el O₂ como fracción molar (% mol), no "
         "volumétrica. Para gas ideal % mol ≈ % vol (diferencia < 0,1 %), pero "
         "la unidad oficial es % mol."],
        ["RD 919/2006 — fecha de publicación",
         "(fecha imprecisa / ausente)",
         "BOE núm. 211, de 4 de septiembre de 2006",
         "Se fija la referencia oficial de publicación en el BOE "
         "(BOE-A-2006-15345)."],
        ["RD 919/2006 — contenido",
         "Se asumía que contenía la tabla de calidad",
         "NO contiene la tabla de calidad del gas de transporte",
         "El RD 919/2006 regula la distribución y utilización (ICG 01–11). El "
         "detalle numérico de calidad del gas está en el PD-01 de la NGTS, no "
         "en el RD."],
    ]

    ctab = doc.add_table(rows=1, cols=len(corr_cols))
    ctab.style = "Table Grid"
    ctab.alignment = WD_TABLE_ALIGNMENT.CENTER
    chdr = ctab.rows[0]
    for i, c in enumerate(corr_cols):
        set_cell_text(chdr.cells[i], c, bold=True, color=BLANCO, size=9,
                      align="center")
    style_header_row(chdr)

    for r in corr_rows:
        cells = ctab.add_row().cells
        set_cell_text(cells[0], r[0], bold=True, size=9)
        set_cell_text(cells[1], r[1], color=ROJO, size=9)
        set_cell_text(cells[2], r[2], color=VERDE, bold=True, size=9)
        set_cell_text(cells[3], r[3], size=9)

    cwidths = [1.45, 1.55, 1.9, 3.1]
    for row in ctab.rows:
        for i, w in enumerate(cwidths):
            row.cells[i].width = Inches(w)

    # ---------------------------------------------------------------- #
    # 4. VALORES NO VERIFICABLES (UE)
    # ---------------------------------------------------------------- #
    doc.add_heading("4. Valores no verificables (UE)", level=1)
    p = doc.add_paragraph()
    add_run(p,
            "El conjunto de datos no atribuye ningún límite numérico de O₂, H₂S "
            "ni rango de PCS a la normativa europea, porque ", )
    add_run(p, "el Reglamento (UE) 2015/703 sencillamente no los define. ",
            bold=True)
    add_run(p,
            "Atribuir cifras europeas supondría inventarlas. Estos parámetros se "
            "marcan como NO_VERIFICABLE_SIN_FUENTE.")

    bullets = [
        ("O₂ (UE): ",
         "el Reglamento (UE) 2015/703 no contiene un límite numérico de "
         "oxígeno. Sólo armoniza unidades y condiciones de referencia; los "
         "límites de O₂ se dejan a la normativa nacional o a acuerdos "
         "bilaterales entre TSOs (referencia no vinculante: EN 16726)."),
        ("H₂S (UE): ",
         "el Reglamento no fija un límite numérico de H₂S (ni en mg/m³ ni en "
         "ppm). Los límites de azufre/H₂S en interconexión se delegan a la "
         "normativa nacional y a acuerdos bilaterales entre TSOs."),
        ("PCS (UE): ",
         "el Reglamento no establece un rango/límite numérico de PCS. Sí fija "
         "(art. 13) la unidad (kWh/m³) y las condiciones de referencia "
         "(volumen 0 ºC y 1,01325 bar; combustión por defecto 25 ºC), y "
         "(art. 16) la obligación de los TSOs de publicar Wobbe y PCS por hora "
         "en cada punto de interconexión."),
    ]
    for head, body in bullets:
        bp = doc.add_paragraph(style="List Bullet")
        add_run(bp, head, bold=True, color=AZUL_ENAGAS)
        add_run(bp, body)

    p = doc.add_paragraph()
    add_run(p, "Implicación de comparabilidad: ", bold=True, color=ROJO)
    add_run(p,
            "al no existir valores UE en la fuente citada, las comparaciones "
            "directas ES vs UE de O₂, H₂S y PCS quedan marcadas como 🔴 "
            "NO_COMPARABLE en la ontología del sistema.")

    # ---------------------------------------------------------------- #
    # 5. PARÁMETROS DE CONTEXTO (PD-01, TABLA 3)
    # ---------------------------------------------------------------- #
    doc.add_heading("5. Parámetros de contexto (PD-01, Tabla 3)", level=1)
    p = doc.add_paragraph()
    add_run(p, "Tabla secundaria — sólo contexto. ", bold=True, italic=True)
    add_run(p,
            "Estos parámetros pertenecen a la misma Tabla 3 del PD-01 y ayudan a "
            "interpretar los límites principales. Se incluyen únicamente las "
            "cifras presentes en el conjunto de datos verificado; los parámetros "
            "recogidos en la tabla sin valor numérico en la ontología se listan "
            "sin cifra para no fabricar datos.")

    ctx_cols = ["Parámetro de contexto", "Valor verificado", "Unidad",
                "Fuente", "Estado"]
    ctx_rows = [
        ["Azufre total (S total)", "≤ 50 (máximo)", "mg/Nm³",
         "PD-01, apdo. 5.2, Tabla 3", "VERIFICADO"],
        ["Mercaptanos RSH (como S)", "≤ 17 (máximo)", "mg/Nm³",
         "PD-01, apdo. 5.2, Tabla 3", "VERIFICADO"],
        ["H₂S + COS (como S)", "≤ 15 (máximo)", "mg/Nm³",
         "PD-01, apdo. 5.2, Tabla 3", "VERIFICADO"],
        ["Índice de Wobbe", "Recogido en Tabla 3 (sin cifra en la ontología)",
         "kWh/Nm³", "PD-01, apdo. 5.2, Tabla 3", "NO INCLUIDO EN DATASET"],
        ["Densidad relativa",
         "Recogido en Tabla 3 (sin cifra en la ontología)", "—",
         "PD-01, apdo. 5.2, Tabla 3", "NO INCLUIDO EN DATASET"],
        ["CO₂", "Recogido en Tabla 3 (sin cifra en la ontología)", "% mol",
         "PD-01, apdo. 5.2, Tabla 3", "NO INCLUIDO EN DATASET"],
        ["Punto de rocío (agua / hidrocarburos)",
         "Recogido en Tabla 3 (sin cifra en la ontología)", "ºC",
         "PD-01, apdo. 5.2, Tabla 3", "NO INCLUIDO EN DATASET"],
    ]
    ctxt = doc.add_table(rows=1, cols=len(ctx_cols))
    ctxt.style = "Table Grid"
    ctxt.alignment = WD_TABLE_ALIGNMENT.CENTER
    cxhdr = ctxt.rows[0]
    for i, c in enumerate(ctx_cols):
        set_cell_text(cxhdr.cells[i], c, bold=True, color=BLANCO, size=9,
                      align="center")
    style_header_row(cxhdr, fill="1F6FB2")

    for r in ctx_rows:
        cells = ctxt.add_row().cells
        set_cell_text(cells[0], r[0], bold=True, size=9)
        set_cell_text(cells[1], r[1], size=9)
        set_cell_text(cells[2], r[2], size=9, align="center")
        set_cell_text(cells[3], r[3], size=9)
        verificado = r[4] == "VERIFICADO"
        set_cell_text(cells[4], r[4], bold=True,
                      color=VERDE if verificado else GRIS, size=8.5)

    cxwidths = [2.0, 2.6, 0.7, 1.9, 1.4]
    for row in ctxt.rows:
        for i, w in enumerate(cxwidths):
            row.cells[i].width = Inches(w)

    p = doc.add_paragraph()
    add_run(p,
            "Condiciones de referencia de toda la Tabla 3 del PD-01: "
            "[0 ºC, V(0 ºC, 1,01325 bar)].", italic=True, color=GRIS, size=9)

    # ---------------------------------------------------------------- #
    # 6. FUENTES OFICIALES
    # ---------------------------------------------------------------- #
    doc.add_heading("6. Fuentes oficiales", level=1)

    fuentes = [
        ("RD 919/2006 (BOE-A-2006-15345)",
         "BOE núm. 211, de 4 de septiembre de 2006",
         "https://www.boe.es/buscar/act.php?id=BOE-A-2006-15345"),
        ("Resolución 21/12/2012 — PD-01, apdo. 5.2 (BOE-A-2013-185)",
         "Redacción vigente de la Tabla 3",
         "https://www.boe.es/eli/es/res/2012/12/21/(3)"),
        ("Resolución 8/10/2018 — PD-01 (BOE-A-2018-14557)",
         "Modificación posterior del PD-01",
         "https://www.boe.es/eli/es/res/2018/10/08/(3)"),
        ("Enagás — Calidad de gas (GTS)",
         "Página oficial con las especificaciones de calidad",
         "https://www.enagas.es/es/gestion-tecnica-sistema/"
         "procesos-sistema-gasista/calidad-gas/"),
        ("Reglamento (UE) 2015/703 — NC INT (CELEX:32015R0703)",
         "Network Code on Interoperability and Data Exchange",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R0703"),
        ("Reglamento (UE) 2017/459 — NC CAM (CELEX:32017R0459)",
         "Network Code on Capacity Allocation Mechanisms",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0459"),
    ]
    for nombre, desc, url in fuentes:
        bp = doc.add_paragraph(style="List Bullet")
        add_run(bp, nombre + " — ", bold=True, color=AZUL_ENAGAS)
        add_run(bp, desc + " ", )
        add_hyperlink(bp, url, url)

    # ---------------------------------------------------------------- #
    # Pie / nota final
    # ---------------------------------------------------------------- #
    doc.add_paragraph()
    foot = doc.add_paragraph()
    add_run(foot,
            "Documento generado a partir de la ontología verificada "
            "(ontologia_enagas.yaml, v2.0.0, revisión 2026-06). Ninguna cifra ha "
            "sido inventada: los valores proceden del PD-01 (Tabla 3) vía BOE y "
            "Enagás, y la ausencia de límites UE refleja el contenido real del "
            "Reglamento (UE) 2015/703.",
            italic=True, color=GRIS, size=8.5)

    return doc


def add_hyperlink(paragraph, url, text):
    """Inserta un hipervínculo real y clicable en un párrafo."""
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F6FB2")
    r_pr.append(color)

    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    r_pr.append(u)

    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "18")
    r_pr.append(sz)

    new_run.append(r_pr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "Calidad_Gas_Valores_Verificados.docx")
    doc = build()
    doc.save(out_path)
    print("OK -> " + out_path)


if __name__ == "__main__":
    main()
