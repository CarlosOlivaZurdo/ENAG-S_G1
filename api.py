import os
import re
import json
import time
import difflib
from functools import wraps
from typing import Callable, Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

from motor_determinista import (
    buscar_pdfs,
    indexar_pdfs,
    consultar_excel,
    evaluar_cumplimiento,
)
from conversor_unidades import (
    convertir_unidades,
    convertir_condiciones_referencia,
    _parse_numeric_value,
    _extract_numeric_with_unit,
    _extract_unit_only,
    _normalize_unit,
)
from condiciones_referencia import (
    convertir_a_condiciones_espana,
    _slug_parametro as _slug_param_comb,
    CONDICIONES_PAIS as _COND_PAIS,
)
import fuente_oficial

try:
    from src.llm.prompts import SYSTEM_PROMPT
except Exception:  # fallback si el paquete src no está en el path
    SYSTEM_PROMPT = (
        "Eres el Asistente Experto de Calidad de Gas Natural. Solo tratas la calidad "
        "del gas natural (España, Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia, UE). Nunca inventas valores "
        "numéricos: los obtienes de las herramientas deterministas. Cita siempre la fuente."
    )

load_dotenv()

# --- Modelo de lenguaje: SOLO OpenAI ---------------------------------------
# Clave leída de la variable de entorno API_OPENAI (patrón acordado por el equipo):
#     clave = os.environ.get("API_OPENAI")
#     client = OpenAI(api_key=clave)
clave = os.environ.get("API_OPENAI")
if clave:
    clave = clave.strip()
    # Las claves válidas de OpenAI empiezan por "sk-". Descarta placeholders/inválidas
    # para no romper el chat (caería al motor determinista).
    if clave in {"", "tu_clave_aqui"} or not clave.startswith("sk-"):
        clave = None
client = OpenAI(api_key=clave) if clave else None
MODELO_OPENAI = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class PeticionChat(BaseModel):
    session_id: str
    mensaje: str


class RespuestaChat(BaseModel):
    respuesta: str
    modo: str = "ia"


class StatusResponse(BaseModel):
    modo: str
    detalle: str


