"""Normalización determinista: SOLO conversiones con base física o documentada.

Restricción 4 (no inventar conversiones): si una diferencia de condiciones de
referencia no tiene factor documentado en la ontología, NO se convierte.
"""

# Magnitud física de cada unidad y factor a su unidad base.
#   energia_vol  -> base MJ/m³   (kWh = 3.6 MJ)
#   conc_masica  -> base mg/m³
#   frac_molar   -> base % mol
#   temperatura  -> base ºC      (no se "convierte" entre presiones de referencia)
#   adimensional -> sin unidad
_BASE = {
    "kWh_per_nm3": ("energia_vol", 3.6),
    "MJ_per_nm3":  ("energia_vol", 1.0),
    "mg_per_nm3":  ("conc_masica", 1.0),
    "pct_mol":     ("frac_molar", 1.0),
    "pct_vol":     ("frac_molar", 1.0),
    "grados_C":    ("temperatura", 1.0),
    "adimensional": ("adimensional", 1.0),
}


def magnitud(unidad):
    return _BASE.get(unidad, (unidad, 1.0))[0]


def convertibles(u_a, u_b):
    """¿Pertenecen a la misma magnitud física (convertibles con factor exacto)?"""
    return magnitud(u_a) == magnitud(u_b)


def convertir(valor, u_origen, u_destino):
    """Convierte un valor entre unidades de la MISMA magnitud (factor exacto)."""
    if valor is None:
        return None
    if u_origen == u_destino:
        return valor
    if not convertibles(u_origen, u_destino):
        raise ValueError(f"Unidades no convertibles: {u_origen} ↔ {u_destino}")
    f_o = _BASE[u_origen][1]
    f_d = _BASE[u_destino][1]
    return valor * f_o / f_d


def factor_texto(u_origen, u_destino):
    """Descripción legible del factor de conversión de unidad."""
    f = _BASE[u_origen][1] / _BASE[u_destino][1]
    return f"× {('%g' % f).replace('.', ',')}  ({u_origen} → {u_destino})"
