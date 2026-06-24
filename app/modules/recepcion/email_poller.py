"""
Lector IMAP para el buzón oficial de radicación.
Lee correos NO VISTOS, los sanitiza y crea preregistros en recepciones.

Medidas de seguridad implementadas:
  - SSL/TLS estricto (sin fallback a conexiones no cifradas)
  - Sanitización HTML con bleach (strip completo de etiquetas)
  - Limpieza de caracteres de control del cuerpo del correo
  - Whitelist de tipos MIME para adjuntos
  - Blocklist de extensiones ejecutables/peligrosas
  - Sanitización de nombres de archivo (prevención de path traversal)
  - Límite de tamaño por adjunto y por correo completo
  - Límite de número de adjuntos por correo
  - Blocklist de dominios de correo desechables conocidos (spam)
  - Timeout de conexión IMAP
  - Los correos procesados se marcan como leídos para no reprocesarse
"""
import email
import imaplib
import logging
import os
import re
import ssl
import uuid
from datetime import datetime, timezone, timedelta
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path
from typing import Optional

import bleach
import requests as req

from app.core.config import settings
from app.core.crypto import decrypt, encrypt
from app.modules.recepcion.models import AdjuntoRecepcion, Recepcion

logger = logging.getLogger(__name__)

# ── Constantes de seguridad ───────────────────────────────────────────────

MIME_PERMITIDOS = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/tiff",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "application/rtf",
}

EXTENSIONES_BLOQUEADAS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".com", ".scr",
    ".vbs", ".js", ".jar", ".py", ".php", ".asp", ".aspx", ".jsp",
    ".dll", ".so", ".dylib", ".rar", ".7z", ".iso", ".img",
    ".pif", ".reg", ".vbe", ".wsf", ".wsh", ".hta", ".cpl",
}

# Dominios de correos temporales / desechables conocidos
DOMINIOS_SPAM = {
    "mailnull.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "10minutemail.com", "maildrop.cc", "yopmail.com", "sharklasers.com",
    "trashmail.com", "dispostable.com", "spamgourmet.com", "mailinator.com",
    "fakeinbox.com", "getairmail.com", "discard.email", "spamhereplease.com",
}

TAMANO_MAXIMO_CORREO_BYTES = 50 * 1024 * 1024   # 50 MB por correo completo
CUERPO_MAXIMO_CARACTERES = 50_000
ASUNTO_MAXIMO_CARACTERES = 300


# ── Utilidades de sanitización ────────────────────────────────────────────

def _decodificar_header(valor: Optional[str]) -> str:
    """Decodifica headers de correo (base64 / quoted-printable / raw)."""
    if not valor:
        return ""
    partes = decode_header(valor)
    resultado = []
    for parte, charset in partes:
        if isinstance(parte, bytes):
            try:
                resultado.append(parte.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                resultado.append(parte.decode("latin-1", errors="replace"))
        else:
            resultado.append(str(parte))
    return " ".join(resultado)


def _sanitizar_texto(texto: str) -> str:
    """
    Elimina todo HTML y caracteres de control del texto del correo.
    Usa bleach para strip completo de etiquetas, luego limpia control chars.
    """
    # Strip total de HTML (sin etiquetas permitidas)
    texto = bleach.clean(texto, tags=[], attributes={}, strip=True)
    # Eliminar caracteres de control excepto LF, CR y TAB
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)
    return texto[:CUERPO_MAXIMO_CARACTERES]


def _sanitizar_nombre_archivo(nombre: str) -> str:
    """
    Previene path traversal y elimina caracteres peligrosos del nombre de archivo.
    """
    nombre = os.path.basename(nombre)                      # elimina rutas absolutas/relativas
    nombre = re.sub(r"[^\w\s\-.]", "_", nombre)           # solo chars seguros
    nombre = nombre.strip(". ")                            # no empieza/termina con punto o espacio
    if not nombre:
        return f"adjunto_{uuid.uuid4().hex[:8]}"
    return nombre[:200]


def _es_remitente_sospechoso(from_header: str) -> bool:
    """Verifica si el remitente pertenece a un dominio de spam conocido."""
    _, address = parseaddr(from_header)
    if not address or "@" not in address:
        return True
    domain = address.split("@")[-1].strip().lower()
    return domain in DOMINIOS_SPAM


