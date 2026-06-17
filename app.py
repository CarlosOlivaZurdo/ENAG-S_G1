import os
import uuid
import requests
import streamlit as st

st.set_page_config(page_title="Comparador de Calidad de Gas", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.title("Comparador de Calidad de Gas")

st.markdown("### Chat técnico-regulatorio")

status_text = "Desconocido"
try:
    status_resp = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
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

user_input = st.chat_input("Escribe tu consulta sobre calidad de gas natural...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Consultando al backend..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/chat",
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
        st.info("Respuesta basada en datos deterministas del proyecto.")
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown(message["content"])
