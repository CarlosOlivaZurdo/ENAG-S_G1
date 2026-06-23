"""Capa de datos OFICIAL: lee de la ontología validada (extracción verificada de los
PDFs oficiales) en lugar del Excel/CSV.

Política de fuentes (acordada con el equipo):
  • La fuente PRIMARIA es la documentación oficial vigente, ya extraída y verificada
    en `data/ontologia/ontologia_enagas.yaml` (con artículo, página, organismo,
    fecha/versión y URL). Los PDFs oficiales están en `data/raw/`.
  • El Excel/CSV pasa a ser solo un ÍNDICE de referencia; nunca la fuente final.
  • Ante discrepancia Excel ↔ oficial, prevalece la oficial (y se señala).

Este módulo devuelve registros con la MISMA forma que consume el resto del sistema
(`consultar_excel` / `evaluar_cumplimiento`), enriquecidos con la cita completa.
"""
import os
import re
import glob
from typing import Any, Dict, Optional

from conversor_unidades import convertir_unidades, _normalizar_unidad

_CACHE: Dict[str, Any] = {}

# slug del chatbot -> clave de parámetro en la ontología
_PARAM_A_ONTO = {
    "wobbe": "WOBBE", "pcs": "PCS", "densidad relativa": "DENS_REL",
    "s total": "S_TOTAL", "h2s+cos": "H2S_COS", "rsh": "RSH",
    "o2": "O2", "co2": "CO2", "h2o(rocío)": "PR_H2O", "hc(rocío)": "PR_HC",
}
_PAIS_A_CODIGO = {"espana": "ES", "portugal": "PT", "francia": "FR", "ue": "UE", "europa": "UE"}
_CODIGO_A_PAIS = {"ES": "España", "PT": "Portugal", "FR": "Francia", "UE": "UE"}
# Condiciones de referencia (combustión/volumen) de cada país, aplicables a TODOS sus
# parámetros. España y Francia: 0/0; Portugal: combustión 25 ºC (ISO 13443/96); UE (EN 16726): 15/15.
_NOTACION_PAIS = {"ES": "(0/0)", "PT": "(25/0)", "FR": "(0/0)", "UE": "(25/0)"}

# Código de unidad de la ontología -> símbolo legible (y convertible por el conversor)
_UNIDAD_DISPLAY = {
    "kWh_per_nm3": "kWh/m³", "MJ_per_nm3": "MJ/m³",
    "mg_per_nm3": "mg/Nm³", "mg_per_sm3": "mg/sm³",
    "pct_mol": "% molar", "pct_vol": "% vol", "ppm_vol": "ppm",
    "grados_C": "°C", "adimensional": "",
}


def _norm(s: Any) -> str:
    s = str(s).strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        s = s.replace(a, b)
    return s


def _fmt(x: Any) -> str:
    if x is None:
        return "-"
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    if f == int(f):
        return str(int(f))
    return ("%g" % f).replace(".", ",")


def _num(x: Any) -> Optional[float]:
    s = str(x).strip().replace(",", ".")
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
    return float(m.group(0)) if m else None


def cargar_ontologia() -> Dict[str, Any]:
    if "data" in _CACHE:
        return _CACHE["data"]
    data: Dict[str, Any] = {}
    try:
        import yaml
        ruta = os.path.join(os.path.dirname(__file__), "data", "ontologia", "ontologia_enagas.yaml")
        if not os.path.exists(ruta):
            cand = glob.glob(os.path.join(os.path.dirname(__file__), "data", "**", "ontologia_enagas.yaml"), recursive=True)
            ruta = cand[0] if cand else ruta
        with open(ruta, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"[fuente_oficial] No se pudo cargar la ontología ({exc}).")
    _CACHE["data"] = data
    return data


def _glosario() -> Dict[str, Dict[str, Any]]:
    onto = cargar_ontologia()
    fuentes = (onto.get("ontologia") or {}).get("fuentes_normativas") or []
    return {f.get("id"): f for f in fuentes if isinstance(f, dict) and f.get("id")}


def _pagina(*textos: str) -> str:
    for s in textos:
        m = re.search(r"p[aá]gs?\.?\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)", str(s or ""), re.I)
        if m:
            return m.group(1).replace(" ", "")
    return ""


