"""
Script de datos iniciales.
Crea los roles del sistema y el primer usuario administrador.

Uso:
    python seed.py
"""
from app.db.session import SessionLocal
from app.modules.admin.models import Rol, Usuario
from app.core.security import hash_password

ROLES = [
    {"nombre": "administrador", "descripcion": "Acceso total al sistema y configuración"},
    {"nombre": "operador",      "descripcion": "Recepción, registro de remitentes y radicación"},
    {"nombre": "consultor",     "descripcion": "Solo consulta y reportes"},
]

ADMIN_DEFAULT = {
    "nombre": "Administrador del Sistema",
    "email": "admin@radica.local",
    "password": "Radica2025*",
}


def seed():
    db = SessionLocal()
    try:
        # Crear roles si no existen
        for rol_data in ROLES:
            if not db.query(Rol).filter(Rol.nombre == rol_data["nombre"]).first():
                db.add(Rol(**rol_data))
        db.commit()
        print("✓ Roles creados")

        # Crear usuario administrador si no existe
        if not db.query(Usuario).filter(Usuario.email == ADMIN_DEFAULT["email"]).first():
            rol_admin = db.query(Rol).filter(Rol.nombre == "administrador").first()
            db.add(Usuario(
                nombre=ADMIN_DEFAULT["nombre"],
                email=ADMIN_DEFAULT["email"],
                password_hash=hash_password(ADMIN_DEFAULT["password"]),
                rol_id=rol_admin.id,
            ))
            db.commit()
            print(f"✓ Usuario administrador creado")
            print(f"  Email:      {ADMIN_DEFAULT['email']}")
            print(f"  Contraseña: {ADMIN_DEFAULT['password']}")
            print(f"  ⚠ Cambia la contraseña en el primer ingreso")
        else:
            print("✓ Usuario administrador ya existe")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
