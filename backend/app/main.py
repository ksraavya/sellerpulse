import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.sellers import router as sellers_router
from app.repositories.seller_repository import SellerDataError

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "SellerPulse AI")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(
    title=APP_NAME,
    description="Voice-first AI Virtual Key Account Manager prototype.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(sellers_router)


@app.exception_handler(SellerDataError)
async def handle_seller_data_error(
    _request: Request,
    exc: SellerDataError,
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME}
