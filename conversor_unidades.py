"""Conversor determinista de unidades para calidad de gas natural.

Herramienta de CERO ALUCINACIONES: todas las conversiones se calculan con fórmulas
matemáticas exactas en Python. El modelo de lenguaje NUNCA debe calcular una
conversión por su cuenta; debe invocar siempre `convertir_unidades`.

Convención de este proyecto (las tablas normativas están a 0 °C y 1,01325 bar):
  • `mg/m³` ≡ `mg/Nm³`  → condiciones NORMALES (0 °C). Son equivalentes.
  • `mg/sm³`, `mg/m³(15)`, `mg/m³@15` → condiciones ESTÁNDAR (15 °C), solo si se marca.
"""
import re
import unicodedata
from typing import Any, Dict, Optional, Tuple

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

# Energía / densidad de energía: factor a MJ (misma base de volumen).
# En este proyecto m³ ≡ Nm³ (0 °C) para energía, así que la base de volumen es equivalente.
_ENERGIA_A_MJ = {
    "wh": 0.0036, "kwh": 3.6, "mwh": 3600.0, "gwh": 3_600_000.0,
    "j": 1e-6, "kj": 1e-3, "mj": 1.0, "gj": 1000.0,
    # Caloría térmica (Turquía y Rumanía expresan PCS/Wobbe en kcal/m³). 1 kcal = 4,1868 kJ.
    "cal": 4.1868e-6, "kcal": 4.1868e-3, "mcal": 4.1868, "gcal": 4186.8,
}
_VOL_ENERGIA = {"", "m3", "nm3"}


def _factor_energia(u: str) -> Optional[float]:
    """Si `u` (ya normalizada) es energía o densidad de energía, devuelve su factor a MJ.

    Acepta Wh/kWh/MWh/GWh/J/kJ/MJ/GJ, opcionalmente por m³ o Nm³ (equivalentes aquí).
    """
    num, _, den = u.partition("/")
    if den not in _VOL_ENERGIA:
        return None
    return _ENERGIA_A_MJ.get(num)
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
    "Energía: Wh · kWh · MWh · GWh · J · kJ · MJ · GJ (por m³/Nm³)",
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

    # --- Energía: MJ/m³ <-> kWh/m³ (fórmula explícita para el caso más común) ---
    if o in _MJ and d in _KWH:
        return _ok(valor, valor / 3.6, unidad_origen, unidad_destino, parametro, "kWh/m³ = MJ/m³ / 3.6")
    if o in _KWH and d in _MJ:
        return _ok(valor, valor * 3.6, unidad_origen, unidad_destino, parametro, "MJ/m³ = kWh/m³ × 3.6")

    # --- Energía con cualquier prefijo SI: Wh, kWh, MWh, GWh, J, kJ, MJ, GJ ---
    # (p. ej. MWh/m³ → kWh/m³ = × 1000). Misma base de volumen (m³ ≡ Nm³ a 0 °C).
    fo, fd = _factor_energia(o), _factor_energia(d)
    if fo is not None and fd is not None:
        factor = fo / fd
        formula = (
            "Sin conversión (unidades equivalentes)" if factor == 1
            else f"{unidad_destino} = {unidad_origen} × {factor:g}"
        )
        return _ok(valor, valor * factor, unidad_origen, unidad_destino, parametro, formula)

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
                   "mg/Nm³(0 °C) = mg/m³(15 °C) × (288,15/273,15) ≈ × 1,0549 "
                   "(UNE-EN ISO 13443, Tabla A.1, base de volumen)")
    if o in _CONC_NORMAL and d in _CONC_STD15:
        return _ok(valor, valor / FACTOR_SM3_A_NM3, unidad_origen, unidad_destino, parametro,
                   "mg/m³(15 °C) = mg/Nm³(0 °C) × (273,15/288,15) ≈ × 0,9479 "
                   "(UNE-EN ISO 13443, Tabla A.1, base de volumen)")

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
# Condiciones de referencia normalizadas — UNE-EN ISO 13443:2006 (ISO 13443:1996)
#
# El PCS, el PCI y el Índice de Wobbe dependen de la temperatura de COMBUSTIÓN
# (t1) y de la de MEDICIÓN/volumen (t2); el volumen y la densidad solo de t2
# (Anexo C, símbolos). Cada país fija sus propias condiciones (Anexo E, Tabla
# E.1), así que para comparar valores hay que llevarlos a una base común.
#
# Implementación: ecuaciones del Anexo B (B.5–B.21), que convierten cualquier
# condición (t1, t2, p) a las condiciones de referencia normalizadas ISO
# (15 °C, 101,325 kPa). VERIFICADAS de forma exacta contra los ejemplos
# resueltos de la propia norma (cero alucinaciones):
#   • Anexo D, Ejemplo 4 (PCS real volum., B.19):  38,57 → 38,56 MJ/m³
#   • Anexo D, Ejemplo 5 (PCI real volum., B.20):  37,35 × 0,9477 = 35,40 MJ/m³
# El Índice de Wobbe se obtiene de su definición W = PCS / √(densidad relativa),
# usando B.19 y B.7; esto reproduce la línea 21 de la Tabla A.1.
#
# FUENTE ÚNICA: para los pares de condiciones TABULADOS se devuelve el factor
# LITERAL de la Tabla A.1 (Anexo A, NORMATIVO; p. ej. Portugal → España = 1,0026);
# para cualquier otra condición se usan las ecuaciones del Anexo B (informativo).
# `condiciones_referencia.py` (comparador de países) delega aquí, de modo que el
# factor normativo vive en UN SOLO sitio (`_TABLA_A1`). El campo `base_normativa`
# del resultado indica qué anexo se aplicó. Las ecuaciones del Anexo B pueden
# diferir de la tabla en la última cifra (1,0025 vs 1,0026), dentro de la precisión
# declarada por la norma (±0,05 % en propiedades de combustión); por eso la tabla
# tiene prioridad.
# ---------------------------------------------------------------------------

