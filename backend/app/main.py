from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, SessionLocal
from .seed import seed
from .core.config import get_settings
from .routers import auth, users, audit, ai, marketplaces, dashboard, products, suppliers, integrations, imports

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_security()
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
    if settings.seed_demo_data:
        with SessionLocal() as session:
            seed(session)
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DropJoy API: SaaS multi-tenant para radar, fornecedores, IA de anúncios e marketplaces.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for router in (auth.router, users.router, audit.router, ai.router, marketplaces.router, dashboard.router, products.router, suppliers.router, integrations.router, imports.router):
    app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version, "environment": settings.environment, "time": datetime.now(timezone.utc).isoformat()}
