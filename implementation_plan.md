# Plan de Implementación actual: Pipeline Visual de Azure

Este documento detalla el plan actualizado para construir el pipeline visual de subida y procesamiento de documentos integrando Azure Blob Storage, Modelos Visuales-Lenguaje (VLM, por ej. OpenAI GPT-4o con visión o Document Intelligence) y Azure AI Search.

## 1. Historias de Usuario (HU)

- **HU1: Subida de Documentos (PDF/Word) a Storage**
  - **Como** usuario, **quiero** poder subir archivos PDF o Word a través de la interfaz.
  - **Para** que sean almacenados e ingresados al proceso de parseo inteligente usando un VLM, capaz de 'leer' texto e imágenes.
- **HU2: Conversión a Markdown Manipulable**
  - **Como** usuario, **quiero** que el sistema extraiga el contenido y layout (estructura) del PDF/Word en formato Markdown ([.md](file:///c:/Users/Jefferson/Documents/Proyectos/Sure/README.md)) y me lo presente en un editor interactivo.
  - **Para** poder manipularlo y corregir manualmente cualquier equivocación que haya tenido el VLM antes de continuar.
- **HU3: Selección y Generación de Resumen**
  - **Como** usuario, **quiero** poder seleccionar partes específicas del layout Markdown aprobado.
  - **Para** indicar a la IA sobre qué secciones exactas generar los resúmenes o análisis adicionales.
- **HU4: Generación y Aprobación de JSONs (Índice y Chunks)**
  - **Como** sistema, **quiero** conformar la información y metadatos extraídos en dos esquemas JSON exactos:
    1. El esquema de configuración del índice.
    2. El "array" de chunks a subir (cada chunk es un documento parcial con su resumen/metadatos).
  - **Para** mostrar ambos JSON al usuario, permitiéndole dar el "ok" definitivo previo a la carga.
- **HU5: Indexación en AI Search**
  - **Como** sistema, **quiero** enviar el JSON de chunks validados hacia el índice correspondiente en Azure AI Search.
  - **Para** disponer del contenido vectorizado e indizado.

---

## 2. Variables de Entorno Necesarias ([.env](file:///c:/Users/Jefferson/Documents/Proyectos/Sure/.env))

```env
# ----------------------------------------
# Azure Blob Storage
# ----------------------------------------
AZURE_STORAGE_CONNECTION_STRING="tu_connection_string_aqui"
AZURE_STORAGE_CONTAINER_NAME="nombre_del_contenedor"

# ----------------------------------------
# Azure OpenAI (VLM para lectura de PDF con imágenes y generación de resúmenes)
# ----------------------------------------
AZURE_OPENAI_ENDPOINT="https://<tu-recurso>.openai.azure.com/"
AZURE_OPENAI_API_KEY="tu_api_key_openai"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o_o_modelo_similar_vlm"
AZURE_OPENAI_API_VERSION="2024-02-15-preview" 

# ----------------------------------------
# Azure AI Search
# ----------------------------------------
AZURE_SEARCH_ENDPOINT="https://<tu-servicio>.search.windows.net"
AZURE_SEARCH_ADMIN_KEY="tu_admin_key"
AZURE_SEARCH_INDEX_NAME="contracts-index"
```

---

## 3. Esquemas de Datos JSON

El sistema construirá y solicitará aprobación sobre una estructura de datos basada en estos esquemas. *Nota: Estos esquemas son un ejemplo de cómo deberían estructurarse los JSON, pero no son estrictos; la implementación final puede adaptarse según las necesidades de los documentos extraídos.*

### 3.1. Esquema del Índice (Ejemplo)

```json
{
  "name": "contracts-index",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true},
    {"name": "product", "type": "Edm.String", "filterable": true},
    {"name": "product_code", "type": "Edm.String", "filterable": true},
    {"name": "product_family", "type": "Edm.String", "filterable": true},
    {"name": "document_name", "type": "Edm.String", "filterable": true},
    {"name": "document_type", "type": "Edm.String", "filterable": true},
    {"name": "document_version", "type": "Edm.String", "filterable": true},
    {"name": "pdf_source", "type": "Edm.String", "filterable": true},
    {"name": "document_priority", "type": "Edm.Int32", "filterable": true},
    {"name": "supports_claim_analysis", "type": "Edm.Boolean", "filterable": true},
    {"name": "section", "type": "Edm.String", "searchable": true},
    {"name": "clause", "type": "Edm.String", "filterable": true},
    {"name": "subclause", "type": "Edm.String", "filterable": true},
    {"name": "clause_title", "type": "Edm.String", "searchable": true},
    {"name": "subclause_title", "type": "Edm.String", "searchable": true},
    {"name": "actor", "type": "Collection(Edm.String)", "filterable": true},
    {"name": "responsibility_type", "type": "Edm.String", "filterable": true},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": true},
    {"name": "risk_holder", "type": "Edm.String", "filterable": true},
    {"name": "legal_effect", "type": "Edm.String", "searchable": true},
    {"name": "is_customer_risk_clause", "type": "Edm.Boolean", "filterable": true},
    {"name": "page", "type": "Edm.Int32", "filterable": true},
    {"name": "citation", "type": "Edm.String", "searchable": true},
    {"name": "content", "type": "Edm.String", "searchable": true},
    {"name": "source_hash", "type": "Edm.String", "filterable": true},
    {"name": "last_updated", "type": "Edm.DateTimeOffset", "filterable": true},
    {"name": "regulatory_reference", "type": "Edm.String", "searchable": true}
  ]
}
```

### 3.2. Esquema de Chunks a Indexar (Los Valores a Subir)

Se generará una lista de objetos similares a este:

```json
{
  "value": [
    {
      "@search.action": "upload",
      "id": "CGCS_1_a",
      "product": "Cuenta Premio",
      "product_code": "CUENTA_PREMIO",
      "product_family": "CUENTAS",
      "document_name": "Condiciones Generales de las Cuentas y Servicios",
      "document_type": "Contrato",
      "document_version": "v1_2025",
      "storage_path": "Productos/Cuentas/Cuenta_Premio/CondicionesGeneralesCuentas&Servicios.pdf",
      "pdf_source": "Condiciones Generales de las Cuentas y Servicios",
      "document_priority": 1,
      "supports_claim_analysis": true,
      "section": "Condiciones Generales",
      "...": "..."
    }
  ]
}
```

---

## 4. Estructura de Archivos Propuesta

Se construirá bajo un sistema modular usando **Streamlit** (para la agilidad en interfaces manipulables o text areas dinámicos).

* `src/main.py` -> Aplicación principal con los pasos interactivos.
* [.env](file:///c:/Users/Jefferson/Documents/Proyectos/Sure/.env) -> Archivo de variables de entorno.
* `src/services/storage_service.py` -> Sube el PDF original a Azure Blob.
* `src/services/vlm_parser.py` -> Llama a Azure OpenAI (VLM) para convertir páginas de PDF/Word en [.md](file:///c:/Users/Jefferson/Documents/Proyectos/Sure/README.md).
* `src/services/metadata_extractor.py` -> Módulo extra que mapea el Markdown a los campos del JSON (product, clause, page, rules, tags, etc) basándose en las secciones indicadas por el usuario.
* `src/services/search_service.py` -> Encargado de mandar el índice al servicio de Azure AI Search y subir los JSONs de "chunks".
* `src/models/chunk_schema.py` -> Modelos Pydantic opcionales para validar la metadata (Asegurando que "document_priority" es `Int32`, etc.).