ISO13443_T_REF_K = 288.15      # 15 °C — temperatura de referencia normalizada ISO
ISO13443_P_REF_KPA = 101.325   # presión de referencia normalizada ISO

_FUENTE_ISO13443 = "UNE-EN ISO 13443:2006 (ISO 13443:1996)"

# Parámetros admitidos: dependen de la combustión (t1) o solo de la medición (t2).
_PARAMS_COMBUSTION_13443 = {"pcs", "pci", "wobbe"}
_PARAMS_MEDICION_13443 = {"volumen", "densidad", "densidad_relativa"}

# FUENTE ÚNICA de los factores NORMATIVOS. Valores LITERALES de la Tabla A.1 (Anexo A,
# normativo; gas real, base volumétrica), para los pares de condiciones tabulados a
# 101,325 kPa. Tienen PRIORIDAD sobre las ecuaciones del Anexo B (informativo). Clave:
# (cond_origen, cond_destino), con cond = (t_combustión, t_medición) en °C.
# Cubren los países del proyecto, todos referidos a España (0,0):
#   Portugal (25,0) y Alemania (25,0)  -> factor (25,0)->(0,0)   [Tabla A.1, col. 25:00->00:00]
#   Italia (15,15)  y UE/ISO (15,15)   -> factor (15,15)->(0,0)  [Tabla A.1, col. 15:15->00:00]
#   España (0,0) y Francia (0,0)       -> identidad (factor 1).
# Valores LITERALES de la Tabla A.1 (gas real, base volumétrica): filas 19 (PCS), 20
# (PCI) y 21 (Wobbe). Verificados contra el PDF oficial de la UNE-EN ISO 13443:2006.
# NOTA: la Tabla E.1 (Anexo E, informativo, 1996) listaba Italia como 25:0; la normativa
# italiana VIGENTE (DM 18/05/2018 + Codice di Rete de Snam) usa condiciones estándar ISO
# 15 ºC/15 ºC (Sm³), por eso Italia se trata como (15,15). No cambiar sin re-verificar.
_TABLA_A1 = {
    ((25, 0), (0, 0)): {"pcs": 1.0026, "wobbe": 1.0026, "pci": 1.0003},
    ((15, 15), (0, 0)): {"pcs": 1.0570, "wobbe": 1.0569, "pci": 1.0555},
}


