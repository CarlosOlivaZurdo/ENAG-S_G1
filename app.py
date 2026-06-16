import uuid
import requests
import streamlit as st

st.set_page_config(page_title="Comparador de Calidad de Gas", layout="wide")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.title("Comparador de Calidad de Gas")

st.markdown("### Chat técnico-regulatorio")

status_text = "Desconocido"
try:
    status_resp = requests.get("http://localhost:8000/api/status", timeout=5)
    if status_resp.ok:
        status_data = status_resp.json()
        status_text = f"Backend: {status_data.get('modo', 'desconocido')} - {status_data.get('detalle', '')}"
    else:
        status_text = f"Backend no disponible (HTTP {status_resp.status_code})"
except Exception as exc:
    status_text = f"Error al consultar estado del backend: {exc}"

st.info(status_text)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

user_input = st.chat_input("Escribe tu consulta sobre calidad de gas natural...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Consultando al backend..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/chat",
                json={"session_id": st.session_state.session_id, "mensaje": user_input},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            assistant_text = data.get("respuesta", "No se recibió respuesta.")
            modo = data.get("modo")
        except Exception as exc:
            assistant_text = f"Error al conectar con el backend: {exc}"
            modo = None
    if modo == "determinista":
        st.warning("La respuesta proviene del motor determinista de datos Excel, no de un modelo IA.")
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
