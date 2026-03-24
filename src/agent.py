"""Cliente del agente de Azure AI Foundry."""

from __future__ import annotations

import streamlit as st
from azure.ai.projects import AIProjectClient

from src.auth import get_credential
from src.config import CONNECTION_STRING


@st.cache_resource(show_spinner=False)
def get_client() -> AIProjectClient:
    """Crea y cachea una instancia única de AIProjectClient."""
    return AIProjectClient.from_connection_string(
        credential=get_credential(),
        conn_str=CONNECTION_STRING,
    )


def create_thread(client: AIProjectClient) -> str:
    """Crea un nuevo hilo de conversación y retorna su ID."""
    return client.agents.create_thread().id


def send_message(
    client: AIProjectClient,
    thread_id: str,
    agent_id: str,
    prompt: str,
) -> dict:
    """Envía un mensaje al agente y retorna la respuesta completa con anotaciones.

    Retorna
    -------
    dict
        ``{"value": "texto de respuesta", "annotations": [...]}``
    """
    # 1. Crear el mensaje del usuario
    client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content=prompt,
    )

    # 2. Ejecutar el agente de forma síncrona
    client.agents.create_and_process_run(
        thread_id=thread_id,
        agent_id=agent_id,
    )

    # 3. Obtener los mensajes más recientes
    api_messages = client.agents.list_messages(thread_id=thread_id)

    for text_msg in api_messages.text_messages:
        data = text_msg.as_dict()
        text_obj = data.get("text", {})
        if isinstance(text_obj, dict):
            return {
                "value": text_obj.get("value", ""),
                "annotations": text_obj.get("annotations", []),
            }
        return {"value": str(text_obj), "annotations": []}

    return {"value": "", "annotations": []}