def _factor_tabla_a1(slug: str, cond_o, cond_d) -> Optional[float]:
    """Factor LITERAL de la Tabla A.1 para el par tabulado (o su inverso), o None."""
    directo = _TABLA_A1.get((cond_o, cond_d))
    if directo and slug in directo:
        return directo[slug]
    inverso = _TABLA_A1.get((cond_d, cond_o))
    if inverso and slug in inverso:
        return 1.0 / inverso[slug]
    return None


def _slug_param_13443(parametro: str) -> str:
    """Reduce el nombre del parámetro al slug ISO 13443 (pcs/pci/wobbe/volumen/…)."""
    p = _norm_txt(parametro)
    if "wobbe" in p:
        return "wobbe"
    if "pci" in p or "inferior" in p:
        return "pci"
    if "pcs" in p or "superior" in p or "calorific" in p or "podercalor" in p:
        return "pcs"
    if "densidadrelativa" in p or p in ("d", "dr"):
        return "densidad_relativa"
    if "densidad" in p or "rho" in p:
        return "densidad"
    if "volumen" in p or "volume" in p or p == "v":
        return "volumen"
    return p


def _factor_a_iso_13443(slug: str, t_comb_c: float, t_med_c: float, p_kpa: float) -> Optional[float]:
    """Factor que lleva una propiedad desde (t1, t2, p) a las condiciones ISO.

    Devuelve f tal que  valor(ISO) = valor(t1, t2, p) × f  (gas real).
    None si el parámetro no está soportado. Ecuaciones del Anexo B de ISO 13443.
    """
    T1 = t_comb_c + 273.15   # temperatura de combustión (K)
    T2 = t_med_c + 273.15    # temperatura de medición/volumen (K)
    p = p_kpa
    cP = 1 + 0.000020 * (p - 101.325)       # corrección de presión (gas real)
    cT2 = 1 + 0.000025 * (T2 - 288.15)      # corrección de T de medición (gas real)
    vol_H = (101.325 * T2) / (288.15 * p)   # parte volumétrica de H!/Wobbe (B.16/B.19)
    if slug == "volumen":
        return ((288.15 * p) / (101.325 * T2)) * cP / cT2           # B.5
    if slug == "densidad":
        return vol_H * cT2 / cP                                     # B.6
    if slug == "densidad_relativa":
        return (1 + 0.000014 * (T2 - 288.15)) / cP                  # B.7
    if slug == "pcs":
        return vol_H * (1 + 0.00010 * (T1 - 288.15)) * cT2 / cP     # B.19
    if slug == "pci":
        return vol_H * (1 + 0.00001 * (T1 - 288.15)) * cT2 / cP     # B.20
    if slug == "wobbe":                                             # W = PCS / √d
        f_pcs = vol_H * (1 + 0.00010 * (T1 - 288.15)) * cT2 / cP
        f_d = (1 + 0.000014 * (T2 - 288.15)) / cP
        return f_pcs / (f_d ** 0.5)
    return None


