import os
import re
import json
import time
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
if clave and clave.strip() in {"", "tu_clave_aqui"}:
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
            "description": "Evalúa si un valor medido cumple los límites regulatorios para un parámetro y país.",
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

    pattern = r"(?<![A-Za-z0-9_.,])([-+]?[0-9]+(?:[\.,][0-9]+)?)(?![A-Za-z0-9_.,])"
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


def _normalize_parameter(text: str) -> Optional[str]:
    normalized = text.lower()
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
    for key, value in aliases.items():
        if key in normalized:
            return value
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


def _evaluate_validated_comparison(parametro: str, pais: str, valor: float, unidad: str) -> str:
    respuesta = evaluar_cumplimiento(parametro, pais, valor, unidad=unidad)
    if respuesta.get("error"):
        return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
    return _format_comparison_response(
        parametro=parametro,
        pais=pais,
        valor=valor,
        unidad=unidad,
        respuesta=respuesta,
    )


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
        return _evaluate_validated_comparison(
            pending["parametro"],
            pending["pais"],
            pending["valor"],
            unidad_respuesta,
        )

    parametro = _normalize_parameter(texto_norm)
    pais = next((kw for kw in ["espa", "portugal", "francia", "espana", "españa"] if kw in texto_norm), None)
    pais_formateado = _normalize_country(pais) if pais else None
    valor_con_unidad, unidad_detectada = _extract_numeric_with_unit(mensaje)
    valor = valor_con_unidad if valor_con_unidad is not None else _parse_numeric_value(mensaje)

    if parametro is None or pais_formateado is None or valor is None or _is_info_request(texto_norm):
        return None
    if not _expected_unit_for_parameter(parametro):
        return None
    if unidad_detectada is None:
        pending_unit_validations[session_id] = {
            "parametro": parametro,
            "pais": pais_formateado,
            "valor": valor,
        }
        return _missing_unit_message(parametro)
    pending_unit_validations.pop(session_id, None)
    if not _unit_matches_expected(parametro, unidad_detectada):
        return _incorrect_unit_message(parametro)
    return _evaluate_validated_comparison(parametro, pais_formateado, valor, unidad_detectada)

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


def _format_comparison_response(
    parametro: str,
    pais: str,
    valor: float,
    unidad: Optional[str],
    respuesta: Dict[str, Any],
) -> str:
    matches = respuesta.get("matches", [])
    if not matches:
        return (
            f"No encontré coincidencias para '{parametro}' en '{pais}' con el valor {valor}"
            f"{f' {unidad}' if unidad else ''}."
        )

    lines = [
        "*Resultado de la evaluación*",
        "",
        "| Parámetro | País | Valor usuario | Resultado |",
        "| --- | --- | ---: | --- |",
    ]
    norm_lines = [
        "",
        "*Información normativa*",
        "",
        "| País | Parámetro | Límites aplicables | Condiciones de medición | Origen documental | Enlace |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for item in matches[:8]:
        parametro_name = item.get("parametro", parametro)
        estado = item.get("cumple", "No evaluable")
        origen = item.get("documento") or "Origen no especificado"
        limite_inf = item.get("limite_inferior", "-")
        limite_sup = item.get("limite_superior", "-")
        unidad_reg = item.get("unidad_registro") or item.get("unidad_evaluada") or unidad or ""
        condiciones = _normalize_condition_text(item.get("condiciones") or item.get("condiciones de medicion") or item.get("condiciones de medición"))
        if not condiciones:
            condiciones = "No especificadas en el registro"
        if estado == "Cumple":
            resultado = "Cumple"
        elif estado == "No cumple":
            resultado = "No cumple"
        else:
            resultado = "No existe un criterio automático de evaluación para este parámetro"

        valor_eval = item.get("valor_evaluado", valor)
        valor_usr = item.get("valor_usuario", valor)
        unidad_usr = item.get("unidad_usuario", unidad or "")
        if item.get("conversion") and str(valor_usr) != str(valor_eval):
            celda_valor = f"{valor_eval} {unidad_reg} (introducido: {valor_usr} {unidad_usr})"
        else:
            celda_valor = f"{valor_eval} {unidad_reg if unidad_reg else unidad or ''}"
        lines.append(f"| {parametro_name} | {pais} | {celda_valor} | {resultado} |")
        norm_lines.append(
            f"| {pais} | {parametro_name} | {limite_inf} / {limite_sup}{f' {unidad_reg}' if unidad_reg else ''} | {condiciones} | {origen} | No disponible en el Excel |"
        )

    return "\n".join(lines + norm_lines)


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
        respuesta = evaluar_cumplimiento(parametro, pais_formateado, valor, unidad=unidad_detectada)
        if respuesta.get("error"):
            return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
        return _format_comparison_response(
            parametro=parametro,
            pais=pais_formateado,
            valor=valor,
            unidad=unidad_detectada,
            respuesta=respuesta,
        )

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

    pdf_resultados = buscar_pdfs(query=texto_norm)
    if pdf_resultados["count"] > 0:
        primer_resultado = pdf_resultados["matches"][0]
        return (
            "No pude identificar con claridad el parámetro, el país o el valor. "
            f"Sí encontré información en PDF: {primer_resultado.get('name')} (página {primer_resultado.get('page')})."
        )

    return (
        "El backend está operativo, pero no hay una clave de modelo configurada. "
        "Envía una consulta con un parámetro de calidad de gas, un país y un valor numérico para obtener una respuesta determinista."
    )


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

    texto = responder_con_openai(request.mensaje, request.session_id)
    return RespuestaChat(respuesta=texto, modo="ia")
