# -*- coding: utf-8 -*-
"""Estudio de consistencia terminológica (Fase 1 de la ampliación a biometano/hidrógeno).

Motivación (indicación del profesor): antes de montar una capa vectorial/semántica en
el RAG, hay que MEDIR cuánto varía la terminología con la que las normas nombran cada
parámetro. Si varía mucho —se espera sobre todo en hidrógeno— la búsqueda léxica actual
(SQLite LIKE, sin sinónimos) se queda corta y el vectorial aporta. Este script cuantifica
esa variación de forma reproducible y emite un veredicto (la "puerta" de la Fase 3).

Qué mide, POR PARÁMETRO:
  - Formas léxicas distintas: alias + expresiones originales de cada jurisdicción.
  - Unidades distintas (kWh/m³, MJ/m³, mg/m³, % mol, ppm, °C…).
  - Condiciones de referencia distintas (@0/0, @25/0, @15/15, @25/20…).
  - Divergencia semántica: el "mismo" parámetro con alcance distinto según la norma
    (p. ej. unas regulan "H₂S" y otras "H₂S + COS").
  - Cobertura léxica en el corpus (data/pdf_database.sqlite3) vía agente_pdf.buscar_pdfs.

Índice de Variación Terminológica (IVT) = nº_expresiones + nº_unidades + nº_condiciones
                                          + (2 si hay divergencia semántica).

Salida:
  - docs/Estudio_Terminologia_Biometano.md  (informe legible)
  - docs/estudio_terminologia_puerta.json    (datos + veredicto para la puerta de Fase 3)

Solo lectura. No modifica la ontología ni el índice. Ejecutar a mano:
    .venv/Scripts/python.exe estudio_terminologia.py
"""
import json
import os
import unicodedata
from typing import Any, Dict, List

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
ONTO_PATH = os.path.join(ROOT, "data", "ontologia", "ontologia_enagas.yaml")
OUT_MD = os.path.join(ROOT, "docs", "Estudio_Terminologia_Biometano.md")
OUT_JSON = os.path.join(ROOT, "docs", "estudio_terminologia_puerta.json")

# Umbral heurístico del IVT medio para justificar la capa vectorial. Es una referencia,
# no un dogma: el objetivo es comparar biometano con gas natural y anticipar hidrógeno.
UMBRAL_IVT = 7.0

# Parámetros del estudio. `seccion` indica de qué árbol de la ontología se leen los datos
# de variación: los que SOLAPAN con gas natural se leen de `parametros` (ahí hay datos de
# las 21 jurisdicciones = señal real de variación); los específicos, de `parametros_biometano`.
PARAMETROS = [
    {"clave": "O2",          "seccion": "parametros",             "solapa_gn": True},
    {"clave": "CO2",         "seccion": "parametros",             "solapa_gn": True},
    {"clave": "S_TOTAL",     "seccion": "parametros",             "solapa_gn": True},
    {"clave": "H2S_COS",     "seccion": "parametros",             "solapa_gn": True},
    {"clave": "PR_H2O",      "seccion": "parametros",             "solapa_gn": True},
    {"clave": "CH4_MIN",     "seccion": "parametros_biometano",   "solapa_gn": False},
    {"clave": "SILOXANOS",   "seccion": "parametros_biometano",   "solapa_gn": False},
    {"clave": "COMP_OIL",    "seccion": "parametros_biometano",   "solapa_gn": False},
    {"clave": "AMINAS",      "seccion": "parametros_biometano",   "solapa_gn": False},
    {"clave": "NH3",         "seccion": "parametros_biometano",   "solapa_gn": False},
    {"clave": "HALOGENADOS", "seccion": "parametros_biometano",   "solapa_gn": False},
]