# URL web oficial por fuente (Nota 4: enlace a la fuente consultada). Se usa cuando la
# ontología no trae una URL explícita. Verificadas (descargan el PDF/documento oficial).
_URL_OFICIAL = {
    "ORDEN_TED_181_2025": "https://www.boe.es/buscar/pdf/2025/BOE-A-2025-3873-consolidado.pdf",
    "RD919": "https://www.boe.es/buscar/pdf/2006/BOE-A-2006-15345-consolidado.pdf",
    "NC_INT": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015R0703",
    "NC_CAM": "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32017R0459",
    "REG_PT_826_2023": "https://www.erse.pt/media/ws0j5wzg/rqs_regulamento-da-qualidade-de-servi%C3%A7o_consolidado.pdf",
    "FR_GRTGAZ": "https://www.natrangroupe.com/sites/default/files/2024-07/annexe-4-spec-grtgaz-methane-de-synthese-pour-injection.pdf",
    "FR_GRDF": "https://projet-methanisation.grdf.fr/cms-assets/2019/07/Prescriptions_techniques_GRDF.pdf",
    "PD01": "https://www.enagas.es/es/gestion-tecnica-sistema/procesos-sistema-gasista/calidad-gas/",
}


def _cita(fuente_code: Optional[str], articulo: Optional[str]) -> Dict[str, str]:
    g = _glosario().get(fuente_code, {})
    url = g.get("url_eurlex") or g.get("url_enagas") or _URL_OFICIAL.get(fuente_code, "")
    return {
        "documento": g.get("nombre") or fuente_code or "No consta",
        "organismo": g.get("organismo") or "",
        "fecha": g.get("publicacion") or g.get("referencia_legal") or "",
        "url": url,
        "pdf": g.get("pdf") or "",
        "articulo": articulo or g.get("tabla_calidad") or "",
        "pagina": _pagina(articulo, g.get("tabla_calidad")),
        "fuente_codigo": fuente_code or "",
    }


def _cond_txt(cr: Optional[Dict[str, Any]]) -> str:
    if not cr:
        return ""
    tv = cr.get("temperatura_volumen_C")
    p = cr.get("presion_bar")
    comb = cr.get("temperatura_combustion_C")
    partes = []
    if tv is not None:
        partes.append(f"{_fmt(tv)} ºC")
    if p is not None:
        partes.append(f"{_fmt(p)} bar")
    base = " y ".join(partes)
    if comb is not None and comb != tv:
        base += f" (combustión {_fmt(comb)} ºC)"
    return base


def _limite_ontologia(slug: str, pais: str) -> Optional[Dict[str, Any]]:
    onto = cargar_ontologia()
    params = onto.get("parametros") or {}
    key = _PARAM_A_ONTO.get(slug)
    cod = _PAIS_A_CODIGO.get(_norm(pais))
    if not key or key not in params or not cod:
        return None
    return (params[key].get("limites") or {}).get(cod)


def _nombre_param(slug: str) -> str:
    onto = cargar_ontologia()
    key = _PARAM_A_ONTO.get(slug)
    if key and key in (onto.get("parametros") or {}):
        return onto["parametros"][key].get("nombre_completo") or key
    return slug


