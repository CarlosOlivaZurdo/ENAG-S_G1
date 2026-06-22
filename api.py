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
from conversor_unidades import convertir_unidades

try:
    from src.llm.prompts import SYSTEM_PROMPT
except Exception:  # fallback si el paquete src no está en el path
    SYSTEM_PROMPT = (
        "Eres el Asistente Experto de Calidad de Gas Natural. Solo tratas la calidad "
        "del gas natural (España, Portugal, Francia, UE). Nunca inventas valores "
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
                    "pais": {"type": "string", "description": "País/jurisdicción (España, Portugal, Francia)."},
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
]

TOOL_FUNCS: Dict[str, Callable[..., Any]] = {
    "consultar_excel": consultar_excel,
    "evaluar_cumplimiento": evaluar_cumplimiento,
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
    """Sirve la interfaz web del chatbot en la raíz (http://localhost:8000/)."""
    return FileResponse(_INDEX_HTML)


def _parse_numeric_value(text: str) -> Optional[float]:
    import re

    # Tolera puntuación/letra justo después ("15,", "0.03de" -> 0.03). El lookbehind
    # evita capturar el "2" de "o2"/"co2" como número.
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


def _extract_numeric_with_unit(text: str) -> tuple[Optional[float], Optional[str]]:
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
                for token in (
                    "kwh",
                    "mj",
                    "mg",
                    "ppm",
                    "kg",
                    "g",
                    "bar",
                    "%",
                    "m^3",
                    "nm^3",
                    "m3",
                    "nm3",
                    "m³",
                    "nm³",
                    "°c",
                    "ºc",
                    "c",
                )
            ):
                try:
                    return float(value), unit_clean
                except ValueError:
                    return None, None
    return None, None


def _extract_unit_only(text: str) -> Optional[str]:
    match = re.search(
        r"(?i)(%\s*(?:molar|mol)?|kwh\s*/\s*[a-z0-9^³°]+|mj\s*/\s*[a-z0-9^³°]+|mg\s*/\s*[a-z0-9^³°]+|ppm\s*/\s*[a-z0-9^³°]+|°c|ºc|\bc\b)",
        text,
    )
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(0))


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
    return None


def _normalize_unit(unit: Optional[str]) -> str:
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
        "Indícame uno de ellos junto con el país (España, Portugal, Francia o UE) "
        "para darte los valores o comprobar el cumplimiento."
    )


