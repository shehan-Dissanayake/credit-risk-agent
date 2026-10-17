from fastapi import FastAPI

from credit_risk_agent import __version__
from credit_risk_agent.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Credit Risk Investigation Agent", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "environment": settings.environment}

    return app


app = create_app()
