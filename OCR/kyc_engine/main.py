from fastapi import FastAPI

from kyc_engine.config import get_settings, load_environment

load_environment()

from kyc_engine.api.routes import router

settings = get_settings()

app = FastAPI(
    title="Zero-Trust Deterministic KYC Validation Engine",
    version="1.0.0",
    description=(
        "Upload PAN, Aadhaar, bank statement, and live signature files to run "
        "deterministic KYC validation with a full audit trail."
    ),
)
app.include_router(router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "gemini_configured": "true" if settings.gemini_configured else "false",
        "gemini_model": settings.gemini_vision_model,
        "tesseract_available": "true" if settings.tesseract_available else "false",
        "tesseract_cmd": settings.resolved_tesseract_cmd or "",
    }
