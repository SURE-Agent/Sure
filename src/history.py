"""Manejo de historial de hilos de conversación en archivo local."""

import json
import os
from datetime import datetime

HISTORY_FILE = "conversation_history.json"

def save_thread(thread_id: str, first_message: str):
    """Guarda un ID de hilo y su primer mensaje como título en el historial local."""
    history = load_history()
    
    # Si el hilo ya existe, no lo duplicamos (o podríamos actualizarlo)
    for entry in history:
        if entry["thread_id"] == thread_id:
            return

    new_entry = {
        "thread_id": thread_id,
        "title": first_message[:50] + ("..." if len(first_message) > 50 else ""),
        "timestamp": datetime.now().isoformat()
    }
    
    history.insert(0, new_entry) # Insertar al principio (más reciente primero)
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def load_history():
    """Carga el historial de hilos desde el archivo local."""
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def clear_history():
    """Borra el archivo de historial."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
