"""Servicio de Inteligencia Artificial para auto-generación de índices y resúmenes."""

import os
import json
from openai import AzureOpenAI

def get_azure_openai_client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    if not endpoint or not api_key:
        raise ValueError("Faltan AZURE_OPENAI_ENDPOINT o AZURE_OPENAI_API_KEY en .env")
        
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-02-15-preview" # Version estable usual
    )

def generate_index_schema(markdown_text: str) -> dict:
    """Genera un esquema estructurado (campos) para un contrato basándose en su contenido crudo."""
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    client = get_azure_openai_client()
    
    prompt = f"""
    Eres un arquitecto de datos experto en Azure AI Search. Analiza el siguiente fragmento de un documento PDF (en formato markdown) 
    y propón un esquema JSON de campos que servirán para catalogar y buscar fragmentos similares de este tipo de archivo.
    
    El esquema siempre DEBE incluir estos campos fijos:
    - id (string)
    - content (string) - El texto completo del fragmento.
    - summary (string) - Un resumen generado por IA de este fragmento específico.
    - document_name (string)
    - section (string)
    
    Además, inventa 3 o 4 campos "custom" MÁS que sean lógicos para este tipo de texto (por ejemplo `legal_category`, `product_type`, `risk_level`, etc).
    Para cada campo, descríbelo e indica si es searchable, filterable.
    
    Devuelve ÚNICAMENTE un objeto JSON con este formato exacto:
    {{
       "fields": [
           {{"name": "id", "type": "Edm.String", "key": true, "searchable": false, "filterable": true}},
           {{"name": "content", "type": "Edm.String", "key": false, "searchable": true, "filterable": false}}
           // ... (agrega el resto fijo y custom) ...
       ]
    }}
    
    Aquí está el texto de muestra:
    {markdown_text[:3000]} # Limitamos a los primeros 3000 caracteres para la base del esquema
    """
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
            # temperature=0.1 Eliminado por incompatibilidad con nuevos modelos
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def extract_structured_metadata(markdown_chunk: str, schema_fields: list, document_name: str) -> dict:
    """Extrae atributos específicos de un texto usando la IA para rellenar un esquema previamente definido e incluye un resumen."""
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    client = get_azure_openai_client()
    
    # Extraemos solo los nombres de los campos que necesitamos adivinar
    # Filtramos id, content, etc. que se llenan estáticamente o en la UI global
    fields_to_guess = [f["name"] for f in schema_fields if f["name"] not in ("id", "content", "document_name", "storage_path", "pdf_source")]
    
    prompt = f"""
    Tu tarea es leer el siguiente fragmento de texto de un documento de nombre {document_name} y extraer metadatos estructurados.
    Debes devolver un ÚNICO objeto JSON (no una lista) que contenga estrictamente y únicamente estas llaves: {fields_to_guess}.
    
    IMPORTANTE: 
    1. Si encuentras múltiples elementos (ej: varias fases, fechas o personas), NO devuelvas una lista. En su lugar, concaténalos en un solo string o resume la información para ese campo.
    2. Los valores deben ser strings simples, NO objetos ni arrays.
    
    Nota especial para 'summary': DEBES escribir un resumen sintético de todo el fragmento en 2-3 oraciones.
    
    Texto del fragmento:
    {markdown_chunk}
    """
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
            # temperature=0.2 Eliminado por incompatibilidad con nuevos modelos
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

def analyze_pdf_page_with_vlm(base64_image: str) -> str:
    """Envía un fotograma de una página PDF estructurada a GPT para obtener Markdown perfecto."""
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    client = get_azure_openai_client()

    prompt = """
    Eres un OCR y analizador visual de documentos de nivel experto. 
    Te he proporcionado una captura de pantalla de UNA PÁGINA de un documento complejo (contratos bancarios, pólizas o legales).
    
    Tu trabajo es:
    1. Transcribir fielmente TODO el texto relevante, manteniendo los párrafos y la jerarquía de títulos.
    2. Si hay **tablas de datos**, formatéalas meticulosamente usando sintaxis Markdown (`|Col1|Col2|...`).
    3. Si hay **gráficos, sellos, firmas o logotipos** importantes, descríbelos usando anotaciones (ej. `[Firma del Gerente General validada]`).
    
    ¡Devuelve ÚNICAMENTE la transcripción final en puro Markdown legible, sin conversar conmigo fuera del resultado!
    """

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}", 
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            # temperature=0.0 Eliminado por incompatibilidad
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"\n> ⚠️ Error al procesar hoja visualmente con la IA: {str(e)}\n"
