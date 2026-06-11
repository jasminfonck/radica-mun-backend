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
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path
from typing import Optional

import bleach

from app.core.config import settings
from app.core.crypto import decrypt
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
) -> list:
    """
    Extrae y valida adjuntos del correo.
    Aplica: límite de cantidad, límite de tamaño, whitelist MIME, blocklist extensiones,
    sanitización de nombre de archivo.
    """
    adjuntos = []
    ruta_base = Path(ruta_storage) / "adjuntos"
    ruta_base.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        if len(adjuntos) >= max_adjuntos:
            logger.warning(
                "Recepcion %d: límite de %d adjuntos alcanzado, el resto fue ignorado",
                recepcion_id, max_adjuntos,
            )
            break

        disposition = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        if "attachment" not in disposition and filename_raw is None:
            continue

        filename_raw = filename_raw or f"adjunto_{len(adjuntos) + 1}"
        filename = _sanitizar_nombre_archivo(_decodificar_header(filename_raw))
        ext = Path(filename).suffix.lower()

        if ext in EXTENSIONES_BLOQUEADAS:
            logger.warning("Adjunto rechazado por extensión bloqueada: %s", filename)
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        if len(payload) > max_tamano_bytes:
            logger.warning(
                "Adjunto '%s' rechazado: %d bytes excede límite de %d bytes",
                filename, len(payload), max_tamano_bytes,
            )
            continue

        mime_type = part.get_content_type()
        if mime_type not in MIME_PERMITIDOS:
            logger.warning("Adjunto rechazado por tipo MIME no permitido: %s (%s)", filename, mime_type)
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

    return adjuntos


# ── Interfaz pública ──────────────────────────────────────────────────────

def probar_conexion_imap(servidor: str, puerto: int, correo: str, password: str) -> None:
    """
    Verifica que las credenciales son válidas conectando y desconectando.
    Lanza excepción con mensaje claro si falla.
    """
    ssl_ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(servidor, puerto, ssl_context=ssl_ctx)
        mail.socket().settimeout(15)
        mail.login(correo, password)
        mail.logout()
    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error de autenticación IMAP: {e}")
    except OSError as e:
        raise ConnectionError(f"No se pudo conectar a {servidor}:{puerto} — {e}")


def procesar_buzon(buzon, db) -> dict:
    """
    Conecta al buzón via IMAP, lee correos UNSEEN y crea preregistros de recepción.
    Retorna estadísticas: {procesados, ignorados_spam, errores}.

    El argumento `buzon` es una instancia de BuzonCorreo.
    El argumento `db` es una Session de SQLAlchemy.
    """
    from app.modules.admin.models import ConfiguracionSistema

    stats = {"procesados": 0, "ignorados_spam": 0, "errores": 0}

    try:
        password = decrypt(buzon.password_app_enc)
    except Exception as e:
        raise ValueError(f"No se pudo descifrar la contraseña del buzón: {e}")

    config = db.query(ConfiguracionSistema).first()
    ruta_storage = (config.ruta_almacenamiento if config else None) or settings.STORAGE_PATH
    max_tam_bytes = buzon.max_tamano_adjunto_mb * 1024 * 1024

    ssl_ctx = ssl.create_default_context()

    try:
        mail = imaplib.IMAP4_SSL(buzon.servidor_imap, buzon.puerto, ssl_context=ssl_ctx)
        mail.socket().settimeout(30)
        mail.login(buzon.correo, password)
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

                adjuntos = _extraer_adjuntos(
                    msg, recepcion.id, buzon.max_adjuntos, max_tam_bytes, ruta_storage
                )
                for adj in adjuntos:
                    db.add(adj)

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
