import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.core.crypto import encrypt, decrypt
from app.shared.exceptions import not_found, conflict, bad_request
from app.modules.admin.models import (
    Usuario, Rol, Entidad, Dependencia, Canal,
    TipoRequerimiento, PlazoRespuesta, ConfiguracionSistema,
    BitacoraAuditoria, BuzonCorreo,
)
from app.modules.admin.schemas import (
    UsuarioCreate, UsuarioUpdate, EntidadUpdate, DependenciaCreate,
    DependenciaUpdate, CanalUpdate, TipoRequerimientoCreate,
    TipoRequerimientoUpdate, PlazoRespuestaCreate, PlazoRespuestaUpdate,
    ConfiguracionUpdate, BuzonCorreoCreate, BuzonCorreoUpdate, OAuthCompletarIn,
)

_IMAP_SERVERS = {
    ("gmail",   "personal"):    ("imap.gmail.com",         993),
    ("gmail",   "empresarial"): ("imap.gmail.com",         993),
    # Microsoft unificó IMAP en outlook.office365.com para autenticación moderna
    # (OAuth2 y contraseñas de aplicación). imap-mail.outlook.com es solo legacy.
    ("outlook", "personal"):    ("outlook.office365.com",  993),
    ("outlook", "empresarial"): ("outlook.office365.com",  993),
}

_OAUTH_AUTH_URLS = {
    ("outlook", "personal"):    "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize",
    ("outlook", "empresarial"): "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
    ("gmail",   "personal"):    "https://accounts.google.com/o/oauth2/v2/auth",
    ("gmail",   "empresarial"): "https://accounts.google.com/o/oauth2/v2/auth",
}

_OAUTH_SCOPES = {
    ("outlook", "imap"):  "https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
    ("outlook", "graph"): "Mail.Read offline_access",
    "gmail":              "https://mail.google.com/",
}


def _resolver_servidor(proveedor: str, tipo_cuenta: str) -> tuple[str, int]:
    key = (proveedor, tipo_cuenta)
    entry = _IMAP_SERVERS.get(key)
    if not entry:
        bad_request(f"Combinación proveedor/tipo_cuenta no soportada: {proveedor}/{tipo_cuenta}")
    return entry


