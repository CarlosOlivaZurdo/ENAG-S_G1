"""Motor determinista de comparación. Asigna el flag 🟢/🟡/🔴 y la evidencia.

Ninguna cifra se genera aquí: todas provienen de la ontología. Ninguna conversión
se aplica sin base física (cambio de unidad exacto) o factor documentado.
"""
from src.ontology.repository import fmt_num
from src.normalization.units import convertibles, convertir, factor_texto

ENERGETICOS = {"WOBBE", "PCS"}
ROCIO = {"PR_H2O", "PR_HC"}


def _disponible(lim):
    if lim is None or lim.get("estado_verificacion") != "VERIFICADO":
        return False
    if lim.get("tipo_limite") == "rango":
        return lim.get("valor_min") is not None and lim.get("valor_max") is not None
    return lim.get("valor") is not None


def _flag(repo, key):
    f = repo.flags[key]
    return {"flag_key": key, "flag_icon": f["icono"], "flag_desc": f["descripcion"]}


def _condiciones_diff(repo, pid, la, lb):
    """None | ('documented', desc) | ('undocumented', desc)."""
    ca = la.get("condiciones_referencia", {}) or {}
    cb = lb.get("condiciones_referencia", {}) or {}
    if pid in ROCIO:
        pa, pb = la.get("presion_referencia_bar"), lb.get("presion_referencia_bar")
        if pa is not None and pb is not None and pa == pb:
            return None
        return ("undocumented",
                f"Presiones de referencia distintas o no especificadas "
                f"(A: {pa}, B: {pb} bar). El punto de rocío no es comparable sin igualarlas.")
    if pid in ENERGETICOS:
        ta, tb = ca.get("temperatura_combustion_C"), cb.get("temperatura_combustion_C")
        if ta is not None and tb is not None and ta != tb:
            if pid == "PCS":
                return ("documented",
                        f"Tª de combustión distinta (@{ta} vs @{tb} ºC); factor documentado "
                        f"PCS @25/0→@0/0 = 1,0026 (Anexo Rgto. UE 2015/703).")
            return ("undocumented",
                    f"Tª de combustión distinta (@{ta} vs @{tb} ºC) y no hay factor documentado "
                    f"para el índice de Wobbe en la ontología. No se inventa (Restricción 4).")
    return None


def _conv_valor(lim, u_destino):
    if lim.get("tipo_limite") == "rango":
        vmin = convertir(lim["valor_min"], lim["unidad"], u_destino)
        vmax = convertir(lim["valor_max"], lim["unidad"], u_destino)
        return f"{fmt_num(vmin)} – {fmt_num(vmax)}"
    return "≤ " + fmt_num(convertir(lim["valor"], lim["unidad"], u_destino))


def _relacion(repo, pid, la, lb, ua, ub):
    """Frase determinista sobre la relación numérica (para la conclusión)."""
    na = repo.jurisdiccion(la["_jur"])["nombre"]
    nb = repo.jurisdiccion(lb["_jur"])["nombre"]
    ud = repo.unidad_display(ua)
    if la.get("tipo_limite") == "maximo" and lb.get("tipo_limite") == "maximo":
        va = la["valor"]
        vb = convertir(lb["valor"], ub, ua)
        if abs(va - vb) < 1e-9:
            return f"Ambas fijan el mismo límite máximo (≤ {fmt_num(va)} {ud})."
        mas, menos = (na, nb) if va < vb else (nb, na)
        return (f"{mas} es más estricto (límite máximo inferior) que {menos} "
                f"[{fmt_num(va)} vs {fmt_num(vb)} {ud}].")
    if la.get("tipo_limite") == "rango" and lb.get("tipo_limite") == "rango":
        amin, amax = la["valor_min"], la["valor_max"]
        bmin = convertir(lb["valor_min"], ub, ua)
        bmax = convertir(lb["valor_max"], ub, ua)
        solapa = not (amax < bmin or bmax < amin)
        rel = "se solapan" if solapa else "no se solapan"
        return (f"{na}: {fmt_num(amin)}–{fmt_num(amax)} {ud}  vs  "
                f"{nb}: {fmt_num(bmin)}–{fmt_num(bmax)} {ud}  →  los rangos {rel}.")
    return None


