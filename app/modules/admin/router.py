from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
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
    BitacoraOut, RespaldoOut,
    BuzonCorreoCreate, BuzonCorreoUpdate, BuzonCorreoOut, TestConexionResult,
    OAuthIniciarOut, OAuthCompletarIn,
)

router = APIRouter(prefix="/admin", tags=["Administración"])


# ── Roles ─────────────────────────────────────────────────────────────────
@router.get("/roles", response_model=List[RolOut])
def listar_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.listar_roles(db)


# ── Usuarios ──────────────────────────────────────────────────────────────
@router.get("/usuarios", response_model=List[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.listar_usuarios(db)

@router.post("/usuarios", response_model=UsuarioOut)
def crear_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.crear_usuario(db, data, current_user.id, current_user.nombre)

@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_usuario(db, usuario_id, data, current_user.id, current_user.nombre)


# ── Entidad ───────────────────────────────────────────────────────────────
@router.get("/entidad", response_model=EntidadOut)
def obtener_entidad(
    db: Session = Depends(get_db),
):
    return service.obtener_entidad(db)

@router.put("/entidad", response_model=EntidadOut)
def actualizar_entidad(
    data: EntidadUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_entidad(db, data, current_user.id, current_user.nombre)


# ── Dependencias ──────────────────────────────────────────────────────────
@router.get("/dependencias", response_model=List[DependenciaOut])
def listar_dependencias(
    solo_activas: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_dependencias(db, solo_activas)

@router.post("/dependencias", response_model=DependenciaOut)
def crear_dependencia(
    data: DependenciaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.crear_dependencia(db, data, current_user.id, current_user.nombre)

@router.put("/dependencias/{dep_id}", response_model=DependenciaOut)
def actualizar_dependencia(
    dep_id: int,
    data: DependenciaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_dependencia(db, dep_id, data, current_user.id, current_user.nombre)


# ── Canales ───────────────────────────────────────────────────────────────
@router.get("/canales", response_model=List[CanalOut])
def listar_canales(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_canales(db)

@router.put("/canales/{canal_id}", response_model=CanalOut)
def actualizar_canal(
    canal_id: int,
    data: CanalUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_canal(db, canal_id, data, current_user.id, current_user.nombre)


# ── Tipos de requerimiento ────────────────────────────────────────────────
@router.get("/tipos-requerimiento", response_model=List[TipoRequerimientoOut])
def listar_tipos(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_tipos_requerimiento(db)

@router.post("/tipos-requerimiento", response_model=TipoRequerimientoOut)
def crear_tipo(
    data: TipoRequerimientoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.crear_tipo_requerimiento(db, data, current_user.id, current_user.nombre)

@router.put("/tipos-requerimiento/{tipo_id}", response_model=TipoRequerimientoOut)
def actualizar_tipo(
    tipo_id: int,
    data: TipoRequerimientoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_tipo_requerimiento(db, tipo_id, data, current_user.id, current_user.nombre)


# ── Plazos de respuesta ───────────────────────────────────────────────────
@router.get("/plazos", response_model=List[PlazoRespuestaOut])
def listar_plazos(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_plazos(db)

@router.post("/plazos", response_model=PlazoRespuestaOut)
def crear_plazo(
    data: PlazoRespuestaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.crear_plazo(db, data, current_user.id, current_user.nombre)

@router.put("/plazos/{plazo_id}", response_model=PlazoRespuestaOut)
def actualizar_plazo(
    plazo_id: int,
    data: PlazoRespuestaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_plazo(db, plazo_id, data, current_user.id, current_user.nombre)


# ── Configuración del sistema ─────────────────────────────────────────────
@router.get("/configuracion", response_model=ConfiguracionOut)
def obtener_configuracion(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_configuracion(db)

@router.put("/configuracion", response_model=ConfiguracionOut)
def actualizar_configuracion(
    data: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_configuracion(db, data, current_user.id, current_user.nombre)

@router.get("/sistema/estado")
def estado_sistema(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    listo = service.verificar_sistema_listo(db)
    return {"sistema_listo": listo}


# ── Bitácora de auditoría ─────────────────────────────────────────────────
@router.get("/auditoria", response_model=List[BitacoraOut])
def listar_auditoria(
    limite: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.listar_auditoria(db, limite)


# ── Respaldo ──────────────────────────────────────────────────────────────
@router.get("/respaldo", response_model=RespaldoOut)
def generar_respaldo(
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.generar_respaldo(db)


# ── Buzón de correo oficial ───────────────────────────────────────────────

# IMPORTANTE: este endpoint es público (sin JWT). Microsoft/Google redirige aquí
# con code+state tras la autorización. Debe declararse ANTES de las rutas /{id}/...
# para que FastAPI no interprete "oauth" como un buzon_id.
@router.get("/buzon-correo/oauth/callback", include_in_schema=False)
def oauth_callback_backend(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Endpoint de redirección OAuth2. Microsoft/Google redirige el navegador aquí
    tras la autorización. No requiere JWT.
    """
    def _page(titulo: str, mensaje: str, ok: bool = True) -> HTMLResponse:
        icono = "✅" if ok else "❌"
        cierre = "<script>setTimeout(()=>window.close(),4000)</script>" if ok else ""
        return HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{titulo}</title>
<style>body{{font-family:sans-serif;max-width:560px;margin:3em auto;padding:1em}}
h2{{color:{'#2e7d32' if ok else '#c62828'}}}</style></head>
<body><h2>{icono} {titulo}</h2><p>{mensaje}</p>
<p style="color:#666;font-size:.9em">{'Esta ventana se cerrará automáticamente en 4 segundos.' if ok else 'Puede cerrar esta ventana.'}</p>
{cierre}</body></html>""",
            status_code=200 if ok else 400,
        )

    if error:
        return _page("Error de autorización", f"<strong>{error}</strong><br>{error_description or ''}", ok=False)
    if not code or not state:
        return _page("Parámetros inválidos", "No se recibieron <em>code</em> ni <em>state</em>.", ok=False)

    try:
        result = service.completar_oauth_buzon(db, OAuthCompletarIn(code=code, state=state))
        return _page("Autorización exitosa", result["mensaje"])
    except HTTPException as exc:
        return _page("Error al procesar la autorización", exc.detail, ok=False)
    except Exception as exc:
        return _page("Error inesperado", str(exc), ok=False)


@router.get("/buzon-correo", response_model=BuzonCorreoOut | None)
def obtener_buzon(
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.obtener_buzon(db)

@router.post("/buzon-correo", response_model=BuzonCorreoOut)
def crear_buzon(
    data: BuzonCorreoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.crear_buzon_correo(db, data, current_user.id, current_user.nombre)

@router.put("/buzon-correo/{buzon_id}", response_model=BuzonCorreoOut)
def actualizar_buzon(
    buzon_id: int,
    data: BuzonCorreoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.actualizar_buzon_correo(db, buzon_id, data, current_user.id, current_user.nombre)

@router.post("/buzon-correo/{buzon_id}/probar", response_model=TestConexionResult)
def probar_buzon(
    buzon_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.probar_conexion_buzon(db, buzon_id)

@router.post("/buzon-correo/{buzon_id}/activar", response_model=BuzonCorreoOut)
def activar_buzon(
    buzon_id: int,
    activo: bool,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    return service.activar_buzon(db, buzon_id, activo, current_user.id, current_user.nombre)


@router.post("/buzon-correo/{buzon_id}/oauth/iniciar", response_model=OAuthIniciarOut)
def iniciar_oauth(
    buzon_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    """Genera la URL de autorización OAuth2. El admin la abre en el navegador."""
    return service.iniciar_oauth_buzon(db, buzon_id)


@router.post("/buzon-correo/oauth/completar", response_model=TestConexionResult)
def completar_oauth(
    data: OAuthCompletarIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_rol("administrador")),
):
    """
    Recibe el code y state que el frontend extrajo del callback de Microsoft/Google.
    Intercambia el code por tokens y los almacena cifrados.
    """
    return service.completar_oauth_buzon(db, data)
