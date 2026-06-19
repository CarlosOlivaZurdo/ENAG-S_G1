"""Conversor determinista de unidades para calidad de gas natural.

Herramienta de CERO ALUCINACIONES: todas las conversiones se calculan con fórmulas
matemáticas exactas en Python. El modelo de lenguaje NUNCA debe calcular una
conversión por su cuenta; debe invocar siempre `convertir_unidades`.

Convención de este proyecto (las tablas normativas están a 0 °C y 1,01325 bar):
  • `mg/m³` ≡ `mg/Nm³`  → condiciones NORMALES (0 °C). Son equivalentes.
  • `mg/sm³`, `mg/m³(15)`, `mg/m³@15` → condiciones ESTÁNDAR (15 °C), solo si se marca.
"""
import unicodedata
from typing import Any, Dict, Optional

# Volumen molar de un gas ideal a 0 °C y 1,01325 bar (Nm³): 22,414 L/mol.
VOLUMEN_MOLAR_NM3 = 22.414

# Factor de renormalización de volumen de m³ estándar (15 °C) a Nm³ (0 °C).
FACTOR_SM3_A_NM3 = 288.15 / 273.15  # ≈ 1.0549

# Masas molares (g/mol) para convertir entre mg/Nm³ y ppm(vol).
MASAS_MOLARES = {
    "h2s": 34.08, "h2s+cos": 34.08, "sulfurodehidrogeno": 34.08, "acidosulfhidrico": 34.08,
    "co2": 44.01, "dioxidodecarbono": 44.01,
    "o2": 32.00, "oxigeno": 32.00,
    "cos": 60.07,
    "rsh": 32.06, "mercaptanos": 32.06, "stotal": 32.06, "s": 32.06, "azufre": 32.06,
    "ch4": 16.04, "metano": 16.04,
}


