"""Capa de abstracción del proveedor de LLM (Large Language Model).

=============================================================================
PROPÓSITO
=============================================================================
Este módulo es la ÚNICA parte del proyecto que conoce detalles de un proveedor
de IA concreto (OpenAI, Anthropic, Gemini, Azure, Ollama, modelo local...).
El resto de la aplicación (api.py, motor determinista, frontend) es
"provider-agnostic": habla solo con la interfaz genérica `LLMProvider`.

    +------------------+       interfaz genérica        +------------------+
    |   api.py         |  ---------------------------->  |  llm_interface   |
    |  (lógica de app) |   provider.chat(...)            |  (esta capa)     |
    +------------------+                                 +---------+--------+
                                                                   |
                             +-------------------+-----------------+-----------------+
                             |                   |                 |                 |
                        OpenAIProvider   AnthropicProvider   OpenAICompatible*   NullProvider
                        (api.openai)     (claude)            (Ollama/Azure/      (sin clave ->
                                                              local/together)     modo determinista)

Para CAMBIAR de proveedor NO hay que tocar api.py: basta con
  1) definir la variable de entorno  LLM_PROVIDER  (openai | anthropic | ollama | azure | null)
  2) y las credenciales/modelo de ese proveedor (ver `get_provider`).

=============================================================================
QUIÉN DEBE USAR ESTA CAPA (call sites en el resto del código)
=============================================================================
Todo el acoplamiento al LLM se concentra aquí. En `api.py` solo debe existir:

  from llm_interface import get_provider
  provider = get_provider()
  ...
  provider.is_available()        # ¿hay LLM operativo? -> decide IA vs. fallback
  provider.display_name()        # texto para /api/status
  provider.chat(system_prompt, history, user_message, tools, tool_functions)

NINGÚN otro fichero debe importar `openai`, `anthropic`, etc. Si en el futuro
se añade streaming, embeddings o "structured outputs", se amplía la interfaz
`LLMProvider` aquí y se implementa en cada adaptador — api.py sigue igual.

=============================================================================
CÓMO AÑADIR UN PROVEEDOR NUEVO (3 pasos)
=============================================================================
1) Crea una subclase de `LLMProvider` (copia `OpenAIProvider` como plantilla).
   Implementa `is_available`, `display_name` y `chat`. El método `chat` debe:
     - construir los mensajes (system + history + user),
     - ejecutar el BUCLE de tool-calling propio del proveedor,
     - ejecutar cada herramienta con `tool_functions[name](**args)`,
     - devolver el TEXTO final del asistente (str).
2) Registra la clase en el diccionario `_PROVIDERS` (abajo).
3) Documenta sus variables de entorno en el docstring de `get_provider`.

El formato de `tools` que recibe `chat` es el "estilo función de OpenAI"
(lista de dicts {type:function, function:{name, description, parameters}}),
usado como formato de intercambio común. Cada adaptador no-OpenAI lo traduce
a su propio formato (ver `AnthropicProvider._to_anthropic_tools`).
=============================================================================
"""
from __future__ import annotations

import abc
import json
import os
from typing import Any, Callable, Dict, List, Optional


# Tipos de conveniencia (puramente documentales).
Message = Dict[str, Any]                      # {"role": "user"|"assistant"|..., "content": str}
ToolSchema = Dict[str, Any]                   # esquema de herramienta estilo OpenAI
ToolFunctions = Dict[str, Callable[..., Any]]  # nombre -> función Python determinista


# ---------------------------------------------------------------------------
# Interfaz genérica
# ---------------------------------------------------------------------------
class LLMProvider(abc.ABC):
    """Contrato que debe cumplir cualquier proveedor de LLM.

    La aplicación SOLO conoce estos tres métodos; nada más.
    """

    #: nombre corto del proveedor ("openai", "anthropic", ...); lo fija cada subclase.
    key: str = "base"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """¿El proveedor está listo para responder? (credenciales, SDK instalado…).

        Si devuelve False, la app usa su fallback determinista y NUNCA llama a `chat`.
        """

    @abc.abstractmethod
    def display_name(self) -> str:
        """Descripción legible para mostrar en /api/status (p. ej. 'OpenAI gpt-4o-mini')."""

    @abc.abstractmethod
    def chat(
        self,
        system_prompt: str,
        history: List[Message],
        user_message: str,
        tools: List[ToolSchema],
        tool_functions: ToolFunctions,
        temperature: float = 0.0,
        max_tool_iterations: int = 5,
    ) -> str:
        """Genera la respuesta del asistente con herramientas deterministas.

        El proveedor NUNCA inventa cifras: cuando necesita un dato, invoca una de
        las `tools` (function-calling); esta capa ejecuta la función Python
        correspondiente (`tool_functions[nombre](**args)`) y le devuelve el
        resultado. El bucle se repite hasta `max_tool_iterations`.

        Parámetros
        ----------
        system_prompt : str
            Instrucciones fijas del asistente (sin números). Va como rol "system".
        history : list[Message]
            Turnos previos de la sesión, en formato {"role","content"}
            (roles "user"/"assistant"). La capa NO lo modifica; api.py lo persiste.
        user_message : str
            Mensaje nuevo del usuario.
        tools : list[ToolSchema]
            Esquemas de las herramientas (estilo función OpenAI). Cada adaptador
            los traduce a su formato si hace falta.
        tool_functions : dict[str, callable]
            Mapa nombre_de_herramienta -> función determinista a ejecutar.
        temperature : float
            0.0 = respuestas deterministas (recomendado para este dominio).
        max_tool_iterations : int
            Tope de iteraciones de tool-calling para evitar bucles infinitos.

        Devuelve
        -------
        str
            El texto final redactado por el asistente (Markdown).
        """