def _extraer_cuerpo(msg: email.message.Message) -> str:
    """
    Extrae el cuerpo del correo priorizando text/plain.
    Si solo hay text/html, lo sanitiza con bleach antes de retornar.
    """
    texto_plano = ""
    html_fallback = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                if content_type == "text/plain" and not texto_plano:
                    texto_plano = payload.decode(charset, errors="replace")
                elif content_type == "text/html" and not html_fallback:
                    html_fallback = payload.decode(charset, errors="replace")
            except Exception:
                pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                texto_plano = payload.decode(charset, errors="replace")
        except Exception:
            pass

    cuerpo = texto_plano if texto_plano else html_fallback
    return _sanitizar_texto(cuerpo)


def _extraer_adjuntos(
    msg: email.message.Message,
    recepcion_id: int,
    max_adjuntos: int,
    max_tamano_bytes: int,
    ruta_storage: str,
    tipos_permitidos: set | None = None,
) -> tuple[list, list[str]]:
    """
    Extrae y valida adjuntos del correo.
    Retorna (adjuntos_guardados, avisos) donde avisos es la lista de problemas
    encontrados que deben reflejarse en la recepción.
    """
    adjuntos: list = []
    avisos:   list[str] = []
    ruta_base = Path(ruta_storage) / "adjuntos"
    ruta_base.mkdir(parents=True, exist_ok=True)
    max_mb = max_tamano_bytes // (1024 * 1024)

    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        if "attachment" not in disposition and filename_raw is None:
            continue

        filename_raw = filename_raw or f"adjunto_{len(adjuntos) + len(avisos) + 1}"
        filename = _sanitizar_nombre_archivo(_decodificar_header(filename_raw))
        ext = Path(filename).suffix.lower()

        # Límite de cantidad alcanzado — registrar el excedente como aviso
        if len(adjuntos) >= max_adjuntos:
            msg_aviso = f"'{filename}' no guardado: se superó el límite de {max_adjuntos} adjuntos."
            avisos.append(msg_aviso)
            logger.warning("Recepcion %d: %s", recepcion_id, msg_aviso)
            continue

        if ext in EXTENSIONES_BLOQUEADAS:
            msg_aviso = f"'{filename}' rechazado: extensión bloqueada por seguridad ({ext})."
            avisos.append(msg_aviso)
            logger.warning("Recepcion %d: %s", recepcion_id, msg_aviso)
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        if len(payload) > max_tamano_bytes:
            msg_aviso = (
                f"'{filename}' rechazado: pesa {len(payload) // (1024*1024)} MB, "
                f"el máximo permitido es {max_mb} MB."
            )
            avisos.append(msg_aviso)
            logger.warning("Recepcion %d: %s", recepcion_id, msg_aviso)
            continue

        mime_type = part.get_content_type()
        lista_mime = tipos_permitidos if tipos_permitidos is not None else MIME_PERMITIDOS
        if mime_type not in lista_mime:
            msg_aviso = f"'{filename}' rechazado: tipo de archivo no permitido ({mime_type})."
            avisos.append(msg_aviso)
            logger.warning("Recepcion %d: %s", recepcion_id, msg_aviso)
            continue

        nombre_disco = f"{uuid.uuid4().hex}_{filename}"
        ruta_archivo = ruta_base / nombre_disco
        ruta_archivo.write_bytes(payload)

        adjuntos.append(AdjuntoRecepcion(
            recepcion_id=recepcion_id,
            nombre_original=filename,
            nombre_archivo=nombre_disco,
            ruta=str(ruta_archivo),
            tipo_mime=mime_type,
            tamano_bytes=len(payload),
        ))

    return adjuntos, avisos


# ── OAuth2 helpers ────────────────────────────────────────────────────────

_OAUTH_TOKEN_URLS = {
    ("outlook", "personal"):    "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
    ("outlook", "empresarial"): "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
    ("gmail",   "personal"):    "https://oauth2.googleapis.com/token",
    ("gmail",   "empresarial"): "https://oauth2.googleapis.com/token",
}


