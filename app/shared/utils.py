from datetime import datetime, timezone, timedelta

TZ_COLOMBIA = timezone(timedelta(hours=-5))


def now_colombia() -> datetime:
    """Retorna la fecha y hora actual en zona horaria de Colombia (UTC-5)."""
    return datetime.now(TZ_COLOMBIA)


def fecha_hora_str(dt: datetime) -> str:
    """Formatea datetime para mostrar al usuario: '23 de marzo de 2025 a las 10:30 a.m.'"""
    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    hora = dt.strftime("%I:%M %p").lower()
    return f"{dt.day} de {meses[dt.month]} de {dt.year} a las {hora}"
