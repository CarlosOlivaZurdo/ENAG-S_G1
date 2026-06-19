"""Conversor determinista de unidades para calidad de gas natural.

Herramienta de CERO ALUCINACIONES: todas las conversiones se calculan con fórmulas
matemáticas exactas en Python. El modelo de lenguaje NUNCA debe calcular una
conversión por su cuenta; debe invocar siempre `convertir_unidades`.
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
    s = s.replace(" ", "")
    s = s.replace("³", "3").replace("²", "2").replace("^", "")
    s = s.replace("º", "°")
    return s


# Conjuntos de alias por unidad (tras normalizar)
_MJ = {"mj/m3", "mj/nm3", "mj"}
_KWH = {"kwh/m3", "kwh/nm3", "kwh"}
_KELVIN = {"k", "kelvin", "°k"}
_CELSIUS = {"c", "°c", "celsius"}
_FAHRENHEIT = {"f", "°f", "fahrenheit"}
_MG_NM3 = {"mg/nm3"}                                  # masa por Nm³ (0 °C)
_MG_SM3 = {"mg/m3", "mg/sm3", "mg/m3(15)", "mg/m315", "mg/m3@15"}  # masa por m³ estándar (15 °C)
_PPM = {"ppm", "ppmv", "ppm(vol)", "ppmvol", "ppm(mol)", "ppmmol"}


def _masa_molar(parametro: str, masa_molar: Optional[float]) -> Optional[float]:
    """Devuelve la masa molar (g/mol): explícita si se pasa, o por parámetro."""
    if masa_molar is not None:
        return float(masa_molar)
    return MASAS_MOLARES.get(_norm_txt(parametro))


def convertir_unidades(
    valor: float,
    unidad_origen: str,
    unidad_destino: str,
    parametro: str = "",
    masa_molar: Optional[float] = None,
) -> Dict[str, Any]:
    """ÚNICA VÍA AUTORIZADA para convertir unidades de energía, temperatura y concentración.

    ⚠ INSTRUCCIÓN PARA EL MODELO DE LENGUAJE ⚠
    Esta herramienta es la ÚNICA forma permitida de realizar conversiones de
    unidades en este sistema. NUNCA calcules, estimes ni "recuerdes" de memoria una
    conversión de energía (MJ/m³, kWh/m³), temperatura (K, °C, °F) o concentración
    (mg/Nm³, mg/m³ a 15 °C, ppm). Si una consulta requiere normalizar o convertir
    cualquiera de estas magnitudes, DEBES invocar SIEMPRE `convertir_unidades` y usar
    EXCLUSIVAMENTE el valor que devuelve. Si la conversión no está soportada o falta
    la masa molar necesaria, la función devuelve un error explícito: en ese caso NO
    inventes el resultado, comunica que no es convertible de forma determinista.

    Conversiones soportadas (deterministas y exactas):
      • Energía:        MJ/m³  ↔ kWh/m³     (÷ 3.6 / × 3.6)
      • Temperatura:    K      ↔ °C         (- 273.15 / + 273.15)
      • Temperatura:    °F     ↔ °C         ((x-32)·5/9 / x·9/5+32)
      • Concentración:  mg/m³(15 °C) ↔ mg/Nm³(0 °C)   (× 1.0549 / × 0.9479)
      • Concentración:  mg/Nm³ ↔ ppm(vol)  (requiere masa molar del componente:
                        ppm = mg/Nm³ · 22.414 / M ; mg/Nm³ = ppm · M / 22.414)

    Parámetros
    ----------
    valor : float
        Magnitud numérica a convertir.
    unidad_origen, unidad_destino : str
        Unidades de partida y de llegada (p.ej. "mg/Nm³", "ppm", "MJ/m³", "°F").
    parametro : str, opcional
        Parámetro de calidad asociado (p.ej. "PCS", "H2S", "O2"). Para las
        conversiones mg/Nm³ ↔ ppm se usa para deducir la masa molar (H2S=34.08,
        CO2=44.01, O2=32.00, mercaptanos/azufre "como S"=32.06, …).
    masa_molar : float, opcional
        Masa molar en g/mol del componente. Tiene prioridad sobre `parametro`. Úsala
        si el componente no está en la tabla interna.

    Devuelve
    --------
    dict
        Éxito: {valor_original, unidad_origen, valor_convertido, unidad_destino,
                parametro, formula[, masa_molar_g_mol]}
        Error: {error, valor_original, unidad_origen, unidad_destino,
                conversiones_soportadas}
    """
    o = _normalizar_unidad(unidad_origen)
    d = _normalizar_unidad(unidad_destino)

    valor_convertido: Optional[float] = None
    formula: Optional[str] = None
    masa_usada: Optional[float] = None

    # --- Energía: MJ/m³ <-> kWh/m³ ---
    if o in _MJ and d in _KWH:
        valor_convertido = valor / 3.6
        formula = "kWh/m³ = MJ/m³ / 3.6"
    elif o in _KWH and d in _MJ:
        valor_convertido = valor * 3.6
        formula = "MJ/m³ = kWh/m³ × 3.6"

    # --- Temperatura: Kelvin <-> Celsius ---
    elif o in _KELVIN and d in _CELSIUS:
        valor_convertido = valor - 273.15
        formula = "°C = K - 273.15"
    elif o in _CELSIUS and d in _KELVIN:
        valor_convertido = valor + 273.15
        formula = "K = °C + 273.15"

    # --- Temperatura: Fahrenheit <-> Celsius ---
    elif o in _FAHRENHEIT and d in _CELSIUS:
        valor_convertido = (valor - 32) * 5 / 9
        formula = "°C = (°F - 32) × 5/9"
    elif o in _CELSIUS and d in _FAHRENHEIT:
        valor_convertido = valor * 9 / 5 + 32
        formula = "°F = °C × 9/5 + 32"

    # --- Concentración: renormalización de condiciones de volumen (15 °C <-> 0 °C) ---
    elif o in _MG_SM3 and d in _MG_NM3:
        valor_convertido = valor * FACTOR_SM3_A_NM3
        formula = "mg/Nm³(0 °C) = mg/m³(15 °C) × (288,15/273,15) ≈ × 1,0549"
    elif o in _MG_NM3 and d in _MG_SM3:
        valor_convertido = valor / FACTOR_SM3_A_NM3
        formula = "mg/m³(15 °C) = mg/Nm³(0 °C) × (273,15/288,15) ≈ × 0,9479"

    # --- Concentración: másica <-> volumétrica (requiere masa molar) ---
    elif o in _MG_NM3 and d in _PPM:
        masa_usada = _masa_molar(parametro, masa_molar)
        if masa_usada is None:
            return _error_masa_molar(valor, unidad_origen, unidad_destino, parametro)
        valor_convertido = valor * VOLUMEN_MOLAR_NM3 / masa_usada
        formula = f"ppm(vol) = mg/Nm³ × 22,414 / M  (M = {masa_usada} g/mol)"
    elif o in _PPM and d in _MG_NM3:
        masa_usada = _masa_molar(parametro, masa_molar)
        if masa_usada is None:
            return _error_masa_molar(valor, unidad_origen, unidad_destino, parametro)
        valor_convertido = valor * masa_usada / VOLUMEN_MOLAR_NM3
        formula = f"mg/Nm³ = ppm(vol) × M / 22,414  (M = {masa_usada} g/mol)"

    # --- Caso no soportado: NO se inventa ningún resultado ---
    if valor_convertido is None:
        return {
            "error": (
                f"Conversión no soportada de '{unidad_origen}' a '{unidad_destino}'. "
                "No se realiza ninguna conversión para evitar resultados inventados."
            ),
            "valor_original": valor,
            "unidad_origen": unidad_origen,
            "unidad_destino": unidad_destino,
            "conversiones_soportadas": _SOPORTADAS,
        }

    resultado: Dict[str, Any] = {
        "valor_original": valor,
        "unidad_origen": unidad_origen,
        "valor_convertido": round(valor_convertido, 6),
        "unidad_destino": unidad_destino,
        "parametro": parametro,
        "formula": formula,
    }
    if masa_usada is not None:
        resultado["masa_molar_g_mol"] = masa_usada
    return resultado


_SOPORTADAS = [
    "MJ/m³ ↔ kWh/m³",
    "K ↔ °C",
    "°F ↔ °C",
    "mg/m³(15 °C) ↔ mg/Nm³(0 °C)",
    "mg/Nm³ ↔ ppm(vol) (requiere masa molar)",
]


def _error_masa_molar(valor, unidad_origen, unidad_destino, parametro):
    return {
        "error": (
            "Conversión mg/Nm³ ↔ ppm no realizada: falta la masa molar del componente. "
            f"El parámetro '{parametro}' no está en la tabla; indica `masa_molar` (g/mol) "
            "o un parámetro reconocido (H2S, CO2, O2, mercaptanos…). No se inventa el valor."
        ),
        "valor_original": valor,
        "unidad_origen": unidad_origen,
        "unidad_destino": unidad_destino,
        "componentes_con_masa_molar": sorted(set(MASAS_MOLARES.keys())),
    }


# ---------------------------------------------------------------------------
# Wrapper OPCIONAL de LangChain (@tool).
# El proyecto usa OpenAI function-calling, por lo que la función pura de arriba es
# la que se integra en api.py. Este wrapper solo se crea si LangChain está
# instalado, para compatibilidad con entornos que usen el decorador @tool.
# ---------------------------------------------------------------------------
try:  # pragma: no cover
    from langchain_core.tools import tool

    convertir_unidades_tool = tool(convertir_unidades)
except Exception:  # LangChain no instalado -> el proyecto sigue funcionando
    convertir_unidades_tool = None


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # consola Windows -> UTF-8
    except Exception:
        pass
    print(convertir_unidades(47.74, "MJ/m³", "kWh/m³", "PCS"))
    print(convertir_unidades(288.15, "K", "°C", "Punto de rocío"))
    print(convertir_unidades(59, "°F", "°C", "Punto de rocío"))
    print(convertir_unidades(15, "mg/Nm³", "ppm", "H2S"))            # 15 mg/Nm³ -> ~9.87 ppm
    print(convertir_unidades(12, "mg/m³", "mg/Nm³", "H2S"))          # 12 @15°C -> 12.66 @0°C
    print(convertir_unidades(10, "ppm", "mg/Nm³", "", masa_molar=34.08))  # masa molar explícita
    print(convertir_unidades(10, "mg/Nm³", "ppm", "compuesto raro")) # error: falta masa molar
    print(convertir_unidades(10, "bar", "Pa", "Presión"))            # error: no soportada
