"""Capa de datos OFICIAL: lee de la ontología validada (extracción verificada de los
PDF oficiales).

Política de fuentes (acordada con el equipo):
  • La fuente ÚNICA es la documentación oficial vigente, ya extraída y verificada
    en `data/ontologia/ontologia_enagas.yaml` (con artículo, página, organismo,
    fecha/versión y URL). Los PDF oficiales están en `data/raw/`.
  • No se inventa ningún valor: lo que la norma no fija se marca como no verificable.

Este módulo devuelve los registros (valor + cita completa) que consume el resto del
sistema a través de `consultar()` y `evaluar()`.
"""
import os
import re
import glob
from typing import Any, Dict, Optional

from conversor_unidades import convertir_unidades, _normalizar_unidad

_CACHE: Dict[str, Any] = {}

# slug del chatbot -> clave de parámetro en la ontología (GAS NATURAL)
_PARAM_A_ONTO = {
    "wobbe": "WOBBE", "pcs": "PCS", "densidad relativa": "DENS_REL",
    "s total": "S_TOTAL", "h2s+cos": "H2S_COS", "rsh": "RSH",
    "o2": "O2", "co2": "CO2", "h2o(rocío)": "PR_H2O", "hc(rocío)": "PR_HC",
}
# slug -> clave en `parametros_biometano` (dominio BIOMETANO; mapa PROPIO para no
# contaminar el camino de gas natural — riesgo R2). Jurisdicciones: UE/ES/FR/PT.
_PARAM_A_ONTO_BIOMETANO = {
    "ch4_min": "CH4_MIN", "o2": "O2", "co2": "CO2", "co": "CO", "s total": "S_TOTAL",
    "h2s+cos": "H2S_COS", "h2o(rocío)": "PR_H2O", "siloxanos": "SILOXANOS",
    "comp_oil": "COMP_OIL", "aminas": "AMINAS", "nh3": "NH3", "halogenados": "HALOGENADOS",
}
# slug -> clave en `parametros_hidrogeno` (dominio HIDRÓGENO; ISO 14687 Grade D).
# Jurisdicción única: ISO14687.
_PARAM_A_ONTO_HIDROGENO = {
    "h2_pureza": "H2_PUREZA", "no_h2": "NO_H2", "h2o": "H2O", "thc": "THC",
    "ch4": "CH4", "o2": "O2", "he": "HE", "n2": "N2", "ar": "AR", "co2": "CO2",
    "co": "CO", "s total": "S_TOTAL", "hcho": "HCHO", "hcooh": "HCOOH",
    "nh3": "NH3", "halogenados": "HALOGENADOS", "particulas": "PARTICULAS",
    "comp_trazas": "COMP_TRAZAS",
}
# Sección de ontología + mapa slug→clave por tipo de gas (los que NO son gas natural).
# (Se usa para el NOMBRE del parámetro; el límite se enruta en `_limite_ontologia`.)
_SECCION_POR_GAS = {
    "biometano": ("parametros_biometano", _PARAM_A_ONTO_BIOMETANO),
    "hidrogeno": ("parametros_hidrogeno", _PARAM_A_ONTO_HIDROGENO),
}
# Parámetros de biometano que NO son propios: el biometano inyectado debe cumplir la spec
# de GAS NATURAL del país (se leen de `parametros`, con jurisdicción ES/PT/FR/UE).
_SHARED_BIOMETANO = {"o2", "co2", "s total", "h2s+cos", "h2o(rocío)"}
_PAIS_A_CODIGO = {"espana": "ES", "portugal": "PT", "francia": "FR", "fr": "FR", "ue": "UE", "europa": "UE",
                  "italia": "IT", "italy": "IT", "alemania": "DE", "germany": "DE",
                  "deutschland": "DE", "germania": "DE",
                  "paises bajos": "NL", "holanda": "NL", "netherlands": "NL", "nederland": "NL",
                  "belgica": "BE", "belgium": "BE", "belgique": "BE", "belgie": "BE",
                  "noruega": "NOR", "norway": "NOR", "norge": "NOR",
                  "polonia": "PL", "poland": "PL", "polska": "PL",
                  "dinamarca": "DK", "denmark": "DK", "danmark": "DK",
                  "hungria": "HU", "hungary": "HU", "magyarorszag": "HU",
                  "austria": "AT", "osterreich": "AT",
                  "suiza": "CH", "switzerland": "CH", "schweiz": "CH", "suisse": "CH",
                  "chequia": "CZ", "republica checa": "CZ", "czech": "CZ", "czechia": "CZ", "cesko": "CZ",
                  "grecia": "GR", "greece": "GR", "hellas": "GR",
                  "irlanda": "IE", "ireland": "IE", "eire": "IE",
                  "rumania": "RO", "romania": "RO",
                  "eslovaquia": "SK", "slovakia": "SK", "slovensko": "SK",
                  "turquia": "TR", "turkey": "TR", "turkiye": "TR",
                  "reino unido": "GB", "united kingdom": "GB", "gran bretana": "GB", "britain": "GB",
                  "en16723": "EN16723", "biometano": "EN16723",
                  "iso14687": "ISO14687", "hidrogeno": "ISO14687"}
