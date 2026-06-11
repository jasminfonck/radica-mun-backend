from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.modules.admin.models import Usuario
from app.modules.auth.schemas import LoginRequest, TokenResponse, UsuarioToken

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo. Contacte al administrador del sistema.",
        )

    # Invalidar cualquier sesión previa incrementando la versión
    user.token_version = (user.token_version or 0) + 1
    db.commit()

    token = create_access_token({"sub": str(user.id), "ver": user.token_version})

    return TokenResponse(
        access_token=token,
        usuario=UsuarioToken(
            id=user.id,
            nombre=user.nombre,
            apellido=user.apellido,
            email=user.email,
            rol=user.rol.nombre,
        )
    )


@router.get("/me", response_model=UsuarioToken)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return UsuarioToken(
        id=current_user.id,
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        email=current_user.email,
        rol=current_user.rol.nombre,
    )
