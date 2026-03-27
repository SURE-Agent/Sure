"""Módulo para la configuración de monitoreo y tracing con OpenTelemetry."""

import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

# Configuración de logging básico para telemetría
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_telemetry(connection_string: str):
    """
    Inicializa el stack de OpenTelemetry para enviar trazas a Azure Monitor.
    
    Args:
        connection_string: Cadena de conexión de Azure AI Foundry / Application Insights.
    """
    if not connection_string:
        logger.warning("⚠️ Telemetría: No se proporcionó CONNECTION_STRING. Tracing deshabilitado.")
        return

    try:
        # 1. Configurar el TracerProvider si no está configurado
        # Nota: Azure AI SDK habilitará instrumentación automática si encuentra un TracerProvider global.
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

        # 2. Configurar el exportador de Azure Monitor
        # Esto enviará las trazas (incluyendo las del SDK de Azure AI) a Application Insights.
        exporter = AzureMonitorTraceExporter.from_connection_string(connection_string)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)

        logger.info("🚀 Telemetría: Tracing habilitado hacia Azure Monitor.")
    except Exception as e:
        logger.error(f"❌ Telemetría: Error al inicializar el exportador: {e}")

def get_tracer(name: str):
    """Obtiene un tracer para instrumentación manual si es necesario."""
    return trace.get_tracer(name)
