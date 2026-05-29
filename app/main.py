import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.api.routes import router as api_router

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Garendil API",
    description="Public corruption risk scoring system for Peruvian officials",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup():
    from app.monitoring.sentry_setup import setup_sentry
    from app.monitoring.logging_config import configure_logging
    configure_logging()
    setup_sentry()
    logger.info("Garendil API iniciada")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.6.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
