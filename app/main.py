from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.admin.router import router as admin_router
from app.modules.recepcion.router import router as recepcion_router
from app.modules.remitente.router import router as remitente_router
from app.modules.radicado.router import router as radicado_router
from app.modules.consulta.router import router as consulta_router
from app.modules.setup.router import router as setup_router
from app.modules.geo.router import router as geo_router

app = FastAPI(
    title="Radica Mun",
    description="Sistema de radicación de comunicaciones para municipios de categoría 5ta y 6ta",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(recepcion_router)
app.include_router(remitente_router)
app.include_router(radicado_router)
app.include_router(consulta_router)
app.include_router(setup_router)
app.include_router(geo_router)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "sistema": "Radica Mun"}