# ---------------------------------------------------------------------------
# Bucle de tool-calling compartido por los proveedores "estilo OpenAI"
# (OpenAI, Azure OpenAI, Ollama, LM Studio, Together, vLLM, ...)
# ---------------------------------------------------------------------------
class _OpenAIStyleProvider(LLMProvider):
    """Base para cualquier API compatible con el esquema de OpenAI Chat Completions.

    Subclases solo tienen que construir `self._client` (un objeto con
    `.chat.completions.create(...)`) y fijar `self._model`.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._model: str = ""

    def is_available(self) -> bool:
        return self._client is not None

    def chat(
        self,
        system_prompt: str,
        history: List[Message],
        user_message: str,
        tools: List[ToolSchema],
        tool_functions: ToolFunctions,
        temperature: float = 0.0,
        max_tool_iterations: int = 5,
    ) -> str:
        mensajes: List[Message] = [{"role": "system", "content": system_prompt}]
        mensajes.extend(history)
        mensajes.append({"role": "user", "content": user_message})

        texto_final = ""
        for _ in range(max_tool_iterations):
            respuesta = self._client.chat.completions.create(
                model=self._model,
                messages=mensajes,
                tools=tools,
                temperature=temperature,
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
                func = tool_functions.get(tc.function.name)
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
        return texto_final


class OpenAIProvider(_OpenAIStyleProvider):
    """OpenAI oficial (api.openai.com).

    Variables de entorno:
      API_OPENAI    -> clave (debe empezar por 'sk-'); alias: OPENAI_API_KEY
      OPENAI_MODEL  -> modelo (por defecto 'gpt-4o-mini')
    """

    key = "openai"

    def __init__(self) -> None:
        super().__init__()
        self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        clave = (os.environ.get("API_OPENAI") or os.environ.get("OPENAI_API_KEY") or "").strip()
        # Descarta placeholders/claves inválidas para no romper el chat.
        if clave in {"", "tu_clave_aqui"} or not clave.startswith("sk-"):
            return
        try:
            from openai import OpenAI  # import perezoso: solo si se usa este proveedor
            self._client = OpenAI(api_key=clave)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm_interface] No se pudo inicializar OpenAI: {exc}")

    def display_name(self) -> str:
        return f"OpenAI {self._model}"


class OpenAICompatibleProvider(_OpenAIStyleProvider):
    """Cualquier endpoint compatible con la API de OpenAI vía `base_url`.

    Sirve para Ollama (local), Azure OpenAI, LM Studio, vLLM, Together, Groq...
    Reutiliza el mismo bucle de tool-calling (todos hablan el esquema de OpenAI).

    Variables de entorno:
      LLM_BASE_URL  -> URL del endpoint (p. ej. http://localhost:11434/v1 para Ollama)
      LLM_API_KEY   -> clave (para Ollama/local suele valer cualquier cosa, p. ej. 'ollama')
      LLM_MODEL     -> nombre del modelo (p. ej. 'llama3.1', 'qwen2.5', 'mistral')
    """

    key = "openai_compatible"

    def __init__(self) -> None:
        super().__init__()
        self._model = os.environ.get("LLM_MODEL", "llama3.1")
        base_url = (os.environ.get("LLM_BASE_URL") or "").strip()
        api_key = (os.environ.get("LLM_API_KEY") or "no-key").strip()
        if not base_url:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm_interface] No se pudo inicializar el endpoint compatible: {exc}")

    def display_name(self) -> str:
        return f"LLM compatible ({self._model})"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude (Messages API). Traduce el tool-calling al formato Anthropic.

    Variables de entorno:
      ANTHROPIC_API_KEY -> clave
      ANTHROPIC_MODEL   -> modelo (por defecto 'claude-opus-4-8')

    NOTA: implementación de referencia. El formato de Anthropic difiere de OpenAI
    en tres cosas: (1) el `system` va como parámetro aparte, no como mensaje;
    (2) las herramientas usan `input_schema` en vez de `parameters`; (3) las
    llamadas a herramienta llegan como bloques `tool_use` y los resultados se
    devuelven como bloques `tool_result`.
    """

    key = "anthropic"

    def __init__(self) -> None:
        self._client = None
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
        clave = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if not clave:
            return
        try:
            import anthropic  # import perezoso
            self._client = anthropic.Anthropic(api_key=clave)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm_interface] No se pudo inicializar Anthropic: {exc}")

    def is_available(self) -> bool:
        return self._client is not None

    def display_name(self) -> str:
        return f"Anthropic {self._model}"

    @staticmethod
    def _to_anthropic_tools(tools: List[ToolSchema]) -> List[Dict[str, Any]]:
        """Convierte esquemas estilo OpenAI -> formato de herramientas de Anthropic."""
        out: List[Dict[str, Any]] = []
        for t in tools:
            fn = t.get("function", t)
            out.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return out

    def chat(
        self,
        system_prompt: str,
        history: List[Message],
        user_message: str,
        tools: List[ToolSchema],
        tool_functions: ToolFunctions,
        temperature: float = 0.0,
        max_tool_iterations: int = 5,
    ) -> str:
        # Historial en formato Anthropic (solo user/assistant con content textual).
        mensajes: List[Dict[str, Any]] = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m.get("role") in ("user", "assistant")
        ]
        mensajes.append({"role": "user", "content": user_message})
        herramientas = self._to_anthropic_tools(tools)

        texto_final = ""
        for _ in range(max_tool_iterations):
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                temperature=temperature,
                system=system_prompt,
                tools=herramientas,
                messages=mensajes,
            )
            # Texto redactado en este turno + posibles llamadas a herramienta.
            texto_turno = "".join(b.text for b in resp.content if b.type == "text")
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                texto_final = texto_turno
                break
            # Adjunta la respuesta del asistente (con los bloques tool_use) al historial.
            mensajes.append({"role": "assistant", "content": resp.content})
            # Ejecuta cada herramienta y responde con bloques tool_result.
            resultados = []
            for tu in tool_uses:
                func = tool_functions.get(tu.name)
                try:
                    resultado = func(**(tu.input or {})) if func else {"error": "herramienta desconocida"}
                except Exception as exc:  # noqa: BLE001
                    resultado = {"error": str(exc)}
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                })
            mensajes.append({"role": "user", "content": resultados})
        return texto_final


