from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.shared.exceptions import not_found, conflict, bad_request
from app.modules.admin.models import (
    Usuario, Rol, Entidad, Dependencia, Canal,
    TipoRequerimiento, PlazoRespuesta, ConfiguracionSistema
)
from app.modules.admin.schemas import (
    UsuarioCreate, UsuarioUpdate, EntidadUpdate, DependenciaCreate,
    DependenciaUpdate, CanalUpdate, TipoRequerimientoCreate,
    TipoRequerimientoUpdate, PlazoRespuestaCreate, PlazoRespuestaUpdate,
    ConfiguracionUpdate
)


# ── Roles ─────────────────────────────────────────────────────────────────
def listar_roles(db: Session):
    return db.query(Rol).all()


# ── Usuarios ──────────────────────────────────────────────────────────────
def listar_usuarios(db: Session):
    return db.query(Usuario).order_by(Usuario.nombre).all()

def crear_usuario(db: Session, data: UsuarioCreate):
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
    db.commit()
    db.refresh(usuario)
    return usuario

def actualizar_usuario(db: Session, usuario_id: int, data: UsuarioUpdate):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        not_found("Usuario")
    if data.email and data.email != usuario.email:
        if db.query(Usuario).filter(Usuario.email == data.email).first():
            conflict("Ya existe un usuario con ese correo electrónico")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(usuario, campo, valor)
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

def actualizar_entidad(db: Session, data: EntidadUpdate) -> Entidad:
    entidad = obtener_entidad(db)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(entidad, campo, valor)
    entidad.configurada = True
    db.commit()
    db.refresh(entidad)
    return entidad


# ── Dependencias ──────────────────────────────────────────────────────────
def listar_dependencias(db: Session, solo_activas: bool = False):
    q = db.query(Dependencia)
    if solo_activas:
        q = q.filter(Dependencia.activa == True)
    return q.order_by(Dependencia.nombre).all()

def crear_dependencia(db: Session, data: DependenciaCreate):
    if db.query(Dependencia).filter(Dependencia.nombre == data.nombre).first():
        conflict("Ya existe una dependencia con ese nombre")
    dep = Dependencia(**data.model_dump())
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep

def actualizar_dependencia(db: Session, dep_id: int, data: DependenciaUpdate):
    dep = db.query(Dependencia).filter(Dependencia.id == dep_id).first()
    if not dep:
        not_found("Dependencia")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(dep, campo, valor)
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

def actualizar_canal(db: Session, canal_id: int, data: CanalUpdate):
    canal = db.query(Canal).filter(Canal.id == canal_id).first()
    if not canal:
        not_found("Canal")
    canal.activo = data.activo
    if data.config_email is not None:
        canal.config_email = data.config_email
    db.commit()
    db.refresh(canal)
    return canal


# ── TipoRequerimiento ─────────────────────────────────────────────────────
def listar_tipos_requerimiento(db: Session):
    return db.query(TipoRequerimiento).order_by(TipoRequerimiento.nombre).all()

def crear_tipo_requerimiento(db: Session, data: TipoRequerimientoCreate):
    tipo = TipoRequerimiento(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo

def actualizar_tipo_requerimiento(db: Session, tipo_id: int, data: TipoRequerimientoUpdate):
    tipo = db.query(TipoRequerimiento).filter(TipoRequerimiento.id == tipo_id).first()
    if not tipo:
        not_found("Tipo de requerimiento")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(tipo, campo, valor)
    db.commit()
    db.refresh(tipo)
    return tipo


# ── PlazoRespuesta ────────────────────────────────────────────────────────
def listar_plazos(db: Session):
    return db.query(PlazoRespuesta).order_by(PlazoRespuesta.dias_habiles).all()

def crear_plazo(db: Session, data: PlazoRespuestaCreate):
    plazo = PlazoRespuesta(**data.model_dump())
    db.add(plazo)
    db.commit()
    db.refresh(plazo)
    return plazo

def actualizar_plazo(db: Session, plazo_id: int, data: PlazoRespuestaUpdate):
    plazo = db.query(PlazoRespuesta).filter(PlazoRespuesta.id == plazo_id).first()
    if not plazo:
        not_found("Plazo de respuesta")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(plazo, campo, valor)
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

def actualizar_configuracion(db: Session, data: ConfiguracionUpdate) -> ConfiguracionSistema:
    config = obtener_configuracion(db)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(config, campo, valor)
    db.commit()
    db.refresh(config)
    return config

def verificar_sistema_listo(db: Session) -> bool:
    """Marca sistema como listo si tiene la configuración mínima completa."""
    entidad = obtener_entidad(db)
    config = obtener_configuracion(db)
    dependencias = listar_dependencias(db, solo_activas=True)
    tipos = db.query(TipoRequerimiento).filter(TipoRequerimiento.activo == True).count()
    plazos = db.query(PlazoRespuesta).filter(PlazoRespuesta.activo == True).count()

    listo = (
        entidad.configurada and
        len(dependencias) >= 1 and
        tipos >= 1 and
        plazos >= 1
    )
    if listo and not config.sistema_listo:
        config.sistema_listo = True
        db.commit()
    return listo