def _mensaje_capacidades() -> str:
    opciones = "\n".join(f"- {p}" for p in PARAMETROS_DISPONIBLES)
    return (
        "Puedo ayudarte con consultas sobre **calidad del gas natural** en España, "
        "Portugal, Francia y la UE. Los parámetros que puedes consultar son:\n\n"
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


ALL_COUNTRIES = ["España", "Portugal", "Francia"]
PAIS_BASE = "España"


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
        resp = consultar_excel(parametro, pais)
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


_PAIS_FUZZY = {"espana": "España", "portugal": "Portugal", "francia": "Francia"}


def _detectar_paises(texto_norm: str) -> list:
    """Devuelve la lista de países mencionados, tolerando erratas (ej. 'frnacia').

    Vacía si el usuario no menciona ningún país (→ se asumirán todos).
    """
    t = _norm_pais(texto_norm)  # minúsculas sin acentos
    encontrados: list = []
    # 1) coincidencia directa por subcadena (evita falsos positivos con "espan")
    for kw, nombre in [("espan", "España"), ("spain", "España"),
                       ("portugal", "Portugal"), ("francia", "Francia"), ("france", "Francia")]:
        if kw in t and nombre not in encontrados:
            encontrados.append(nombre)
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
        resp = evaluar_cumplimiento(parametro, pais, valor, unidad=unidad)
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
    # UNA SOLA TABLA: cumplimiento + límite normativo + comparabilidad en la misma fila.
    # Origen documental y condiciones van debajo, en "Evidencias" (texto, no segunda tabla).
    lines = [
        titulo,
        "",
        "| País | Parámetro | Valor evaluado | Límite normativo | Resultado | Detalle | Comparabilidad |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    conversiones: list = []
    evidencias: list = []
    cumple_en: list = []
    for item in filas[:12]:
        pais_fila = item.get("pais", "")
        nombre = str(item.get("parametro") or parametro).strip()
        estado = item.get("cumple", "No evaluable")
        detalle = item.get("detalle", "")
        origen = item.get("documento") or "Origen no especificado"
        inf = _txt(item.get("limite_inferior")) or "-"
        sup = _txt(item.get("limite_superior")) or "-"
        unidad_reg = item.get("unidad_registro") or unidad or ""
        condiciones = _normalize_condition_text(item.get("condiciones") or item.get("condiciones de medicion") or item.get("condiciones de medición"))
        if not condiciones:
            condiciones = "No especificadas"
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
        lines.append(f"| {pais_fila} | {nombre} | {celda} | {limite_cell} | {res} | {detalle} | {comp} |")
        evidencias.append(f"- **{pais_fila}** · {nombre}: {origen}. Condiciones: {condiciones}.")
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
    for pais in paises:
        try:
            resp = consultar_excel(parametro, pais)
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
            lines.append(f"| {pais} | {nombre} | {limite} | {unidad_reg or '—'} | {cond} | {comp} |")
    if not hubo:
        return f"No encontré datos normativos de '{parametro}' en {', '.join(paises)}."
    if estados:
        estados_u = list(dict.fromkeys(estados))  # dedup (un país puede tener varias filas)
        sint = "; ".join(f"España vs {p}: {e}" for p, e in estados_u)
        lines += ["", f"**Síntesis:** {sint}."]
    return "\n".join(lines)


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
    valor_con_unidad, unidad_detectada = _extract_numeric_with_unit(mensaje)
    valor = valor_con_unidad if valor_con_unidad is not None else _parse_numeric_value(mensaje)
    # Si el número y la unidad venían separados ("0.03de % molar"), busca la unidad aparte.
    if unidad_detectada is None:
        unidad_detectada = _extract_unit_only(mensaje)

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

    # Comparación de NORMATIVA entre países (sin valor del usuario):
    # "compara el Wobbe entre España y Francia", "diferencia de O2 España vs Portugal"…
    cue_comparar = any(c in texto_norm for c in [
        "compara", "comparar", "comparacion", "comparación", "diferencia",
        "frente a", "versus", " vs ", "enfrenta", "respecto",
    ])
    if parametro is not None and valor is None and (len(paises) >= 2 or (cue_comparar and len(paises) >= 1)):
        paises_efectivos = list(paises)
        # En comparaciones de un solo país, añadir España como referencia visual.
        if len(paises_efectivos) == 1 and _norm_pais(paises_efectivos[0]) != _norm_pais(PAIS_BASE):
            paises_efectivos = [PAIS_BASE] + paises_efectivos
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
        f"*Consulta sobre {parametro} en {pais}*",
        "",
        "| Parámetro | Límites aplicables | Condiciones de medición | Origen documental | Enlace |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in matches[:8]:
        parametro_name = item.get("parametro", parametro)
        inferior = item.get("limite_inferior", "-")
        superior = item.get("limite_superior", "-")
        unidad_reg = item.get("unidad") or item.get("unidad_registro") or ""
        unidad_reg = unidad_reg.strip().strip("()")
        condiciones = _normalize_condition_text(item.get("condiciones") or item.get("condiciones de medicion") or item.get("condiciones de medición"))
        if not condiciones:
            condiciones = "No especificadas en el registro"
        origen = item.get("documento") or "Origen no especificado"
        if inferior == "-" and superior == "-":
            rango = "Sin límites numéricos definidos"
        else:
            rango = f"{inferior} / {superior}"
            if unidad_reg:
                rango = f"{rango} ({unidad_reg})"
        lines.append(f"| {parametro_name} | {rango} | {condiciones} | {origen} | {item.get('url') or 'No disponible en el Excel'} |")
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
        respuesta = consultar_excel(parametro, pais_formateado)
        if respuesta.get("count", 0) == 0:
            return f"No encontré información específica para '{parametro}' en '{pais_formateado}'."
        return _format_info_response(parametro, pais_formateado, respuesta)

    if parametro and pais_formateado:
        respuesta = consultar_excel(parametro, pais_formateado)
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
