"""Procesa las anotaciones de citas nativas del agente de Azure AI Foundry."""

from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from azure.ai.projects import AIProjectClient


def process_citations(
    text: str,
    annotations: list[Any],
    client: AIProjectClient | None = None,
) -> str:
    if not annotations:
        return _limpiar_marcadores(text)

    notas: list[str] = []
    num_nota = 1

    # 🔥 TRUCO HACKATHON: Extraer el nombre real del documento desde el texto generado por SURE 🔥
    # Buscamos la parte donde el bot dice "De acuerdo con el documento **[Nombre]**"
    match = re.search(r"De acuerdo con el documento\s*\*\*([^*]+)\*\*", text)
    if not match:
        # Si no lo encuentra ahí, lo busca en el Audit Trail
        match = re.search(r"\*\s*Documento:\s*(.*?)\s*(?:\||\n)", text)
    
    # Si encuentra el nombre, lo guarda; si no, usa uno genérico
    nombre_real = match.group(1).strip() if match else "Documento de Referencia"

    for ann in annotations:
        tipo = _get_val(ann, "type", "")
        marcador = _get_val(ann, "text", "")

        if not marcador:
            continue

        # Interceptamos la cita nativa (ya sea url_citation o file_citation)
        if tipo in ["url_citation", "file_citation"]:
            
            # En lugar de usar el dato basura de Azure ("doc_0"), INYECTAMOS el nombre real que extrajimos
            etiqueta = nombre_real

            # Reemplazamos el marcador feo 【3:0†source】 por un número bonito [1]
            text = text.replace(marcador, f" **[{num_nota}]**")
            
            # Agregamos la nota a la lista final
            notas.append(f"**{num_nota}.** 📄 {etiqueta}")
            num_nota += 1

    # Limpiamos cualquier marcador sobrante
    text = _limpiar_marcadores(text)

    # Agregamos la sección de citas nativas al final
    if notas:
        text += "\n\n---\n📎 **Citas Nativas (Azure AI Search):**\n\n" + "\n".join(notas)

    return text


# ── Funciones auxiliares ──────────────────────────────────

def _get_val(obj: Any, key: str, default: Any = "") -> Any:
    """Extrae un valor de forma segura (soporta dicts y objetos Pydantic)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _limpiar_marcadores(text: str) -> str:
    """Elimina marcadores 【...】 o [doc_1] que no hayan sido procesados."""
    text = re.sub(r"\s*【[^】]*】\s*", " ", text)
    text = re.sub(r"\s*\[doc_?\d+\]\s*", " ", text)
    return text.strip()