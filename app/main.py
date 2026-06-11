import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.auth.router import router as auth_router
from app.modules.admin.router import router as admin_router
from app.modules.recepcion.router import router as recepcion_router
from app.modules.remitente.router import router as remitente_router
from app.modules.radicado.router import router as radicado_router
from app.modules.consulta.router import router as consulta_router
from app.modules.setup.router import router as setup_router
from app.modules.geo.router import router as geo_router

logger = logging.getLogger(__name__)


async def _polling_loop() -> None:
    """
    Tarea de fondo que revisa los buzones activos según su intervalo configurado.
    Se ejecuta cada 60 segundos y determina qué buzones deben ejecutarse.
    """
    # Espera inicial para que la app termine de arrancar
    await asyncio.sleep(10)

    while True:
        try:
            db = SessionLocal()
            try:
                from app.modules.admin.models import BuzonCorreo
                from app.modules.recepcion.email_poller import procesar_buzon

                buzones = db.query(BuzonCorreo).filter(BuzonCorreo.activo == True).all()
                ahora = datetime.now(timezone.utc)

                for buzon in buzones:
                    if buzon.ultimo_polling is None:
                        debe_ejecutar = True
                    else:
                        ultimo = buzon.ultimo_polling
                        if ultimo.tzinfo is None:
                            ultimo = ultimo.replace(tzinfo=timezone.utc)
                        segundos_transcurridos = (ahora - ultimo).total_seconds()
                        debe_ejecutar = segundos_transcurridos >= (buzon.intervalo_minutos * 60)

                    if debe_ejecutar:
                        try:
                            stats = procesar_buzon(buzon, db)
                            buzon.estado_conexion = "ok"
                            buzon.ultimo_error = None
                            logger.info(
                                "Buzón %s procesado: %d correos, %d spam, %d errores",
                                buzon.correo, stats["procesados"], stats["ignorados_spam"], stats["errores"],
                            )
                        except Exception as e:
                            buzon.estado_conexion = "error"
                            buzon.ultimo_error = str(e)[:500]
                            logger.error("Error procesando buzón %s: %s", buzon.correo, e)

                        buzon.ultimo_polling = ahora
                        db.commit()

            finally:
                db.close()

        except Exception as e:
            logger.error("Error en polling loop: %s", e)

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_polling_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Radica Mun",
    description="Sistema de radicación de comunicaciones para municipios de categoría 5ta y 6ta",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
