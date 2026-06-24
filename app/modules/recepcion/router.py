from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user, require_rol
from app.modules.admin.models import Usuario
from app.modules.recepcion import service
from app.modules.recepcion.schemas import (
    RecepcionCreate, RecepcionUpdate, RecepcionOut, AdjuntoOut,
    FormularioPublicoCreate, FormularioPublicoOut, InfoPublicaOut,
)
from app.modules.consulta.models import BitacoraOperativa
from app.modules.consulta.schemas import LogAuditoriaOut

router = APIRouter(prefix="/recepcion", tags=["Recepción"])


@router.get("", response_model=List[RecepcionOut])
def listar(
    canal_id:    Optional[int] = Query(None),
    estado:      Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_recepciones(db, canal_id, estado, fecha_desde, fecha_hasta)


# Rutas estáticas /publica/* deben ir ANTES de /{recepcion_id}
@router.get("/publica/info", response_model=InfoPublicaOut)
def info_publica(db: Session = Depends(get_db)):
    return service.get_info_publica(db)


@router.get("/{recepcion_id}/bitacora", response_model=List[LogAuditoriaOut])
def bitacora_recepcion(
    recepcion_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return (
        db.query(BitacoraOperativa)
        .filter(BitacoraOperativa.modulo == "recepciones", BitacoraOperativa.modulo_id == recepcion_id)
        .order_by(BitacoraOperativa.created_at.desc())
        .all()
    )


@router.get("/{recepcion_id}", response_model=RecepcionOut)
def obtener(recepcion_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.obtener_recepcion(db, recepcion_id)


@router.post("", response_model=RecepcionOut)
def crear(
    data: RecepcionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ip = request.client.host if request.client else None
    return service.crear_recepcion(db, data, current_user.id, ip)


# Endpoint público para formulario web (ciudadano sin autenticación)
# Usa multipart/form-data para soportar adjuntos opcionales
@router.post("/publica", response_model=FormularioPublicoOut)
async def crear_publica(
    request: Request,
    tipo_persona:          str           = Form("natural"),
    nombres:               Optional[str] = Form(None),
    apellidos:             Optional[str] = Form(None),
    razon_social:          Optional[str] = Form(None),
    tipo_identificacion:   Optional[str] = Form(None),
    numero_identificacion: Optional[str] = Form(None),
    email:                 Optional[str] = Form(None),
    telefono:              Optional[str] = Form(None),
    asunto:                str           = Form(...),
    tipo_requerimiento_id: Optional[int] = Form(None),
    observaciones:         Optional[str] = Form(None),
    acepta_politica:       bool          = Form(False),
    adjuntos: List[UploadFile]           = File(default=[]),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    service.check_rate_limit(ip or "unknown")
    data = FormularioPublicoCreate(
        tipo_persona=tipo_persona,
        nombres=nombres,
        apellidos=apellidos,
        razon_social=razon_social,
        tipo_identificacion=tipo_identificacion,
        numero_identificacion=numero_identificacion,
        email=email,
        telefono=telefono,
        asunto=asunto,
        tipo_requerimiento_id=tipo_requerimiento_id,
        observaciones=observaciones,
        acepta_politica=acepta_politica,
    )
    return await service.crear_desde_formulario(db, data, ip, adjuntos)


@router.put("/{recepcion_id}", response_model=RecepcionOut)
def actualizar(
    recepcion_id: int,
    data: RecepcionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ip = request.client.host if request.client else None
    return service.actualizar_recepcion(db, recepcion_id, data, current_user.id, ip)


@router.get("/{recepcion_id}/adjuntos/{adjunto_id}")
def descargar_adjunto(
    recepcion_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.descargar_adjunto(db, adjunto_id)


@router.post("/{recepcion_id}/adjuntos", response_model=AdjuntoOut)
async def subir_adjunto(
    recepcion_id: int,
    archivo: UploadFile = File(...),
    fase_creacion: bool = Query(False, description="Solo True durante la creación inicial"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return await service.guardar_adjunto(db, recepcion_id, archivo, fase_creacion)


@router.post("/{recepcion_id}/notificar-adjuntos")
def notificar_adjuntos(
    recepcion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ip = request.client.host if request.client else None
    enviado = service.notificar_adjuntos(db, recepcion_id, current_user.id, ip)
    return {"enviado": enviado}


@router.delete("/{recepcion_id}/adjuntos/{adjunto_id}", status_code=405)
def eliminar_adjunto(
    recepcion_id: int,
    adjunto_id: int,
):
    from fastapi import HTTPException
    raise HTTPException(
        status_code=405,
        detail="La eliminación de adjuntos no está permitida. "
               "Los documentos son parte del registro oficial de la recepción.",
    )
