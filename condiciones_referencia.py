"""Conversión determinista entre CONDICIONES DE REFERENCIA (combustión / medición).

Base normativa: UNE-EN ISO 13443:2006 (ISO 13443:1996), Anexo A, **Tabla A.1**
«Factores para la conversión entre condiciones de referencia».

Cada país fija sus condiciones de referencia: temperatura de COMBUSTIÓN (t1) y de
MEDICIÓN/volumen (t2). Para poder comparar el **PCS** o el **Índice de Wobbe** entre
países hay que llevarlos a una base común. Aquí se convierten a las condiciones
**ESPAÑOLAS** (combustión 0 °C, medición 0 °C), que son la base del comparador.

Condiciones por país (normas nacionales vigentes; ISO 13443 Anexo E «Tabla E.1» como
referencia histórica):
    España   : combustión 0 °C,  medición 0 °C
    Portugal : combustión 25 °C, medición 0 °C   <- difiere SOLO en la combustión
    Francia  : combustión 0 °C,  medición 0 °C   (igual que España)
    Italia   : combustión 15 °C, medición 15 °C  (DM 18/05/2018 + Snam, Sm³ a 15 °C)
    Alemania : combustión 25 °C, medición 0 °C   (DVGW G 260, como Portugal)
    P. Bajos : combustión 25 °C, medición 0 °C   (Regeling gaskwaliteit, m³(n))
    Bélgica  : combustión 25 °C, medición 0 °C   (Fluxys, m³(n))
    Noruega  : combustión 25 °C, medición 0 °C   (Gassco/Gassled, Nm³)
    Polonia  : combustión 25 °C, medición 0 °C   (Rozporządzenie, Rozdział 8: warunki
               odniesienia 298,15 K / 273,15 K; concentraciones a 0 °C)
    Dinamarca: combustión 25 °C, medición 0 °C   (BEK nr 230, Nm³)
    Hungría  : combustión 25 °C, medición 0 °C   (Decreto 19/2009/ÜKSZ: Wobbe y PCS @25/0; conc. 0 °C)
    Austria  : combustión 25 °C, medición 0 °C   (ÖVGW G B210; vol. Nm³ 0 °C)
    Suiza    : combustión 25 °C, medición 0 °C   (SVGW G18)
    Chequia  : combustión 15 °C, medición 15 °C  (NET4GAS; conc. a 15 °C)
    Grecia   : combustión 25 °C, medición 0 °C   (DESFA, Nm³)
    Irlanda  : combustión 15 °C, medición 15 °C  (GNI Code; conc. a 15 °C)
    Rumanía  : combustión 15 °C, medición 15 °C  (ANRE; PCS en kcal)
    Eslovaquia: combustión 25 °C, medición 20 °C (eustream; ATÍPICO, Anexo B)
    Turquía  : combustión 15 °C, medición 15 °C  (BOTAŞ; kcal/m³)
    R. Unido : combustión 15 °C, medición 15 °C  (GS(M)R; conc. a 15 °C)
    UE (ISO) : combustión 15 °C, medición 15 °C
NOTA: la Tabla E.1 (1996) listaba Italia como 25/0, pero su normativa vigente usa las
condiciones estándar ISO 15/15; por eso Italia se trata como 15/15.

Como España, Portugal y Francia miden el volumen a 0 °C, la ÚNICA diferencia entre
Portugal y España es la temperatura de combustión (25 °C vs 0 °C). Por eso solo
cambian las propiedades que dependen de la combustión: PCS, PCI e Índice de Wobbe.
El resto (concentraciones en mg/Nm³, % mol, ppm; densidad relativa; puntos de rocío)
se mide a 0 °C en ambos países y NO necesita ajuste.

Cero alucinaciones: los factores normativos (Tabla A.1) viven en un ÚNICO sitio,
`conversor_unidades._TABLA_A1`. Este módulo solo resuelve País -> condiciones y
DELEGA el cálculo del factor en `conversor_unidades.convertir_condiciones_referencia`.
No se calcula ni se copia nada "de memoria".
"""
import unicodedata
from typing import Any, Dict

from conversor_unidades import convertir_condiciones_referencia as _conv_cond_ref

