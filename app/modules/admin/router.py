from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.dependencies import get_db, get_current_user, require_rol
from app.modules.admin import service
from app.modules.admin.schemas import (
    RolOut, UsuarioCreate, UsuarioUpdate, UsuarioOut,
    EntidadUpdate, EntidadOut,
    DependenciaCreate, DependenciaUpdate, DependenciaOut,
    CanalUpdate, CanalOut,
    TipoRequerimientoCreate, TipoRequerimientoUpdate, TipoRequerimientoOut,
    PlazoRespuestaCreate, PlazoRespuestaUpdate, PlazoRespuestaOut,
    ConfiguracionUpdate, ConfiguracionOut,
)

router = APIRouter(prefix="/admin", tags=["Administración"])
solo_admin = Depends(require_rol("administrador"))


# ── Roles ─────────────────────────────────────────────────────────────────
@router.get("/roles", response_model=List[RolOut], dependencies=[solo_admin])
def listar_roles(db: Session = Depends(get_db)):
    return service.listar_roles(db)


# ── Usuarios ──────────────────────────────────────────────────────────────
@router.get("/usuarios", response_model=List[UsuarioOut], dependencies=[solo_admin])
def listar_usuarios(db: Session = Depends(get_db)):
    return service.listar_usuarios(db)

@router.post("/usuarios", response_model=UsuarioOut, dependencies=[solo_admin])
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    return service.crear_usuario(db, data)

@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut, dependencies=[solo_admin])
def actualizar_usuario(usuario_id: int, data: UsuarioUpdate, db: Session = Depends(get_db)):
    return service.actualizar_usuario(db, usuario_id, data)


# ── Entidad ───────────────────────────────────────────────────────────────
@router.get("/entidad", response_model=EntidadOut)
def obtener_entidad(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.obtener_entidad(db)

@router.put("/entidad", response_model=EntidadOut, dependencies=[solo_admin])
def actualizar_entidad(data: EntidadUpdate, db: Session = Depends(get_db)):
    return service.actualizar_entidad(db, data)


# ── Dependencias ──────────────────────────────────────────────────────────
@router.get("/dependencias", response_model=List[DependenciaOut])
def listar_dependencias(
    solo_activas: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    return service.listar_dependencias(db, solo_activas)

@router.post("/dependencias", response_model=DependenciaOut, dependencies=[solo_admin])
def crear_dependencia(data: DependenciaCreate, db: Session = Depends(get_db)):
    return service.crear_dependencia(db, data)

@router.put("/dependencias/{dep_id}", response_model=DependenciaOut, dependencies=[solo_admin])
def actualizar_dependencia(dep_id: int, data: DependenciaUpdate, db: Session = Depends(get_db)):
    return service.actualizar_dependencia(db, dep_id, data)


# ── Canales ───────────────────────────────────────────────────────────────
@router.get("/canales", response_model=List[CanalOut])
def listar_canales(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.listar_canales(db)

@router.put("/canales/{canal_id}", response_model=CanalOut, dependencies=[solo_admin])
def actualizar_canal(canal_id: int, data: CanalUpdate, db: Session = Depends(get_db)):
    return service.actualizar_canal(db, canal_id, data)


# ── Tipos de requerimiento ────────────────────────────────────────────────
@router.get("/tipos-requerimiento", response_model=List[TipoRequerimientoOut])
def listar_tipos(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.listar_tipos_requerimiento(db)

@router.post("/tipos-requerimiento", response_model=TipoRequerimientoOut, dependencies=[solo_admin])
def crear_tipo(data: TipoRequerimientoCreate, db: Session = Depends(get_db)):
    return service.crear_tipo_requerimiento(db, data)

@router.put("/tipos-requerimiento/{tipo_id}", response_model=TipoRequerimientoOut, dependencies=[solo_admin])
def actualizar_tipo(tipo_id: int, data: TipoRequerimientoUpdate, db: Session = Depends(get_db)):
    return service.actualizar_tipo_requerimiento(db, tipo_id, data)


# ── Plazos de respuesta ───────────────────────────────────────────────────
@router.get("/plazos", response_model=List[PlazoRespuestaOut])
def listar_plazos(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.listar_plazos(db)

@router.post("/plazos", response_model=PlazoRespuestaOut, dependencies=[solo_admin])
def crear_plazo(data: PlazoRespuestaCreate, db: Session = Depends(get_db)):
    return service.crear_plazo(db, data)

@router.put("/plazos/{plazo_id}", response_model=PlazoRespuestaOut, dependencies=[solo_admin])
def actualizar_plazo(plazo_id: int, data: PlazoRespuestaUpdate, db: Session = Depends(get_db)):
    return service.actualizar_plazo(db, plazo_id, data)


# ── Configuración del sistema ─────────────────────────────────────────────
@router.get("/configuracion", response_model=ConfiguracionOut)
def obtener_configuracion(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.obtener_configuracion(db)

@router.put("/configuracion", response_model=ConfiguracionOut, dependencies=[solo_admin])
def actualizar_configuracion(data: ConfiguracionUpdate, db: Session = Depends(get_db)):
    return service.actualizar_configuracion(db, data)

@router.get("/sistema/estado")
def estado_sistema(db: Session = Depends(get_db), _=Depends(get_current_user)):
    listo = service.verificar_sistema_listo(db)
    return {"sistema_listo": listo}