def _record(slug: str, pais: str, lim: Dict[str, Any]) -> Dict[str, Any]:
    tipo = lim.get("tipo_limite")
    if tipo == "maximo":
        inf, sup = None, lim.get("valor")
    elif tipo == "minimo":
        inf, sup = lim.get("valor"), None
    else:  # rango
        inf, sup = lim.get("valor_min"), lim.get("valor_max")
    ucode = lim.get("unidad")
    udisp = _UNIDAD_DISPLAY.get(ucode, ucode or "")
    cita = _cita(lim.get("fuente"), lim.get("articulo"))
    # Condiciones de referencia: si la fuente no las detalla para este parámetro,
    # rige la condición normal del proyecto (0 ºC, 1,01325 bar) para ES/PT/FR.
    condiciones = _cond_txt(lim.get("condiciones_referencia")) or "0 ºC y 1,01325 bar"
    # Notación compacta (combustión/volumen). Si el parámetro no la detalla, rige la
    # del país (p. ej. Portugal = "(25/0)" en TODOS sus parámetros, no solo PCS/Wobbe).
    cr = lim.get("condiciones_referencia") or {}
    comb, med = cr.get("temperatura_combustion_C"), cr.get("temperatura_volumen_C")
    if comb is not None and med is not None:
        notacion = f"({_fmt(comb)}/{_fmt(med)})"
    else:
        notacion = _NOTACION_PAIS.get(_PAIS_A_CODIGO.get(_norm(pais)), "(0/0)")
    return {
        "parametro": _nombre_param(slug),
        "pais": _CODIGO_A_PAIS.get(_PAIS_A_CODIGO.get(_norm(pais)), pais),
        "limite_inferior": _fmt(inf) if inf is not None else "-",
        "limite_superior": _fmt(sup) if sup is not None else "-",
        "unidad": udisp,
        "condiciones": condiciones,
        "notacion": notacion,
        "documento": cita["documento"],
        "organismo": cita["organismo"],
        "fecha": cita["fecha"],
        "url": cita["url"],
        "pdf": cita["pdf"],
        "articulo": cita["articulo"],
        "pagina": cita["pagina"],
        "fuente_codigo": cita["fuente_codigo"],
        "estado": lim.get("estado_verificacion") or "",
        "expresion_original": lim.get("expresion_original") or "",
        "nota": lim.get("nota") or lim.get("nota_comparabilidad") or "",
        "origen_dato": "oficial",
    }


def consultar(slug: str, pais: str) -> Dict[str, Any]:
    """Devuelve {count, matches:[record]} desde la ontología (fuente oficial)."""
    lim = _limite_ontologia(slug, pais)
    if not lim:
        return {"count": 0, "matches": [], "origen": "oficial"}
    return {"count": 1, "matches": [_record(slug, pais, lim)], "origen": "oficial"}


def evaluar(slug: str, pais: str, valor: float, unidad: Optional[str] = None) -> Dict[str, Any]:
    """Evalúa cumplimiento contra el límite OFICIAL (ontología), con cita completa."""
    base = consultar(slug, pais)
    if base["count"] == 0:
        return {"count": 0, "matches": [], "error": "Sin límite oficial para ese parámetro y país."}
    rec = dict(base["matches"][0])
    inf, sup = _num(rec["limite_inferior"]), _num(rec["limite_superior"])
    ureg = rec["unidad"]
    tiene = inf is not None or sup is not None

    valor_comp = valor
    conversion = ""
    compat = True
    if tiene and unidad and ureg and _normalizar_unidad(unidad) != _normalizar_unidad(ureg):
        conv = convertir_unidades(valor, unidad, ureg, slug)
        if "valor_convertido" in conv:
            valor_comp = conv["valor_convertido"]
            conversion = conv.get("formula", "")
        else:
            compat = False

    if not tiene or not compat:
        estado = "No evaluable"
    else:
        cumple = True
        if sup is not None and valor_comp > sup:
            cumple = False
        if inf is not None and valor_comp < inf:
            cumple = False
        estado = "Cumple" if cumple else "No cumple"

    if not tiene:
        detalle = "Sin límite numérico en la fuente oficial (no regulado / no fijado)"
        comparable = False
    elif not compat:
        detalle = "Unidades incompatibles: no convertibles de forma determinista"
        comparable = False
    elif estado == "Cumple":
        detalle = "Dentro de los límites"
        comparable = True
    else:
        partes = []
        if sup is not None and valor_comp > sup:
            partes.append(f"supera el máximo ({_fmt(sup)} {ureg})".strip())
        if inf is not None and valor_comp < inf:
            partes.append(f"no alcanza el mínimo ({_fmt(inf)} {ureg})".strip())
        detalle = "; ".join(partes) if partes else "fuera de los límites"
        comparable = True

    rec.update({
        "valor_evaluado": round(valor_comp, 6) if isinstance(valor_comp, float) else valor_comp,
        "valor_usuario": valor,
        "unidad_usuario": unidad or ureg,
        "unidad_evaluada": ureg,
        "unidad_registro": ureg,
        "conversion": conversion,
        "cumple": estado,
        "comparable": comparable,
        "detalle": detalle,
    })
    return {"count": 1, "matches": [rec], "origen": "oficial"}


if __name__ == "__main__":
    import sys, json
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(consultar("o2", "Portugal"), ensure_ascii=False, indent=1))
    print(json.dumps(evaluar("h2s+cos", "Portugal", 4.0, "mg/Nm³")["matches"][0], ensure_ascii=False, indent=1))