def _norm(s: Any) -> str:
    t = str(s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def _cargar_onto() -> Dict[str, Any]:
    with open(ONTO_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _buscar_pdfs_seguro(query: str) -> Dict[str, Any]:
    """Consulta léxica al índice RAG. Envuelta: si el módulo/DB no está, no rompe el estudio."""
    try:
        from agente_pdf import buscar_pdfs
        return buscar_pdfs(query=query)
    except Exception as e:  # noqa: BLE001
        return {"count": 0, "matches": [], "_error": str(e)}


def analizar_parametro(onto: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    seccion = onto.get(spec["seccion"]) or {}
    nodo = seccion.get(spec["clave"]) or {}
    limites = nodo.get("limites") or {}

    aliases = [a for a in (nodo.get("aliases") or [])]
    nombre = nodo.get("nombre_completo") or spec["clave"]
    nombre_en = nodo.get("nombre_ingles") or ""

    # Recolecta, a través de TODAS las jurisdicciones, las formas de nombrar/medir el parámetro.
    expresiones, unidades, condiciones = set(), set(), set()
    menciona_cos, no_menciona_cos = False, False
    for cod, lim in limites.items():
        exp = (lim.get("expresion_original") or "").strip()
        if exp:
            expresiones.add(exp)
            # Señal de divergencia semántica para el azufre: unas normas citan COS, otras no.
            if "cos" in _norm(exp):
                menciona_cos = True
            elif "h2s" in _norm(exp) or "sulf" in _norm(exp) or "svovl" in _norm(exp) or "schwefel" in _norm(exp):
                no_menciona_cos = True
        u = (lim.get("unidad") or "").strip()
        if u:
            unidades.add(u)
        cr = lim.get("condiciones_referencia") or {}
        notac = cr.get("notacion")
        if notac:
            condiciones.add(str(notac))
        elif cr.get("temperatura_combustion_C") is not None:
            condiciones.add(f"@{cr.get('temperatura_combustion_C')}/{cr.get('temperatura_volumen_C')}")

    # Divergencia semántica de alcance (solo aplica de forma automática al azufre H2S/COS).
    divergencia = spec["clave"] == "H2S_COS" and menciona_cos and no_menciona_cos

    # Cobertura léxica en el corpus: ¿cuántos documentos distintos menciona cada alias?
    cobertura = []
    for alias in aliases[:4]:
        r = _buscar_pdfs_seguro(alias)
        docs = sorted({m.get("name") for m in (r.get("matches") or []) if m.get("name")})
        cobertura.append({"alias": alias, "hits": r.get("count", 0), "documentos": docs})

    ivt = len(expresiones) + len(unidades) + len(condiciones) + (2 if divergencia else 0)

    return {
        "clave": spec["clave"],
        "nombre": nombre,
        "nombre_ingles": nombre_en,
        "solapa_gas_natural": spec["solapa_gn"],
        "n_jurisdicciones": len(limites),
        "n_aliases": len(set(_norm(a) for a in aliases)),
        "aliases": aliases,
        "n_expresiones_distintas": len(expresiones),
        "expresiones": sorted(expresiones),
        "n_unidades_distintas": len(unidades),
        "unidades": sorted(unidades),
        "n_condiciones_distintas": len(condiciones),
        "condiciones": sorted(condiciones),
        "divergencia_semantica": divergencia,
        "cobertura_corpus": cobertura,
        "IVT": ivt,
    }


def construir_informe(resultados: List[Dict[str, Any]]) -> Dict[str, Any]:
    solapan = [r for r in resultados if r["solapa_gas_natural"]]
    especificos = [r for r in resultados if not r["solapa_gas_natural"]]
    ivt_solapan = round(sum(r["IVT"] for r in solapan) / len(solapan), 2) if solapan else 0.0
    ivt_especificos = round(sum(r["IVT"] for r in especificos) / len(especificos), 2) if especificos else 0.0
    ivt_global = round(sum(r["IVT"] for r in resultados) / len(resultados), 2) if resultados else 0.0

    # Veredicto de la puerta de Fase 3 (capa vectorial). El biometano se evalúa con los
    # parámetros que SOLAPAN con gas natural (los que tienen datos reales de 21 países);
    # los específicos aún no tienen corpus (llegará en Fase 2), así que se anota aparte.
    justificado_biometano = ivt_solapan >= UMBRAL_IVT
    return {
        "umbral_ivt": UMBRAL_IVT,
        "ivt_medio_parametros_solapados": ivt_solapan,
        "ivt_medio_parametros_especificos": ivt_especificos,
        "ivt_medio_global": ivt_global,
        "vectorial_justificado_para_biometano": justificado_biometano,
        "nota_hidrogeno": (
            "Los parámetros específicos de biometano aún no tienen corpus (Fase 2). "
            "La variación real de hidrógeno (ENTSOG/ENNOH) se medirá al añadir esos "
            "documentos; se ESPERA que supere el umbral (pureza de H₂ / fracción molar "
            "de hidrógeno / Wasserstoffreinheit), reabriendo la puerta de la capa vectorial."
        ),
    }


def render_md(resultados: List[Dict[str, Any]], resumen: Dict[str, Any]) -> str:
    L = []
    L.append("# Estudio de consistencia terminológica — Biometano (Fase 1)\n")
    L.append(
        "> Objetivo (indicación del profesor): medir cuánto varía la terminología entre "
        "normas antes de decidir si montar una capa vectorial en el RAG. La búsqueda actual "
        "es **léxica** (SQLite `LIKE`, sin sinónimos); si la variación es alta, el vectorial "
        "aporta algo que el léxico no capta.\n"
    )
    L.append("## Metodología\n")
    L.append(
        "Para cada parámetro se recogen, a través de todas las jurisdicciones disponibles en "
        "la ontología, las **formas de nombrarlo** (alias + expresiones originales), las "
        "**unidades** y las **condiciones de referencia**, más una señal de **divergencia "
        "semántica** (mismo nombre, alcance distinto). El **Índice de Variación Terminológica "
        "(IVT)** = nº expresiones distintas + nº unidades + nº condiciones + (2 si hay "
        f"divergencia semántica). Umbral heurístico para justificar el vectorial: **{resumen['umbral_ivt']}**.\n"
    )
    L.append("## Resumen y veredicto\n")
    L.append(f"- IVT medio (parámetros que **solapan** con gas natural, con datos de 21 jurisdicciones): **{resumen['ivt_medio_parametros_solapados']}**")
    L.append(f"- IVT medio (parámetros **específicos** de biometano, aún sin corpus): **{resumen['ivt_medio_parametros_especificos']}**")
    L.append(f"- IVT medio global: **{resumen['ivt_medio_global']}**")
    veredicto = "**SÍ**" if resumen["vectorial_justificado_para_biometano"] else "**NO (de momento)**"
    L.append(f"- ¿Capa vectorial justificada para biometano? {veredicto}\n")
    L.append(f"> {resumen['nota_hidrogeno']}\n")

    L.append("## Detalle por parámetro\n")
    L.append("| Parámetro | Solapa GN | Jurisd. | Alias | Expr. dist. | Uds. | Cond. | Diverg. sem. | IVT |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(resultados, key=lambda x: x["IVT"], reverse=True):
        L.append(
            f"| {r['nombre']} (`{r['clave']}`) | {'sí' if r['solapa_gas_natural'] else 'no'} | "
            f"{r['n_jurisdicciones']} | {r['n_aliases']} | {r['n_expresiones_distintas']} | "
            f"{r['n_unidades_distintas']} | {r['n_condiciones_distintas']} | "
            f"{'⚠️ sí' if r['divergencia_semantica'] else '—'} | **{r['IVT']}** |"
        )
    L.append("")

    for r in sorted(resultados, key=lambda x: x["IVT"], reverse=True):
        L.append(f"### {r['nombre']} (`{r['clave']}`)  ·  IVT = {r['IVT']}\n")
        if r["unidades"]:
            L.append(f"- **Unidades distintas** ({r['n_unidades_distintas']}): {', '.join(r['unidades'])}")
        if r["condiciones"]:
            L.append(f"- **Condiciones distintas** ({r['n_condiciones_distintas']}): {', '.join(r['condiciones'])}")
        if r["divergencia_semantica"]:
            L.append("- **Divergencia semántica**: unas normas regulan «H₂S» y otras «H₂S + COS» (mismo nombre, alcance distinto).")
        if r["expresiones"]:
            L.append(f"- **Formas encontradas** ({r['n_expresiones_distintas']}):")
            for e in r["expresiones"][:12]:
                L.append(f"    - {e}")
            if len(r["expresiones"]) > 12:
                L.append(f"    - … (+{len(r['expresiones'])-12} más)")
        # Cobertura léxica en el corpus.
        cob = [c for c in r["cobertura_corpus"] if c["hits"]]
        if cob:
            L.append("- **Cobertura léxica en el corpus** (alias → nº aciertos):")
            for c in r["cobertura_corpus"]:
                L.append(f"    - `{c['alias']}` → {c['hits']} aciertos" + (f" en {len(c['documentos'])} doc(s)" if c["documentos"] else ""))
        else:
            L.append("- **Cobertura léxica en el corpus**: sin aciertos directos (esperado en parámetros específicos: aún no hay PDFs de biometano en `data/raw`).")
        L.append("")

    L.append("---")
    L.append("_Generado por `estudio_terminologia.py` (solo lectura). Reejecutar tras añadir los PDFs de biometano/hidrógeno en la Fase 2 para medir su variación real._")
    return "\n".join(L)


def main() -> None:
    onto = _cargar_onto()
    resultados = [analizar_parametro(onto, spec) for spec in PARAMETROS]
    resumen = construir_informe(resultados)

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(resultados, resumen))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"resumen": resumen, "parametros": resultados}, f, ensure_ascii=False, indent=2)

    print("Estudio de terminología generado:")
    print(f"  - {os.path.relpath(OUT_MD, ROOT)}")
    print(f"  - {os.path.relpath(OUT_JSON, ROOT)}")
    print(f"IVT medio (solapados)={resumen['ivt_medio_parametros_solapados']} | "
          f"global={resumen['ivt_medio_global']} | umbral={resumen['umbral_ivt']} | "
          f"vectorial biometano={'SÍ' if resumen['vectorial_justificado_para_biometano'] else 'NO'}")


if __name__ == "__main__":
    main()
