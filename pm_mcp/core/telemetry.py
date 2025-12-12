"""OpenTelemetry integration for distributed tracing."""

import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from pm_mcp.config import Settings, get_settings

logger = logging.getLogger(__name__)


def init_telemetry(
    settings: Settings | None = None, service_name: str | None = None
) -> None:
    """Initialize OpenTelemetry tracing with OTLP or console exporter.

    Supports both production (container) and local development environments.

    Production config (Phoenix Cloud - priority):
    - phoenix_project_name: Project identifier (used as service.name)
    - otel_endpoint: OTEL Telemetry collector address
    - enable_phoenix: Enable Phoenix telemetry (default: True)

    Local dev fallback config:
    - otel_service_name: Fallback for service name
    - otel_exporter_otlp_endpoint: Fallback for OTEL endpoint

    Args:
        settings: Application settings (default: loaded from environment)
        service_name: Service name override (default: from settings or 'pm-mcp-server')
    """
    try:
        # Load settings if not provided
        if settings is None:
            settings = get_settings()

        # Check if Phoenix telemetry is enabled
        if not settings.enable_phoenix:
            logger.info("Phoenix telemetry disabled (enable_phoenix=false)")
            return

        # Get service name with priority: param > phoenix_project_name > otel_service_name > default
        service_name = (
            service_name
            or settings.phoenix_project_name
            or settings.otel_service_name
            or "pm-mcp-server"
        )

        # Create tracer provider with resource attributes
        resource = Resource(attributes={"service.name": service_name})
        provider = TracerProvider(resource=resource)

        # Get OTLP endpoint with priority: otel_endpoint > otel_exporter_otlp_endpoint
        otlp_endpoint = settings.otel_endpoint or settings.otel_exporter_otlp_endpoint

        if otlp_endpoint:
            logger.info(f"Initializing OTLP exporter: {otlp_endpoint}")
            # Add /v1/traces suffix if not present
            endpoint_url = (
                otlp_endpoint
                if "/v1/traces" in otlp_endpoint
                else f"{otlp_endpoint}/v1/traces"
            )
            exporter = OTLPSpanExporter(endpoint=endpoint_url)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        else:
            logger.info("OTLP endpoint not set, using console exporter for local dev")
            exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry initialized for service: {service_name}")

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        logger.info("Continuing without tracing...")