# (t1 combustión, t2 medición) en °C, por país (clave normalizada sin acentos).
CONDICIONES_PAIS = {
    "espana": (0, 0),
    "portugal": (25, 0),
    "francia": (0, 0),
    "ue": (15, 15),      # EN 16726: Wobbe en condiciones estándar 15 ºC / 15 ºC
    "europa": (15, 15),
    "italia": (15, 15),  # DM 18/05/2018 + Snam: condiciones estándar ISO 13443 (15 ºC / 15 ºC), Sm³
    "alemania": (25, 0), # DVGW G 260: combustión 25 ºC, volumen Normbedingungen 0 ºC
    "paises bajos": (25, 0),  # Regeling gaskwaliteit: combustión 25 ºC (298,15 K), volumen m³(n) 0 ºC
    "holanda": (25, 0),
    "belgica": (25, 0),  # Fluxys: combustión 25 ºC, volumen m³(n) 0 ºC
    "noruega": (25, 0),  # Gassco/Gassled: combustión 25 ºC, volumen Nm³ 0 ºC
    "polonia": (25, 0),  # Rozporządzenie (Rozdział 8): warunki odniesienia = combustión 298,15 K (25 ºC), volumen 273,15 K (0 ºC) → @25/0; concentraciones a 0 ºC (cf. nota verificada de la ontología)
    "dinamarca": (25, 0),  # BEK 230: combustión 25 ºC, volumen Nm³ 0 ºC → 25/0
    "hungria": (25, 0),    # Decreto 19/2009 / ÜKSZ: Wobbe y égéshő (PCS) @25/0; concentraciones a 0 ºC
    "austria": (25, 0),    # ÖVGW G B210: volumen Nm³ 0 ºC (E-Control); combustión 25 ºC (ISO 6976)
    "suiza": (25, 0),      # SVGW G18: combustión 25 ºC, volumen Nm³ 0 ºC
    "chequia": (15, 15),   # NET4GAS: t1=t2=15 ºC (ČSN EN ISO 6976); conc. a 15 ºC
    "grecia": (25, 0),     # DESFA: Nm³ 0 ºC, combustión 25 ºC
    "irlanda": (15, 15),   # GNI Code: 15 ºC y 101,325 kPa (Real Gross Dry)
    "rumania": (15, 15),   # ANRE: combustión 15 ºC, volumen 15 ºC
    "eslovaquia": (25, 20), # eustream: combustión 25 ºC, VOLUMEN 20 ºC (atípico → Anexo B)
    "turquia": (15, 15),   # BOTAŞ: 15 ºC; Wobbe/PCS en kcal/m³
    "reino unido": (15, 15), # GS(M)R: reference conditions 15 ºC y 1,01325 bar
}

# Parámetros que dependen de la temperatura de COMBUSTIÓN (los únicos que cambian).
_PARAMETROS_COMBUSTION = {"pcs", "wobbe", "pci"}

_FUENTE = "UNE-EN ISO 13443:2006 (ISO 13443:1996), Anexo A, Tabla A.1"


def _norm(s: Any) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


def _slug_parametro(parametro: str) -> str:
    """Reduce el nombre del parámetro a 'pcs' / 'wobbe' / 'pci' (o '' si no aplica)."""
    p = _norm(parametro)
    if "wobbe" in p:
        return "wobbe"
    if "pci" in p or "inferior" in p:
        return "pci"
    if "pcs" in p or "superior" in p or "calorific" in p or "poder calor" in p:
        return "pcs"
    return p


def convertir_a_condiciones_espana(valor: float, parametro: str, pais_origen: str) -> Dict[str, Any]:
    """Lleva `valor` (de `parametro` en `pais_origen`) a las condiciones españolas.

    Devuelve un dict con valor_convertido, factor, fórmula y la cita de la Tabla A.1.
    Si el parámetro no depende de la combustión, devuelve el valor sin cambio.
    """
    cod = _norm(pais_origen)
    cond = CONDICIONES_PAIS.get(cod)
    if cond is None:
        return {
            "error": f"No conozco las condiciones de referencia de '{pais_origen}'.",
            "paises_conocidos": ["España", "Portugal", "Francia", "Italia", "Alemania", "Países Bajos", "Bélgica", "Noruega", "Polonia", "Dinamarca", "Hungría", "Austria", "Suiza", "Chequia", "Grecia", "Irlanda", "Rumanía", "Eslovaquia", "Turquía", "Reino Unido", "UE"],
        }

    slug = _slug_parametro(parametro)
    cond_es = (0, 0)
    cond_origen_txt = f"combustión {cond[0]} °C, medición {cond[1]} °C"
    cond_es_txt = "combustión 0 °C, medición 0 °C (España)"

    # Parámetro que no depende de la temperatura de combustión, o país ya en base española.
    if slug not in _PARAMETROS_COMBUSTION or cond == cond_es:
        motivo = (
            "Mismas condiciones de referencia que España." if cond == cond_es
            else "El parámetro se mide a 0 °C y no depende de la temperatura de combustión."
        )
        return {
            "valor_original": valor,
            "valor_convertido": round(float(valor), 6),
            "factor": 1.0,
            "parametro": slug or parametro,
            "pais_origen": pais_origen,
            "condiciones_origen": cond_origen_txt,
            "condiciones_destino": cond_es_txt,
            "sin_cambio": True,
            "motivo": motivo,
            "fuente": _FUENTE,
        }

    # Delega en el motor unificado: para estos pares devuelve el factor LITERAL de la
    # Tabla A.1 (normativo). La fuente normativa vive en un único sitio (_TABLA_A1).
    res = _conv_cond_ref(valor, slug, cond[0], cond[1], 0, 0)
    factor = res["factor"]
    return {
        "valor_original": valor,
        "valor_convertido": res["valor_convertido"],
        "factor": factor,
        "parametro": slug,
        "pais_origen": pais_origen,
        "condiciones_origen": cond_origen_txt,
        "condiciones_destino": cond_es_txt,
        "sin_cambio": False,
        "formula": f"valor(España) = valor({pais_origen}) × {factor}",
        "fuente": res.get("base_normativa", _FUENTE),
    }


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    casos = [
        (13.381, "wobbe", "Portugal"),   # Wobbe PT (ya en kWh/m³) -> España
        (57.66, "pcs", "Portugal"),
        (15.0, "o2", "Portugal"),        # no depende de combustión -> sin cambio
        (13.5, "wobbe", "Francia"),      # misma base que España -> sin cambio
    ]
    for c in casos:
        print(c, "->", convertir_a_condiciones_espana(*c))