def refrescar_token_si_necesario(buzon, db) -> str:
    """
    Devuelve el access token vigente; si está por vencer (< 5 min) o ya venció,
    lo renueva con el refresh token y actualiza la BD.
    """
    now = datetime.now(timezone.utc)
    expiry = buzon.oauth_token_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry and expiry > now + timedelta(minutes=5) and buzon.oauth_access_token_enc:
        return decrypt(buzon.oauth_access_token_enc)

    if not buzon.oauth_refresh_token_enc:
        raise ConnectionError("No hay refresh token disponible. Re-autorice el buzón OAuth2.")

    refresh_token = decrypt(buzon.oauth_refresh_token_enc)
    client_secret = decrypt(buzon.oauth_client_secret_enc)
    key = (buzon.proveedor, buzon.tipo_cuenta)
    token_url = _OAUTH_TOKEN_URLS.get(key, "")
    if buzon.proveedor == "outlook" and buzon.tipo_cuenta == "empresarial":
        token_url = token_url.replace("{tenant}", buzon.oauth_tenant_id or "organizations")

    resp = req.post(token_url, data={
        "client_id": buzon.oauth_client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)

    if not resp.ok:
        err = resp.json()
        msg = err.get("error_description") or err.get("error") or resp.text
        raise ConnectionError(f"No se pudo renovar el token OAuth: {msg}")

    data = resp.json()
    access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    new_refresh = data.get("refresh_token")

    buzon.oauth_access_token_enc = encrypt(access_token)
    if new_refresh:
        buzon.oauth_refresh_token_enc = encrypt(new_refresh)
    buzon.oauth_token_expiry = now + timedelta(seconds=expires_in)
    db.commit()

    return access_token


def _imap_autenticar_xoauth2(mail: imaplib.IMAP4_SSL, correo: str, access_token: str) -> None:
    auth_string = f"user={correo}\x01auth=Bearer {access_token}\x01\x01"
    mail.authenticate("XOAUTH2", lambda _: auth_string.encode("ascii"))


def probar_conexion_imap_oauth(servidor: str, puerto: int, correo: str, access_token: str) -> None:
    """Verifica la conexión IMAP con autenticación XOAUTH2."""
    import socket as _socket
    import errno as _errno

    # Verifica conectividad TCP antes del handshake SSL para dar un mensaje claro.
    try:
        sock = _socket.create_connection((servidor, puerto), timeout=10)
        sock.close()
    except _socket.timeout:
        raise ConnectionError(
            f"Tiempo de espera agotado al intentar conectar a {servidor}:{puerto}. "
            "Verifique que el firewall del servidor permita conexiones salientes en el puerto 993."
        )
    except OSError as e:
        if e.errno in (_errno.ECONNREFUSED, _errno.ECONNRESET, _errno.ENETUNREACH, _errno.EHOSTUNREACH):
            raise ConnectionError(
                f"El servidor no puede alcanzar {servidor}:{puerto} — {e}. "
                "Verifique las reglas de firewall para conexiones salientes IMAP (puerto 993)."
            )
        raise ConnectionError(f"Error de red al conectar a {servidor}:{puerto} — {e}")

    ssl_ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(servidor, puerto, ssl_context=ssl_ctx)
        mail.socket().settimeout(15)
        _imap_autenticar_xoauth2(mail, correo, access_token)
        mail.logout()
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error de autenticación XOAUTH2: {e}")
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar a {servidor}:{puerto} — {e}")


# ── Microsoft Graph API ───────────────────────────────────────────────────

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def probar_conexion_graph(access_token: str) -> None:
    """Verifica acceso al buzón vía Microsoft Graph API (HTTPS puerto 443)."""
    resp = req.get(
        f"{_GRAPH_BASE}/me/mailFolders/inbox",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if resp.status_code == 401:
        raise ConnectionError("Token OAuth2 inválido o expirado. Re-autorice el buzón.")
    if resp.status_code == 403:
        raise ConnectionError(
            "Sin permisos Mail.Read. Re-autorice el buzón con el botón 'Autorizar OAuth2'."
        )
    if not resp.ok:
        raise ConnectionError(
            f"Error al verificar acceso Graph API: {resp.status_code} — {resp.text[:200]}"
        )


def _extraer_adjuntos_graph(
    msg_id: str,
    attachments_meta: list,
    access_token: str,
    recepcion_id: int,
    max_adjuntos: int,
    max_tam_bytes: int,
    ruta_storage: str,
    tipos_permitidos: set | None,
) -> tuple[list, list[str]]:
    import base64

    adjuntos: list = []
    avisos:   list[str] = []
    ruta_base = Path(ruta_storage) / "adjuntos"
    ruta_base.mkdir(parents=True, exist_ok=True)
    max_mb = max_tam_bytes // (1024 * 1024)
    headers = {"Authorization": f"Bearer {access_token}"}

    for att in attachments_meta:
        if att.get("isInline", False):
            continue
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue

        filename = _sanitizar_nombre_archivo(att.get("name") or f"adjunto_{uuid.uuid4().hex[:8]}")
        ext = Path(filename).suffix.lower()

        if len(adjuntos) >= max_adjuntos:
            avisos.append(f"'{filename}' no guardado: se superó el límite de {max_adjuntos} adjuntos.")
            continue
        if ext in EXTENSIONES_BLOQUEADAS:
            avisos.append(f"'{filename}' rechazado: extensión bloqueada por seguridad ({ext}).")
            continue

        size = att.get("size", 0)
        if size > max_tam_bytes:
            avisos.append(f"'{filename}' rechazado: pesa {size // (1024*1024)} MB, máximo {max_mb} MB.")
            continue

        mime_type = att.get("contentType", "application/octet-stream")
        lista_mime = tipos_permitidos if tipos_permitidos is not None else MIME_PERMITIDOS
        if mime_type not in lista_mime:
            avisos.append(f"'{filename}' rechazado: tipo de archivo no permitido ({mime_type}).")
            continue

        # Descarga el contenido del adjunto (base64 en la respuesta expandida)
        content_b64 = att.get("contentBytes")
        if content_b64:
            payload = base64.b64decode(content_b64)
        else:
            att_resp = req.get(
                f"{_GRAPH_BASE}/me/messages/{msg_id}/attachments/{att['id']}",
                headers=headers,
                timeout=60,
            )
            if not att_resp.ok:
                avisos.append(f"'{filename}' no se pudo descargar del servidor.")
                continue
            content_b64 = att_resp.json().get("contentBytes", "")
            payload = base64.b64decode(content_b64)

        nombre_disco = f"{uuid.uuid4().hex}_{filename}"
        ruta_archivo = ruta_base / nombre_disco
        ruta_archivo.write_bytes(payload)

        adjuntos.append(AdjuntoRecepcion(
            recepcion_id=recepcion_id,
            nombre_original=filename,
            nombre_archivo=nombre_disco,
            ruta=str(ruta_archivo),
            tipo_mime=mime_type,
            tamano_bytes=len(payload),
        ))

    return adjuntos, avisos


def procesar_buzon_graph(buzon, db) -> dict:
    """
    Lee correos NO VISTOS vía Microsoft Graph API (HTTPS).
    Alternativa a IMAP para cuentas Microsoft cuyo puerto 993 esté bloqueado.
    """
    from app.modules.admin.models import ConfiguracionSistema

    stats = {"procesados": 0, "ignorados_spam": 0, "errores": 0}

    try:
        access_token = refrescar_token_si_necesario(buzon, db)
    except Exception as e:
        raise ValueError(f"No se pudieron obtener las credenciales del buzón: {e}")

    config = db.query(ConfiguracionSistema).first()
    ruta_storage  = (config.ruta_almacenamiento if config else None) or settings.STORAGE_PATH
    max_adjuntos  = config.max_adjuntos if config else 5
    max_tam_bytes = (config.max_tamano_adjunto_mb if config else 10) * 1024 * 1024
    tipos_mime    = None
    if config and config.tipos_archivo_permitidos:
        from app.shared.utils import tipos_permitidos_set
        tipos_mime = tipos_permitidos_set(config.tipos_archivo_permitidos)

    headers = {"Authorization": f"Bearer {access_token}"}

    url = (
        f"{_GRAPH_BASE}/me/mailFolders/inbox/messages"
        "?$filter=isRead eq false"
        "&$top=50"
        "&$select=id,subject,from,body,hasAttachments,receivedDateTime"
        "&$expand=attachments($select=id,name,contentType,size,isInline,@odata.type,contentBytes)"
    )

    resp = req.get(url, headers=headers, timeout=30)
    if not resp.ok:
        raise ConnectionError(f"Error al leer mensajes Graph API: {resp.status_code} — {resp.text[:200]}")

    messages = resp.json().get("value", [])

    for msg in messages:
        try:
            from_info  = msg.get("from", {}).get("emailAddress", {})
            email_from = from_info.get("address", "").lower().strip()
            from_header = f"{from_info.get('name', '')} <{email_from}>"

            if _es_remitente_sospechoso(from_header):
                req.patch(
                    f"{_GRAPH_BASE}/me/messages/{msg['id']}",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"isRead": True},
                    timeout=10,
                )
                stats["ignorados_spam"] += 1
                continue

            asunto = (msg.get("subject") or "(sin asunto)")[:ASUNTO_MAXIMO_CARACTERES]
            body_content = msg.get("body", {}).get("content", "")
            cuerpo = _sanitizar_texto(body_content)

            recepcion = Recepcion(
                canal_id=buzon.canal_id,
                asunto_provisional=asunto,
                observaciones=cuerpo[:2000] if cuerpo else None,
                email_remitente=email_from[:200],
                estado="recibido",
                recibido_por_id=None,
            )
            db.add(recepcion)
            db.flush()

            from app.modules.radicado.service import _asignar_radicado_inicial
            _asignar_radicado_inicial(db, recepcion.id)

            adjuntos, avisos = [], []
            if msg.get("hasAttachments"):
                adjuntos, avisos = _extraer_adjuntos_graph(
                    msg["id"],
                    msg.get("attachments", []),
                    access_token,
                    recepcion.id,
                    max_adjuntos,
                    max_tam_bytes,
                    ruta_storage,
                    tipos_mime,
                )
                for adj in adjuntos:
                    db.add(adj)

            if avisos:
                recepcion.aviso_adjuntos = "\n".join(avisos)
                recepcion.estado = "incompleto"

            db.commit()

            req.patch(
                f"{_GRAPH_BASE}/me/messages/{msg['id']}",
                headers={**headers, "Content-Type": "application/json"},
                json={"isRead": True},
                timeout=10,
            )
            stats["procesados"] += 1

        except Exception as e:
            db.rollback()
            logger.error("Error procesando mensaje Graph API id=%s: %s", msg.get("id"), e)
            stats["errores"] += 1

    return stats


# ── Interfaz pública ──────────────────────────────────────────────────────

def _imap_autenticar(mail: imaplib.IMAP4_SSL, correo: str, password: str) -> None:
    """
    Intenta AUTHENTICATE PLAIN si el servidor lo anuncia; si falla o no está
    disponible, cae a LOGIN. Así funciona con Outlook personal, Gmail y la
    mayoría de servidores IMAP.
    """
    caps = getattr(mail, "capabilities", ())
    if b"AUTH=PLAIN" in caps:
        try:
            auth_bytes = f"\x00{correo}\x00{password}".encode()
            mail.authenticate("PLAIN", lambda _: auth_bytes)
            return
        except imaplib.IMAP4.error:
            pass  # PLAIN rechazado → intento con LOGIN
    mail.login(correo, password)


def probar_conexion_imap(servidor: str, puerto: int, correo: str, password: str) -> None:
    """
    Verifica que las credenciales son válidas conectando y desconectando.
    Lanza excepción con mensaje claro si falla.
    """
    ssl_ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(servidor, puerto, ssl_context=ssl_ctx)
        mail.socket().settimeout(15)
        _imap_autenticar(mail, correo, password)
        mail.logout()
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error de autenticación IMAP: {e}")
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar a {servidor}:{puerto} — {e}")


def procesar_buzon(buzon, db) -> dict:
    """
    Lee correos no vistos y crea preregistros de recepción.
    Delega a Graph API o IMAP según buzon.metodo_conexion.
    """
    if getattr(buzon, "metodo_conexion", "imap") == "graph":
        return procesar_buzon_graph(buzon, db)
    return _procesar_buzon_imap(buzon, db)


def _procesar_buzon_imap(buzon, db) -> dict:
    from app.modules.admin.models import ConfiguracionSistema

    stats = {"procesados": 0, "ignorados_spam": 0, "errores": 0}

    try:
        access_token = refrescar_token_si_necesario(buzon, db)
    except Exception as e:
        raise ValueError(f"No se pudieron obtener las credenciales del buzón: {e}")

    config = db.query(ConfiguracionSistema).first()
    ruta_storage  = (config.ruta_almacenamiento if config else None) or settings.STORAGE_PATH
    max_adjuntos  = config.max_adjuntos if config else 5
    max_tam_bytes = (config.max_tamano_adjunto_mb if config else 10) * 1024 * 1024
    tipos_mime    = None
    if config and config.tipos_archivo_permitidos:
        from app.shared.utils import tipos_permitidos_set
        tipos_mime = tipos_permitidos_set(config.tipos_archivo_permitidos)

    ssl_ctx = ssl.create_default_context()

    try:
        mail = imaplib.IMAP4_SSL(buzon.servidor_imap, buzon.puerto, ssl_context=ssl_ctx)
        mail.socket().settimeout(30)
        _imap_autenticar_xoauth2(mail, buzon.correo, access_token)
        mail.select("INBOX")

        _, ids = mail.search(None, "UNSEEN")
        email_ids = ids[0].split() if ids[0] else []

        for uid in email_ids:
            try:
                _, data = mail.fetch(uid, "(RFC822)")
                if not data or not data[0]:
                    continue

                raw_email = data[0][1]

                # Anti-DoS: ignorar correos excesivamente grandes
                if len(raw_email) > TAMANO_MAXIMO_CORREO_BYTES:
                    logger.warning("Correo uid=%s ignorado: supera %d MB", uid, TAMANO_MAXIMO_CORREO_BYTES // (1024 * 1024))
                    mail.store(uid, "+FLAGS", "\\Seen")
                    stats["ignorados_spam"] += 1
                    continue

                msg = email.message_from_bytes(raw_email)

                from_header = msg.get("From", "")
                _, email_from = parseaddr(from_header)
                email_from = email_from.lower().strip()

                # Filtro de spam por dominio
                if _es_remitente_sospechoso(from_header):
                    logger.warning("Correo de dominio sospechoso ignorado: %s", email_from)
                    mail.store(uid, "+FLAGS", "\\Seen")
                    stats["ignorados_spam"] += 1
                    continue

                asunto = _decodificar_header(msg.get("Subject", "(sin asunto)"))[:ASUNTO_MAXIMO_CARACTERES]
                cuerpo = _extraer_cuerpo(msg)

                recepcion = Recepcion(
                    canal_id=buzon.canal_id,
                    asunto_provisional=asunto,
                    observaciones=cuerpo[:2000] if cuerpo else None,
                    email_remitente=email_from[:200],
                    estado="recibido",
                    recibido_por_id=None,
                )
                db.add(recepcion)
                db.flush()

                # Asignar número de radicado como referencia de seguimiento desde el inicio
                from app.modules.radicado.service import _asignar_radicado_inicial
                _asignar_radicado_inicial(db, recepcion.id)

                adjuntos, avisos = _extraer_adjuntos(
                    msg, recepcion.id, max_adjuntos, max_tam_bytes, ruta_storage, tipos_mime
                )
                for adj in adjuntos:
                    db.add(adj)

                if avisos:
                    recepcion.aviso_adjuntos = "\n".join(avisos)
                    recepcion.estado = "incompleto"

                db.commit()
                mail.store(uid, "+FLAGS", "\\Seen")
                stats["procesados"] += 1

            except Exception as e:
                db.rollback()
                logger.error("Error procesando correo uid=%s: %s", uid, e)
                stats["errores"] += 1

        mail.logout()

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP al procesar buzón {buzon.correo}: {e}")
    except OSError as e:
        raise ConnectionError(f"Sin conexión a {buzon.servidor_imap}: {e}")

    return stats
