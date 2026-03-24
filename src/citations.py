"""Procesa las anotaciones de citas del agente de Azure AI Foundry en notas al pie de Markdown."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure.ai.projects import AIProjectClient


def process_citations(
    text: str,
    annotations: list[dict],
    client: AIProjectClient | None = None,
) -> str:
    """Reemplaza marcadores de citas (ej: 【5:0†source】) con notas al pie en Markdown.

    Soporta tipos de anotación: ``url_citation``, ``file_citation``, ``file_path``.
    """
    if not annotations:
        return _limpiar_marcadores(text)

    notas: list[str] = []
    num_nota = 1

    for ann in annotations:
        tipo = ann.get("type", "")
        marcador = ann.get("text", "")

        if not marcador:
            continue

        # ── url_citation (más común con agentes grounded) ──
        if tipo == "url_citation":
            citation = ann.get("url_citation", {})
            titulo = citation.get("title", "")
            url = citation.get("url", "")

            # Construir etiqueta legible
            if titulo:
                etiqueta = titulo
            elif url and url.startswith("http"):
                etiqueta = url
            else:
                etiqueta = f"Fuente {num_nota}"

            text = text.replace(marcador, f" **[{num_nota}]**")
            notas.append(f"**{num_nota}.** 📄 {etiqueta}")
            num_nota += 1

        # ── file_citation ──
        elif tipo == "file_citation":
            nombre_archivo = _resolver_nombre_archivo(ann.get("file_citation", {}), client)
            text = text.replace(marcador, f" **[{num_nota}]**")
            notas.append(f"**{num_nota}.** 📄 {nombre_archivo}")
            num_nota += 1

        # ── file_path ──
        elif tipo == "file_path":
            nombre_archivo = _resolver_nombre_archivo(ann.get("file_path", {}), client)
            text = text.replace(marcador, f"📎 {nombre_archivo}")

    # Limpiar marcadores que no fueron cubiertos por las anotaciones
    text = _limpiar_marcadores(text)

    # Agregar sección de fuentes al final
    if notas:
        text += "\n\n---\n📎 **Fuentes:**\n\n" + "\n\n".join(notas)

    return text


# ── Funciones auxiliares ──────────────────────────────────


def _resolver_nombre_archivo(
    obj_citation: dict, client: AIProjectClient | None
) -> str:
    """Intenta obtener el nombre legible del archivo a partir del file_id."""
    file_id = obj_citation.get("file_id", "")
    if not file_id or not client:
        return obj_citation.get("title", "Documento")
    try:
        info_archivo = client.agents.get_file(file_id)
        return getattr(info_archivo, "filename", None) or file_id
    except Exception:
        return file_id


def _limpiar_marcadores(text: str) -> str:
    """Elimina cualquier marcador 【...】 restante que no fue procesado."""
    return re.sub(r"\s*【[^】]*】\s*", " ", text).strip()
