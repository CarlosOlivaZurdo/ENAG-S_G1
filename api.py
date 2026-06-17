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
        tools=[consultar_excel_tool, evaluar_cumplimiento_tool, buscar_pdfs_tool],
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


def _extract_unit_from_text(text: str) -> Optional[str]:
    patterns = [
        r"(?i)\b(?:kwh|mj|mg|ppm|kg|g|bar)\s*/\s*[a-z0-9^°]+",
        r"(?i)\b(?:kwh|mj|mg|ppm|kg|g|bar)\b",
        r"(?i)\b%\s*molar\b",
        r"(?i)\b(?:m\^3|nm\^3|m3|nm3)\b",
        r"(?i)\b(?:ºc|°c)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(0).strip()
            if candidate and candidate.lower() not in {"de", "del", "para", "y", "en", "con"}:
                return candidate
    return None


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


def _format_summary_response(
    mensaje: str,
    parametro: str,
    pais: str,
    valor: float,
    unidad_detectada: Optional[str],
    respuesta: Dict[str, Any],
) -> str:
    matches = respuesta.get("matches", [])
    if not matches:
        return f"No encontré coincidencias para {parametro} en {pais} con el valor {valor}."

    lines = [
        f"Parámetro: {parametro.upper()} | País: {pais} | Valor: {valor}",
    ]
    if unidad_detectada:
        lines.append(f"Unidad detectada: {unidad_detectada}")
    else:
        lines.append("Unidad detectada: no se especificó claramente")

    lines.append("")
    lines.append("Resultados:")
    for item in matches[:5]:
        estado = "Cumple" if item.get("cumple") == "Cumple" else "No cumple"
        rango = f"{item.get('limite_inferior', '-')} / {item.get('limite_superior', '-')}"
        unidad = item.get("unidad_registro") or item.get("unidad_evaluada") or ""
        if unidad:
            rango = f"{rango} {unidad}"
        lines.append(f"- {item.get('parametro', parametro)}: {estado} ({rango})")
    if len(matches) > 5:
        lines.append(f"- ... y {len(matches) - 5} más")

    return "\n".join(lines)


def _fallback_deterministic_response(mensaje: str) -> str:
    texto = mensaje.lower()
    param_keywords = [
        "o2",
        "pcs",
        "h2s",
        "wobbe",
        "s total",
        "co2",
        "h2o",
        "rsh",
        "densidad relativa",
        "hco",
    ]
    country_keywords = ["espa", "portugal", "francia", "espana", "españa"]
    parametro = next((kw for kw in param_keywords if kw in texto), None)
    pais = next((kw for kw in country_keywords if kw in texto), None)
    valor = _parse_numeric_value(texto)
    unidad_detectada = _extract_unit_from_text(mensaje)

    if pais:
        pais_formateado = _normalize_country(pais) or pais.title()
    else:
        pais_formateado = None

    if parametro and pais_formateado and valor is not None:
        respuesta = evaluar_cumplimiento(parametro, pais_formateado, valor)
        if respuesta.get("error"):
            return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
        if respuesta["count"] == 0:
            return (
                f"No encontré coincidencias para '{parametro}' en '{pais_formateado}' con el valor {valor}. "
                "Revisa el parámetro, el país o la unidad introducida."
            )
        return _format_summary_response(
            mensaje=mensaje,
            parametro=parametro,
            pais=pais_formateado,
            valor=valor,
            unidad_detectada=unidad_detectada,
            respuesta=respuesta,
        )

    if parametro and pais_formateado:
        respuesta = consultar_excel(parametro, pais_formateado)
        if respuesta.get("error"):
            return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
        if respuesta["count"] == 0:
            pdf_resultados = buscar_pdfs(query=texto)
            if pdf_resultados["count"] > 0:
                return (
                    f"Encontré referencia(s) en PDF sobre '{parametro}' en '{pais_formateado}', "
                    "pero no hay un resultado determinista exacto para esa combinación."
                )
            return (
                f"No encontré datos deterministas para '{parametro}' en '{pais_formateado}'."
            )
        return _format_summary_response(
            mensaje=mensaje,
            parametro=parametro,
            pais=pais_formateado,
            valor=valor if valor is not None else 0,
            unidad_detectada=unidad_detectada,
            respuesta={
                "matches": [
                    {
                        "parametro": item.get("parametro"),
                        "cumple": "Información",
                        "limite_inferior": item.get("limite_inferior"),
                        "limite_superior": item.get("limite_superior"),
                        "unidad_registro": item.get("unidad"),
                    }
                    for item in respuesta["matches"]
                ]
            },
        )

    pdf_resultados = buscar_pdfs(query=texto)
    if pdf_resultados["count"] > 0:
        return (
            "No pude identificar con claridad el parámetro, el país o el valor. "
            "Te dejo los documentos PDF que mejor encajan con tu consulta."
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
