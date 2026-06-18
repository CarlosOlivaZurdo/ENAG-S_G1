"""Clasificador de intención (parte conversacional). NO produce números.

Detecta: si la consulta está fuera de ámbito, el parámetro y las jurisdicciones.
En el sistema final esta etapa la asistiría el LLM; aquí va por reglas/alias para
que el motor determinista sea ejecutable de forma autónoma.
"""
from src.ontology.repository import norm

JUR_KEYWORDS = {
    "ES": ["espana", "espanol", "ngts", "enagas", "pd-01", "pd01", "ted/181", "spain"],
    "PT": ["portugal", "portugues", "erse", "826", "lisboa"],
    "FR": ["francia", "frances", "france", "grtgaz", "grdf", "paris"],
    "UE": ["union europea", "europeo", "europea", "europa", "network code",
           "2015/703", "marco europeo", "easee", "comunitari"],
}

FUERA_DE_AMBITO = [
    "peaje", "tarifa", "mercado electrico", "capacidad", "balance", "almacenamiento",
    "contratacion", "fiscal", "impuesto", "tributa", "societari", "financ", "subasta",
    "retribucion", "comercializ",
]

DEFINICION = ["que es", "que significa", "definicion", "que dice", "explica"]


def detectar_jurisdicciones(question):
    t = norm(question)
    return [cod for cod, kws in JUR_KEYWORDS.items() if any(k in t for k in kws)]


def _par(jurs):
    js = list(dict.fromkeys(jurs))
    if len(js) >= 2:
        return (js[0], js[1])
    if len(js) == 1:
        return ("ES", js[0]) if js[0] != "ES" else ("ES", "UE")
    return ("ES", "UE")


def classify(repo, question):
    t = norm(question)
    pid = repo.find_parameter(question)
    jurs = detectar_jurisdicciones(question)
    fuera = any(k in t for k in FUERA_DE_AMBITO)
    es_definicion = any(k in t for k in DEFINICION)

    if fuera and pid is None:
        return {"intent": "fuera_de_ambito", "param": None, "jurs": jurs, "pair": None}
    if pid is None:
        return {"intent": "abierta", "param": None, "jurs": jurs, "pair": None}
    if es_definicion and len(jurs) < 2:
        return {"intent": "abierta", "param": pid, "jurs": jurs, "pair": None}
    return {"intent": "comparativa", "param": pid, "jurs": jurs, "pair": _par(jurs)}