def convertir_condiciones_referencia(
    valor: float,
    parametro: str,
    comb_origen: float,
    med_origen: float,
    comb_destino: float,
    med_destino: float,
    p_origen: float = 101.325,
    p_destino: float = 101.325,
) -> Dict[str, Any]:
    """Convierte una propiedad del gas entre dos CONDICIONES DE REFERENCIA (ISO 13443).

    Lleva `valor` (de `parametro`, en las condiciones de origen — temperatura de
    combustión `comb_origen` y de medición `med_origen`, en °C) a las condiciones de
    destino, aplicando las ecuaciones del Anexo B de la UNE-EN ISO 13443. No realiza
    ninguna conversión de UNIDAD (convierte antes con `convertir_unidades` si hace falta).

    Soporta PCS, PCI e Índice de Wobbe (dependen de combustión y medición) y volumen,
    densidad y densidad relativa (solo medición). Las presiones de referencia son
    101,325 kPa salvo que se indique otra cosa.

    Devuelve dict con valor_convertido, factor, formula y fuente; o {error, ...} si el
    parámetro no está cubierto por la norma (no se inventa ningún resultado).
    """
    slug = _slug_param_13443(parametro)
    if slug not in _PARAMS_COMBUSTION_13443 and slug not in _PARAMS_MEDICION_13443:
        return {
            "error": (
                f"Parámetro '{parametro}' no soportado para conversión de condiciones de "
                "referencia ISO 13443. Soportados: PCS, PCI, Wobbe, volumen, densidad, "
                "densidad relativa. No se realiza ninguna conversión."
            ),
            "valor_original": valor,
            "parametros_soportados": sorted(_PARAMS_COMBUSTION_13443 | _PARAMS_MEDICION_13443),
        }

    cond_o_t = (comb_origen, med_origen)
    cond_d_t = (comb_destino, med_destino)
    presion_iso = (p_origen == ISO13443_P_REF_KPA and p_destino == ISO13443_P_REF_KPA)
    factor_tabla = _factor_tabla_a1(slug, cond_o_t, cond_d_t) if presion_iso else None

    if cond_o_t == cond_d_t and p_origen == p_destino:
        # Mismas condiciones: sin conversión (factor exacto 1).
        factor = 1.0
        base = "Identidad (mismas condiciones de referencia)"
    elif factor_tabla is not None:
        # Par tabulado: factor LITERAL de la Tabla A.1 (Anexo A, normativo). Prioritario.
        factor = factor_tabla
        base = "UNE-EN ISO 13443, Anexo A, Tabla A.1 (normativo)"
    else:
        # Resto de condiciones: ecuaciones del Anexo B (informativo, verificadas vs. Anexo D).
        f_o = _factor_a_iso_13443(slug, comb_origen, med_origen, p_origen)
        f_d = _factor_a_iso_13443(slug, comb_destino, med_destino, p_destino)
        factor = f_o / f_d
        base = "UNE-EN ISO 13443, Anexo B (ecuaciones B.5–B.21)"

    cond_o = f"combustión {comb_origen:g} °C, medición {med_origen:g} °C, {p_origen:g} kPa"
    cond_d = f"combustión {comb_destino:g} °C, medición {med_destino:g} °C, {p_destino:g} kPa"
    return {
        "valor_original": valor,
        "valor_convertido": round(float(valor) * factor, 6),
        "factor": round(factor, 6),
        "parametro": slug,
        "condiciones_origen": cond_o,
        "condiciones_destino": cond_d,
        "formula": f"valor(destino) = valor(origen) × {factor:.6g}",
        "base_normativa": base,
        "fuente": _FUENTE_ISO13443,
    }


# ---------------------------------------------------------------------------
# Parseo y normalización de unidades a partir de texto libre del usuario.
#
# Estas funciones NO realizan ninguna conversión: solo extraen el valor numérico
# y/o la cadena de unidad de un mensaje, y normalizan unidades para poder
# compararlas. Viven aquí (junto a `convertir_unidades`) para centralizar toda
# la lógica de unidades en un único módulo analizable; el chat (api.py) las
# importa en lugar de tener su propia copia.
# ---------------------------------------------------------------------------

# Tokens de unidad que reconocemos al extraer "valor + unidad" de un mensaje.
_TOKENS_UNIDAD = (
    "kwh", "mj", "mg", "ppm", "kg", "g", "bar", "%",
    "m^3", "nm^3", "m3", "nm3", "m³", "nm³", "°c", "ºc", "c",
)


