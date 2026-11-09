import os

from dotenv import load_dotenv
load_dotenv()

from opentelemetry import trace # pyright: ignore[reportMissingImports]
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.http.trace_exporter import ( # type: ignore
    OTLPSpanExporter
)
from langfuse import Langfuse

# Identify our application in telemetry
resource = Resource.create({
    "service.name": "ai-observability-lab",
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

# Create tracer provider
provider = TracerProvider(resource=resource)

# Destination 1: Jaeger
jaeger_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces"
)

provider.add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Register global provider
trace.set_tracer_provider(provider)

# Destination 2: Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    base_url=os.getenv(
        "LANGFUSE_BASE_URL",
        "https://cloud.langfuse.com"
    ),
    tracer_provider=provider,
    should_export_span=lambda span: True
)
# Get application tracer
tracer = trace.get_tracer("ai-observability-lab")