_CODIGO_A_PAIS = {"ES": "España", "PT": "Portugal", "FR": "Francia", "UE": "UE",
                  "EN16723": "EN 16723-1", "ISO14687": "ISO 14687 Grade D",
                  "IT": "Italia", "DE": "Alemania", "NL": "Países Bajos", "BE": "Bélgica",
                  "NOR": "Noruega", "PL": "Polonia", "DK": "Dinamarca", "HU": "Hungría", "AT": "Austria", "CH": "Suiza", "CZ": "Chequia", "GR": "Grecia",
                  "IE": "Irlanda", "RO": "Rumanía", "SK": "Eslovaquia", "TR": "Turquía", "GB": "Reino Unido"}
# Condiciones de referencia (combustión/volumen) de cada país, aplicables a TODOS sus
# parámetros. España y Francia: 0/0; Portugal: combustión 25 ºC (ISO 13443/96); UE (EN 16726): 15/15.
# UE = EN 16726. El Wobbe se expresa a 15/15 (lo lleva su propia condicion_referencia);
# concentraciones y fracciones molares: equivalentes a 0/0 (comparables directamente).
_NOTACION_PAIS = {"ES": "(0/0)", "PT": "(25/0)", "FR": "(0/0)", "UE": "(0/0)",
                  "IT": "(15/15)", "DE": "(25/0)", "NL": "(25/0)", "BE": "(25/0)",
                  "NOR": "(25/0)", "PL": "(25/0)", "DK": "(25/0)", "HU": "(25/0)", "AT": "(25/0)", "CH": "(25/0)", "CZ": "(15/15)",
                  "GR": "(25/0)", "IE": "(15/15)", "RO": "(15/15)", "SK": "(25/20)", "TR": "(15/15)", "GB": "(15/15)"}