def compare(repo, pid, jur_a, jur_b):
    la = repo.limite(pid, jur_a)
    lb = repo.limite(pid, jur_b)
    # anotar la jurisdicción dentro del límite para los helpers
    if la is not None:
        la = dict(la, _jur=jur_a)
    if lb is not None:
        lb = dict(lb, _jur=jur_b)

    res = {
        "param": pid,
        "param_nombre": repo.param(pid).get("nombre_completo", pid),
        "jur_a": jur_a, "jur_b": jur_b,
        "lim_a": la, "lim_b": lb,
        "conversion": None, "relacion": None,
    }

    # 1) disponibilidad
    motivos = []
    if not _disponible(la):
        motivos.append(f"{repo.jurisdiccion(jur_a)['nombre']} no fija este parámetro en la fuente citada")
    if not _disponible(lb):
        motivos.append(f"{repo.jurisdiccion(jur_b)['nombre']} no fija este parámetro en la fuente citada")
    if motivos:
        res.update(_flag(repo, "NO_COMPARABLE"))
        res["reason"] = ". ".join(motivos) + ". No se inventa la cifra ausente (Restricción 1)."
        return res

    ua, ub = la.get("unidad"), lb.get("unidad")

    # 2) magnitudes incompatibles
    if not convertibles(ua, ub):
        res.update(_flag(repo, "UNIDADES_INCOMPATIBLES"))
        res["reason"] = (f"Magnitudes no convertibles entre sí "
                         f"({repo.unidad_display(ua)} vs {repo.unidad_display(ub)}).")
        return res

    transforms_unidad = (ua != ub)
    cond = _condiciones_diff(repo, pid, la, lb)

    # 3) condición no documentada → 🔴 (con conversión informativa de unidad si aplica)
    if cond and cond[0] == "undocumented":
        res.update(_flag(repo, "NO_COMPARABLE"))
        res["reason"] = cond[1]
        if transforms_unidad:
            res["conversion"] = {
                "lineas": [
                    f"{repo.jurisdiccion(jur_b)['nombre']}: {repo.valor_display(lb)}"
                    f"  →  {factor_texto(ub, ua)}  →  {_conv_valor(lb, ua)} {repo.unidad_display(ua)}",
                ],
                "nota": "Conversión de unidad informativa: NO es suficiente para comparar "
                        "por la diferencia de condiciones de referencia indicada.",
            }
        return res

    # 4) comparable tras normalizar (unidad y/o condición documentada)
    if transforms_unidad or (cond and cond[0] == "documented"):
        res.update(_flag(repo, "COMPARABLE_TRAS_NORMALIZAR"))
        lineas = []
        if transforms_unidad:
            lineas.append(
                f"{repo.jurisdiccion(jur_b)['nombre']}: {repo.valor_display(lb)}"
                f"  →  {factor_texto(ub, ua)}  →  {_conv_valor(lb, ua)} {repo.unidad_display(ua)}")
        if cond and cond[0] == "documented":
            lineas.append(cond[1])
        res["conversion"] = {"lineas": lineas, "nota": None}
        res["relacion"] = _relacion(repo, pid, la, lb, ua, ua)
        res["reason"] = "Comparable tras aplicar la normalización determinista (ver sección 5)."
        return res

    # 5) comparable directo
    res.update(_flag(repo, "COMPARABLE"))
    res["reason"] = "Misma unidad y condiciones de referencia: comparación directa válida."
    res["relacion"] = _relacion(repo, pid, la, lb, ua, ub)
    return res
