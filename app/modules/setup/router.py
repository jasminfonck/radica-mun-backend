from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.modules.admin.models import Rol, Usuario

router = APIRouter(prefix="/setup", tags=["Setup"])

ROLES = [
    {"nombre": "administrador", "descripcion": "Acceso total al sistema y configuración"},
    {"nombre": "operador",      "descripcion": "Recepción, registro de remitentes y radicación"},
    {"nombre": "consultor",     "descripcion": "Solo consulta y reportes"},
]


@router.post("")
def setup_inicial(db: Session = Depends(get_db)):
    if db.query(Rol).count() > 0:
        return {"ok": False, "mensaje": "El sistema ya fue inicializado"}

    # Crear tablas si no existen (por si las migraciones no corrieron)
    Base.metadata.create_all(bind=engine)

    # Crear roles
    roles_creados = []
    for r in ROLES:
        rol = Rol(**r)
        db.add(rol)
        roles_creados.append(r["nombre"])
    db.commit()

    # Crear usuario administrador
    rol_admin = db.query(Rol).filter(Rol.nombre == "administrador").first()
    admin = Usuario(
        nombre="Administrador del Sistema",
        email="admin@radica.local",
        password_hash=hash_password("Radica2025*"),
        rol_id=rol_admin.id,
    )
    db.add(admin)
    db.commit()

    return {
        "ok": True,
        "roles_creados": roles_creados,
        "usuario": {
            "email": "admin@radica.local",
            "password": "Radica2025*",
            "advertencia": "Cambia la contraseña en el primer ingreso"
        }
    }
