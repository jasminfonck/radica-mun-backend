import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.shared.exceptions import not_found, conflict, bad_request
from app.modules.admin.models import (
    Usuario, Rol, Entidad, Dependencia, Canal,
    TipoRequerimiento, PlazoRespuesta, ConfiguracionSistema,
    BitacoraAuditoria,
)
from app.modules.admin.schemas import (
    UsuarioCreate, UsuarioUpdate, EntidadUpdate, DependenciaCreate,
    DependenciaUpdate, CanalUpdate, TipoRequerimientoCreate,
    TipoRequerimientoUpdate, PlazoRespuestaCreate, PlazoRespuestaUpdate,
    ConfiguracionUpdate,
)


# ── Bitácora de auditoría ─────────────────────────────────────────────────
def registrar_auditoria(
    db: Session,
    accion: str,
    entidad: str,
    usuario_id: int,
    usuario_nombre: str,
    entidad_id: int = None,
    detalle: dict = None,
):
    """Registra un evento crítico en la bitácora. RN-10 / V-14."""
    registro = BitacoraAuditoria(
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=json.dumps(detalle, ensure_ascii=False, default=str) if detalle else None,
    )
    db.add(registro)
    # No se hace commit aquí; se deja que el flujo del servicio lo gestione.


def listar_auditoria(db: Session, limite: int = 200):
    return (
        db.query(BitacoraAuditoria)
        .order_by(BitacoraAuditoria.created_at.desc())
        .limit(limite)
        .all()
    )


# ── Roles ─────────────────────────────────────────────────────────────────
def listar_roles(db: Session):
    return db.query(Rol).all()


# ── Usuarios ──────────────────────────────────────────────────────────────
def listar_usuarios(db: Session):
    return db.query(Usuario).order_by(Usuario.nombre).all()

def crear_usuario(db: Session, data: UsuarioCreate, actor_id: int, actor_nombre: str):
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        conflict("Ya existe un usuario con ese correo electrónico")
    if not db.query(Rol).filter(Rol.id == data.rol_id).first():
        not_found("Rol")
    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol_id=data.rol_id,
    )
    db.add(usuario)
    db.flush()  # obtener el id antes del commit
    registrar_auditoria(
        db, accion="crear_usuario", entidad="Usuario",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=usuario.id,
        detalle={"email": data.email, "rol_id": data.rol_id},
    )
    db.commit()
    db.refresh(usuario)
    return usuario

