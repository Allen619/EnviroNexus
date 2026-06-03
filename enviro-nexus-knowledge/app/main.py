from fastapi import FastAPI

from app.api.routes.factor_query import router as factor_query_router
from app.api.routes.health import router as health_router
from app.api.routes.method_cards import router as method_cards_router
from app.settings import get_settings


settings = get_settings()

app = FastAPI(
    title="EnviroNexus Knowledge",
    version=settings.api_version,
)

app.include_router(health_router, prefix=f"/api/{settings.api_version}")
app.include_router(factor_query_router, prefix=f"/api/{settings.api_version}")
app.include_router(method_cards_router, prefix=f"/api/{settings.api_version}")
