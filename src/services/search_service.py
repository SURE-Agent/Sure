"""Servicio de Indexación a Azure AI Search con Auto-Configuración y Creación."""

import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)

def get_search_index_client() -> SearchIndexClient:
    """Cliente para administración estructurada del Índice."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    if not endpoint or not admin_key:
        raise ValueError("AZURE_SEARCH_ENDPOINT o ADMIN_KEY no definidos.")
    return SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))

def get_search_client(index_name: str) -> SearchClient:
    """Cliente para operaciones de datos (subir chunks)."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    if not endpoint or not admin_key:
        raise ValueError("AZURE_SEARCH_ENDPOINT o ADMIN_KEY no definidos en .env.")
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

def create_custom_index(index_name: str, schema_fields: list) -> dict:
    """Construye un Índice en Azure Search usando la respuesta generada por IA."""
    client = get_search_index_client()
    fields = []
    
    for f in schema_fields:
        name = f.get("name")
        ftype = SearchFieldDataType.String
        is_key = f.get("key", False)
        searchable = f.get("searchable", False)
        filterable = f.get("filterable", False)
        
        if is_key:
            fields.append(SimpleField(name=name, type=ftype, key=True))
        elif searchable:
            fields.append(SearchableField(name=name, type=ftype, filterable=filterable))
        else:
            fields.append(SimpleField(name=name, type=ftype, filterable=filterable))
            
    # Autoconfiguración Semántica Heurística
    field_names = [f.get("name") for f in schema_fields if f.get("name")]
    
    title_field = None
    content_fields = []
    keyword_fields = []
    
    for candidate in field_names:
        c_low = candidate.lower()
        if c_low in ["document_name", "title", "nombre_documento"]:
            title_field = SemanticField(field_name=candidate)
        elif c_low in ["content", "summary", "resumen", "texto"]:
            content_fields.append(SemanticField(field_name=candidate))
        elif candidate != "id":
            keyword_fields.append(SemanticField(field_name=candidate))
            
    if not title_field and len(field_names) > 1:
        title_field = SemanticField(field_name=field_names[1])

    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=title_field,
            content_fields=content_fields if content_fields else [SemanticField(field_name=field_names[-1])],
            keyword_fields=keyword_fields[:5] # Top 5 keywords
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(
        name=index_name,
        fields=fields,
        semantic_search=semantic_search
    )
    
    try:
        result = client.create_or_update_index(index)
        return {"success": True, "message": f"Índice '{result.name}' creado con configuración semántica incluida."}
    except Exception as e:
        return {"success": False, "message": f"Error Azure: {str(e)}"}

def upload_chunks_to_search(chunks: list[dict], index_name: str) -> dict:
    """Sube una lista de chunks a un índice preexistente."""
    try:
        client = get_search_client(index_name)
        result = client.upload_documents(documents=chunks)
        succeeded = sum(1 for res in result if res.succeeded)
        failed = len(result) - succeeded
        
        return {
            "success": True if failed == 0 else False,
            "message": f"{succeeded} almacenados exitosamente. {failed} fallaron.",
            "succeeded": succeeded,
            "failed": failed
        }
    except Exception as e:
        return {"success": False, "message": f"Fallo al subir data: {str(e)}"}