# ── Bitácora de auditoría ─────────────────────────────────────────────────
def registrar_auditoria(
    db: Session,
    accion: str,
    modulo: str,
    usuario_id: int,
    usuario_nombre: str,
    modulo_id: int = None,
    detalle: dict = None,
):
    """Registra un evento crítico en la bitácora admin. RN-10 / V-14."""
    registro = BitacoraAuditoria(
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=accion,
        modulo=modulo,
        modulo_id=modulo_id,
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
        apellido=data.apellido,
        email=data.email,
        password_hash=hash_password(data.password),
        rol_id=data.rol_id,
    )
    db.add(usuario)
    db.flush()  # obtener el id antes del commit
    registrar_auditoria(
        db, accion="crear_usuario", modulo="Usuario",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=usuario.id,
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
        db, accion="actualizar_usuario", modulo="Usuario",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=usuario_id,
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
        db, accion="actualizar_entidad", modulo="Entidad",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=entidad.id,
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
    if data.codigo and db.query(Dependencia).filter(Dependencia.codigo == data.codigo).first():
        conflict("Ya existe una dependencia con ese código")
    dep = Dependencia(**data.model_dump())
    db.add(dep)
    db.flush()
    registrar_auditoria(
        db, accion="crear_dependencia", modulo="Dependencia",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=dep.id,
        detalle={"nombre": data.nombre},
    )
    db.commit()
    db.refresh(dep)
    return dep

def actualizar_dependencia(db: Session, dep_id: int, data: DependenciaUpdate, actor_id: int, actor_nombre: str):
    dep = db.query(Dependencia).filter(Dependencia.id == dep_id).first()
    if not dep:
        not_found("Dependencia")
    if data.codigo and data.codigo != dep.codigo:
        if db.query(Dependencia).filter(Dependencia.codigo == data.codigo, Dependencia.id != dep_id).first():
            conflict("Ya existe una dependencia con ese código")
    anterior = {"activa": dep.activa, "nombre": dep.nombre}
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(dep, campo, valor)
    registrar_auditoria(
        db, accion="actualizar_dependencia", modulo="Dependencia",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=dep_id,
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

    # Canal email: sincronizar buzón en cascada
    if canal.tipo == "email":
        buzon = db.query(BuzonCorreo).filter(BuzonCorreo.canal_id == canal_id).first()
        if data.activo:
            if not buzon:
                bad_request("Configure el buzón de correo antes de activar este canal.")
            if buzon.estado_conexion != "ok":
                bad_request("Pruebe la conexión del buzón antes de activar el canal.")
            if not buzon.oauth_autorizado:
                bad_request("Autorice el acceso OAuth2 del buzón antes de activar el canal.")
            buzon.activo = True
        else:
            if buzon:
                buzon.activo = False

    anterior = {"activo": canal.activo}
    canal.activo = data.activo
    if data.config_email is not None:
        canal.config_email = data.config_email
    if data.acuse_configurado is not None:
        canal.acuse_configurado = data.acuse_configurado

    registrar_auditoria(
        db, accion="actualizar_canal", modulo="Canal",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=canal_id,
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
        db, accion="crear_tipo_requerimiento", modulo="TipoRequerimiento",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=tipo.id,
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
        db, accion="actualizar_tipo_requerimiento", modulo="TipoRequerimiento",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=tipo_id,
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
        db, accion="crear_plazo_respuesta", modulo="PlazoRespuesta",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=plazo.id,
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
        db, accion="actualizar_plazo_respuesta", modulo="PlazoRespuesta",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=plazo_id,
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
        db, accion="actualizar_configuracion", modulo="ConfiguracionSistema",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=config.id,
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


# ── BuzonCorreo ───────────────────────────────────────────────────────────
def obtener_buzon(db: Session) -> Optional[BuzonCorreo]:
    return db.query(BuzonCorreo).first()

def crear_buzon_correo(db: Session, data: BuzonCorreoCreate, actor_id: int, actor_nombre: str) -> BuzonCorreo:
    if db.query(BuzonCorreo).filter(BuzonCorreo.canal_id == data.canal_id).first():
        conflict("Ya existe un buzón configurado para ese canal")

    canal = db.query(Canal).filter(Canal.id == data.canal_id, Canal.tipo == "email").first()
    if not canal:
        not_found("Canal de tipo email")

    servidor, puerto = _resolver_servidor(data.proveedor, data.tipo_cuenta)

    buzon = BuzonCorreo(
        canal_id=data.canal_id,
        proveedor=data.proveedor,
        tipo_cuenta=data.tipo_cuenta,
        metodo_conexion=data.metodo_conexion,
        auth_type="oauth2",
        correo=str(data.correo),
        servidor_imap=servidor,
        puerto=puerto,
        intervalo_minutos=data.intervalo_minutos,
        oauth_client_id=data.oauth_client_id,
        oauth_client_secret_enc=encrypt(data.oauth_client_secret),
        oauth_tenant_id=data.oauth_tenant_id,
    )

    db.add(buzon)
    db.flush()
    registrar_auditoria(
        db, accion="crear_buzon_correo", modulo="BuzonCorreo",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=buzon.id,
        detalle={"correo": str(data.correo), "proveedor": data.proveedor, "tipo_cuenta": data.tipo_cuenta},
    )
    db.commit()
    db.refresh(buzon)
    return buzon


def actualizar_buzon_correo(db: Session, buzon_id: int, data: BuzonCorreoUpdate, actor_id: int, actor_nombre: str) -> BuzonCorreo:
    buzon = db.query(BuzonCorreo).filter(BuzonCorreo.id == buzon_id).first()
    if not buzon:
        not_found("Buzón de correo")

    if data.proveedor:
        buzon.proveedor = data.proveedor
    if data.tipo_cuenta:
        buzon.tipo_cuenta = data.tipo_cuenta

    servidor_correcto, puerto_correcto = _resolver_servidor(buzon.proveedor, buzon.tipo_cuenta)
    if servidor_correcto != buzon.servidor_imap or puerto_correcto != buzon.puerto:
        buzon.servidor_imap = servidor_correcto
        buzon.puerto = puerto_correcto
        buzon.estado_conexion = "sin_probar"

    if data.metodo_conexion is not None and data.metodo_conexion != buzon.metodo_conexion:
        buzon.metodo_conexion = data.metodo_conexion
        buzon.oauth_access_token_enc = None
        buzon.oauth_refresh_token_enc = None
        buzon.oauth_token_expiry = None
        buzon.oauth_state = None
        buzon.estado_conexion = "sin_probar"
    if data.correo is not None:
        buzon.correo = data.correo
        buzon.estado_conexion = "sin_probar"
    if data.oauth_client_id is not None:
        buzon.oauth_client_id = data.oauth_client_id
        buzon.estado_conexion = "sin_probar"
    if data.oauth_client_secret:
        buzon.oauth_client_secret_enc = encrypt(data.oauth_client_secret)
        buzon.oauth_access_token_enc = None
        buzon.oauth_refresh_token_enc = None
        buzon.oauth_token_expiry = None
        buzon.oauth_state = None
        buzon.estado_conexion = "sin_probar"
    if data.oauth_tenant_id is not None:
        buzon.oauth_tenant_id = data.oauth_tenant_id
    if data.intervalo_minutos is not None:
        buzon.intervalo_minutos = data.intervalo_minutos

    registrar_auditoria(
        db, accion="actualizar_buzon_correo", modulo="BuzonCorreo",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=buzon_id,
        detalle={"actualizado": data.model_dump(exclude_none=True, exclude={"oauth_client_secret"})},
    )
    db.commit()
    db.refresh(buzon)
    return buzon

def activar_buzon(db: Session, buzon_id: int, activo: bool, actor_id: int, actor_nombre: str) -> BuzonCorreo:
    buzon = db.query(BuzonCorreo).filter(BuzonCorreo.id == buzon_id).first()
    if not buzon:
        not_found("Buzón de correo")

    if activo and buzon.estado_conexion == "sin_probar":
        bad_request("Debe probar la conexión antes de activar el buzón")
    if activo and buzon.estado_conexion == "error":
        bad_request("No se puede activar el buzón con error de conexión. Pruebe la conexión primero.")

    buzon.activo = activo
    registrar_auditoria(
        db,
        accion="activar_buzon_correo" if activo else "desactivar_buzon_correo",
        modulo="BuzonCorreo",
        usuario_id=actor_id, usuario_nombre=actor_nombre,
        modulo_id=buzon_id,
        detalle={"activo": activo},
    )
    db.commit()
    db.refresh(buzon)
    return buzon

def probar_conexion_buzon(db: Session, buzon_id: int) -> dict:
    from app.modules.recepcion.email_poller import (
        probar_conexion_graph,
        probar_conexion_imap_oauth,
        refrescar_token_si_necesario,
    )

    buzon = db.query(BuzonCorreo).filter(BuzonCorreo.id == buzon_id).first()
    if not buzon:
        not_found("Buzón de correo")

    try:
        if not buzon.oauth_refresh_token_enc and not buzon.oauth_access_token_enc:
            bad_request(
                "El buzón no ha sido autorizado. "
                "Use el botón 'Autorizar OAuth2' para completar la autorización."
            )
        access_token = refrescar_token_si_necesario(buzon, db)
        metodo = getattr(buzon, "metodo_conexion", "imap")
        if metodo == "graph":
            probar_conexion_graph(access_token)
            mensaje = "Conexión exitosa a Microsoft Graph API"
        else:
            probar_conexion_imap_oauth(buzon.servidor_imap, buzon.puerto, buzon.correo, access_token)
            mensaje = "Conexión exitosa al buzón IMAP"

        buzon.estado_conexion = "ok"
        buzon.ultimo_error = None
        db.commit()
        return {"ok": True, "mensaje": mensaje}
    except Exception as e:
        buzon.estado_conexion = "error"
        buzon.ultimo_error = str(e)[:500]
        db.commit()
        return {"ok": False, "mensaje": str(e)}


def iniciar_oauth_buzon(db: Session, buzon_id: int) -> dict:
    """
    Genera la URL de autorización OAuth2 para que el admin la abra en el navegador.
    Almacena el 'state' para verificación CSRF en el callback.
    """
    import secrets
    import urllib.parse
    from app.core.config import settings

    buzon = db.query(BuzonCorreo).filter(BuzonCorreo.id == buzon_id).first()
    if not buzon:
        not_found("Buzón de correo")
    if buzon.auth_type != "oauth2":
        buzon.auth_type = "oauth2"
    if not buzon.oauth_client_id:
        bad_request("Falta oauth_client_id en la configuración del buzón")

    key = (buzon.proveedor, buzon.tipo_cuenta)
    auth_base = _OAUTH_AUTH_URLS.get(key)
    if not auth_base:
        bad_request(f"OAuth2 no soportado para {buzon.proveedor}/{buzon.tipo_cuenta}")

    if buzon.proveedor == "outlook" and buzon.tipo_cuenta == "empresarial":
        tenant = buzon.oauth_tenant_id or "organizations"
        auth_base = auth_base.replace("{tenant}", tenant)

    state = secrets.token_urlsafe(32)
    if buzon.proveedor == "outlook":
        metodo = getattr(buzon, "metodo_conexion", "imap")
        scope = _OAUTH_SCOPES[("outlook", metodo)]
    else:
        scope = _OAUTH_SCOPES["gmail"]

    params: dict = {
        "client_id": buzon.oauth_client_id,
        "response_type": "code",
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "scope": scope,
        "state": state,
        "response_mode": "query",
    }
    if buzon.proveedor == "gmail":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    url = auth_base + "?" + urllib.parse.urlencode(params)
    buzon.oauth_state = state
    db.commit()

    return {
        "url": url,
        "mensaje": (
            "Abre esta URL en el navegador. Tras autorizar, Microsoft/Google "
            f"redirigirá a {settings.OAUTH_REDIRECT_URI}. "
            "El frontend debe enviar code+state al endpoint /oauth/completar."
        ),
    }


def completar_oauth_buzon(db: Session, data: OAuthCompletarIn) -> dict:
    """
    Recibe el code y state del callback OAuth2, intercambia el code por tokens
    y los almacena cifrados en el buzón.
    """
    import requests as req
    from datetime import timedelta
    from app.core.config import settings

    buzon = db.query(BuzonCorreo).filter(BuzonCorreo.oauth_state == data.state).first()
    if not buzon:
        bad_request("Estado OAuth inválido o expirado. Reinicie el flujo de autorización.")

    if buzon.proveedor == "outlook":
        if buzon.tipo_cuenta == "personal":
            token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
        else:
            tenant = buzon.oauth_tenant_id or "organizations"
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    else:
        token_url = "https://oauth2.googleapis.com/token"

    client_secret = decrypt(buzon.oauth_client_secret_enc)

    resp = req.post(token_url, data={
        "client_id": buzon.oauth_client_id,
        "client_secret": client_secret,
        "code": data.code,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=30)

    if not resp.ok:
        err = resp.json()
        msg = err.get("error_description") or err.get("error") or resp.text
        buzon.estado_conexion = "error"
        buzon.ultimo_error = f"OAuth error: {msg}"[:500]
        buzon.oauth_state = None
        db.commit()
        bad_request(f"Error al obtener tokens OAuth: {msg}")

    from datetime import datetime, timezone
    token_data = resp.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

    buzon.oauth_access_token_enc = encrypt(access_token)
    if refresh_token:
        buzon.oauth_refresh_token_enc = encrypt(refresh_token)
    buzon.oauth_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    buzon.oauth_state = None
    buzon.estado_conexion = "sin_probar"
    db.commit()

    return {"ok": True, "mensaje": "OAuth autorizado correctamente. Ahora puede probar la conexión."}


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
        "generado_en": datetime.now(timezone.utc),
        "entidad": _row(entidad, ["nombre", "nit", "municipio", "departamento", "direccion", "telefono", "email_institucional"]) if entidad else None,
        "configuracion": _row(config, ["prefijo_radicado", "anio_radicado", "secuencia_actual", "ruta_almacenamiento", "color_primario", "politica_privacidad_activa"]) if config else None,
        "dependencias": [_row(d, ["nombre", "codigo", "responsable", "email", "activa"]) for d in dependencias],
        "canales": [_row(c, ["nombre", "tipo", "activo", "acuse_configurado"]) for c in canales],
        "tipos_requerimiento": [_row(t, ["nombre", "descripcion", "activo"]) for t in tipos],
        "plazos_respuesta": [_row(p, ["nombre", "dias_habiles", "activo"]) for p in plazos],
        "total_usuarios": total_usuarios,
    }
