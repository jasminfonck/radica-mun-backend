from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.modules.admin.models import Usuario
from app.modules.auth.schemas import LoginRequest, TokenResponse, UsuarioToken

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.activo == True
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )

    token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        usuario=UsuarioToken(
            id=user.id,
            nombre=user.nombre,
            email=user.email,
            rol=user.rol.nombre,
        )
    )


@router.get("/me", response_model=UsuarioToken)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return UsuarioToken(
        id=current_user.id,
        nombre=current_user.nombre,
        email=current_user.email,
        rol=current_user.rol.nombre,
    )
