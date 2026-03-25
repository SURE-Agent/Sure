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
    # 1. MEJORA: Carga de logo local con manejo de errores
    try:
        # Esto hace que el logo se expanda para llenar la barra lateral
        st.image("logo.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ Logo no encontrado. Verifica la ruta del archivo.")
        
    st.title("Sure Agent")
    st.caption("Make **SURE** your compliance is grounded.")
    st.divider()
    
    # 2. MEJORA: Botón primario y borrado total del estado
    if st.button("🗑️ Nueva conversación", use_container_width=True, type="primary"):
        st.session_state.clear() # Borra todo de forma más segura
        st.rerun()

# ── Cliente e hilo de conversación ───────────────────────
client = get_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = create_thread(client)

thread_id = st.session_state.thread_id

# ── Helpers de streaming ─────────────────────────────────
def transmitir_texto(texto: str):
    """Genera texto palabra por palabra para crear efecto de escritura."""
    palabras = texto.split(" ")
    for i, palabra in enumerate(palabras):
        yield palabra + ("" if i == len(palabras) - 1 else " ")
        time.sleep(0.015) # 3. MEJORA: Reduje el tiempo para que la lectura sea más fluida

# ── Pantalla de bienvenida ───────────────────────────────
# 4. MEJORA: Mensaje inicial si el chat está vacío para no mostrar pantalla en blanco
if not st.session_state.messages:
    st.info("👋 **¡Hola! Soy SURE.**\n¿En qué te puedo ayudar hoy?")

# ── Renderizar historial de chat ─────────────────────────
for msg in st.session_state.messages:
    # 5. MEJORA: Avatares personalizados visuales
    avatar_icon = "🛡️" if msg["role"] == "assistant" else "👤"
    
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.markdown(msg["content"])
        
        if msg.get("fuentes"):
            with st.expander("📚 Ver documentos fuente"):
                for fuente in msg["fuentes"]:
                    st.caption(f"- {fuente}")

# ── Entrada del chat ─────────────────────────────────────
if prompt := st.chat_input("Escribe tu consulta aquí…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🛡️"):
        fuentes_extraidas = [] 
        try:
            with st.spinner("Analizando documentos técnicos..."):
                resultado = send_message(client, thread_id, AGENT_ID, prompt)
                respuesta = process_citations(
                    resultado["value"],
                    resultado["annotations"],
                    client,
                )

            st.write_stream(transmitir_texto(respuesta))
            
            if resultado.get("annotations"):
                with st.expander("📚 Ver documentos fuente"):
                    for anotacion in resultado["annotations"]:
                        texto_cita = getattr(anotacion, 'text', str(anotacion)) 
                        st.caption(f"- {texto_cita}")
                        fuentes_extraidas.append(texto_cita)

            # Guardar el mensaje exitoso en el historial
            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta, "fuentes": fuentes_extraidas}
            )

        except Exception as exc:
            # 6. MEJORA: UI de error más amigable sin guardarlo en el historial permanente
            st.error("Ocurrió un error al procesar la solicitud.")
            with st.expander("Detalles del error técnico"):
                st.code(exc, language="python")