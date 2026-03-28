"""Componente UI para el Pipeline de Administración de Documentos orientados a carpetas e IA."""

import streamlit as st
import uuid
import json
import time
import base64

from src.services.local_parser import extract_text_from_pdf
from src.services.search_service import upload_chunks_to_search, create_custom_index
from src.services.storage_service import upload_document_to_blob
from src.services.ai_generator import generate_index_schema, extract_structured_metadata

def clean_json_for_azure(data):
    """Asegura que todos los valores sean strings o números, convirtiendo listas accidentales en strings."""
    if isinstance(data, list):
        # Si la IA devolvió una lista, tomamos el primer objeto o lo que parezca útil
        return clean_json_for_azure(data[0]) if data else {}
    
    clean_data = {}
    for k, v in data.items():
        if isinstance(v, (list, dict)):
            # Convertimos listas/objetos anidados a string plano para evitar errores de OData StartArray
            clean_data[k] = json.dumps(v, ensure_ascii=False)
        else:
            clean_data[k] = v
    return clean_data

def reset_pipeline():
    for key in ["pipeline_view", "selected_folder", "selected_file_id", "schema_draft"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def render_pipeline():
    st.title("📂 Explorador de Colecciones (Storage UI) 🚀")
    
    # Init states
    if "collections" not in st.session_state:
        st.session_state.collections = {} # {"nombre_carpeta": {"schema": None, "files": []}}
    if "pipeline_view" not in st.session_state:
        st.session_state.pipeline_view = "explorer" # explorer, schema_builder, pdf_analyzer
    if "selected_folder" not in st.session_state:
        st.session_state.selected_folder = None
    if "selected_file_id" not in st.session_state:
        st.session_state.selected_file_id = None

    view = st.session_state.pipeline_view

    # ==========================================
    # VISTA 1: EXPLORADOR DE ARCHIVOS (CARPETAS)
    # ==========================================
    if view == "explorer":
        # Formulario para crear carpeta
        with st.form("new_folder_form", clear_on_submit=True):
            cols = st.columns([3, 1])
            folder_name = cols[0].text_input("📁 Nueva Colección (minúsculas y guiones, ej. polizas)", placeholder="Nombre de la carpeta")
            submitted = cols[1].form_submit_button("Crear Colección", use_container_width=True)
            
            if submitted:
                if folder_name:
                    safe_name = folder_name.lower().replace(" ", "-")
                    if safe_name not in st.session_state.collections:
                        st.session_state.collections[safe_name] = {"schema": None, "files": []}
                        st.success(f"Carpeta '{safe_name}' creada.")
                        st.rerun()
                    else:
                        st.error("Ya existe esa carpeta.")
        
        st.divider()
        st.subheader("Tus Colecciones")
        
        if not st.session_state.collections:
            st.info("No tienes colecciones creadas todavía. Crea una carpeta para comenzar.")
        
        for f_name, f_data in st.session_state.collections.items():
            archivos = f_data["files"]
            schema = f_data["schema"]
            
            with st.expander(f"📁 {f_name} ({len(archivos)} archivos)", expanded=True):
                # Opciones de Carpeta
                c_head1, c_head2 = st.columns([1, 1])
                has_files = len(archivos) > 0
                has_schema = schema is not None
                
                with c_head1:
                    if has_schema:
                        st.success("✅ Esquema de Índice Creado")
                    else:
                        if has_files:
                            if st.button("✨ Crear Esquema de Índice", key=f"btn_schema_{f_name}"):
                                st.session_state.selected_folder = f_name
                                st.session_state.pipeline_view = "schema_builder"
                                st.rerun()
                        else:
                            st.warning("⚠️ Sube un PDF para crear el esquema")
                
                with c_head2:
                    if st.button("🗑️ Eliminar Colección", key=f"del_col_{f_name}", type="secondary"):
                        del st.session_state.collections[f_name]
                        st.rerun()

                st.markdown("---")
                
                # Uploader de archivos a esta carpeta
                uploaded_files = st.file_uploader("Subir PDFs", type=["pdf"], accept_multiple_files=True, key=f"up_{f_name}")
                if uploaded_files:
                    if st.button("Guardar Archivos Subidos", key=f"save_{f_name}"):
                        for uf in uploaded_files:
                            # Avoid duplicates by name
                            if not any(a["name"] == uf.name for a in archivos):
                                archivos.append({
                                    "id": str(uuid.uuid4()),
                                    "name": uf.name,
                                    "bytes": uf.read(),
                                    "status": "Pendiente",
                                    "markdown": None,
                                    "json_chunk": None
                                })
                        st.rerun()
                
                # Lista de Archivos
                if archivos:
                    st.write("#### Archivos extraídos")
                    for a in archivos:
                        fa_col1, fa_col2, fa_col3 = st.columns([3, 1, 1])
                        estado_icon = "🏷️ (Indexado)" if a.get("status") == "Indexado" else "📝 (Pendiente)"
                        fa_col1.write(f"📄 **{a['name']}** {estado_icon}")
                        
                        if fa_col2.button("⚙️ Analizar PDF", key=f"an_{a['id']}"):
                            st.session_state.selected_folder = f_name
                            st.session_state.selected_file_id = a['id']
                            st.session_state.pipeline_view = "pdf_analyzer"
                            st.rerun()
                            
                        if fa_col3.button("🗑️ Eliminar", key=f"del_{a['id']}"):
                            f_data["files"] = [f for f in archivos if f["id"] != a["id"]]
                            st.rerun()

    # ==========================================
    # VISTA 2: CREADOR DE ESQUEMA (CARPETA)
    # ==========================================
    elif view == "schema_builder":
        f_name = st.session_state.selected_folder
        f_data = st.session_state.collections[f_name]
        
        st.header(f"Esquema de Índice: {f_name}")
        st.write("La IA recomendará una estructura de base de datos basada en tus PDFs.")
        
        if st.button("🔙 Volver al Explorador", key="btn_back_schema"):
            if "schema_draft" in st.session_state:
                del st.session_state.schema_draft
            st.session_state.pipeline_view = "explorer"
            st.rerun()
            
        with st.spinner("Leyendo primer documento para extraer Taxonomía..."):
            primer_pdf_bytes = f_data["files"][0]["bytes"]
            texto_base = extract_text_from_pdf(primer_pdf_bytes)
                
            if "schema_draft" not in st.session_state:
                esquema = generate_index_schema(texto_base)
                if "error" in esquema:
                    st.error(esquema["error"])
                else:
                    st.session_state.schema_draft = esquema.get("fields", [])
                    st.rerun()
                        
        if "schema_draft" in st.session_state:
            st.success("🤖 ¡La IA propuso el siguiente esquema estructural!")
            schema_str = json.dumps(st.session_state.schema_draft, indent=4)
            edited_schema_str = st.text_area("JSON Formato:", value=schema_str, height=350)
            
            if st.button("🔨 Construir Índice Semántico en Azure", type="primary"):
                with st.spinner("Creando el índice..."):
                    try:
                        campos_aprobados = json.loads(edited_schema_str)
                        resultado = create_custom_index(f_name, campos_aprobados)
                        
                        if resultado.get("success"):
                            st.success(resultado["message"])
                            f_data["schema"] = campos_aprobados
                            del st.session_state.schema_draft
                            time.sleep(1.5)
                            st.session_state.pipeline_view = "explorer"
                            st.rerun()
                        else:
                            st.error(resultado["message"])
                    except Exception as e:
                        st.error(f"Error parseando el JSON: {e}")

    # ==========================================
    # VISTA 3: ANALIZADOR DE PDF LADO A LADO
    # ==========================================
    elif view == "pdf_analyzer":
        f_name = st.session_state.selected_folder
        f_data = st.session_state.collections[f_name]
        archivo = next((f for f in f_data["files"] if f["id"] == st.session_state.selected_file_id), None)
        schema = f_data["schema"]
        
        col_hdr1, col_hdr2 = st.columns([3, 1])
        with col_hdr1:
            st.header(f"🔍 Análisis: {archivo['name']}")
        with col_hdr2:
            if st.button("🔙 Volver al Explorador", key="btn_back_pdf"):
                st.session_state.pipeline_view = "explorer"
                st.rerun()
        
        if not schema:
            st.warning("⚠️ Debes crear el esquema del índice en la carpeta antes de extraer metadatos del PDF.")
            st.stop()
            
        col_pdf, col_data = st.columns(2)
        
        # LADO IZQUIERDO: PREVISUALIZACION PDF
        with col_pdf:
            st.subheader("Visor de PDF Original")
            base64_pdf = base64.b64encode(archivo["bytes"]).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        # LADO DERECHO: DATOS Y METADATOS
        with col_data:
            st.subheader("💡 Extracción y Etiquetas")
            
            # 1. Extracción Markdown
            if not archivo.get("markdown"):
                if st.button("1. Extraer Texto Base (OCR Semántico)"):
                    with st.spinner("Parseando PDF..."):
                        archivo["markdown"] = extract_text_from_pdf(archivo["bytes"])
                        st.rerun()
            else:
                st.success("Capa 1: Markdown Extraído.")
                with st.expander("Ver el texto extraído (.md)", expanded=True):
                    archivo["markdown"] = st.text_area("Puedes corregirlo aquí:", value=archivo["markdown"], height=200)
            
            # 2. Generación JSON (IA)
            if archivo.get("markdown"):
                if not archivo.get("json_chunk"):
                    if st.button("2. 🧠 Generar Chunk JSON (Heredado)"):
                        with st.spinner("Desatando IA sobre el texto..."):
                            json_r = extract_structured_metadata(archivo["markdown"], schema, archivo["name"])
                            if "error" in json_r:
                                st.error(json_r["error"])
                            else:
                                archivo["json_chunk"] = json_r
                                st.rerun()
                                
            # 3. Vista y Subida
            if archivo.get("json_chunk"):
                st.success("Capa 2: JSON Generado de Etiquetas.")
                json_str = json.dumps(archivo["json_chunk"], indent=4, ensure_ascii=False)
                edited_json_chunk = st.text_area("JSON para Azure Search:", value=json_str, height=200)
                
                if st.button("📤 Aprobar y Subir al Índice", type="primary"):
                    with st.spinner(f"Indexando en Azure '{f_name}'..."):
                        try:
                            raw_dict = json.loads(edited_json_chunk)
                            chunk_dict = clean_json_for_azure(raw_dict) # Capa de seguridad anti-arrays
                            
                            chunk_dict["@search.action"] = "upload"
                            chunk_dict["id"] = st.session_state.selected_file_id.replace("-", "")
                            
                            # Datos fijos
                            chunk_dict["content"] = archivo["markdown"]
                            chunk_dict["document_name"] = archivo["name"]
                            resultado = upload_chunks_to_search([chunk_dict], f_name)
                            
                            # Subir al Blob Storage real
                            blob_result = upload_document_to_blob(f"{f_name}/{archivo['name']}", archivo["bytes"])
                            
                            if resultado.get("success"):
                                archivo["status"] = "Indexado"
                                st.success("🎉 ¡Documento guardado al Índice Cognitivo de Azure!")
                                if not "Error" in blob_result:
                                    st.success(f"☁️ Guardado en el Blob (Ruta: {blob_result})")
                                else:
                                    st.error(f"Fallo al subir a Blob: {blob_result}")
                            else:
                                st.error(resultado["message"])
                        except Exception as e:
                            st.error(f"Error parseando el JSON editado: {e}")
