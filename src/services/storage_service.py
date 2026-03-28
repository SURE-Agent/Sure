"""Servicio para interactuar con Azure Blob Storage."""

import os
from azure.storage.blob import BlobServiceClient

def get_blob_service_client() -> BlobServiceClient:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    if not conn_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING no está definido en el .env")
    return BlobServiceClient.from_connection_string(conn_str)

def upload_document_to_blob(file_name: str, file_bytes: bytes) -> str:
    """Sube un documento a Blob Storage y retorna su ruta relativa."""
    try:
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "documentos")
        
        client = get_blob_service_client()
        container_client = client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
        
        # Opcional: Anidar los archivos subidos de las colecciones a sus respectivas carpetas virtuales
        # Pero según este esquema, va a 'documentos/file_name'
        blob_client = client.get_blob_client(container=container_name, blob=file_name)
        blob_client.upload_blob(file_bytes, overwrite=True)
        
        return f"{container_name}/{file_name}"
    except Exception as e:
        return f"Error_Blob: {str(e)}"
