import os
import time
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.telemetry import tracer

#Load environment variables from .env file
load_dotenv()

#Configure Application Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("ai_observability")

#Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

#Initialize FastAPI app
app = FastAPI(
    title="AI Observability Lab",
    description="Week-1 LLM Monitoring Application",
    version="1.0.0"
)

FastAPIInstrumentor.instrument_app(app)

#Request Model
class ChatRequest(BaseModel):
    question: str

#Response Model
class ChatResponse(BaseModel):
    answer: str
    model: str
    latency_seconds: float
    input_tokens: int
    output_tokens: int

#Application Statistics
request_count = 0

#Health Endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI Observability Lab"
    }

# AI application endpoint
@app.post("/ask", response_model=ChatResponse)

def ask_ai(request: ChatRequest):

    global request_count
    request_count += 1

    with tracer.start_as_current_span("ai.process") as ai_span:

        ai_span.set_attribute("ai.operation", "chat")
        ai_span.set_attribute("ai.provider", "openai")

        start_time = time.time()

        logger.info("AI request received")

        try:

            # Custom span around the LLM API call
            with tracer.start_as_current_span("openai.chat.completion") as llm_span:

                llm_span.set_attribute(
                    "gen_ai.system", "openai"
                )

                llm_span.set_attribute(
                    "gen_ai.request.model", "gpt-4.1-mini"
                )

                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful technical assistant."
                        },
                        {
                            "role": "user",
                            "content": request.question
                        }
                    ]
                )

                answer = response.choices[0].message.content

                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                # Capture model response metadata
                llm_span.set_attribute(
                    "gen_ai.response.model", response.model
                )

                llm_span.set_attribute(
                    "gen_ai.usage.input_tokens", input_tokens
                )

                llm_span.set_attribute(
                    "gen_ai.usage.output_tokens", output_tokens
                )

            latency = time.time() - start_time

            ai_span.set_attribute(
                "ai.latency_seconds", round(latency, 3)
            )

            ai_span.set_attribute(
                "ai.input_tokens", input_tokens
            )

            ai_span.set_attribute(
                "ai.output_tokens", output_tokens
            )

            logger.info(
                "AI request completed | latency=%.3f | input_tokens=%d | output_tokens=%d",
                latency,
                input_tokens,
                output_tokens
            )

            return ChatResponse(
                answer=answer,
                model=response.model,
                latency_seconds=round(latency, 3),
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

        except Exception as exc:

            ai_span.record_exception(exc)
            ai_span.set_status(Status(StatusCode.ERROR))

            logger.exception("AI request failed")

            raise HTTPException(
                status_code=500,
                detail="AI request failed. Check application logs."
            )



# Basic statistics endpoint
@app.get("/metrics-info")
def metrics_info():
    return {
        "total_requests": request_count
    }
