"""Acceso de solo lectura a la ontología. El motor nunca inventa: solo consulta."""
import re
import unicodedata

UNIT_DISPLAY = {
    "kWh_per_nm3": "kWh/m³", "MJ_per_nm3": "MJ/m³", "mg_per_nm3": "mg/m³",
    "mg_per_sm3": "mg/m³(15ºC)", "pct_mol": "% mol", "pct_vol": "% vol",
    "ppm_vol": "ppm", "grados_C": "ºC", "adimensional": "", None: "",
}


def norm(text):
    """Minúsculas sin acentos, para emparejar alias y palabras clave."""
    t = unicodedata.normalize("NFKD", text or "")
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    return t


def fmt_num(x):
    return ("%g" % x).replace(".", ",")


class OntologyRepository:
    def __init__(self, onto):
        self.onto = onto
        self.params = onto["parametros"]
        meta = onto["ontologia"]
        self.jurisdicciones = {j["codigo"]: j for j in meta["jurisdicciones"]}
        self.fuentes = {f["id"]: f for f in meta["fuentes_normativas"]}
        self.flags = onto["flags"]
        self.unidades = onto["unidades"]

    # -- parámetros -----------------------------------------------------------
    def find_parameter(self, text):
        """Devuelve el id de parámetro cuyo alias más largo aparece en el texto."""
        t = norm(text)
        best, best_len = None, 0
        for pid, p in self.params.items():
            candidatos = list(p.get("aliases", []))
            candidatos += [p.get("nombre_completo", ""), p.get("nombre_ingles", ""), pid]
            for alias in candidatos:
                na = norm(alias)
                if len(na) < 2:
                    continue
                patron = r"(?<![a-z0-9])" + re.escape(na) + r"(?![a-z0-9])"
                if re.search(patron, t) and len(na) > best_len:
                    best, best_len = pid, len(na)
        return best

    def param(self, pid):
        return self.params[pid]

    def limite(self, pid, jur):
        return self.params[pid]["limites"].get(jur)

    # -- fuentes / jurisdicciones --------------------------------------------
    def fuente(self, fid):
        return self.fuentes.get(fid, {})

    def jurisdiccion(self, cod):
        return self.jurisdicciones.get(cod, {"codigo": cod, "nombre": cod})

    # -- formato --------------------------------------------------------------
    def unidad_display(self, uid):
        return UNIT_DISPLAY.get(uid, uid or "")

    def valor_display(self, lim):
        """Texto legible de un límite (o 'No fija' si la norma no lo establece)."""
        if lim is None:
            return "—"
        if lim.get("estado_verificacion") == "NO_VERIFICABLE_SIN_FUENTE":
            return "No fija"
        if lim.get("estado_verificacion") == "PENDIENTE_EXTRACCION":
            return "Pendiente de extracción"
        u = self.unidad_display(lim.get("unidad"))
        if lim.get("tipo_limite") == "rango":
            vmin, vmax = lim.get("valor_min"), lim.get("valor_max")
            if vmin is None or vmax is None:
                return "No fija"
            txt = f"{fmt_num(vmin)} – {fmt_num(vmax)} {u}".strip()
        else:
            v = lim.get("valor")
            if v is None:
                return "No fija"
            txt = f"≤ {fmt_num(v)} {u}".strip()
        p = lim.get("presion_referencia_bar")
        if p is not None:
            txt += f" @ {p} bar"
        return txt
