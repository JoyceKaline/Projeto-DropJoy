from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, SessionLocal
from .seed import seed
from .core.config import get_settings
from .routers import dashboard, products, suppliers, integrations

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API DropJoy V4: catálogo multi-fornecedor, score, histórico, tenants e conectores.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(dashboard.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(integrations.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version, "time": datetime.now(timezone.utc).isoformat()}