def _norm_txt(s: Any) -> str:
    """Minúsculas sin acentos ni espacios (para emparejar parámetros)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return s.lower().replace(" ", "")


def _normalizar_unidad(unidad: str) -> str:
    """Normaliza la cadena de unidad para poder compararla de forma robusta."""
    s = str(unidad).strip().lower()
    # quitar acentos españoles conservando símbolos (°, /, %)
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        s = s.replace(a, b)
    s = s.replace("³", "3").replace("²", "2").replace("^", "")
    s = s.replace("º", "°")
    s = s.replace(" ", "").replace("(", "").replace(")", "")
    return s


# Conjuntos de alias por unidad (tras normalizar)
_MJ = {"mj/m3", "mj/nm3", "mj"}
_KWH = {"kwh/m3", "kwh/nm3", "kwh"}
_KELVIN = {"k", "kelvin", "°k"}
_CELSIUS = {"c", "°c", "celsius", "°gradoscentigrados", "gradoscentigrados"}
_FAHRENHEIT = {"f", "°f", "fahrenheit"}
# Concentración másica en condiciones NORMALES (0 °C). En este proyecto mg/m³ ≡ mg/Nm³.
_CONC_NORMAL = {"mg/nm3", "mg/m3", "mgs/nm3", "mgs/m3", "mg/m3n", "mg/m3(n)"}
# Concentración másica en condiciones ESTÁNDAR (15 °C), SOLO si se marca explícitamente.
_CONC_STD15 = {"mg/sm3", "mgs/sm3", "mg/m3(15)", "mg/m315", "mg/m3@15", "mg/m3std"}
# Fracción volumétrica/molar
_PCT = {"%", "%mol", "%molar", "%vol", "%v", "%m"}
_PPM = {"ppm", "ppmv", "ppm(vol)", "ppmvol", "ppm(mol)", "ppmmol"}

# Familias en las que origen y destino son la MISMA magnitud equivalente (factor 1).
_FAMILIAS_IDENTIDAD = (_MJ, _KWH, _KELVIN, _CELSIUS, _FAHRENHEIT, _PCT, _PPM, _CONC_NORMAL)

_SOPORTADAS = [
    "MJ/m³ ↔ kWh/m³",
    "K ↔ °C ↔ °F",
    "mg/m³ ≡ mg/Nm³ (0 °C)",
    "mg/m³(15 °C) ↔ mg/Nm³(0 °C)",
    "mg/Nm³ ↔ ppm (requiere masa molar)",
    "% ↔ ppm",
]


def _masa_molar(parametro: str, masa_molar: Optional[float]) -> Optional[float]:
    """Devuelve la masa molar (g/mol): explícita si se pasa, o por parámetro."""
    if masa_molar is not None:
        return float(masa_molar)
    return MASAS_MOLARES.get(_norm_txt(parametro))


def _ok(valor_orig, valor_conv, uo, ud, parametro, formula, masa=None) -> Dict[str, Any]:
    r = {
        "valor_original": valor_orig,
        "unidad_origen": uo,
        "valor_convertido": round(valor_conv, 6),
        "unidad_destino": ud,
        "parametro": parametro,
        "formula": formula,
    }
    if masa is not None:
        r["masa_molar_g_mol"] = masa
    return r


def _error_no_soportada(valor, uo, ud) -> Dict[str, Any]:
    return {
        "error": (
            f"Conversión no soportada de '{uo}' a '{ud}'. "
            "No se realiza ninguna conversión para evitar resultados inventados."
        ),
        "valor_original": valor,
        "unidad_origen": uo,
        "unidad_destino": ud,
        "conversiones_soportadas": _SOPORTADAS,
    }


def _error_masa_molar(valor, uo, ud, parametro) -> Dict[str, Any]:
    return {
        "error": (
            "Conversión mg/Nm³ ↔ ppm no realizada: falta la masa molar del componente. "
            f"El parámetro '{parametro}' no está en la tabla; indica `masa_molar` (g/mol) "
            "o un parámetro reconocido (H2S, CO2, O2, mercaptanos…). No se inventa el valor."
        ),
        "valor_original": valor,
        "unidad_origen": uo,
        "unidad_destino": ud,
        "componentes_con_masa_molar": sorted(set(MASAS_MOLARES.keys())),
    }


def convertir_unidades(
    valor: float,
    unidad_origen: str,
    unidad_destino: str,
    parametro: str = "",
    masa_molar: Optional[float] = None,
) -> Dict[str, Any]:
    """ÚNICA VÍA AUTORIZADA para convertir unidades de energía, temperatura y concentración.

    ⚠ INSTRUCCIÓN PARA EL MODELO DE LENGUAJE ⚠
    Esta herramienta es la ÚNICA forma permitida de realizar conversiones de unidades en
    este sistema. NUNCA calcules, estimes ni "recuerdes" de memoria una conversión de
    energía (MJ/m³, kWh/m³), temperatura (K, °C, °F) o concentración (mg/m³, mg/Nm³, ppm,
    % molar). Si una consulta requiere normalizar o convertir cualquiera de estas
    magnitudes, DEBES invocar SIEMPRE `convertir_unidades` y usar EXCLUSIVAMENTE el valor
    que devuelve. Si la conversión no está soportada o falta la masa molar necesaria, la
    función devuelve un error explícito: en ese caso NO inventes el resultado.

    Conversiones soportadas (deterministas y exactas):
      • Energía:        MJ/m³  ↔ kWh/m³            (÷ 3.6 / × 3.6)
      • Temperatura:    K ↔ °C ↔ °F                (offsets exactos)
      • Concentración:  mg/m³ ≡ mg/Nm³ (0 °C)      (equivalentes)
      • Concentración:  mg/m³(15 °C) ↔ mg/Nm³(0 °C) (× 1.0549 / × 0.9479)
      • Concentración:  mg/Nm³ ↔ ppm(vol)          (requiere masa molar M del componente)
      • Fracción:       % ↔ ppm                    (× 10000 / ÷ 10000)

    Parámetros
    ----------
    valor : float — magnitud a convertir.
    unidad_origen, unidad_destino : str — unidades de partida y llegada.
    parametro : str, opcional — parámetro de calidad (PCS, Wobbe, H2S, O2…); para
        mg/Nm³ ↔ ppm se usa para deducir la masa molar.
    masa_molar : float, opcional — masa molar (g/mol); tiene prioridad sobre `parametro`.

    Devuelve
    --------
    dict con {valor_original, unidad_origen, valor_convertido, unidad_destino, parametro,
    formula[, masa_molar_g_mol]} o, si no es posible, {error, ...}.
    """
    o = _normalizar_unidad(unidad_origen)
    d = _normalizar_unidad(unidad_destino)

    # 0) Identidad exacta o unidades equivalentes dentro de la misma familia (factor 1).
    if o == d:
        return _ok(valor, valor, unidad_origen, unidad_destino, parametro, "Sin conversión (misma unidad)")
    for fam in _FAMILIAS_IDENTIDAD:
        if o in fam and d in fam:
            return _ok(valor, valor, unidad_origen, unidad_destino, parametro,
                       "Sin conversión (unidades equivalentes)")

    # --- Energía: MJ/m³ <-> kWh/m³ ---
    if o in _MJ and d in _KWH:
        return _ok(valor, valor / 3.6, unidad_origen, unidad_destino, parametro, "kWh/m³ = MJ/m³ / 3.6")
    if o in _KWH and d in _MJ:
        return _ok(valor, valor * 3.6, unidad_origen, unidad_destino, parametro, "MJ/m³ = kWh/m³ × 3.6")

    # --- Temperatura ---
    if o in _KELVIN and d in _CELSIUS:
        return _ok(valor, valor - 273.15, unidad_origen, unidad_destino, parametro, "°C = K - 273.15")
    if o in _CELSIUS and d in _KELVIN:
        return _ok(valor, valor + 273.15, unidad_origen, unidad_destino, parametro, "K = °C + 273.15")
    if o in _FAHRENHEIT and d in _CELSIUS:
        return _ok(valor, (valor - 32) * 5 / 9, unidad_origen, unidad_destino, parametro, "°C = (°F - 32) × 5/9")
    if o in _CELSIUS and d in _FAHRENHEIT:
        return _ok(valor, valor * 9 / 5 + 32, unidad_origen, unidad_destino, parametro, "°F = °C × 9/5 + 32")
    if o in _KELVIN and d in _FAHRENHEIT:
        return _ok(valor, (valor - 273.15) * 9 / 5 + 32, unidad_origen, unidad_destino, parametro, "°F = (K - 273.15) × 9/5 + 32")
    if o in _FAHRENHEIT and d in _KELVIN:
        return _ok(valor, (valor - 32) * 5 / 9 + 273.15, unidad_origen, unidad_destino, parametro, "K = (°F - 32) × 5/9 + 273.15")

    # --- Concentración: estándar 15 °C <-> normal 0 °C ---
    if o in _CONC_STD15 and d in _CONC_NORMAL:
        return _ok(valor, valor * FACTOR_SM3_A_NM3, unidad_origen, unidad_destino, parametro,
                   "mg/Nm³(0 °C) = mg/m³(15 °C) × (288,15/273,15) ≈ × 1,0549")
    if o in _CONC_NORMAL and d in _CONC_STD15:
        return _ok(valor, valor / FACTOR_SM3_A_NM3, unidad_origen, unidad_destino, parametro,
                   "mg/m³(15 °C) = mg/Nm³(0 °C) × (273,15/288,15) ≈ × 0,9479")

    # --- Concentración másica <-> ppm(vol) (requiere masa molar) ---
    if (o in _CONC_NORMAL or o in _CONC_STD15) and d in _PPM:
        m = _masa_molar(parametro, masa_molar)
        if m is None:
            return _error_masa_molar(valor, unidad_origen, unidad_destino, parametro)
        base = valor * FACTOR_SM3_A_NM3 if o in _CONC_STD15 else valor  # llevar a Nm³ (0 °C)
        return _ok(valor, base * VOLUMEN_MOLAR_NM3 / m, unidad_origen, unidad_destino, parametro,
                   f"ppm(vol) = mg/Nm³ × 22,414 / M  (M = {m} g/mol)", masa=m)
    if o in _PPM and (d in _CONC_NORMAL or d in _CONC_STD15):
        m = _masa_molar(parametro, masa_molar)
        if m is None:
            return _error_masa_molar(valor, unidad_origen, unidad_destino, parametro)
        base = valor * m / VOLUMEN_MOLAR_NM3  # mg/Nm³ (0 °C)
        conv = base / FACTOR_SM3_A_NM3 if d in _CONC_STD15 else base
        return _ok(valor, conv, unidad_origen, unidad_destino, parametro,
                   f"mg/Nm³ = ppm(vol) × M / 22,414  (M = {m} g/mol)", masa=m)

    # --- Fracción: % <-> ppm ---
    if o in _PCT and d in _PPM:
        return _ok(valor, valor * 10000, unidad_origen, unidad_destino, parametro, "ppm = % × 10.000")
    if o in _PPM and d in _PCT:
        return _ok(valor, valor / 10000, unidad_origen, unidad_destino, parametro, "% = ppm / 10.000")

    # --- No soportada: NO se inventa ningún resultado ---
    return _error_no_soportada(valor, unidad_origen, unidad_destino)


# ---------------------------------------------------------------------------
# Wrapper OPCIONAL de LangChain (@tool). El proyecto usa OpenAI function-calling;
# este wrapper solo se crea si LangChain está instalado.
# ---------------------------------------------------------------------------
try:  # pragma: no cover
    from langchain_core.tools import tool

    convertir_unidades_tool = tool(convertir_unidades)
except Exception:
    convertir_unidades_tool = None


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    casos = [
        (47.74, "MJ/m³", "kWh/m³", "PCS"),
        (14, "kWh/m³", "MJ/m³", "Wobbe"),
        (288.15, "K", "°C", "Punto de rocío"),
        (59, "°F", "°C", "Punto de rocío"),
        (5, "mg/m³", "mg/Nm³", "H2S"),           # equivalentes -> 5
        (15, "mg/Nm³", "ppm", "H2S"),            # -> ~9.87 ppm
        (12, "mg/sm³", "mg/Nm³", "H2S"),         # 15°C -> 0°C -> 12.66
        (50, "ppm", "% molar", "O2"),            # -> 0.005 %
        (0.01, "% molar", "ppm", "O2"),          # -> 100 ppm
        (10, "bar", "Pa", "Presión"),            # no soportada
    ]
    for c in casos:
        print(c, "->", convertir_unidades(*c))
