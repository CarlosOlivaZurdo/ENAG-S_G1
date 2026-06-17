import os
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

    if parametro and pais and valor is not None:
        respuesta = evaluar_cumplimiento(parametro, pais, valor)
        if respuesta.get("error"):
            return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
        if respuesta["count"] == 0:
            return (
                f"No se han encontrado resultados deterministas para el parámetro '{parametro}' en '{pais}'. "
                f"Asegúrate de usar un parámetro y país presentes en el archivo de datos."
            )
        salida = [
            f"Resultado determinista ({respuesta['file']}) - {respuesta['count']} coincidencia(s):"
        ]
        for item in respuesta["matches"][:5]:
            salida.append(
                f"Índice {item['indice']}: {item['parametro']} ({item['sheet']}) - {item['cumple']} "
                f"con valor {item['valor_evaluado']} {item['unidad_evaluada']} "
                f"[{item['limite_inferior']} / {item['limite_superior']}]."
            )
        if respuesta["count"] > 5:
            salida.append(f"... y {respuesta['count'] - 5} coincidencia(s) adicionales.")
        return "\n".join(salida)

    if parametro and pais:
        respuesta = consultar_excel(parametro, pais)
        if respuesta.get("error"):
            return f"Consulta determinista disponible, pero ocurrió un error: {respuesta['error']}"
        if respuesta["count"] == 0:
            pdf_resultados = buscar_pdfs(request_text=texto)
            if pdf_resultados["count"] > 0:
                salida = [
                    f"No se han encontrado resultados deterministas de Excel para '{parametro}' en '{pais}'. "
                    "Sin embargo, se han encontrado coincidencias en documentos PDF procesados:"
                ]
                for item in pdf_resultados["matches"][:5]:
                    salida.append(
                        f"{item['indice']}. {item['name']} - {item['file']}"
                    )
                if pdf_resultados["count"] > 5:
                    salida.append(f"... y {pdf_resultados['count'] - 5} coincidencia(s) adicionales.")
                return "\n".join(salida)
            return (
                f"No se han encontrado resultados deterministas para el parámetro '{parametro}' en '{pais}'. "
                f"Asegúrate de usar un parámetro y país presentes en el archivo de datos."
            )
        matches = respuesta["matches"]
        salida = [
            f"Resultado determinista ({respuesta['file']}) - {respuesta['count']} coincidencia(s):"
        ]
        for item in matches[:5]:
            fields = ", ".join(
                f"{k}: {v}" for k, v in item.items() if k not in {"sheet"}
            )
            output_line = f"Hoja: {item.get('sheet', 'N/A')} - {fields}"
            salida.append(output_line)
        if respuesta["count"] > 5:
            salida.append(f"... y {respuesta['count'] - 5} coincidencia(s) adicionales.")
        return "\n".join(salida)

    pdf_resultados = buscar_pdfs(request_text=texto)
    if pdf_resultados["count"] > 0:
        salida = [
            "No hay una consulta determinista clara de parámetros/país/valor. "
            "Se han encontrado estos documentos PDF relevantes:"
        ]
        for item in pdf_resultados["matches"][:5]:
            salida.append(f"{item['indice']}. {item['name']} - {item['file']}")
        if pdf_resultados["count"] > 5:
            salida.append(f"... y {pdf_resultados['count'] - 5} coincidencia(s) adicionales.")
        return "\n".join(salida)

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