# Código de unidad de la ontología -> símbolo legible (y convertible por el conversor)
_UNIDAD_DISPLAY = {
    "kWh_per_nm3": "kWh/m³", "MJ_per_nm3": "MJ/m³", "kcal_per_nm3": "kcal/m³",
    "mg_per_nm3": "mg/Nm³", "mg_per_sm3": "mg/sm³", "g_per_nm3": "g/Nm³",
    "pct_mol": "% molar", "pct_vol": "% vol", "ppm_vol": "ppm",
    "umol_per_mol": "μmol/mol", "mg_per_kg": "mg/kg",
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


def url_de(fuente: Optional[Dict[str, Any]]) -> str:
    """URL oficial CANÓNICA de una fuente (única para descarga y cita).

    Fuente ÚNICA de verdad: el campo `url` de la ontología (data/ontologia/). Los
    campos antiguos (`url_pdf`/`url_eurlex`/`url_enagas`) se mantienen solo como
    respaldo retrocompatible. Este mismo enlace lo usan `actualizar_fuentes.py`
    (descarga del PDF) y la comparativa (cita), de modo que SIEMPRE coinciden.
    """
    g = fuente or {}
    return (g.get("url") or g.get("url_pdf") or g.get("url_eurlex")
            or g.get("url_enagas") or "")


def _cita(fuente_code: Optional[str], articulo: Optional[str]) -> Dict[str, str]:
    g = _glosario().get(fuente_code, {})
    url = url_de(g)
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


def _limite_ontologia(slug: str, pais: str, tipo_gas: str = "gas_natural") -> Optional[Dict[str, Any]]:
    """Único punto donde se elige el árbol de parámetros y la jurisdicción por tipo de gas.
    Biometano e hidrógeno se leen POR JURISDICCIÓN (ES/PT/FR/UE), igual que el gas natural:
    cada celda tiene su valor y su fuente propios (corpus jul-2026; ver sección correspondiente)."""
    onto = cargar_ontologia()
    if tipo_gas == "biometano":
        params = onto.get("parametros_biometano") or {}
        key = _PARAM_A_ONTO_BIOMETANO.get(slug)
        cod_q = _PAIS_A_CODIGO.get(_norm(pais), pais)
        # La spec UE del biometano vive bajo la clave `UE`. Los alias legados
        # ("biometano"/"en16723") se resuelven AQUÍ, no en `_PAIS_A_CODIGO`, que es
        # un mapa COMPARTIDO: tocarlo haría que gas natural e hidrógeno aceptasen
        # "biometano" como si fuese "UE".
        if cod_q == "EN16723":
            cod_q = "UE"
    elif tipo_gas == "hidrogeno":
        params = onto.get("parametros_hidrogeno") or {}
        key = _PARAM_A_ONTO_HIDROGENO.get(slug)
        cod_q = _PAIS_A_CODIGO.get(_norm(pais), pais)
    else:
        params = onto.get("parametros") or {}
        key = _PARAM_A_ONTO.get(slug)
        cod_q = _PAIS_A_CODIGO.get(_norm(pais))
    if not key or key not in params or not cod_q:
        return None
    return (params[key].get("limites") or {}).get(cod_q)


def _nombre_param(slug: str, tipo_gas: str = "gas_natural") -> str:
    onto = cargar_ontologia()
    seccion = _SECCION_POR_GAS.get(tipo_gas)
    if seccion:
        params = onto.get(seccion[0]) or {}
        key = seccion[1].get(slug)
    else:
        params = onto.get("parametros") or {}
        key = _PARAM_A_ONTO.get(slug)
    if key and key in params:
        return params[key].get("nombre_completo") or key
    return slug


def _record(slug: str, pais: str, lim: Dict[str, Any], tipo_gas: str = "gas_natural") -> Dict[str, Any]:
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
        "parametro": _nombre_param(slug, tipo_gas),
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


def consultar(slug: str, pais: str, tipo_gas: str = "gas_natural") -> Dict[str, Any]:
    """Devuelve {count, matches:[record]} desde la ontología (fuente oficial).

    `tipo_gas` por defecto "gas_natural" → comportamiento idéntico al actual.
    "biometano" consulta la sección `parametros_biometano` (jurisdicciones UE/ES/FR/PT).
    """
    lim = _limite_ontologia(slug, pais, tipo_gas)
    if not lim:
        return {"count": 0, "matches": [], "origen": "oficial"}
    return {"count": 1, "matches": [_record(slug, pais, lim, tipo_gas)], "origen": "oficial"}


def evaluar(slug: str, pais: str, valor: float, unidad: Optional[str] = None,
            tipo_gas: str = "gas_natural") -> Dict[str, Any]:
    """Evalúa cumplimiento contra el límite OFICIAL (ontología), con cita completa."""
    base = consultar(slug, pais, tipo_gas)
    if base["count"] == 0:
        return {"count": 0, "matches": [], "error": "Sin límite oficial para ese parámetro y país."}
    rec = dict(base["matches"][0])
    inf, sup = _num(rec["limite_inferior"]), _num(rec["limite_superior"])
    ureg = rec["unidad"]
    tiene = inf is not None or sup is not None

    valor_comp = valor
    conversion = ""
    compat = True
    # Convierte SIEMPRE a la unidad del registro (aunque no haya límite), para que el
    # valor mostrado lleve el prefijo correcto (p. ej. 0,0123 MWh/m³ → 12,3 kWh/m³).
    if unidad and ureg and _normalizar_unidad(unidad) != _normalizar_unidad(ureg):
        conv = convertir_unidades(valor, unidad, ureg, slug)
        if "valor_convertido" in conv:
            valor_comp = conv["valor_convertido"]
            conversion = conv.get("formula", "")
        elif tiene:
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
