"""Conversión determinista entre CONDICIONES DE REFERENCIA (combustión / medición).

Base normativa: UNE-EN ISO 13443:2006 (ISO 13443:1996), Anexo A, **Tabla A.1**
«Factores para la conversión entre condiciones de referencia».

Cada país fija sus condiciones de referencia: temperatura de COMBUSTIÓN (t1) y de
MEDICIÓN/volumen (t2). Para poder comparar el **PCS** o el **Índice de Wobbe** entre
países hay que llevarlos a una base común. Aquí se convierten a las condiciones
**ESPAÑOLAS** (combustión 0 °C, medición 0 °C), que son la base del comparador.

Condiciones por país (ISO 13443, Anexo E «Tabla E.1» + normas nacionales):
    España   : combustión 0 °C,  medición 0 °C
    Portugal : combustión 25 °C, medición 0 °C   <- difiere SOLO en la combustión
    Francia  : combustión 0 °C,  medición 0 °C   (igual que España)
    UE (ISO) : combustión 15 °C, medición 15 °C

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
            "paises_conocidos": ["España", "Portugal", "Francia", "UE"],
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