def _parse_numeric_value(text: str) -> Optional[float]:
    """Extrae el número más "informativo" de un texto (admite coma decimal).

    Tolera puntuación/letra justo después ("15," , "0.03de" -> 0.03). El
    lookbehind evita capturar el "2" de "o2"/"co2" como número.
    """
    pattern = r"(?<![A-Za-z0-9])([-+]?[0-9]+(?:[\.,][0-9]+)?)"
    matches = re.findall(pattern, text)
    if not matches:
        return None
    best_match = max(matches, key=lambda m: ('.' in m, len(m)))
    raw = best_match.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_numeric_with_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Devuelve (valor, unidad) si el texto contiene un número seguido de unidad."""
    patterns = [
        r"(?i)([-+]?[0-9]+(?:[\.,][0-9]+)?)\s*(kwh\s*/\s*[a-z0-9^³°]+|mj\s*/\s*[a-z0-9^³°]+|mg\s*/\s*[a-z0-9^³°]+|ppm\s*/\s*[a-z0-9^³°]+|%\s*(?:molar|mol)?|kwh|mj|mg|ppm|kg|g|bar|m\^3|nm\^3|m3|nm3|m³|nm³|°c|ºc|c\b)",
        r"(?i)([-+]?[0-9]+(?:[\.,][0-9]+)?)\s*([a-z0-9^°]+\s*/\s*[a-z0-9^°]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1).replace(",", ".")
            unit_raw = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(0)
            unit_clean = re.sub(r"\s+", "", unit_raw)
            unit_norm = unit_clean.lower()
            if any(
                unit_norm.startswith(token) or token in unit_norm
                for token in _TOKENS_UNIDAD
            ):
                try:
                    return float(value), unit_clean
                except ValueError:
                    return None, None
    return None, None


def _extract_unit_only(text: str) -> Optional[str]:
    """Devuelve solo la unidad mencionada en el texto (sin número), o None."""
    match = re.search(
        r"(?i)(%\s*(?:molar|mol)?|kwh\s*/\s*[a-z0-9^³°]+|mj\s*/\s*[a-z0-9^³°]+|mg\s*/\s*[a-z0-9^³°]+|ppm\s*/\s*[a-z0-9^³°]+|°c|ºc|\bc\b)",
        text,
    )
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(0))


def _normalize_unit(unit: Optional[str]) -> str:
    """Normaliza una unidad para comparaciones robustas (m³→m3, °→o, sin espacios)."""
    if not unit:
        return ""
    text = str(unit)
    text = text.replace("^", "")
    text = text.replace("³", "3").replace("²", "2")
    text = text.replace("º", "°")
    text = re.sub(r"\s+", "", text)
    text = text.replace("°", "o")
    text = text.replace("m³", "m3").replace("nm³", "nm3")
    text = text.lower()
    return text


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
        (0.015, "MWh/m³", "kWh/m³", "PCS"),      # -> 15 kWh/m³
        (15, "kWh/m³", "MWh/m³", "PCS"),         # -> 0.015 MWh/m³
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

    print("\n--- Condiciones de referencia (UNE-EN ISO 13443) ---")
    # Validación contra los ejemplos resueltos de la propia norma (Anexo D):
    #   Ejemplo 4: PCS real vol. 38,57 MJ/m³ (60 °F ≈ 15,556 °C) -> ISO (15 °C) = 38,56
    #   Ejemplo 5: PCI real vol. 37,35 MJ/m³ (comb 25 °C, med 0 °C) -> ISO   = 35,40
    ref = [
        (38.57, "PCS", 15.5556, 15.5556, 15, 15, 101.560, 101.325),  # Ej. 4 -> 38,56
        (37.35, "PCI", 25, 0, 15, 15),                               # Ej. 5 -> 35,40
        (13.381, "Wobbe", 25, 0, 0, 0),     # Portugal -> España (cf. Tabla A.1 ≈ 1,0026)
        (57.66, "PCS", 25, 0, 0, 0),        # Portugal -> España
        (40.0, "PCS", 15, 15, 0, 0),        # UE/ISO -> España (Tabla A.1 ≈ 1,0570)
        (15.0, "O2", 25, 0, 0, 0),          # no cubierto por la norma -> error explícito
    ]
    for c in ref:
        print(c, "->", convertir_condiciones_referencia(*c))
