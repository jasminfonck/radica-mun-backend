from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UsuarioToken(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioToken
