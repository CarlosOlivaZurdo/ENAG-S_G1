"""Construye la respuesta con la ESTRUCTURA OBLIGATORIA de 7 secciones.

En el sistema final, el LLM redacta esta respuesta a partir de los datos del motor
determinista (usando SYSTEM_PROMPT) sin alterar ninguna cifra. Aquí se renderiza de
forma determinista para que el prototipo sea ejecutable sin clave de API.
"""

LINEA = "─" * 70


def _cond_display(lim):
    c = lim.get("condiciones_referencia") or {}
    parts = []
    if c.get("notacion"):
        parts.append(str(c["notacion"]))
    else:
        if c.get("temperatura_combustion_C") is not None:
            parts.append(f"comb {c['temperatura_combustion_C']}ºC")
        if c.get("temperatura_volumen_C") is not None:
            parts.append(f"vol {c['temperatura_volumen_C']}ºC")
    if lim.get("presion_referencia_bar") is not None:
        parts.append(f"{lim['presion_referencia_bar']} bar")
    return ", ".join(parts) if parts else "n/d"


def _fuente_display(repo, lim):
    f = repo.fuente(lim.get("fuente"))
    art = lim.get("articulo", "")
    base = f.get("nombre", lim.get("fuente", "?"))
    return base + (f" — {art}" if art else "")


def _evidencia_url(f):
    for k in ("pdf", "url_eurlex", "url_boe", "url_enagas", "publicacion"):
        if f.get(k):
            return f[k]
    return ""


def _cabecera():
    return (f"{LINEA}\n ASISTENTE EXPERTO DE CALIDAD DE GAS NATURAL  ·  motor determinista\n{LINEA}")


def render_fuera_de_ambito(question):
    return (f"{_cabecera()}\n\n"
            f"Consulta: «{question}»\n\n"
            "⛔ FUERA DE ÁMBITO. Este asistente solo trata la CALIDAD DEL GAS NATURAL "
            "(Wobbe, PCS, densidad, azufre, H₂S+COS, mercaptanos, O₂, CO₂, puntos de rocío) "
            "en España, Portugal, Francia y la UE.\nNo cubre tarifas, peajes, capacidad, "
            "balance, mercado ni fiscalidad. Reformula la pregunta dentro del dominio de calidad.")


def render_abierta(repo, question, cls):
    out = [_cabecera(), "", f"Consulta: «{question}»", ""]
    pid = cls.get("param")
    if pid:
        p = repo.param(pid)
        definicion = p.get("definicion") or p.get("descripcion") or "(sin definición en la ontología)"
        out.append(f"📖 {p.get('nombre_completo', pid)} ({p.get('simbolo','')})")
        out.append(f"   {definicion.strip()}")
        out.append("")
    out.append("ℹ Consulta abierta (no comparativa). En el sistema completo se resolvería por "
               "RAG sobre los PDFs normativos, con cita por documento/artículo/página.")
    return "\n".join(out)


def render_comparativa(repo, question, cls, res):
    ja, jb = res["jur_a"], res["jur_b"]
    nA = repo.jurisdiccion(ja)["nombre"]
    nB = repo.jurisdiccion(jb)["nombre"]
    la, lb = res["lim_a"], res["lim_b"]
    out = [_cabecera(), ""]

    out.append("1. PREGUNTA INTERPRETADA")
    out.append(f"   Comparar «{res['param_nombre']}» entre {nA} y {nB}.")
    out.append(f"   (Consulta original: «{question}»)")
    out.append("")

    out.append("2. JURISDICCIONES ANALIZADAS")
    for cod in (ja, jb):
        j = repo.jurisdiccion(cod)
        out.append(f"   - {j['nombre']} (nivel {j.get('nivel','?')})")
    out.append("")

    out.append("3. INFORMACIÓN RECUPERADA")
    for cod, lim in ((ja, la), (jb, lb)):
        nombre = repo.jurisdiccion(cod)["nombre"]
        out.append(f"   [{cod}] {nombre}")
        out.append(f"        valor   : {repo.valor_display(lim)}")
        out.append(f"        cond.ref: {_cond_display(lim)}")
        out.append(f"        fuente  : {_fuente_display(repo, lim)}")
    out.append("")

    out.append("4. ANÁLISIS DE COMPARABILIDAD")
    out.append(f"   {res['flag_icon']} {res['flag_key']}")
    out.append(f"   {res['reason']}")
    out.append("")

    out.append("5. CONVERSIÓN APLICADA")
    conv = res.get("conversion")
    if conv:
        for ln in conv["lineas"]:
            out.append(f"   {ln}")
        if conv.get("nota"):
            out.append(f"   ⚠ {conv['nota']}")
    else:
        out.append("   No procede.")
    out.append("")

    out.append("6. EVIDENCIAS")
    for cod, lim in ((ja, la), (jb, lb)):
        f = repo.fuente(lim.get("fuente"))
        url = _evidencia_url(f)
        out.append(f"   - [{cod}] {f.get('nombre', lim.get('fuente'))}"
                   f" — {lim.get('articulo','')}")
        if url:
            out.append(f"          {url}")
    out.append("")

    out.append("7. CONCLUSIÓN TÉCNICA")
    if res.get("relacion"):
        out.append(f"   {res['relacion']}")
    out.append(f"   Resultado de comparabilidad: {res['flag_icon']} {res['flag_key']}.")
    out.append("")
    out.append(LINEA)
    out.append("Generado por el MOTOR DETERMINISTA. En producción, el LLM redacta esta")
    out.append("respuesta con SYSTEM_PROMPT sin alterar ninguna cifra (Restricción 1).")
    return "\n".join(out)


def render(repo, question, cls, res=None):
    intent = cls["intent"]
    if intent == "fuera_de_ambito":
        return render_fuera_de_ambito(question)
    if intent == "abierta":
        return render_abierta(repo, question, cls)
    return render_comparativa(repo, question, cls, res)
