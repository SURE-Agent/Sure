"""Servicio Local de Extracción de Texto de PDFs Híbrido (Texto / VLM)."""

import io
import fitz # PyMuPDF
import base64
from PIL import Image

# Importamos el extractor visual de IA
from src.services.ai_generator import analyze_pdf_page_with_vlm

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extrae texto de un documento PDF de forma híbrida.
    Si una página tiene imágenes, vectores o muy poco texto (escaneo puro),
    solicita apoyo al VLM configurado (gpt-4o-mini o gpt-5-mini).
    """
    try:
        documento = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return f"Error leyendo PDF inicial: {str(e)}"
        
    texto_total = []

    for idx in range(len(documento)):
        pagina = documento[idx]
        
        # 1. Extracción Estándar ($0)
        texto_nativo = pagina.get_text("text").strip()
        num_imagenes = len(pagina.get_images())
        
        # 2. Detección heurística de tablas por vectores entrelazados
        # Detectar líneas horizontales y verticales cruzanadas nos indica una tabla dibujada
        dict_text = pagina.get_text("dict")
        tiene_vectores = len(pagina.get_drawings()) > 30 
        
        # 2. Criterio de Rescate Híbrido ("Regla de Negocio")
        necesita_vision = False
        razon = ""
        
        if len(texto_nativo) < 150:
            # Texto nulo o tan corto que probablmente es una imagen escaneada entera
            necesita_vision = True
            razon = "Escaneo Plano / Texto Insuficiente"
        elif num_imagenes > 0:
            # Hay elementos como logos, firmas o fotocopias pegadas
            necesita_vision = True
            razon = "Imágenes Incrustadas / Gráficos"
        elif tiene_vectores:
            necesita_vision = True
            razon = "Diseño Tabular Complejo Interceptado"
            
        # 3. Flujo Condicional
        if necesita_vision:
            texto_total.append(f"\n\n---\n### 👁️ [Página {idx+1} analizada por VLM - Motivo: {razon}]\n")
            
            try:
                # Zoom elevado para asegurar legibilidad de texto pequeño sin reventar la RAM
                zoom = 2.0
                matriz = fitz.Matrix(zoom, zoom)
                pix = pagina.get_pixmap(matrix=matriz, alpha=False)
                
                # Convertimos Pixmap a formato estandar PIL e inyectamos a Base64
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # Lanzar el Frame Fotográfico a tu GPT-5-Mini
                texto_foto = analyze_pdf_page_with_vlm(base64_img)
                texto_total.append(texto_foto)
            except Exception as e:
                # Si falla Pillow o el API por rate limits, guardamos lo que haya en texto puro
                texto_total.append(f"> ⚠️ Error procesando visualmente Pág {idx+1}: {str(e)}\n\n{texto_nativo}")
                
        else:
            # El texto puro extraído es de calidad y no tiene imágenes
            texto_total.append(f"\n\n---\n### 📄 [Página {idx+1} extraída localmente ($0 costo)]\n")
            texto_total.append(texto_nativo)

    return "\n".join(texto_total)