class NullProvider(LLMProvider):
    """Proveedor "vacío": no hay LLM. La app usará siempre su fallback determinista."""

    key = "null"

    def is_available(self) -> bool:
        return False

    def display_name(self) -> str:
        return "Sin LLM (modo determinista)"

    def chat(self, *args: Any, **kwargs: Any) -> str:  # noqa: D401
        raise RuntimeError("NullProvider no puede generar texto; usa el fallback determinista.")


# ---------------------------------------------------------------------------
# Fábrica: selecciona el proveedor según el entorno
# ---------------------------------------------------------------------------
#: Registro de proveedores disponibles. Añade aquí tu clase nueva.
_PROVIDERS: Dict[str, Callable[[], LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OpenAICompatibleProvider,
    "azure": OpenAICompatibleProvider,
    "compatible": OpenAICompatibleProvider,
    "null": NullProvider,
}


def get_provider() -> LLMProvider:
    """Devuelve el proveedor de LLM configurado.

    Selección (variable de entorno `LLM_PROVIDER`):
      - "openai"  (por defecto): OpenAI oficial     -> API_OPENAI / OPENAI_MODEL
      - "anthropic":            Anthropic Claude     -> ANTHROPIC_API_KEY / ANTHROPIC_MODEL
      - "ollama" | "azure" | "compatible": endpoint estilo OpenAI vía base_url
                                                   -> LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
      - "null":                 sin LLM (fuerza el modo determinista)

    Compatibilidad hacia atrás: si NO se define `LLM_PROVIDER`, se usa "openai"
    (comportamiento histórico del proyecto). Si el proveedor elegido no puede
    inicializarse (sin clave, SDK ausente…), `is_available()` será False y la
    aplicación caerá con elegancia al motor determinista.
    """
    nombre = (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    constructor = _PROVIDERS.get(nombre)
    if constructor is None:
        print(f"[llm_interface] Proveedor '{nombre}' desconocido; usando OpenAI por defecto.")
        constructor = OpenAIProvider
    try:
        return constructor()
    except Exception as exc:  # noqa: BLE001
        print(f"[llm_interface] Error creando el proveedor '{nombre}': {exc}. Modo determinista.")
        return NullProvider()