def actualizar_usuario(db: Session, usuario_id: int, data: UsuarioUpdate, actor_id: int, actor_nombre: str):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        not_found("Usuario")

    # RN-03 / CA-14: proteger al último administrador activo
    if data.activo is False:
        rol_admin = db.query(Rol).filter(Rol.nombre == "administrador").first()
        if rol_admin and usuario.rol_id == rol_admin.id:
            admins_activos = (
                db.query(Usuario)
                .filter(Usuario.rol_id == rol_admin.id, Usuario.activo == True)
                .count()
            )
            if admins_activos <= 1:
                bad_request(
                    "No se puede inactivar al único administrador activo del sistema"
                )

    if data.email and data.email != usuario.email:
        if db.query(Usuario).filter(Usuario.email == data.email).first():
            conflict("Ya existe un usuario con ese correo electrónico")

    anterior = {"activo": usuario.activo, "rol_id": usuario.rol_id}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(usuario, campo, valor)

    registrar_auditoria(
        db, accion="actualizar_usuario", entidad="Usuario",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=usuario_id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(usuario)
    return usuario


# ── Entidad ───────────────────────────────────────────────────────────────
def obtener_entidad(db: Session) -> Entidad:
    entidad = db.query(Entidad).first()
    if not entidad:
        entidad = Entidad(nombre="Mi Municipio")
        db.add(entidad)
        db.commit()
        db.refresh(entidad)
    return entidad

def actualizar_entidad(db: Session, data: EntidadUpdate, actor_id: int, actor_nombre: str) -> Entidad:
    entidad = obtener_entidad(db)
    anterior = {"nombre": entidad.nombre}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(entidad, campo, valor)
    entidad.configurada = True
    registrar_auditoria(
        db, accion="actualizar_entidad", entidad="Entidad",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=entidad.id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(entidad)
    return entidad


# ── Dependencias ──────────────────────────────────────────────────────────
def listar_dependencias(db: Session, solo_activas: bool = False):
    q = db.query(Dependencia)
    if solo_activas:
        q = q.filter(Dependencia.activa == True)
    return q.order_by(Dependencia.nombre).all()

def crear_dependencia(db: Session, data: DependenciaCreate, actor_id: int, actor_nombre: str):
    if db.query(Dependencia).filter(Dependencia.nombre == data.nombre).first():
        conflict("Ya existe una dependencia con ese nombre")
    dep = Dependencia(**data.model_dump())
    db.add(dep)
    db.flush()
    registrar_auditoria(
        db, accion="crear_dependencia", entidad="Dependencia",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=dep.id,
        detalle={"nombre": data.nombre},
    )
    db.commit()
    db.refresh(dep)
    return dep

def actualizar_dependencia(db: Session, dep_id: int, data: DependenciaUpdate, actor_id: int, actor_nombre: str):
    dep = db.query(Dependencia).filter(Dependencia.id == dep_id).first()
    if not dep:
        not_found("Dependencia")
    anterior = {"activa": dep.activa, "nombre": dep.nombre}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(dep, campo, valor)
    registrar_auditoria(
        db, accion="actualizar_dependencia", entidad="Dependencia",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=dep_id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(dep)
    return dep


# ── Canales ───────────────────────────────────────────────────────────────
def listar_canales(db: Session):
    canales = db.query(Canal).all()
    if not canales:
        canales = _crear_canales_iniciales(db)
    return canales

def _crear_canales_iniciales(db: Session):
    defaults = [
        Canal(nombre="Ventanilla presencial", tipo="presencial"),
        Canal(nombre="Formulario web",        tipo="digital"),
        Canal(nombre="Correo electrónico",    tipo="email"),
    ]
    db.add_all(defaults)
    db.commit()
    return defaults

def actualizar_canal(db: Session, canal_id: int, data: CanalUpdate, actor_id: int, actor_nombre: str):
    canal = db.query(Canal).filter(Canal.id == canal_id).first()
    if not canal:
        not_found("Canal")

    # RN-20 / V-20: canal digital (formulario) requiere acuse de recibo configurado
    if canal.tipo == "digital" and data.activo:
        acuse_final = data.acuse_configurado if data.acuse_configurado is not None else canal.acuse_configurado
        if not acuse_final:
            bad_request(
                "El canal formulario no puede activarse sin configurar el mecanismo "
                "de acuse de recibo automático al ciudadano (RN-20)"
            )

    anterior = {"activo": canal.activo}
    canal.activo = data.activo
    if data.config_email is not None:
        canal.config_email = data.config_email
    if data.acuse_configurado is not None:
        canal.acuse_configurado = data.acuse_configurado

    registrar_auditoria(
        db, accion="actualizar_canal", entidad="Canal",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=canal_id,
        detalle={"anterior": anterior, "nuevo": {"activo": data.activo}},
    )
    db.commit()
    db.refresh(canal)
    return canal


# ── TipoRequerimiento ─────────────────────────────────────────────────────
def listar_tipos_requerimiento(db: Session):
    return db.query(TipoRequerimiento).order_by(TipoRequerimiento.nombre).all()

def crear_tipo_requerimiento(db: Session, data: TipoRequerimientoCreate, actor_id: int, actor_nombre: str):
    tipo = TipoRequerimiento(**data.model_dump())
    db.add(tipo)
    db.flush()
    registrar_auditoria(
        db, accion="crear_tipo_requerimiento", entidad="TipoRequerimiento",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=tipo.id,
        detalle={"nombre": data.nombre},
    )
    db.commit()
    db.refresh(tipo)
    return tipo

def actualizar_tipo_requerimiento(db: Session, tipo_id: int, data: TipoRequerimientoUpdate, actor_id: int, actor_nombre: str):
    tipo = db.query(TipoRequerimiento).filter(TipoRequerimiento.id == tipo_id).first()
    if not tipo:
        not_found("Tipo de requerimiento")
    anterior = {"activo": tipo.activo, "nombre": tipo.nombre}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(tipo, campo, valor)
    registrar_auditoria(
        db, accion="actualizar_tipo_requerimiento", entidad="TipoRequerimiento",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=tipo_id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(tipo)
    return tipo


# ── PlazoRespuesta ────────────────────────────────────────────────────────
def listar_plazos(db: Session):
    return db.query(PlazoRespuesta).order_by(PlazoRespuesta.dias_habiles).all()

def crear_plazo(db: Session, data: PlazoRespuestaCreate, actor_id: int, actor_nombre: str):
    plazo = PlazoRespuesta(**data.model_dump())
    db.add(plazo)
    db.flush()
    registrar_auditoria(
        db, accion="crear_plazo_respuesta", entidad="PlazoRespuesta",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=plazo.id,
        detalle={"nombre": data.nombre, "dias_habiles": data.dias_habiles},
    )
    db.commit()
    db.refresh(plazo)
    return plazo

def actualizar_plazo(db: Session, plazo_id: int, data: PlazoRespuestaUpdate, actor_id: int, actor_nombre: str):
    plazo = db.query(PlazoRespuesta).filter(PlazoRespuesta.id == plazo_id).first()
    if not plazo:
        not_found("Plazo de respuesta")
    anterior = {"activo": plazo.activo, "dias_habiles": plazo.dias_habiles}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(plazo, campo, valor)
    registrar_auditoria(
        db, accion="actualizar_plazo_respuesta", entidad="PlazoRespuesta",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=plazo_id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(plazo)
    return plazo


# ── Configuracion Sistema ─────────────────────────────────────────────────
def obtener_configuracion(db: Session) -> ConfiguracionSistema:
    config = db.query(ConfiguracionSistema).first()
    if not config:
        config = ConfiguracionSistema()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def actualizar_configuracion(db: Session, data: ConfiguracionUpdate, actor_id: int, actor_nombre: str) -> ConfiguracionSistema:
    config = obtener_configuracion(db)
    anterior = {
        "prefijo_radicado": config.prefijo_radicado,
        "politica_privacidad_activa": config.politica_privacidad_activa,
    }
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(config, campo, valor)
    registrar_auditoria(
        db, accion="actualizar_configuracion", entidad="ConfiguracionSistema",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        entidad_id=config.id,
        detalle={"anterior": anterior, "nuevo": data.model_dump(exclude_none=True)},
    )
    db.commit()
    db.refresh(config)
    return config

def verificar_sistema_listo(db: Session) -> bool:
    """Marca sistema como listo si tiene la configuración mínima completa. RN-02 / V-08."""
    entidad = obtener_entidad(db)
    config = obtener_configuracion(db)
    dependencias_activas = listar_dependencias(db, solo_activas=True)
    tipos = db.query(TipoRequerimiento).filter(TipoRequerimiento.activo == True).count()
    plazos = db.query(PlazoRespuesta).filter(PlazoRespuesta.activo == True).count()
    canales_activos = db.query(Canal).filter(Canal.activo == True).count()  # V-08

    listo = (
        entidad.configurada
        and len(dependencias_activas) >= 1
        and tipos >= 1
        and plazos >= 1
        and canales_activos >= 1          # V-08: al menos un canal habilitado
        and config.politica_privacidad_activa  # RN-19: política de privacidad activa
    )
    if listo and not config.sistema_listo:
        config.sistema_listo = True
        db.commit()
    elif not listo and config.sistema_listo:
        config.sistema_listo = False
        db.commit()
    return listo


# ── Respaldo ──────────────────────────────────────────────────────────────
def generar_respaldo(db: Session) -> dict:
    """Genera una exportación básica de la configuración del sistema. RN-13 / V-16."""
    entidad = db.query(Entidad).first()
    config = db.query(ConfiguracionSistema).first()
    dependencias = db.query(Dependencia).all()
    canales = db.query(Canal).all()
    tipos = db.query(TipoRequerimiento).all()
    plazos = db.query(PlazoRespuesta).all()
    total_usuarios = db.query(Usuario).count()

    def _row(obj, campos):
        return {c: getattr(obj, c, None) for c in campos}

    return {
        "generado_en": datetime.utcnow(),
        "entidad": _row(entidad, ["nombre", "nit", "municipio", "departamento", "direccion", "telefono", "email_institucional"]) if entidad else None,
        "configuracion": _row(config, ["prefijo_radicado", "anio_radicado", "secuencia_actual", "ruta_almacenamiento", "color_primario", "politica_privacidad_activa"]) if config else None,
        "dependencias": [_row(d, ["nombre", "codigo", "responsable", "email", "activa"]) for d in dependencias],
        "canales": [_row(c, ["nombre", "tipo", "activo", "acuse_configurado"]) for c in canales],
        "tipos_requerimiento": [_row(t, ["nombre", "descripcion", "activo"]) for t in tipos],
        "plazos_respuesta": [_row(p, ["nombre", "dias_habiles", "activo"]) for p in plazos],
        "total_usuarios": total_usuarios,
    }