def medir_tiempo(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        inicio = time.perf_counter()
        resultado = await func(*args, **kwargs)
        duracion = time.perf_counter() - inicio
        print(f"[medir_tiempo] {func.__name__} tardó {duracion:.3f} segundos")
        return resultado

    return wrapper


def gestionar_errores(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            print(f"[gestionar_errores] Error interno: {exc}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    return wrapper


# Historial de conversación por sesión (lista de mensajes estilo OpenAI).
session_histories: Dict[str, List[Dict[str, Any]]] = {}


class PendingValidation(TypedDict):
    parametro: str
    pais: str
    valor: float


pending_unit_validations: Dict[str, PendingValidation] = {}


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_histories[session_id]


# --- Herramientas deterministas expuestas a OpenAI (function calling) ------
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_excel",
            "description": "Consulta los límites regulatorios de calidad de gas para un parámetro y país.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parametro": {"type": "string", "description": "Parámetro de calidad (p.ej. O2, PCS, Wobbe, S total)."},
                    "pais": {"type": "string", "description": "País/jurisdicción (España, Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia, UE)."},
                },
                "required": ["parametro", "pais"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluar_cumplimiento",
            "description": (
                "Evalúa si un valor MEDIDO (aportado por el usuario) cumple los límites "
                "regulatorios. ÚSALA SOLO si el usuario da un valor numérico a evaluar. "
                "Si el usuario solo pregunta por el límite/valor de la normativa (sin dar "
                "un valor propio), usa `consultar_excel`; NUNCA inventes un valor."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "parametro": {"type": "string"},
                    "pais": {"type": "string"},
                    "valor": {"type": "number"},
                    "unidad": {"type": "string"},
                },
                "required": ["parametro", "pais", "valor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_pdfs",
            "description": "Busca texto relevante dentro de los PDF normativos indexados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Texto a buscar en los documentos."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_unidades",
            "description": (
                "ÚNICA vía autorizada para convertir unidades de forma exacta y determinista. "
                "Úsala SIEMPRE que necesites normalizar energía (MJ/m³ ↔ kWh/m³), temperatura "
                "(K ↔ °C, °F ↔ °C) o concentración (mg/m³ a 15 °C ↔ mg/Nm³ a 0 °C; mg/Nm³ ↔ ppm). "
                "Nunca calcules una conversión por tu cuenta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "valor": {"type": "number", "description": "Valor numérico a convertir."},
                    "unidad_origen": {"type": "string", "description": "Unidad de partida (p.ej. mg/Nm³, ppm, MJ/m³, K, °F)."},
                    "unidad_destino": {"type": "string", "description": "Unidad de llegada (p.ej. kWh/m³, °C, ppm)."},
                    "parametro": {"type": "string", "description": "Parámetro asociado (PCS, Wobbe, H2S, O2…); se usa para deducir la masa molar en mg/Nm³ ↔ ppm."},
                    "masa_molar": {"type": "number", "description": "Masa molar en g/mol (opcional; solo para mg/Nm³ ↔ ppm si el componente no es conocido)."},
                },
                "required": ["valor", "unidad_origen", "unidad_destino"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_condiciones_referencia",
            "description": (
                "Lleva un PCS o Índice de Wobbe desde las condiciones de referencia (temperatura "
                "de combustión) de un país a las de España, con los factores de la Tabla A.1 de la "
                "ISO 13443. Portugal usa combustión 25 °C y España 0 °C, por lo que su PCS/Wobbe se "
                "multiplica por 1,0026 para compararlos. Úsala para comparar PCS/Wobbe entre países "
                "con distinta temperatura de combustión. NO la uses para otros parámetros."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "valor": {"type": "number", "description": "Valor a convertir (en kWh/m³; convierte antes la unidad si hace falta)."},
                    "parametro": {"type": "string", "description": "PCS o Wobbe."},
                    "pais_origen": {"type": "string", "description": "País de origen (España, Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia, UE)."},
                },
                "required": ["valor", "parametro", "pais_origen"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_condiciones_iso13443",
            "description": (
                "Convierte PCS, PCI, Índice de Wobbe (o volumen/densidad/densidad relativa) entre DOS "
                "condiciones de referencia ARBITRARIAS según la UNE-EN ISO 13443. A diferencia de "
                "convertir_condiciones_referencia (que solo lleva a España), aquí indicas explícitamente "
                "las temperaturas de combustión y medición de origen y destino. Para los pares tabulados "
                "usa los factores literales de la Tabla A.1 (normativos); para el resto, las ecuaciones del "
                "Anexo B. Úsala cuando las condiciones no sean las de un país conocido. No convierte unidades."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "valor": {"type": "number", "description": "Valor a convertir (ya en la unidad correcta)."},
                    "parametro": {"type": "string", "description": "PCS, PCI, Wobbe, volumen, densidad o densidad relativa."},
                    "comb_origen": {"type": "number", "description": "Temperatura de combustión de origen (°C)."},
                    "med_origen": {"type": "number", "description": "Temperatura de medición/volumen de origen (°C)."},
                    "comb_destino": {"type": "number", "description": "Temperatura de combustión de destino (°C)."},
                    "med_destino": {"type": "number", "description": "Temperatura de medición/volumen de destino (°C)."},
                },
                "required": ["valor", "parametro", "comb_origen", "med_origen", "comb_destino", "med_destino"],
            },
        },
    },
]

TOOL_FUNCS: Dict[str, Callable[..., Any]] = {
    # Las consultas normativas usan la FUENTE OFICIAL (ontología) como primaria; el Excel
    # solo como respaldo. Lambdas con enlace tardío (los wrappers se definen más abajo).
    "consultar_excel": lambda **kw: _consultar_norma(kw.get("parametro", ""), kw.get("pais", "")),
    "evaluar_cumplimiento": lambda **kw: _evaluar_norma(kw.get("parametro", ""), kw.get("pais", ""), kw.get("valor"), kw.get("unidad")),
    "convertir_condiciones_referencia": convertir_a_condiciones_espana,
    "convertir_condiciones_iso13443": convertir_condiciones_referencia,
    "buscar_pdfs": buscar_pdfs,
    "convertir_unidades": convertir_unidades,
}


def responder_con_openai(mensaje: str, session_id: str) -> str:
    """Redacta la respuesta con OpenAI usando las herramientas deterministas.

    El modelo NUNCA inventa cifras: los números provienen de las herramientas
    (Excel/PDF). El LLM solo interpreta la pregunta y redacta el resultado.
    """
    history = get_session_history(session_id)
    mensajes: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    mensajes.extend(history)
    mensajes.append({"role": "user", "content": mensaje})

    texto_final = ""
    for _ in range(5):  # límite de iteraciones de tool-calling
        respuesta = client.chat.completions.create(
            model=MODELO_OPENAI,
            messages=mensajes,
            tools=OPENAI_TOOLS,
            temperature=0,
        )
        msg = respuesta.choices[0].message
        if not msg.tool_calls:
            texto_final = msg.content or ""
            break
        mensajes.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            func = TOOL_FUNCS.get(tc.function.name)
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                resultado = func(**args) if func else {"error": "herramienta desconocida"}
            except Exception as exc:  # noqa: BLE001
                resultado = {"error": str(exc)}
            mensajes.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

    # Persistir el turno en el historial de la sesión.
    history.append({"role": "user", "content": mensaje})
    history.append({"role": "assistant", "content": texto_final})
    return texto_final


backend_mode = "ia" if client is not None else "determinista"
backend_detail = (
    "Agente OpenAI operativo" if backend_mode == "ia"
    else "Sin clave API_OPENAI válida: usando fallback determinista"
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_INDEX_HTML = os.path.join(os.path.dirname(__file__), "index.html")


@app.get("/")
async def servir_chat() -> FileResponse:
    """Sirve la interfaz web del chatbot en la raíz (http://localhost:8000/).

    Sin caché: así los compañeros ven SIEMPRE la última versión tras un `git pull`,
    sin tener que forzar recarga (Ctrl+F5) en el navegador.
    """
    return FileResponse(
        _INDEX_HTML,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def _normalize_country(text: str) -> Optional[str]:
    normalized = text.lower()
    aliases = {
        "espa": "España",
        "espana": "España",
        "españa": "España",
        "portugal": "Portugal",
        "francia": "Francia",
    }
    for key, value in aliases.items():
        if key in normalized:
            return value
    return None


# Dígitos en subíndice (H₂S, CO₂, O₂) y superíndice (Nm³) → dígitos ASCII.
_SUB_SUP_DIGITS = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
})


def _normalize_parameter(text: str) -> Optional[str]:
    normalized = text.lower()
    # H₂S, CO₂, O₂… escritos con dígitos en subíndice: pásalos a "h2s", "co2", "o2".
    normalized = normalized.translate(_SUB_SUP_DIGITS)
    # "02" (cero-dos) escrito como O2 (oxígeno): normalizar el token aislado.
    # No toca "1.02", "2002" ni "co2" (la barrera \w/.,/ lo evita).
    normalized = re.sub(r"(?<![\w./,])02(?![\w])", "o2", normalized)
    # Punto de rocío: desambiguar HC (hidrocarburos) frente a H2O (agua).
    # Sin esto, "rocío de HC" caía siempre en H2O por el alias genérico "rocío".
    na = normalized.translate(str.maketrans("áéíóúü", "aeiouu"))
    if "rocio" in na or "dew point" in na:
        if "hc" in na or "hidrocarbur" in na:
            return "hc(rocío)"
        return "h2o(rocío)"
    aliases = {
        "o2": "o2",
        "oxigeno": "o2",
        "oxígeno": "o2",
        "pcs": "pcs",
        "h2s": "h2s+cos",
        "h2s+cos": "h2s+cos",
        "wobbe": "wobbe",
        "s total": "s total",
        "co2": "co2",
        "h2o": "h2o(rocío)",
        "h2o(rocío)": "h2o(rocío)",
        "h2o(rocio)": "h2o(rocío)",
        "rocio": "h2o(rocío)",
        "rocío": "h2o(rocío)",
        "hc": "hc(rocío)",
        "hc(rocío)": "hc(rocío)",
        "rsh": "rsh",
        "densidad relativa": "densidad relativa",
        "hco": "hco",
        "indice de wobbe": "wobbe",
        "índice de wobbe": "wobbe",
        "azufre total": "s total",
        "azufre": "s total",
    }
    # Del alias más largo al más corto: evita que un alias corto contenido en otro
    # más largo gane por error (p. ej. "o2" dentro de "co2", o "hc" dentro de "hco").
    for key in sorted(aliases, key=len, reverse=True):
        if key in normalized:
            return aliases[key]
    # Fallback: "S" suelto = símbolo del azufre total (no la "s" interna de otras palabras).
    if re.search(r"(?<![\w])s(?![\w])", normalized):
        return "s total"
    return None


def _normalize_condition_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = str(text).strip()
    cleaned = cleaned.replace("Condiciones de medición:", "")
    cleaned = cleaned.replace("Condiciones de medicion:", "")
    cleaned = cleaned.replace("Condiciones:", "")
    return cleaned.strip()


# --- Strict measurement-unit validation dictionary ---
VALIDATION_UNITS = {
    "Índice de Wobbe": "kWh/m³",
    "PCS": "kWh/m³",
    "S": "mg/m³",
    "H2S + COS + RSH": "mg/m³",
    "O2": "% molar",
    "CO2": "% molar",
    "Temperatura de rocío del H2O": "°C",
    "Temperatura de rocío de HC": "°C",
}

DISPLAY_MAP = {
    "wobbe": "Índice de Wobbe",
    "pcs": "PCS",
    "s total": "S",
    "h2s+cos": "H2S + COS + RSH",
    "o2": "O2",
    "co2": "CO2",
    "h2o(rocío)": "Temperatura de rocío del H2O",
    "hc(rocío)": "Temperatura de rocío de HC",
}


def _unit_matches_expected(param: str, unit: Optional[str]) -> bool:
    if not param or not unit:
        return False
    expected = VALIDATION_UNITS.get(DISPLAY_MAP.get(param, param))
    if expected is None:
        return False
    # Acepta la unidad si es la esperada O si es convertible de forma determinista a ella
    # (p.ej. MJ/m³ para Wobbe, ppm para H2S, mg/Nm³ para S…). El conversor decide.
    if _normalize_unit(unit) == _normalize_unit(expected):
        return True
    conv = convertir_unidades(1.0, unit, expected, param)
    return "valor_convertido" in conv


def _expected_unit_for_parameter(param: str) -> str:
    return VALIDATION_UNITS.get(DISPLAY_MAP.get(param, param), "")


def _missing_unit_message(parametro: str) -> str:
    param_display = DISPLAY_MAP.get(parametro, parametro)
    return f"⚠️ Valor detectado sin unidades. Por favor, indícame en qué unidades estás expresando este valor para el parámetro {param_display}."


def _incorrect_unit_message(parametro: str) -> str:
    param_display = DISPLAY_MAP.get(parametro, parametro)
    expected_unit = _expected_unit_for_parameter(parametro)
    return f"❌ Unidades incorrectas. Para el parámetro {param_display}, la unidad requerida es {expected_unit}."


# Lista de parámetros que el sistema sabe consultar (ámbito del PROMPT MAESTRO).
# Se muestra al usuario cuando escribe un índice que no reconocemos.
PARAMETROS_DISPONIBLES = [
    "Índice de Wobbe",
    "PCS (Poder Calorífico Superior)",
    "Densidad relativa",
    "Azufre total (S)",
    "H₂S + COS",
    "Mercaptanos (RSH)",
    "O₂ (oxígeno)",
    "CO₂",
    "Punto de rocío del agua (H₂O)",
    "Punto de rocío de hidrocarburos (HC)",
]


def _parametro_no_reconocido_message() -> str:
    opciones = "\n".join(f"- {p}" for p in PARAMETROS_DISPONIBLES)
    return (
        "No he reconocido el parámetro de tu consulta. "
        "Los parámetros disponibles son:\n\n"
        f"{opciones}\n\n"
        "Indícame uno de ellos junto con el país (España, Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia o UE) "
        "para darte los valores o comprobar el cumplimiento."
    )


def _mensaje_capacidades() -> str:
    opciones = "\n".join(f"- {p}" for p in PARAMETROS_DISPONIBLES)
    return (
        "Puedo ayudarte con consultas sobre **calidad del gas natural** en España, "
        "Portugal, Francia, Italia, Alemania, Países Bajos, Bélgica, Noruega, Polonia y la UE. Los parámetros que puedes consultar son:\n\n"
        f"{opciones}\n\n"
        "Puedes pedirme, por ejemplo: los valores de un parámetro en un país, "
        "comprobar si un valor cumple la normativa, o comparar dos países."
    )


def _mensaje_fuera_de_ambito() -> str:
    return (
        "Este chat no admite respuestas para ese tipo de preguntas. "
        "Solo respondo a consultas sobre **calidad del gas natural**: introduce un "
        "índice o parámetro de calidad del gas (Índice de Wobbe, PCS, O₂, CO₂, azufre, "
        "punto de rocío…) y, si quieres, un país y un valor."
    )


def _es_pregunta_capacidades(texto_norm: str) -> bool:
    """¿El usuario pregunta qué puede hacer/consultar el chatbot?"""
    patrones = (
        "que puedo consultar", "qué puedo consultar", "que puedo preguntar",
        "qué puedo preguntar", "que se puede consultar", "qué se puede consultar",
        "que valores se pueden consultar", "qué valores se pueden consultar",
        "que valores puedo", "qué valores puedo", "que parametros", "qué parámetros",
        "que parámetros", "qué parametros", "que indices", "qué índices",
        "que índices", "qué indices", "para que sirve", "para qué sirve",
        "que haces", "qué haces", "que puedes hacer", "qué puedes hacer",
        "como funciona", "cómo funciona", "que datos", "qué datos",
        "que preguntas puedo", "qué preguntas puedo", "opciones disponibles",
    )
    return any(p in texto_norm for p in patrones)


def _es_tema_calidad_gas(texto_norm: str) -> bool:
    """¿El mensaje trata, aunque sea vagamente, de calidad del gas natural?"""
    terminos = (
        "gas", "calidad", "wobbe", "pcs", "poder calorifico", "poder calorífico",
        "azufre", "sulfur", "h2s", "cos", "mercaptano", "rsh", "oxigeno", "oxígeno",
        "o2", "co2", "dioxido", "dióxido", "carbono", "rocio", "rocío", "densidad",
        "indice", "índice", "ppm", "nm3", "nm³", "kwh", "mj", "molar",
        "limite", "límite", "normativa", "especificac", "hidrocarburo",
    )
    return any(t in texto_norm for t in terminos)


def _evaluate_validated_comparison(parametro: str, pais: str, valor: float, unidad: str) -> str:
    # Filtrado estricto: solo el país pedido (España se usa por detrás para comparar).
    return _evaluar_paises(parametro, valor, unidad, [pais])


ALL_COUNTRIES = ["España", "Portugal", "Francia", "Italia", "Alemania", "Países Bajos", "Bélgica", "Noruega", "Polonia", "UE"]
PAIS_BASE = "España"


def _num_simple(x: Any) -> Optional[float]:
    s = str(x).replace(",", ".")
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
    return float(m.group(0)) if m else None


def _detectar_discrepancia(rec_oficial: Dict[str, Any], excel: Optional[Dict[str, Any]]) -> str:
    """Compara el límite OFICIAL con el del Excel (mismo parámetro/país). Nota si difieren
    (solo si las unidades coinciden y ambos son numéricos)."""
    if not excel or not excel.get("matches"):
        return ""
    m = excel["matches"][0]
    u_excel = _normalize_unit(_txt(m.get("unidad")).strip("()"))
    u_ofi = _normalize_unit(rec_oficial.get("unidad") or "")
    if u_excel and u_ofi and u_excel != u_ofi:
        return ""  # unidades distintas: no comparamos crudo
    difs = []
    for campo, etiqueta in (("limite_superior", "máximo"), ("limite_inferior", "mínimo")):
        o = _num_simple(rec_oficial.get(campo)); e = _num_simple(_txt(m.get(campo)))
        if o is not None and e is not None and abs(o - e) > 1e-6:
            difs.append(f"{etiqueta}: oficial {rec_oficial.get(campo)} vs Excel {_txt(m.get(campo))}")
    return "; ".join(difs)


def _consultar_norma(parametro: str, pais: str) -> Dict[str, Any]:
    """Consulta normativa. FUENTE PRIMARIA: documentación oficial (ontología verificada
    de los PDFs en data/raw). El Excel solo como índice/respaldo. Si hay dato oficial y
    el Excel discrepa, prevalece el oficial y se marca la discrepancia."""
    oficial = fuente_oficial.consultar(parametro, pais)
    try:
        excel = consultar_excel(parametro, pais)
    except Exception:
        excel = {"count": 0, "matches": []}
    if oficial.get("count"):
        disc = _detectar_discrepancia(oficial["matches"][0], excel)
        if disc:
            oficial["matches"][0]["discrepancia"] = disc
        return oficial
    return excel  # el oficial no cubre este caso → respaldo del Excel


def _evaluar_norma(parametro: str, pais: str, valor: float, unidad: Optional[str] = None) -> Dict[str, Any]:
    """Evaluación de cumplimiento contra el límite OFICIAL; Excel solo como respaldo."""
    oficial = fuente_oficial.evaluar(parametro, pais, valor, unidad)
    if oficial.get("count"):
        try:
            disc = _detectar_discrepancia(oficial["matches"][0], consultar_excel(parametro, pais))
            if disc:
                oficial["matches"][0]["discrepancia"] = disc
        except Exception:
            pass
        return oficial
    return evaluar_cumplimiento(parametro, pais, valor, unidad=unidad)


def _cita_oficial(item: Dict[str, Any]) -> str:
    """Cita completa de un registro: norma · organismo · fecha · artículo/página — URL."""
    doc = item.get("documento") or "Fuente no especificada"
    partes = [f"**{doc}**"]
    for campo in ("organismo", "fecha", "articulo"):
        v = (item.get(campo) or "").strip()
        if v:
            partes.append(v)
    linea = " · ".join(partes)
    url = (item.get("url") or item.get("pdf") or "").strip()
    if url:
        linea += f" — {url}"
    estado = item.get("estado") or ""
    if estado and estado != "VERIFICADO":
        linea += f" _({estado})_"
    return linea


def _norm_pais(p: Any) -> str:
    s = str(p).strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        s = s.replace(a, b)
    return s


def _txt(v: Any) -> str:
    """Coerciona a texto de forma robusta (NaN de pandas / None -> '')."""
    if v is None:
        return ""
    if isinstance(v, float) and v != v:  # NaN
        return ""
    return str(v).strip()


def _sin_limite(s: str) -> bool:
    """¿La celda indica ausencia de límite numérico?"""
    s = s.lower()
    return (s in ("-", "") or "especific" in s or s.startswith("sin")
            or "no regulad" in s or "monitor" in s or "incluido" in s or "no es fijo" in s)


def _unidad_de_pais(parametro: str, pais: str) -> Optional[str]:
    """Devuelve la unidad que exige la normativa de `pais` para `parametro`."""
    try:
        resp = _consultar_norma(parametro, pais)
    except Exception:
        return None
    for m in resp.get("matches", []):
        u = (m.get("unidad") or m.get("unidad_registro") or "").strip()
        if u:
            return u
    return None


def _estado_comparabilidad(parametro: str, unidad_es: Optional[str], unidad_pais: Optional[str]) -> str:
    """Compara la normativa española vs la del país por su unidad/magnitud.

    - 'Directamente Comparable': misma unidad (o equivalente, factor 1).
    - 'Comparable con Normalización': unidades distintas, misma magnitud física.
    - 'No Comparable': magnitudes incompatibles o falta de datos.
    """
    if not unidad_es or not unidad_pais:
        return "No Comparable"
    conv = convertir_unidades(1.0, unidad_pais, unidad_es, parametro)
    if "valor_convertido" not in conv:
        return "No Comparable"
    if "Sin conversión" in conv.get("formula", ""):
        return "Directamente Comparable"
    return "Comparable con Normalización"


def _celda_es_vs_pais(parametro: str, pais: str, unidad_pais: Optional[str], unidad_es: Optional[str]) -> str:
    """Texto de la celda de comparabilidad cruzada: 'España vs [País]: [Estado]'."""
    if _norm_pais(pais) == _norm_pais(PAIS_BASE):
        return "— (base de referencia)"
    estado = _estado_comparabilidad(parametro, unidad_es, unidad_pais)
    return f"España vs {pais}: {estado}"


_PAIS_FUZZY = {"espana": "España", "portugal": "Portugal", "francia": "Francia",
               "italia": "Italia", "alemania": "Alemania",
               "holanda": "Países Bajos", "nederland": "Países Bajos",
               "belgica": "Bélgica", "belgium": "Bélgica",
               "noruega": "Noruega", "norway": "Noruega",
               "polonia": "Polonia", "poland": "Polonia"}


def _detectar_paises(texto_norm: str) -> list:
    """Devuelve la lista de países mencionados, tolerando erratas (ej. 'frnacia').

    Vacía si el usuario no menciona ningún país (→ se asumirán todos).
    """
    t = _norm_pais(texto_norm)  # minúsculas sin acentos
    encontrados: list = []
    # 1) coincidencia directa por subcadena (evita falsos positivos con "espan")
    for kw, nombre in [("espan", "España"), ("spain", "España"),
                       ("portugal", "Portugal"), ("francia", "Francia"), ("france", "Francia"),
                       ("italia", "Italia"), ("italy", "Italia"),
                       ("alemania", "Alemania"), ("germania", "Alemania"), ("germany", "Alemania"), ("deutschland", "Alemania"),
                       ("paises bajos", "Países Bajos"), ("holanda", "Países Bajos"), ("netherlands", "Países Bajos"), ("nederland", "Países Bajos"),
                       ("belgica", "Bélgica"), ("belgium", "Bélgica"), ("belgique", "Bélgica"), ("belgie", "Bélgica"),
                       ("noruega", "Noruega"), ("norway", "Noruega"), ("norge", "Noruega"),
                       ("polonia", "Polonia"), ("poland", "Polonia"), ("polska", "Polonia"),
                       ("europa", "UE"), ("union europea", "UE"), ("easee", "UE")]:
        if kw in t and nombre not in encontrados:
            encontrados.append(nombre)
    # "UE" suelto (no la "ue" interna de "fuente", "que", "pequeño"…)
    if "UE" not in encontrados and re.search(r"(?<![\w])ue(?![\w])", t):
        encontrados.append("UE")
    if encontrados:
        return encontrados
    # 2) coincidencia difusa por palabra (tolera erratas: frnacia, portgal, espanha…)
    for palabra in re.findall(r"[a-z]{4,}", t):
        match = difflib.get_close_matches(palabra, list(_PAIS_FUZZY.keys()), n=1, cutoff=0.78)
        if match:
            nombre = _PAIS_FUZZY[match[0]]
            if nombre not in encontrados:
                encontrados.append(nombre)
    return encontrados


def _evaluar_paises(parametro: str, valor: float, unidad: Optional[str], paises: list, todos: bool = False) -> str:
    """Evalúa un valor contra los países indicados y devuelve la tabla.

    FILTRADO ESTRICTO: solo se muestran filas de los países pedidos. España se
    consulta SIEMPRE por detrás (en memoria) para la columna 'Comparabilidad
    normativa', pero NO aparece como fila salvo que el usuario la pida.
    """
    unidad_es = _unidad_de_pais(parametro, PAIS_BASE)  # background: solo para comparar
    filas: list = []
    for pais in paises:
        resp = _evaluar_norma(parametro, pais, valor, unidad=unidad)
        if resp.get("error"):
            continue
        filas.extend(resp.get("matches", []))
    if not filas:
        return (
            f"No encontré registros de '{parametro}' en {', '.join(paises)} "
            f"para evaluar el valor {valor}{f' {unidad}' if unidad else ''}."
        )

    if todos:
        titulo = f"**¿En qué países cumple {parametro} = {valor}{f' {unidad}' if unidad else ''}?**"
    else:
        titulo = f"**Evaluación de cumplimiento — {', '.join(paises)}**"
    # UNA SOLA TABLA: cumplimiento + límite + condiciones de referencia + comparabilidad
    # en la misma fila (las condiciones van AL LADO de los valores, no debajo).
    lines = [
        titulo,
        "",
        "| País | Parámetro | Valor evaluado | Límite normativo | Condiciones de referencia | Resultado | Detalle | Comparabilidad |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    conversiones: list = []
    evidencias: list = []
    cumple_en: list = []
    for item in filas[:12]:
        pais_fila = item.get("pais", "")
        nombre = str(item.get("parametro") or parametro).strip()
        estado = item.get("cumple", "No evaluable")
        detalle = item.get("detalle", "")
        inf = _txt(item.get("limite_inferior")) or "-"
        sup = _txt(item.get("limite_superior")) or "-"
        unidad_reg = item.get("unidad_registro") or unidad or ""
        condiciones = _normalize_condition_text(item.get("condiciones") or item.get("condiciones de medicion") or item.get("condiciones de medición"))
        condiciones = condiciones.replace("bars", "bar").strip() if condiciones else "—"
        res = "🟢 Cumple" if estado == "Cumple" else ("🔴 No cumple" if estado == "No cumple" else "⚪ No evaluable")
        comp = _celda_es_vs_pais(parametro, pais_fila, unidad_reg, unidad_es)
        # Límite normativo compacto (en la misma fila).
        if _sin_limite(inf) and _sin_limite(sup):
            limite_cell = "Sin límite numérico"
        else:
            limite_cell = f"{inf} / {sup}" + (f" {unidad_reg}" if unidad_reg else "")
        # Valor evaluado, con nota de conversión si la hubo.
        valor_eval = item.get("valor_evaluado", valor)
        valor_usr = item.get("valor_usuario", valor)
        unidad_usr = item.get("unidad_usuario", unidad or "")
        conv = item.get("conversion", "")
        if conv and str(valor_usr) != str(valor_eval):
            celda = f"{valor_eval} {unidad_reg} (de {valor_usr} {unidad_usr})"
            if conv not in conversiones and "Sin conversión" not in conv:
                conversiones.append(conv)
        else:
            celda = f"{valor_eval} {unidad_reg}".strip()
        lines.append(f"| {pais_fila} | {nombre} | {celda} | {limite_cell} | {condiciones} | {res} | {detalle} | {comp} |")
        evidencias.append(f"- **{pais_fila}** · {nombre}: {_cita_oficial(item)}")
        if item.get("discrepancia"):
            evidencias.append(f"  - ⚠ Discrepancia con el Excel (prevalece la fuente oficial): {item['discrepancia']}")
        if item.get("nota"):
            evidencias.append(f"  - 📝 Nota de la fuente: {item['nota']}")
        if estado == "Cumple":
            cumple_en.append(f"{pais_fila} ({nombre})")
    bloques = list(lines)
    if conversiones:
        bloques += ["", "**Conversión aplicada**", ""] + [f"- {c}" for c in conversiones]
    if evidencias:
        bloques += ["", "**Evidencias**", ""] + evidencias
    if todos:
        resumen = ", ".join(cumple_en) if cumple_en else "ninguno de los evaluados"
        bloques += ["", f"**Cumple en:** {resumen}."]
    return "\n".join(bloques)


def _comparar_normativa(parametro: str, paises: list) -> str:
    """Compara la NORMATIVA (límites/unidades) entre países, SIN valor del usuario.

    Muestra una fila por país enfrentando sus límites, con la columna de
    comparabilidad cruzada (España como referencia).
    """
    unidad_es = _unidad_de_pais(parametro, PAIS_BASE)
    if len(paises) <= 1:
        titulo = f"**Límites normativos de {parametro} — {paises[0] if paises else ''}**"
    else:
        titulo = f"**Comparación normativa de {parametro} — {' vs '.join(paises)}**"
    lines = [
        titulo,
        "",
        "| País | Parámetro | Límites | Unidad | Condiciones | Comparabilidad normativa |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    hubo = False
    estados: list = []
    normalizaciones: list = []  # PCS/Wobbe llevados a condiciones de España (Tabla A.1)
    evidencias: list = []
    for pais in paises:
        try:
            resp = _consultar_norma(parametro, pais)
        except Exception:
            continue
        for m in resp.get("matches", []):
            hubo = True
            nombre = str(m.get("parametro") or parametro).strip()
            inf = _txt(m.get("limite_inferior")) or "-"
            sup = _txt(m.get("limite_superior")) or "-"
            unidad_reg = _txt(m.get("unidad")).strip("()").replace("^3", "³").replace("^2", "²")
            cond = _normalize_condition_text(_txt(m.get("condiciones"))) or "—"
            if _sin_limite(inf) and _sin_limite(sup):
                limite = "Sin límite numérico"
            else:
                limite = f"{inf} / {sup}"
            comp = _celda_es_vs_pais(parametro, pais, unidad_reg, unidad_es)
            if _norm_pais(pais) != _norm_pais(PAIS_BASE):
                estados.append((pais, _estado_comparabilidad(parametro, unidad_es, unidad_reg)))
                nota = _limites_en_condiciones_espana(parametro, pais, inf, sup, unidad_reg, nombre)
                if nota:
                    normalizaciones.append(nota)
            lines.append(f"| {pais} | {nombre} | {limite} | {unidad_reg or '—'} | {cond} | {comp} |")
            evidencias.append(f"- **{pais}** · {nombre}: {_cita_oficial(m)}")
            if m.get("discrepancia"):
                evidencias.append(f"  - ⚠ Discrepancia con el Excel (prevalece la oficial): {m['discrepancia']}")
            if m.get("nota"):
                evidencias.append(f"  - 📝 Nota de la fuente: {m['nota']}")
    if not hubo:
        return f"No encontré datos normativos de '{parametro}' en {', '.join(paises)}."
    if normalizaciones:
        lines += [
            "",
            "**Normalización a condiciones de España** (combustión 0 °C; ISO 13443, Tabla A.1)",
            "",
        ] + normalizaciones
    if evidencias:
        lines += ["", "**Evidencias (fuente oficial)**", ""] + evidencias
    if estados:
        estados_u = list(dict.fromkeys(estados))  # dedup (un país puede tener varias filas)
        sint = "; ".join(f"España vs {p}: {e}" for p, e in estados_u)
        lines += ["", f"**Síntesis:** {sint}."]
    return "\n".join(lines)


def _num_limite(x: Any) -> Optional[float]:
    """Extrae el primer número de un límite ('48,17', 'no especificado'…)."""
    s = str(x).strip().replace(",", ".")
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
    return float(m.group(0)) if m else None


def _limites_en_condiciones_espana(
    parametro: str, pais: str, inf: Any, sup: Any, unidad_reg: str, nombre: str
) -> Optional[str]:
    """Para PCS/Wobbe de un país no-España: devuelve sus límites llevados a las
    condiciones españolas (unidad kWh/m³ + combustión 0 °C, Tabla A.1). None si no aplica."""
    if _slug_param_comb(parametro) not in {"pcs", "wobbe"}:
        return None
    cond = _COND_PAIS.get(_norm_pais(pais))
    misma_unidad = _normalize_unit(unidad_reg or "kwh/m3") == _normalize_unit("kWh/m³")
    # Si el país ya está en base española (combustión 0 °C) y misma unidad, no hay nada que cambiar.
    if cond == (0, 0) and misma_unidad:
        return None
    vi, vs = _num_limite(inf), _num_limite(sup)
    if vi is None and vs is None:
        return None
    factor = 1.0
    partes = []
    for v in (vi, vs):
        if v is None:
            partes.append("—")
            continue
        # 1) Unidad -> kWh/m³ (si hace falta), de forma determinista.
        if unidad_reg and not misma_unidad:
            cu = convertir_unidades(v, unidad_reg, "kWh/m³", parametro)
            if "valor_convertido" in cu:
                v = cu["valor_convertido"]
        # 2) Condición de combustión del país -> España (Tabla A.1).
        cr = convertir_a_condiciones_espana(v, parametro, pais)
        factor = cr.get("factor", 1.0)
        partes.append(f"{cr['valor_convertido']:.2f}".replace(".", ","))
    return f"- **{pais}** · {nombre}: {partes[0]} / {partes[1]} kWh/m³ (de {unidad_reg or 'kWh/m³'}, combustión {cond[0] if cond else '?'} → 0 °C, factor {factor:g})"


def _coma(x: Any) -> str:
    try:
        return f"{round(float(x), 4):g}".replace(".", ",")
    except (TypeError, ValueError):
        return str(x)


def _es_consulta_condiciones(texto_norm: str) -> bool:
    """¿Pide llevar un valor a las condiciones de referencia (combustión) de España?"""
    claves = (
        "condiciones de españa", "condiciones de espana", "condiciones espanola",
        "condiciones española", "condiciones espanolas", "condiciones españolas",
        "condicion de combustion", "condiciones de combustion", "temperatura de combustion",
        "tabla a1", "tabla a.1", "iso 13443", "base espanola", "base española",
        "referencia espanola", "referencia española", "a condiciones espanola",
        "normalizar a espana", "normalizar a españa", "pasar a espana", "pasar a españa",
    )
    return any(k in texto_norm for k in claves)


def _responder_condiciones(parametro: str, valor, unidad, pais_origen: str) -> str:
    """Convierte un PCS/Wobbe de `pais_origen` a las condiciones de combustión de España."""
    display = DISPLAY_MAP.get(parametro, parametro)
    if _slug_param_comb(parametro) not in {"pcs", "wobbe"}:
        return (
            f"El parámetro **{display}** se mide a 0 °C y no depende de la temperatura de "
            f"combustión, así que es directamente comparable entre {pais_origen} y España "
            "sin ajustar las condiciones de referencia."
        )
    if valor is None:
        # Sin valor del usuario: muestra los límites del país ya normalizados a España.
        return _comparar_normativa(parametro, [PAIS_BASE, pais_origen])

    pasos = []
    v = float(valor)
    u = unidad or ""
    if u and _normalize_unit(u) != _normalize_unit("kWh/m³"):
        cu = convertir_unidades(v, u, "kWh/m³", parametro)
        if "valor_convertido" in cu:
            pasos.append(f"- Unidad: {_coma(v)} {u} → {_coma(cu['valor_convertido'])} kWh/m³  ({cu.get('formula','')})")
            v = cu["valor_convertido"]
    cr = convertir_a_condiciones_espana(v, parametro, pais_origen)
    pasos.append(
        f"- Combustión: {cr['condiciones_origen']} → {cr['condiciones_destino']}  "
        f"(Tabla A.1, factor {cr['factor']:g})"
    )
    return "\n".join([
        f"**{display} de {pais_origen} en condiciones de España**",
        "",
        f"**{_coma(valor)} {unidad or ''}** ({pais_origen}) → **{_coma(cr['valor_convertido'])} kWh/m³** (España)",
        "",
        *pasos,
        "",
        f"_Fuente del factor: {cr['fuente']}._",
    ])


# --- Comparativa estructurada (sección de la web con desplegables) ----------
# Unidades ofrecidas por parámetro (la 1.ª es la base normativa española).
PARAMETROS_UI = [
    {"slug": "wobbe", "label": "Índice de Wobbe", "unidades": ["kWh/m³", "MJ/m³"]},
    {"slug": "pcs", "label": "PCS (Poder Calorífico Superior)", "unidades": ["kWh/m³", "MJ/m³"]},
    {"slug": "densidad relativa", "label": "Densidad relativa", "unidades": ["adimensional"]},
    {"slug": "s total", "label": "Azufre total (S)", "unidades": ["mg/m³", "mg/Nm³", "ppm"]},
    {"slug": "h2s+cos", "label": "H₂S + COS", "unidades": ["mg/m³", "mg/Nm³", "ppm"]},
    {"slug": "rsh", "label": "Mercaptanos (RSH)", "unidades": ["mg/m³", "mg/Nm³", "ppm"]},
    {"slug": "o2", "label": "O₂ (oxígeno)", "unidades": ["% molar", "ppm"]},
    {"slug": "co2", "label": "CO₂", "unidades": ["% molar", "ppm"]},
    {"slug": "h2o(rocío)", "label": "Punto de rocío del agua (H₂O)", "unidades": ["°C", "K", "°F"]},
    {"slug": "hc(rocío)", "label": "Punto de rocío de HC", "unidades": ["°C", "K", "°F"]},
]
PAISES_UI = ["Portugal", "Francia", "Italia", "Alemania", "Países Bajos", "Bélgica", "Noruega", "Polonia", "UE"]  # España es siempre la base de referencia


def _es_mg_por_volumen(unidad: str) -> bool:
    """True si la unidad es una concentración másica por volumen (mg/m³, mg/Nm³, mg/Sm³).

    Estas dependen de la temperatura del volumen de referencia (gas ideal); el % mol,
    el ppm (molar) y las adimensionales NO.
    """
    s = (unidad or "").lower().replace(" ", "")
    return "mg" in s and ("m³" in s or "m3" in s or "nm" in s or "sm" in s)


def comparar_estructurado(parametro_slug: str, paises: list, unidad_destino: str = "") -> Dict[str, Any]:
    """Comparativa para la sección con desplegables. Devuelve filas estructuradas y,
    para PCS/Wobbe de países con distinta temperatura de combustión, el equivalente
    en condiciones de España (ISO 13443, Tabla A.1)."""
    orden = [PAIS_BASE] + [p for p in (paises or []) if _norm_pais(p) != _norm_pais(PAIS_BASE)]
    display = DISPLAY_MAP.get(parametro_slug, parametro_slug)
    es_combustion = _slug_param_comb(parametro_slug) in {"pcs", "wobbe"}
    filas: list = []
    notas: list = []
    for pais in orden:
        try:
            matches = _consultar_norma(parametro_slug, pais).get("matches", [])
        except Exception:
            matches = []
        for m in matches:
            nombre = str(m.get("parametro") or parametro_slug).strip()
            inf_raw = _txt(m.get("limite_inferior")) or "-"
            sup_raw = _txt(m.get("limite_superior")) or "-"
            unidad_reg = _txt(m.get("unidad")).strip("()").replace("^3", "³").replace("^2", "²")
            # Condiciones POR PARÁMETRO (de la notación del registro), no del país:
            # en la UE el Wobbe es 15/15 pero las concentraciones se expresan a 0/0.
            ccomb, cmed = _parse_notac(m.get("notacion") or "(0/0)")
            cond_txt = f"comb. {_coma(ccomb)} °C · med. {_coma(cmed)} °C"
            sin_lim = _sin_limite(inf_raw) and _sin_limite(sup_raw)
            es_base = _norm_pais(pais) == _norm_pais(PAIS_BASE)

            def a_unidad(raw):
                v = _num_limite(raw)
                if v is None:
                    return None
                if unidad_destino and unidad_destino != "adimensional" and unidad_reg \
                        and _normalize_unit(unidad_destino) != _normalize_unit(unidad_reg):
                    cu = convertir_unidades(v, unidad_reg, unidad_destino, parametro_slug)
                    return cu.get("valor_convertido") if "valor_convertido" in cu else None
                return v

            vi, vs = a_unidad(inf_raw), a_unidad(sup_raw)
            unidad_out = (unidad_destino or unidad_reg or "—")

            vi_es = vs_es = None
            factor = 1.0
            if not es_base and not sin_lim:
                if es_combustion:
                    if vi is not None:
                        cr = convertir_a_condiciones_espana(vi, parametro_slug, pais)
                        vi_es, factor = cr["valor_convertido"], cr["factor"]
                    if vs is not None:
                        cr = convertir_a_condiciones_espana(vs, parametro_slug, pais)
                        vs_es, factor = cr["valor_convertido"], cr["factor"]
                    if factor and factor != 1.0:
                        notas.append(f"{pais}: combustión {_coma(ccomb)} °C → 0 °C (× {factor:g}, ISO 13443 Tabla A.1)")
                elif cmed and cmed != 0 and _es_mg_por_volumen(unidad_out):
                    # Concentración MÁSICA (mg/m³) referida a un volumen a T ≠ 0 °C
                    # (p. ej. Italia: mg/Sm³ a 15 °C). Se normaliza el volumen a 0 °C
                    # con factor (273,15 + T_vol)/273,15 (base de gas ideal). El % mol,
                    # ppm (molar) y adimensionales NO dependen de la temperatura.
                    fvol = (273.15 + cmed) / 273.15
                    vi_es = round(vi * fvol, 6) if vi is not None else None
                    vs_es = round(vs * fvol, 6) if vs is not None else None
                    factor = fvol
                    notas.append(f"{pais}: volumen {_coma(cmed)} °C → 0 °C (× {fvol:.4f}, base de gas ideal)")
                else:
                    # No depende de la temperatura de combustión ni del volumen: mismo valor, referido a 0/0.
                    vi_es, vs_es = vi, vs

            def rng(a, b):
                if sin_lim:
                    return "Sin límite numérico"
                return f"{_coma(a) if a is not None else '—'} / {_coma(b) if b is not None else '—'}"

            filas.append({
                "pais": pais,
                "parametro": nombre,
                "limite": rng(vi, vs),
                "unidad": "—" if sin_lim else unidad_out,
                "condiciones": cond_txt,
                "es_base": es_base,
                "limite_espana": (
                    None if es_base
                    else ("Sin límite numérico" if sin_lim
                          else (rng(vi_es, vs_es) if (vi_es is not None or vs_es is not None) else None))
                ),
                "factor_iso": (factor if (es_combustion and not es_base and factor != 1.0) else None),
                # Cita de la fuente oficial (para mostrar en el frontend).
                "fuente": m.get("documento") or "",
                "organismo": m.get("organismo") or "",
                "fecha": m.get("fecha") or "",
                "articulo": m.get("articulo") or "",
                "url": m.get("url") or m.get("pdf") or "",
                "estado": m.get("estado") or "",
                "discrepancia": m.get("discrepancia") or "",
                # Condiciones/matices que el reglamento adjunta al límite (p. ej. el O₂
                # de la EN 16726: ≤1 % general, ≤0,01 %/0,001 % por evaluación).
                "nota": m.get("nota") or "",
            })
    return {
        "parametro": display,
        "unidad": unidad_destino,
        "es_combustion": es_combustion,
        "filas": filas,
        "notas_iso": list(dict.fromkeys(notas)),
    }


# --- Matriz comparativa avanzada (heatmap) ----------------------------------
# Filas = países, columnas = parámetros. Cada celda: rango normalizado a condiciones
# de España, un NIVEL frente a España (para el color) y un FLAG si hubo diferencia
# metodológica (unidad o condiciones distintas → se aplicó conversión).
PAISES_MATRIZ = ["España", "Portugal", "Francia", "Italia", "Alemania", "Países Bajos", "Bélgica", "Noruega", "Polonia", "UE"]


def _celda_heatmap(slug, pais, unidad_es, notac_es, es_rng, es_maximo, ancho_es):
    es_base = _norm_pais(pais) == _norm_pais(PAIS_BASE)
    resp = fuente_oficial.consultar(slug, pais)
    if not resp.get("matches"):
        return {"valor": "—", "nivel": "sin_dato", "flag": False, "flag_desc": ""}
    m = resp["matches"][0]
    r = _rango_de_match(m, slug, pais, unidad_es)
    est = r.get("estado")

    def fr(lo, hi):
        return f"{_coma(lo) if lo is not None else '—'} / {_coma(hi) if hi is not None else '—'}"

    if est in ("sin_datos", "sin_dato"):
        return {"valor": "—", "nivel": "sin_dato", "flag": False, "flag_desc": ""}
    if est == "incomparable":
        return {"valor": "≠ unidades", "nivel": "incomparable", "flag": True, "flag_desc": "No comparable de forma determinista"}
    if est == "sin_limite":
        return {"valor": "Sin límite", "nivel": "sin_limite", "flag": False, "flag_desc": ""}

    # Flag metodológico: solo si hay límite real con unidad o condiciones RELEVANTES
    # distintas a España (la combustión solo cuenta para PCS/Wobbe).
    difs = []
    if not es_base:
        u = _txt(m.get("unidad"))
        if u and unidad_es and _normalize_unit(u) != _normalize_unit(unidad_es):
            difs.append(f"unidad {u}")
        if m.get("notacion") and notac_es and not _condiciones_iguales(slug, m.get("notacion"), notac_es):
            difs.append(f"condiciones {m.get('notacion')}")
    flag = bool(difs)
    flag_desc = (" · ".join(difs) + " → convertido a condiciones de España") if flag else ""

    if es_base:
        nivel = "base"
    elif es_rng.get("estado") != "ok":
        nivel = "sin_ref"
    else:
        lo = r["lo"] if r["lo"] is not None else float("-inf")
        hi = r["hi"] if r["hi"] is not None else float("inf")
        if es_maximo:
            es_hi = es_rng["hi"] if es_rng["hi"] is not None else float("inf")
            nivel = "restrictivo" if hi < es_hi - 1e-9 else ("amplio" if hi > es_hi + 1e-9 else "igual")
        else:
            ancho = hi - lo
            if ancho_es is None:
                nivel = "igual"
            else:
                nivel = "restrictivo" if ancho < ancho_es - 1e-9 else ("amplio" if ancho > ancho_es + 1e-9 else "igual")
    return {"valor": fr(r["lo"], r["hi"]), "nivel": nivel, "flag": flag, "flag_desc": flag_desc}


def matriz_comparativa() -> Dict[str, Any]:
    """Heatmap: filas=países, columnas=parámetros, celdas con nivel (color) y flag."""
    cols = []
    filas = {p: {} for p in PAISES_MATRIZ}
    for pinfo in PARAMETROS_UI:
        slug = pinfo["slug"]
        cols.append({"slug": slug, "label": pinfo["label"]})
        es = fuente_oficial.consultar(slug, PAIS_BASE)
        esm = es["matches"][0] if es.get("matches") else None
        unidad_es = (esm.get("unidad") if esm else "") or ""
        notac_es = esm.get("notacion") if esm else None
        es_rng = _rango_de_match(esm, slug, PAIS_BASE, unidad_es) if esm else {"estado": "sin_datos"}
        es_maximo = es_rng.get("estado") == "ok" and es_rng.get("lo") is None
        ancho_es = None
        if es_rng.get("estado") == "ok":
            lo = es_rng["lo"] if es_rng["lo"] is not None else float("-inf")
            hi = es_rng["hi"] if es_rng["hi"] is not None else float("inf")
            ancho_es = hi - lo
        for pais in PAISES_MATRIZ:
            filas[pais][slug] = _celda_heatmap(slug, pais, unidad_es, notac_es, es_rng, es_maximo, ancho_es)
    return {
        "paises": PAISES_MATRIZ,
        "parametros": cols,
        "filas": [{"pais": p, "celdas": filas[p]} for p in PAISES_MATRIZ],
        "unidad_nota": "Valores normalizados a unidad y condiciones de España (ISO 13443 para PCS/Wobbe).",
    }


# --- Fuente normativa: ¿de qué reglamento procede cada dato? ----------------
# Se lee de la ontología validada (data/ontologia/ontologia_enagas.yaml), que
# guarda la fuente, el artículo y la página verificados por parámetro y país.
_ONTOLOGIA_CACHE: Dict[str, Any] = {}
_PARAM_A_ONTO = {
    "wobbe": "WOBBE", "pcs": "PCS", "densidad relativa": "DENS_REL",
    "s total": "S_TOTAL", "h2s+cos": "H2S_COS", "rsh": "RSH",
    "o2": "O2", "co2": "CO2", "h2o(rocío)": "PR_H2O", "hc(rocío)": "PR_HC",
}
_PAIS_A_CODIGO = {"espana": "ES", "portugal": "PT", "francia": "FR", "ue": "UE", "europa": "UE",
                  "italia": "IT", "italy": "IT", "alemania": "DE", "germany": "DE",
                  "deutschland": "DE", "germania": "DE",
                  "paises bajos": "NL", "holanda": "NL", "netherlands": "NL", "nederland": "NL",
                  "belgica": "BE", "belgium": "BE", "belgique": "BE", "belgie": "BE",
                  "noruega": "NOR", "norway": "NOR", "norge": "NOR",
                  "polonia": "PL", "poland": "PL", "polska": "PL"}
_CODIGO_A_PAIS = {"ES": "España", "PT": "Portugal", "FR": "Francia", "UE": "UE",
                  "IT": "Italia", "DE": "Alemania", "NL": "Países Bajos", "BE": "Bélgica",
                  "NOR": "Noruega", "PL": "Polonia"}
_PAISES_FUENTE = ["España", "Portugal", "Francia", "Italia", "Alemania", "Países Bajos", "Bélgica", "Noruega", "Polonia", "UE"]


def _cargar_ontologia() -> Dict[str, Any]:
    """Carga (una sola vez) la ontología validada. Devuelve {} si no es posible."""
    if "data" in _ONTOLOGIA_CACHE:
        return _ONTOLOGIA_CACHE["data"]
    data: Dict[str, Any] = {}
    try:
        import yaml  # en requirements.txt
        ruta = os.path.join(os.path.dirname(__file__), "data", "ontologia", "ontologia_enagas.yaml")
        if not os.path.exists(ruta):
            import glob
            cand = glob.glob(os.path.join(os.path.dirname(__file__), "data", "**", "ontologia_enagas.yaml"), recursive=True)
            ruta = cand[0] if cand else ruta
        with open(ruta, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"[fuente] No se pudo cargar la ontología ({exc}).")
    _ONTOLOGIA_CACHE["data"] = data
    return data


def _glosario_fuentes() -> Dict[str, Dict[str, Any]]:
    onto = _cargar_ontologia()
    fuentes = (onto.get("ontologia") or {}).get("fuentes_normativas") or []
    return {f.get("id"): f for f in fuentes if isinstance(f, dict) and f.get("id")}


def _fuentes_de(parametro_slug: str, paises: list) -> list:
    """Lista de fuentes [{pais, reglamento, ubicacion, estado, publicacion, nota}]."""
    onto = _cargar_ontologia()
    params = onto.get("parametros") or {}
    clave = _PARAM_A_ONTO.get(parametro_slug)
    if not clave or clave not in params:
        return []
    limites = params[clave].get("limites") or {}
    glos = _glosario_fuentes()
    salida = []
    for pais in paises:
        cod = _PAIS_A_CODIGO.get(_norm_pais(pais))
        if not cod or cod not in limites:
            continue
        lim = limites[cod] or {}
        info = glos.get(lim.get("fuente"), {})
        salida.append({
            "pais": _CODIGO_A_PAIS.get(cod, pais),
            "reglamento": info.get("nombre") or lim.get("fuente") or "No consta en la fuente",
            "ubicacion": lim.get("articulo") or info.get("tabla_calidad") or "—",
            "estado": lim.get("estado_verificacion") or "—",
            "publicacion": info.get("publicacion") or info.get("referencia_legal") or "",
            "nota": lim.get("nota") or "",
        })
    return salida


def _responder_fuente(parametro_slug: str, paises: list) -> str:
    datos = _fuentes_de(parametro_slug, paises)
    display = DISPLAY_MAP.get(parametro_slug, parametro_slug)
    if not datos:
        return (
            f"No tengo registrada la fuente normativa de '{display}' en la ontología validada "
            f"para {', '.join(paises)}."
        )
    lines = [
        f"**Fuente normativa de {display}**",
        "",
        "| País | Reglamento / Norma | Ubicación en el documento | Estado |",
        "| --- | --- | --- | --- |",
    ]
    extra = []
    for d in datos:
        lines.append(f"| {d['pais']} | {d['reglamento']} | {d['ubicacion']} | {d['estado']} |")
        if d["publicacion"]:
            extra.append(f"- **{d['pais']}**: {d['publicacion']}")
        if d["nota"]:
            extra.append(f"- **{d['pais']}** (nota): {d['nota']}")
    if extra:
        lines += ["", "**Publicación / referencia**", ""] + extra
    return "\n".join(lines)


def _listar_fuentes() -> str:
    """Lista los reglamentos primarios realmente usados por los parámetros."""
    onto = _cargar_ontologia()
    params = onto.get("parametros") or {}
    glos = _glosario_fuentes()
    usados: list = []
    for p in params.values():
        for lim in (p.get("limites") or {}).values():
            fc = (lim or {}).get("fuente")
            if fc and fc not in usados:
                usados.append(fc)
    if not usados:
        return "No pude cargar la lista de reglamentos de la ontología validada."
    lines = [
        "**Reglamentos y normas que utiliza el comparador**",
        "",
        "| País | Reglamento / Norma | Publicación |",
        "| --- | --- | --- |",
    ]
    for fc in usados:
        info = glos.get(fc, {})
        pais = _CODIGO_A_PAIS.get(info.get("pais"), info.get("pais") or "—")
        nombre = info.get("nombre") or fc
        pub = info.get("publicacion") or info.get("referencia_legal") or "—"
        lines.append(f"| {pais} | {nombre} | {pub} |")
    return "\n".join(lines)


def _normativa_de_pais(paises: list) -> str:
    """#1 — «¿Qué normativa aplican en [país]?» Lista las normas oficiales que ese país
    aplica a la calidad del gas (fuentes distintas usadas en sus parámetros)."""
    onto = _cargar_ontologia()
    params = onto.get("parametros") or {}
    glos = _glosario_fuentes()
    bloques: list = []
    for pais in paises:
        cod = _PAIS_A_CODIGO.get(_norm_pais(pais))
        if not cod:
            continue
        usados: list = []
        for p in params.values():
            fc = ((p.get("limites") or {}).get(cod) or {}).get("fuente")
            if fc and fc not in usados:
                usados.append(fc)
        nombre_pais = _CODIGO_A_PAIS.get(cod, pais)
        if not usados:
            bloques.append(f"No tengo registrada la normativa de calidad del gas de {nombre_pais}.")
            continue
        lineas = [f"**Normativa de calidad del gas aplicable en {nombre_pais}**", ""]
        for fc in usados:
            info = glos.get(fc, {})
            partes = [f"- **{info.get('nombre') or fc}**"]
            if info.get("organismo"):
                partes.append(info["organismo"])
            pub = info.get("publicacion") or info.get("referencia_legal") or ""
            if pub:
                partes.append(pub)
            linea = " · ".join(partes)
            url = fuente_oficial.url_de(info)
            if url:
                linea += f" — {url}"
            lineas.append(linea)
            ambito = info.get("tabla_calidad") or info.get("ambito") or ""
            if ambito:
                lineas.append(f"  - {ambito}")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques) if bloques else "No encontré normativa para el país indicado."


def _rango_de_match(m: Dict[str, Any], parametro: str, pais: str, unidad_es: Optional[str]) -> Dict[str, Any]:
    """Lleva el rango de un registro `m` a la UNIDAD y CONDICIONES de España (ISO 13443)."""
    inf = _num_limite(_txt(m.get("limite_inferior")))
    sup = _num_limite(_txt(m.get("limite_superior")))
    if inf is None and sup is None:
        return {"estado": "sin_limite"}
    ureg = _txt(m.get("unidad")).strip("()").replace("^3", "³").replace("^2", "²")
    es_combustion = _slug_param_comb(parametro) in {"pcs", "wobbe"}
    base_es = _norm_pais(pais) == _norm_pais(PAIS_BASE)

    def conv(v):
        if v is None:
            return None
        if unidad_es and ureg and _normalize_unit(unidad_es) != _normalize_unit(ureg):
            c = convertir_unidades(v, ureg, unidad_es, parametro)
            if "valor_convertido" not in c:
                return "incomparable"
            v = c["valor_convertido"]
        if es_combustion and not base_es:
            v = convertir_a_condiciones_espana(v, parametro, pais)["valor_convertido"]
        elif not base_es:
            # Concentración másica (mg/m³) a volumen ≠ 0 °C (p. ej. Italia, Sm³ a 15 °C):
            # normaliza el volumen a 0 °C (gas ideal). El % mol/ppm/adimensional no cambia.
            _cc, cmed = _parse_notac(m.get("notacion") or "(0/0)")
            if cmed and cmed != 0 and _es_mg_por_volumen(unidad_es or ureg):
                v = round(v * (273.15 + cmed) / 273.15, 6)
        return v

    lo, hi = conv(inf), conv(sup)
    if lo == "incomparable" or hi == "incomparable":
        return {"estado": "incomparable"}
    return {"estado": "ok", "lo": lo, "hi": hi}


def _rango_en_condiciones_es(parametro: str, pais: str, unidad_es: Optional[str]) -> Dict[str, Any]:
    """Rango de límites de `pais` para `parametro`, llevado a la UNIDAD y CONDICIONES de
    España. Devuelve {estado, lo, hi} con estado: 'ok' | 'sin_limite' | 'sin_datos' | 'incomparable'."""
    resp = _consultar_norma(parametro, pais)
    if not resp.get("matches"):
        return {"estado": "sin_datos"}
    return _rango_de_match(resp["matches"][0], parametro, pais, unidad_es)


def _intercambiabilidad(parametro: str, paises: Optional[list] = None) -> str:
    """#2 — «Teniendo en cuenta los límites de España de [parámetro], ¿con qué país
    podría intercambiar gas?» Compara el rango español con el de cada país (en
    condiciones de España) y decide si son intercambiables (solape de rangos)."""
    paises = paises or [p for p in ALL_COUNTRIES if _norm_pais(p) != _norm_pais(PAIS_BASE)]
    display = DISPLAY_MAP.get(parametro, parametro)
    unidad_es = _unidad_de_pais(parametro, PAIS_BASE)
    es = _rango_en_condiciones_es(parametro, PAIS_BASE, unidad_es)
    if es.get("estado") != "ok":
        return f"No tengo un límite numérico de España para {display}, así que no puedo evaluar la intercambiabilidad."
    es_lo = es["lo"] if es["lo"] is not None else float("-inf")
    es_hi = es["hi"] if es["hi"] is not None else float("inf")

    def fr(lo, hi):
        a = _coma(lo) if lo is not None else "—"
        b = _coma(hi) if hi is not None else "—"
        return f"{a} / {b}"

    lines = [
        f"**Intercambiabilidad de gas según {display}** (base España: {fr(es['lo'], es['hi'])} {unidad_es or ''})",
        "",
        "| País | Límite (en condiciones de España) | ¿Intercambiable? | Detalle |",
        "| --- | --- | --- | --- |",
    ]
    compatibles = []
    for pais in paises:
        r = _rango_en_condiciones_es(parametro, pais, unidad_es)
        est = r.get("estado")
        if est == "sin_datos":
            lines.append(f"| {pais} | — | ⚪ Sin datos | No consta el parámetro en su normativa |")
            continue
        if est == "incomparable":
            lines.append(f"| {pais} | (no convertible) | 🔴 No | Unidades/magnitud no comparables con España |")
            continue
        if est == "sin_limite":
            lines.append(f"| {pais} | Sin límite | 🟢 Sí | {pais} no fija este parámetro: admite el gas español |")
            compatibles.append(pais)
            continue
        lo = r["lo"] if r["lo"] is not None else float("-inf")
        hi = r["hi"] if r["hi"] is not None else float("inf")
        solapan = max(es_lo, lo) <= min(es_hi, hi) + 1e-9
        es_subset = (lo - 1e-9) <= es_lo and es_hi <= (hi + 1e-9)
        if not solapan:
            detalle = "Rangos sin solape: el gas español no cumpliría su norma"
            verdict = "🔴 No"
        elif es_subset:
            detalle = "Todo gas que cumple en España cumple también aquí"
            verdict = "🟢 Sí"
            compatibles.append(pais)
        else:
            detalle = "Solape parcial: parte del gas español cumple (revisar valor concreto)"
            verdict = "🟡 Parcial"
            compatibles.append(pais + " (parcial)")
        lines.append(f"| {pais} | {fr(r['lo'], r['hi'])} {unidad_es or ''} | {verdict} | {detalle} |")

    resumen = ", ".join(compatibles) if compatibles else "ninguno de los evaluados"
    lines += ["", f"**Intercambio posible con:** {resumen}.",
              "", "_Nota: evaluación por solape de límites del parámetro indicado; el intercambio real exige cumplir TODOS los parámetros a la vez._"]
    return "\n".join(lines)


def _es_consulta_intercambio(texto_norm: str) -> bool:
    """¿Pregunta con qué país se puede intercambiar/compatibilizar el gas?"""
    if "intercambi" in texto_norm or "intercanvi" in texto_norm:
        return True
    pistas_pais = any(p in texto_norm for p in (
        "con que pais", "con qué país", "con que paises", "con qué países",
        "con quien", "con quién", "que pais podria", "qué país podría",
    ))
    return pistas_pais and ("gas" in texto_norm or "compatible" in texto_norm or "intercambi" in texto_norm)


def _es_consulta_restriccion(texto_norm: str) -> bool:
    """¿Pregunta qué país es más restrictivo/amplio que España en un parámetro?"""
    return any(k in texto_norm for k in (
        "restrictiv", "estrict", "exigent", "mas amplio", "más amplio", "mas amplia",
        "más amplia", "permisiv", "laxo", "laxa", "flexible", "menos exigent",
    ))


def _restriccion_vs_espana(parametro: str, texto_norm: str) -> str:
    """#4 — «¿Qué país de la UE tiene un límite de [parámetro] más restrictivo/amplio
    que España?» Clasifica cada país frente a España (en condiciones de España)."""
    display = DISPLAY_MAP.get(parametro, parametro)
    unidad_es = _unidad_de_pais(parametro, PAIS_BASE)
    es = _rango_en_condiciones_es(parametro, PAIS_BASE, unidad_es)
    if es.get("estado") != "ok":
        return f"No tengo un límite numérico de España para {display}, así que no puedo compararlo."
    es_maximo = es.get("lo") is None  # solo cota superior (contaminantes) vs rango
    es_lo = es["lo"] if es["lo"] is not None else float("-inf")
    es_hi = es["hi"] if es["hi"] is not None else float("inf")
    ancho_es = es_hi - es_lo

    quiere_amplio = any(k in texto_norm for k in ("amplio", "amplia", "permisiv", "laxo", "laxa", "flexible", "menos exigent"))
    quiere_restr = any(k in texto_norm for k in ("restrictiv", "estrict", "exigent")) and not quiere_amplio

    def fr(lo, hi):
        return f"{_coma(lo) if lo is not None else '—'} / {_coma(hi) if hi is not None else '—'}"

    paises = [p for p in ALL_COUNTRIES if _norm_pais(p) != _norm_pais(PAIS_BASE)]
    lines = [
        f"**{display}: ¿qué país es más restrictivo/amplio que España?** (base España: {fr(es['lo'], es['hi'])} {unidad_es or ''})",
        "",
        "| País | Límite (en condiciones de España) | Frente a España |",
        "| --- | --- | --- |",
    ]
    mas_restr, mas_amplio = [], []
    for pais in paises:
        r = _rango_en_condiciones_es(parametro, pais, unidad_es)
        est = r.get("estado")
        if est == "sin_datos":
            lines.append(f"| {pais} | — | ⚪ No consta el parámetro |")
            continue
        if est == "incomparable":
            lines.append(f"| {pais} | (no convertible) | ⚪ No comparable |")
            continue
        if est == "sin_limite":
            lines.append(f"| {pais} | Sin límite | 🔼 Más amplio (no lo regula) |")
            mas_amplio.append(pais)
            continue
        lo = r["lo"] if r["lo"] is not None else float("-inf")
        hi = r["hi"] if r["hi"] is not None else float("inf")
        if es_maximo:
            if hi < es_hi - 1e-9:
                verd, lst = "🔽 Más restrictivo (máximo más bajo)", mas_restr
            elif hi > es_hi + 1e-9:
                verd, lst = "🔼 Más amplio (máximo más alto)", mas_amplio
            else:
                verd, lst = "➖ Igual de exigente", None
        else:
            ancho = hi - lo
            if ancho < ancho_es - 1e-9:
                verd, lst = "🔽 Más restrictivo (rango más estrecho)", mas_restr
            elif ancho > ancho_es + 1e-9:
                verd, lst = "🔼 Más amplio (rango más ancho)", mas_amplio
            else:
                verd, lst = "➖ Rango equivalente", None
        if lst is not None:
            lst.append(pais)
        lines.append(f"| {pais} | {fr(r['lo'], r['hi'])} {unidad_es or ''} | {verd} |")

    if quiere_restr:
        foco = f"**Más restrictivos que España:** {', '.join(mas_restr) if mas_restr else 'ninguno'}."
    elif quiere_amplio:
        foco = f"**Más amplios que España:** {', '.join(mas_amplio) if mas_amplio else 'ninguno'}."
    else:
        foco = (f"**Más restrictivos:** {', '.join(mas_restr) or 'ninguno'}. "
                f"**Más amplios:** {', '.join(mas_amplio) or 'ninguno'}.")
    lines += ["", foco]
    return "\n".join(lines)


def _decimales(s: Any) -> int:
    """Nº de decimales de un valor escrito ('10,26' -> 2, '50' -> 0)."""
    t = str(s)
    for sep in (",", "."):
        if sep in t:
            return len(t.split(sep)[-1].strip())
    return 0


def _redondea_coma(v: Optional[float], dec: int) -> str:
    if v is None:
        return "—"
    if dec <= 0:
        return str(int(round(v)))
    return f"{round(v, dec):.{dec}f}".replace(".", ",")


def _parse_notac(n: Any) -> tuple:
    """'(25/0)' -> (25.0, 0.0)  [combustión, volumen]."""
    try:
        a, b = str(n).strip("()").split("/")
        return float(a.replace(",", ".")), float(b.replace(",", "."))
    except Exception:
        return (0.0, 0.0)


def _condiciones_iguales(parametro: str, notac_a: Any, notac_b: Any) -> bool:
    """¿Las condiciones de referencia son equivalentes PARA ESTE parámetro?

    La temperatura del VOLUMEN de referencia solo afecta a magnitudes VOLUMÉTRICAS:
    PCS/Wobbe (MJ/m³) y concentraciones MÁSICAS por volumen (mg/m³ — azufre total,
    H₂S+COS, mercaptanos). El % mol, el ppm, lo adimensional (densidad relativa) y los
    puntos de rocío (°C) NO dependen de la temperatura del volumen. Para PCS/Wobbe
    importa además la temperatura de combustión."""
    ca, va = _parse_notac(notac_a)
    cb, vb = _parse_notac(notac_b)
    es_comb = _slug_param_comb(parametro) in {"pcs", "wobbe"}
    p = _norm_pais(parametro)
    masa_volumen = any(k in p for k in ("s total", "azufre", "h2s", "mercapt", "rsh"))
    if (es_comb or masa_volumen) and va != vb:
        return False
    if es_comb and ca != cb:
        return False
    return True


def _celda_limite(inf: Any, sup: Any, unidad: str, notac: str) -> str:
    i, s = _txt(inf), _txt(sup)
    if _sin_limite(i) and _sin_limite(s):
        return "Sin límite numérico"
    rango = f"{i if not _sin_limite(i) else '—'} - {s if not _sin_limite(s) else '—'}"
    return f"{rango} {unidad}{(' ' + notac) if notac else ''}".strip()


def _limite_convertido_a_es(parametro, pais, inf, sup, u_pa, unidad_es, notac_es, dec):
    """Convierte el límite del país a unidad+condiciones de España (ISO 13443) y lo
    redondea a las cifras de España (Nota 1)."""
    vi, vs = _num_limite(inf), _num_limite(sup)
    if vi is None and vs is None:
        return "Sin límite numérico"

    def conv(v):
        if v is None:
            return None
        if u_pa and unidad_es and _normalize_unit(u_pa) != _normalize_unit(unidad_es):
            c = convertir_unidades(v, u_pa, unidad_es, parametro)
            if "valor_convertido" not in c:
                return "incompat"
            v = c["valor_convertido"]
        if _slug_param_comb(parametro) in {"pcs", "wobbe"} and _norm_pais(pais) != _norm_pais(PAIS_BASE):
            v = convertir_a_condiciones_espana(v, parametro, pais)["valor_convertido"]
        return v

    ci, cs = conv(vi), conv(vs)
    if ci == "incompat" or cs == "incompat":
        return "No convertible de forma determinista"
    a = _redondea_coma(ci, dec) if ci is not None else "—"
    b = _redondea_coma(cs, dec) if cs is not None else "—"
    return f"{a} - {b} {unidad_es} {notac_es}".strip()


def _comparativa_enagas(parametro: str, pais: str) -> str:
    """Módulo 2 (formato Enagás): «¿Cuál es el límite de [parámetro] en [país]
    comparado con España?». Tabla de 5 columnas con el límite del país convertido a
    unidad y condiciones de España (ISO 13443), redondeado a las cifras de España."""
    display = DISPLAY_MAP.get(parametro, parametro)
    es_resp = _consultar_norma(parametro, PAIS_BASE)
    pa_resp = _consultar_norma(parametro, pais)
    if not es_resp.get("matches"):
        return f"No tengo el límite oficial de España para {display}."
    if not pa_resp.get("matches"):
        return f"No tengo el límite oficial de {pais} para {display}."
    es = es_resp["matches"][0]
    unidad_es = es.get("unidad") or ""
    notac_es = es.get("notacion") or "(0/0)"
    es_inf, es_sup = _txt(es.get("limite_inferior")), _txt(es.get("limite_superior"))
    es_celda = _celda_limite(es_inf, es_sup, unidad_es, notac_es)
    ref = es_inf if not _sin_limite(es_inf) else es_sup
    dec = _decimales(ref)

    lines = [
        f"**¿Cuál es el límite de {display} en {pais} comparado con España?**",
        "",
        f"| Parámetro | Límite en España | Límite en {pais} | ¿Unidades y condiciones comparables? | Límite {pais} en condiciones comparables |",
        "| --- | --- | --- | --- | --- |",
    ]
    evidencias = [f"- **España** · {es.get('parametro') or display}: {_cita_oficial(es)}"]
    # Condiciones/matices que el reglamento adjunta a cada límite (p. ej. el O₂ de la
    # EN 16726 es ≤1 % general, pero ≤0,01 %/0,001 % por proceso de evaluación en
    # instalaciones sensibles). Sin esto, la comparación de un solo número engaña.
    notas: list = []
    if es.get("nota"):
        notas.append(f"- **España**: {es['nota']}")
    for m in pa_resp["matches"]:  # Nota 3: una fila por límite (tipos de gas H/L…)
        nombre = str(m.get("parametro") or display).strip()
        u_pa = _txt(m.get("unidad")).strip("()").replace("^3", "³").replace("^2", "²")
        notac_pa = m.get("notacion") or "(0/0)"
        pa_inf, pa_sup = _txt(m.get("limite_inferior")), _txt(m.get("limite_superior"))
        pa_celda = _celda_limite(pa_inf, pa_sup, u_pa, notac_pa)
        misma_unidad = _normalize_unit(u_pa) == _normalize_unit(unidad_es)
        comparable = "Sí" if (misma_unidad and _condiciones_iguales(parametro, notac_pa, notac_es)) else "No"
        conv_celda = _limite_convertido_a_es(parametro, pais, pa_inf, pa_sup, u_pa, unidad_es, notac_es, dec)
        lines.append(f"| {nombre} | {es_celda} | {pa_celda} | {comparable} | {conv_celda} |")
        evidencias.append(f"- **{pais}** · {nombre}: {_cita_oficial(m)}")
        if m.get("nota"):
            notas.append(f"- **{pais}**: {m['nota']}")
    if notas:
        lines += ["", "**Condiciones y matices del reglamento**", ""] + notas
    lines += ["", "**Fuente consultada**", ""] + evidencias
    if _slug_param_comb(parametro) in {"pcs", "wobbe"}:
        lines += ["", "_Conversión de unidad y de condiciones de referencia según ISO 13443:1996; "
                  "valor convertido redondeado a las cifras significativas del límite de España._"]
    return "\n".join(lines)


def _es_consulta_fuente(texto_norm: str) -> bool:
    """¿El usuario pregunta de qué reglamento/norma procede la información?"""
    claves = (
        "reglament", "normativ", "documento", "fuente", "real decreto", "orden ted",
        "directiva", "origen normativo", "base legal", "referencia legal", "que norma",
        "qué norma", "de donde sale", "de dónde sale", "de donde proviene", "de dónde proviene",
        "de donde procede", "de dónde procede", "procede de", "proviene de", "en que se basa",
        "en qué se basa", "de que ley", "de qué ley", "que ley regula", "qué ley regula",
    )
    return any(k in texto_norm for k in claves)


def _pregunta_lista_fuentes(texto_norm: str) -> bool:
    """Pregunta GENERAL por el conjunto de reglamentos (sin un parámetro concreto)."""
    patrones = (
        "que reglamentos", "qué reglamentos", "que normas", "qué normas",
        "que normativas", "qué normativas", "que fuentes", "qué fuentes",
        "que documentos", "qué documentos", "reglamentos usa", "normas usa",
        "fuentes usa", "en que se basa", "en qué se basa", "que reglamento usa",
    )
    return any(p in texto_norm for p in patrones)


def _validate_measurement_gate(session_id: str, mensaje: str) -> Optional[str]:
    texto_norm = mensaje.lower()
    pending = pending_unit_validations.get(session_id)
    if pending and _parse_numeric_value(mensaje) is None:
        unidad_respuesta = _extract_unit_only(mensaje)
        if unidad_respuesta is None:
            return None
        if not _unit_matches_expected(pending["parametro"], unidad_respuesta):
            pending_unit_validations.pop(session_id, None)
            return _incorrect_unit_message(pending["parametro"])
        pending_unit_validations.pop(session_id, None)
        return _evaluar_paises(
            pending["parametro"], pending["valor"], unidad_respuesta,
            pending["paises"], todos=pending.get("todos", False),
        )

    parametro = _normalize_parameter(texto_norm)
    paises = _detectar_paises(texto_norm)        # lista de países pedidos (tolera erratas)
    # "02" aislado significa O₂ (oxígeno), NO el número 2: normalízalo antes de buscar valores.
    mensaje_num = re.sub(r"(?<![\w./,])02(?![\w])", "o2", mensaje)
    valor_con_unidad, unidad_detectada = _extract_numeric_with_unit(mensaje_num)
    valor = valor_con_unidad if valor_con_unidad is not None else _parse_numeric_value(mensaje_num)
    # Si el número y la unidad venían separados ("0.03de % molar"), busca la unidad aparte.
    if unidad_detectada is None:
        unidad_detectada = _extract_unit_only(mensaje)

    # Conversión a CONDICIONES DE REFERENCIA de España (temperatura de combustión),
    # con los factores de la Tabla A.1 de la ISO 13443. Requiere lenguaje explícito de
    # condiciones, así que no interfiere con cumplimiento/límite normales.
    if parametro is not None and _es_consulta_condiciones(texto_norm):
        pais_origen = next((p for p in paises if _norm_pais(p) != _norm_pais(PAIS_BASE)), "Portugal")
        return _responder_condiciones(parametro, valor, unidad_detectada, pais_origen)

    # Compliance: hay parámetro + valor, y se menciona país(es) o hay señal de cumplimiento.
    cue_cumplimiento = any(c in texto_norm for c in [
        "cumple", "paises", "países", "donde", "dónde", "pais", "país", "valido", "válido", "dentro",
    ])
    if parametro is not None and valor is not None and (paises or cue_cumplimiento):
        # FILTRADO ESTRICTO: si hay país(es) explícito(s), solo esos. Si no, todos.
        todos = not paises
        paises_efectivos = paises if paises else list(ALL_COUNTRIES)
        expected = _expected_unit_for_parameter(parametro)
        if expected and unidad_detectada is None:
            pending_unit_validations[session_id] = {
                "parametro": parametro, "paises": paises_efectivos, "todos": todos, "valor": valor,
            }
            return _missing_unit_message(parametro)
        if expected and unidad_detectada is not None and not _unit_matches_expected(parametro, unidad_detectada):
            return _incorrect_unit_message(parametro)
        return _evaluar_paises(parametro, valor, unidad_detectada, paises_efectivos, todos=todos)

    # El usuario plantea un cumplimiento (valor + unidad o señal de "cumple") pero el
    # parámetro no se reconoce → indícalo y ofrece la lista de parámetros disponibles.
    if parametro is None and valor is not None and (unidad_detectada is not None or cue_cumplimiento):
        return _parametro_no_reconocido_message()

    # ¿De qué reglamento/norma procede la información? → fuente documental verificada
    # (ontología). Tiene prioridad sobre comparación/límite (puede mencionar ambos).
    if valor is None and _es_consulta_fuente(texto_norm):
        if parametro is not None:
            paises_f = list(paises) if paises else list(_PAISES_FUENTE)
            return _responder_fuente(parametro, paises_f)
        if paises:  # #1 «¿qué normativa aplican en [país]?» (sin parámetro concreto)
            return _normativa_de_pais(paises)
        if _pregunta_lista_fuentes(texto_norm):
            return _listar_fuentes()

    # #2 «Teniendo en cuenta los límites de España de [parámetro], ¿con qué país
    # podría intercambiar gas?» → intercambiabilidad (solape de rangos vs España).
    if parametro is not None and valor is None and _es_consulta_intercambio(texto_norm):
        return _intercambiabilidad(parametro)

    # #4 «¿Qué país tiene un límite de [parámetro] más restrictivo/amplio que España?»
    if parametro is not None and valor is None and _es_consulta_restriccion(texto_norm):
        return _restriccion_vs_espana(parametro, texto_norm)

    # Comparación de NORMATIVA entre países (sin valor del usuario):
    # "compara el Wobbe entre España y Francia", "diferencia de O2 España vs Portugal"…
    cue_comparar = any(c in texto_norm for c in [
        "compara", "comparar", "comparacion", "comparación", "diferencia",
        "frente a", "versus", " vs ", "enfrenta", "respecto",
    ])
    if parametro is not None and valor is None and (len(paises) >= 2 or (cue_comparar and len(paises) >= 1)):
        otros = [p for p in paises if _norm_pais(p) != _norm_pais(PAIS_BASE)]
        # España vs UN país → formato Enagás (módulo 2): tabla con conversión a condiciones ES.
        if len(otros) == 1:
            return _comparativa_enagas(parametro, otros[0])
        # Varios países → tabla comparativa multi-país.
        paises_efectivos = list(paises) if otros else [PAIS_BASE]
        return _comparar_normativa(parametro, paises_efectivos)

    # Consulta del LÍMITE/valor de un parámetro SIN que el usuario aporte un valor a
    # evaluar → mostrar los límites, NUNCA "cumple/no cumple" (sin un valor no hay nada
    # que cumplir). Cierra el hueco por el que la IA inventaba veredictos de cumplimiento.
    if parametro is not None and valor is None and _es_consulta_limite(texto_norm):
        paises_info = list(paises) if paises else list(ALL_COUNTRIES)
        return _comparar_normativa(parametro, paises_info)

    return None


def _es_consulta_limite(texto_norm: str) -> bool:
    """¿El usuario pregunta por el límite/valor de un parámetro (sin dar un valor a evaluar)?"""
    claves = (
        "limite", "límite", "limites", "límites", "valor", "valores", "rango",
        "maximo", "máximo", "minimo", "mínimo", "cuanto", "cuánto", "umbral",
        "tope", "especificac", "requisito", "requisitos", "que valor", "qué valor",
        "exige", "permite", "permitido", "admite", "admitido", "establece",
    )
    return any(k in texto_norm for k in claves)


def _is_info_request(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "limite",
        "límite",
        "requisito",
        "documento",
        "regula",
        "diferencia",
        "todos los límites",
        "todos los limites",
        "monitoriz",
        "parámetro",
        "parametro",
        "origen",
        "cuál es",
        "que es",
        "qué",
    ]
    return any(keyword in lowered for keyword in keywords)


def _format_info_response(
    parametro: str,
    pais: str,
    respuesta: Dict[str, Any],
) -> str:
    matches = respuesta.get("matches", [])
    if not matches:
        return f"No encontré información determinista para '{parametro}' en '{pais}'."

    lines = [
        f"**Consulta sobre {parametro} en {pais}**",
        "",
        "| Parámetro | Límites aplicables | Condiciones de medición |",
        "| --- | --- | --- |",
    ]
    evidencias = []
    for item in matches[:8]:
        parametro_name = item.get("parametro", parametro)
        inferior = item.get("limite_inferior", "-")
        superior = item.get("limite_superior", "-")
        unidad_reg = item.get("unidad") or item.get("unidad_registro") or ""
        unidad_reg = unidad_reg.strip().strip("()")
        condiciones = _normalize_condition_text(item.get("condiciones") or item.get("condiciones de medicion") or item.get("condiciones de medición"))
        if not condiciones:
            condiciones = "No especificadas en el registro"
        if inferior == "-" and superior == "-":
            rango = "Sin límites numéricos definidos"
        else:
            rango = f"{inferior} / {superior}"
            if unidad_reg:
                rango = f"{rango} ({unidad_reg})"
        lines.append(f"| {parametro_name} | {rango} | {condiciones} |")
        evidencias.append(f"- **{parametro_name}**: {_cita_oficial(item)}")
        if item.get("discrepancia"):
            evidencias.append(f"  - ⚠ Discrepancia con el Excel (prevalece la oficial): {item['discrepancia']}")
    if evidencias:
        lines += ["", "**Evidencias (fuente oficial)**", ""] + evidencias
    return "\n".join(lines)


def _fallback_deterministic_response(mensaje: str, session_id: str = "default") -> str:
    texto = mensaje
    texto_norm = texto.lower()

    validation_response = _validate_measurement_gate(session_id, mensaje)
    if validation_response is not None:
        return validation_response

    parametro = _normalize_parameter(texto_norm)
    pais = next((kw for kw in ["espa", "portugal", "francia", "espana", "españa"] if kw in texto_norm), None)
    pais_formateado = _normalize_country(pais) if pais else None

    valor_con_unidad, unidad_detectada = _extract_numeric_with_unit(texto)
    valor = valor_con_unidad if valor_con_unidad is not None else _parse_numeric_value(texto)

    comparison_intent = (
        parametro is not None
        and pais_formateado is not None
        and valor is not None
        and (
            unidad_detectada is not None
            or any(token in texto_norm for token in ("cumple", "válido", "valido", "excede", "dentro", "rango", "compar"))
        )
    )

    if comparison_intent and unidad_detectada and _unit_matches_expected(parametro, unidad_detectada):
        return _evaluar_paises(parametro, valor, unidad_detectada, [pais_formateado])

    if (
        parametro is not None
        and pais_formateado is not None
        and valor is not None
        and not _is_info_request(texto_norm)
    ):
        if unidad_detectada is None:
            return _missing_unit_message(parametro)
        if not _unit_matches_expected(parametro, unidad_detectada):
            return _incorrect_unit_message(parametro)
        # If unit matches but we are here because not comparison_intent? Actually this block runs when not info request.
        # We'll just fall through to default handling (maybe ask for country/param etc.)

    if parametro and pais_formateado and _is_info_request(texto_norm):
        respuesta = _consultar_norma(parametro, pais_formateado)
        if respuesta.get("count", 0) == 0:
            return f"No encontré información específica para '{parametro}' en '{pais_formateado}'."
        return _format_info_response(parametro, pais_formateado, respuesta)

    if parametro and pais_formateado:
        respuesta = _consultar_norma(parametro, pais_formateado)
        if respuesta.get("count", 0) == 0:
            pdf_resultados = buscar_pdfs(query=texto_norm)
            if pdf_resultados["count"] > 0:
                primer_resultado = pdf_resultados["matches"][0]
                return (
                    f"No encontré coincidencia exacta en el Excel/CSV para '{parametro}' en '{pais_formateado}', "
                    f"pero sí encontré información en PDF: {primer_resultado.get('name')} (página {primer_resultado.get('page')}). "
                    f"Extracto: {primer_resultado.get('snippet', '')}"
                )
            return f"No encontré información específica para '{parametro}' en '{pais_formateado}'."
        return _format_info_response(parametro, pais_formateado, respuesta)

    # 1) El usuario pregunta qué puede consultar el chatbot → lista de parámetros.
    if _es_pregunta_capacidades(texto_norm):
        return _mensaje_capacidades()

    # 2) La pregunta NO trata de calidad del gas (aunque mencione un país) → fuera de ámbito.
    if not _es_tema_calidad_gas(texto_norm):
        return _mensaje_fuera_de_ambito()

    # 3) Es de calidad del gas pero no reconocimos el parámetro → indícalo y ofrece la lista.
    return _parametro_no_reconocido_message()


@app.get("/api/status", response_model=StatusResponse)
@gestionar_errores
async def status_endpoint() -> StatusResponse:
    return StatusResponse(modo=backend_mode, detalle=backend_detail)


@app.post("/api/chat", response_model=RespuestaChat)
@gestionar_errores
@medir_tiempo
async def chat_endpoint(request: PeticionChat) -> RespuestaChat:
    validation_response = _validate_measurement_gate(request.session_id, request.mensaje)
    if validation_response is not None:
        return RespuestaChat(respuesta=validation_response, modo="determinista")

    if client is None:
        respuesta = _fallback_deterministic_response(request.mensaje, request.session_id)
        return RespuestaChat(respuesta=respuesta, modo="determinista")

    # Si OpenAI falla (clave inválida, red, límite…), NO rompemos el chat:
    # caemos al motor determinista en vez de devolver un error 500.
    try:
        texto = responder_con_openai(request.mensaje, request.session_id)
        return RespuestaChat(respuesta=texto, modo="ia")
    except Exception as exc:  # noqa: BLE001
        print(f"[chat] OpenAI no disponible ({exc}); usando motor determinista.")
        respuesta = _fallback_deterministic_response(request.mensaje, request.session_id)
        return RespuestaChat(respuesta=respuesta, modo="determinista")


# --- Sección de COMPARATIVA (desplegables) ---------------------------------
class PeticionComparar(BaseModel):
    parametro: str
    paises: List[str] = []
    unidad: Optional[str] = None


@app.get("/api/parametros")
@gestionar_errores
async def parametros_endpoint() -> Dict[str, Any]:
    """Lista de parámetros y unidades para poblar los desplegables del frontend."""
    return {"parametros": PARAMETROS_UI, "paises": PAISES_UI, "base": PAIS_BASE}


@app.post("/api/comparar")
@gestionar_errores
async def comparar_endpoint(req: PeticionComparar) -> Dict[str, Any]:
    slug = _normalize_parameter((req.parametro or "").lower()) or (req.parametro or "").lower()
    return comparar_estructurado(slug, req.paises, req.unidad or "")


@app.get("/api/matriz")
@gestionar_errores
async def matriz_endpoint() -> Dict[str, Any]:
    """Matriz comparativa (heatmap): países × parámetros, normalizado a condiciones de España."""
    return matriz_comparativa()
