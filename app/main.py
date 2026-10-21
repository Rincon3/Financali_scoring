from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.model import service
from app.schemas import ScoreRequest, ScoreResponse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(
    title="FinanCali Scoring Lab",
    version="0.1.0",
    description=(
        "Prototipo académico para observar parámetros, métricas y controles "
        "de un scoring tabular. No es un sistema de otorgamiento de crédito."
    ),
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    if request.url.path == "/api/score":
        service.register_invalid_request()
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "detail": exc.errors(),
                "message": "La solicitud contiene valores fuera del contrato permitido.",
            }
        ),
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model_version": service.bundle.metadata["model_version"],
    }


@app.get("/api/model-card")
async def model_card() -> dict:
    return {
        "metadata": service.bundle.metadata,
        "metrics": service.bundle.metrics,
        "operations": service.operational_metrics(),
    }


@app.get("/api/metrics")
async def metrics() -> dict:
    return {
        "baseline": service.bundle.metrics,
        "operations": service.operational_metrics(),
    }


@app.post("/api/score", response_model=ScoreResponse)
async def score(request: ScoreRequest) -> dict:
    return service.score(request.application, request.thresholds)
