from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

TZ_COLOMBIA = timezone(timedelta(hours=-5))


def now_colombia() -> datetime:
    """Retorna la fecha y hora actual en zona horaria de Colombia (UTC-5)."""
    return datetime.now(TZ_COLOMBIA)


def tipos_permitidos_set(tipos_str: str) -> set[str]:
    """Convierte la cadena CSV de la configuración en un conjunto de MIME types."""
    return {t.strip() for t in tipos_str.split(",") if t.strip()}


def validar_adjunto(
    mime_type: str,
    tamano_bytes: int,
    max_tamano_mb: int,
    tipos_permitidos: str,
) -> None:
    """Lanza HTTP 400 si el archivo no cumple la parametrización de adjuntos."""
    permitidos = tipos_permitidos_set(tipos_permitidos)
    if permitidos and mime_type not in permitidos:
        etiquetas = ", ".join(sorted(permitidos))
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: '{mime_type}'. Tipos aceptados: {etiquetas}.",
        )
    max_bytes = max_tamano_mb * 1024 * 1024
    if tamano_bytes > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el tamaño máximo permitido de {max_tamano_mb} MB.",
        )


def fecha_hora_str(dt: datetime) -> str:
    """Formatea datetime para mostrar al usuario: '23 de marzo de 2025 a las 10:30 a.m.'"""
    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    hora = dt.strftime("%I:%M %p").lower()
    return f"{dt.day} de {meses[dt.month]} de {dt.year} a las {hora}"
