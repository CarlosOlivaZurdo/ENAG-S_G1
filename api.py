import os
import re
from functools import wraps
import time
from typing import Callable, Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_xai import ChatXAI

from motor_determinista import (
    buscar_pdfs,
    buscar_pdfs_tool,
    indexar_pdfs,
    indexar_pdfs_tool,
    consultar_excel,
    consultar_excel_tool,
    evaluar_cumplimiento,
    evaluar_cumplimiento_tool,
)

load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if XAI_API_KEY and XAI_API_KEY.strip() == "tu_clave_aqui":
    XAI_API_KEY = None
if OPENAI_API_KEY and OPENAI_API_KEY.strip() == "tu_clave_aqui":
    OPENAI_API_KEY = None


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


class InMemoryHistory(BaseChatMessageHistory):
    def __init__(self) -> None:
        self._messages: list[BaseMessage] = []

    @property
    def messages(self) -> list[BaseMessage]:
        return self._messages

    def add_messages(self, messages: list[BaseMessage]) -> None:
        self._messages.extend(messages)

    def clear(self) -> None:
        self._messages = []


session_histories: Dict[str, InMemoryHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in session_histories:
        session_histories[session_id] = InMemoryHistory()
    return session_histories[session_id]


chat_model = None
agent = None

if XAI_API_KEY:
    os.environ["XAI_API_KEY"] = XAI_API_KEY
    chat_model = ChatXAI(model="grok-2", temperature=0)
    print("[api] INFO: Usando ChatXAI con XAI_API_KEY.")
elif OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    chat_model = init_chat_model(model="gpt-4o-mini", model_provider="openai")
    print("[api] INFO: Usando OpenAI a través de langchain.init_chat_model con OPENAI_API_KEY.")
else:
    print("[api] WARNING: Ninguna clave de modelo está configurada. El backend arrancará, pero el agente no estará disponible.")

if chat_model is not None:
    agent = create_agent(
        model=chat_model,
        tools=[consultar_excel_tool, evaluar_cumplimiento_tool, indexar_pdfs_tool, buscar_pdfs_tool],
        response_format=str,
    )

agent_with_history = None
if agent is not None:
    agent_with_history = RunnableWithMessageHistory(
        agent,
        get_session_history,
        input_messages_key="mensaje",
        history_messages_key="history",
    )

backend_mode = "ia" if agent_with_history is not None else "determinista"
backend_detail = (
    "Agente IA operativo" if backend_mode == "ia" else "Sin clave de modelo válida: usando fallback determinista"
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        r"(?i)([-+]?[0-9]+(?:[\.,][0-9]+)?)\s*(kwh\s*/\s*[a-z0-9^°]+|mj\s*/\s*[a-z0-9^°]+|mg\s*/\s*[a-z0-9^°]+|ppm\s*/\s*[a-z0-9^°]+|kwh|mj|mg|ppm|kg|g|bar|%|m\^3|nm\^3|m3|nm3|°c|ºc)",
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
                    "°c",
                    "ºc",
                )
            ):
                try:
                    return float(value), unit_clean
                except ValueError:
                    return None, None
    return None, None


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


EXPECTED_UNITS = {
    "wobbe": ["kwh/m3", "kwh/nm3", "kwh/m3", "kwh/nm3"],
    "pcs": ["kwh/m3", "kwh/nm3", "kwh/m3", "kwh/nm3"],
    "s total": ["mg/m3", "mg/nm3", "mgs/m3", "mgs/nm3"],
    "h2s+cos": ["mg/m3", "mg/nm3", "mgs/m3", "mgs/nm3"],
    "rsh": ["mg/m3", "mg/nm3", "mgs/m3", "mgs/nm3"],
    "o2": ["%molar", "%molar", "%m", "%mol"],
    "co2": ["%molar", "%molar", "%m", "%mol"],
    "h2o(rocío)": ["oc", "oc", "°c", "c"],
    "hc(rocío)": ["oc", "oc", "°c", "c"],
}


def _unit_matches_expected(param: str, unit: Optional[str]) -> bool:
    if not param or not unit:
        return False
    normalized = _normalize_unit(unit)
    expected = EXPECTED_UNITS.get(param, [])
    return any(candidate == normalized for candidate in expected)


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

        lines.append(f"| {parametro_name} | {pais} | {valor} {unidad_reg if unidad_reg else unidad or ''} | {resultado} |")
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


def _fallback_deterministic_response(mensaje: str) -> str:
    texto = mensaje
    texto_norm = texto.lower()

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
            return (
                f"Para comparar {parametro} correctamente necesito la unidad exacta. "
                f"Ejemplo: {parametro} en {pais_formateado} con unidades compatibles al valor introducido."
            )
        if not _unit_matches_expected(parametro, unidad_detectada):
            expected = EXPECTED_UNITS.get(parametro, [])
            expected_msg = expected[0] if expected else "la unidad adecuada"
            return (
                f"La unidad detectada ({unidad_detectada}) no coincide con la esperada para {parametro}. "
                f"Introduce el valor nuevamente expresado en {expected_msg}."
            )

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
    if agent_with_history is None:
        respuesta = _fallback_deterministic_response(request.mensaje)
        return RespuestaChat(respuesta=respuesta, modo="determinista")

    response = agent_with_history.invoke(
        {"mensaje": request.mensaje},
        config={"configurable": {"session_id": request.session_id}},
    )
    if isinstance(response, dict) and "output" in response:
        texto = str(response["output"])
    else:
        texto = str(response)
    return RespuestaChat(respuesta=texto, modo="ia")
