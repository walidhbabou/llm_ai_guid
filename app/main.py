from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.ai_search import router as ai_search_router
from app.api.routes.test_ui import router as test_ui_router
from app.core.exceptions import AppError
from app.dto.search_dto import ApiErrorResponseDTO

app = FastAPI(title="AI Tourist Guide Backend", version="1.0.0")


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    payload = ApiErrorResponseDTO(
        error={
            "code": exc.code,
            "message": exc.message,
        }
    )
    return JSONResponse(status_code=400, content=payload.model_dump())


@app.exception_handler(Exception)
async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
    payload = ApiErrorResponseDTO(
        error={
            "code": "internal_error",
            "message": f"Erreur interne: {str(exc)}",
        }
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> dict:
    return {}


app.include_router(ai_search_router)
app.include_router(test_ui_router)
