from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError
from app.routers import admin, auth, dev

settings = get_settings()
app = FastAPI(
    title="Samavesh API",
    docs_url=None if settings.is_prod else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_prod else "/openapi.json",
)


@app.exception_handler(AppError)
def app_error_handler(_: Request, exc: AppError):
    return JSONResponse({"code": exc.code, "message": exc.message}, status_code=exc.status)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(admin.router)
if not settings.is_prod:
    app.include_router(dev.router)  # dev outbox; never mounted in production
