"""Sure Agent – Interfaz de Chat con Streamlit."""

import time
import streamlit as st

from src.agent import get_client, create_thread, send_message
from src.citations import process_citations
from src.config import AGENT_ID

# ── Configuración de página ──────────────────────────────
st.set_page_config(
    page_title="Sure Agent",
    page_icon="🛡️",
    layout="centered",
)

# ── Barra lateral ────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/shield.png",
        width=80,
    )
    st.title("Sure Agent")
    st.caption("Make **SURE** your compliance is grounded.")
    st.divider()
    if st.button("🗑️ Nueva conversación", use_container_width=True):
        st.session_state.pop("thread_id", None)
        st.session_state.pop("messages", None)
        st.rerun()

# ── Cliente y hilo de conversación ───────────────────────
client = get_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = create_thread(client)

thread_id = st.session_state.thread_id

# ── Renderizar historial de chat ─────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── Helpers de streaming ─────────────────────────────────
def transmitir_texto(texto: str):
    """Genera texto palabra por palabra para crear efecto de escritura."""
    palabras = texto.split(" ")
    for i, palabra in enumerate(palabras):
        yield palabra + ("" if i == len(palabras) - 1 else " ")
        time.sleep(0.03)


# ── Entrada del chat ─────────────────────────────────────
if prompt := st.chat_input("Escribe tu mensaje…"):
    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta del agente
    with st.chat_message("assistant"):
        try:
            # 1. Llamar al agente (muestra spinner mientras espera respuesta)
            with st.spinner("Pensando…"):
                resultado = send_message(client, thread_id, AGENT_ID, prompt)
                respuesta = process_citations(
                    resultado["value"],
                    resultado["annotations"],
                    client,
                )

            # 2. Mostrar respuesta palabra por palabra (efecto typewriter)
            st.write_stream(transmitir_texto(respuesta))

        except Exception as exc:
            respuesta = f"❌ Error:\n\n```\n{exc}\n```"
            st.markdown(respuesta)

    st.session_state.messages.append(
        {"role": "assistant", "content": respuesta}
    )
