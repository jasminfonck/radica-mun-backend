from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    STORAGE_PATH: str = "../storage"
    ALLOWED_ORIGINS: str = "http://localhost:4200"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # Clave Fernet para cifrar credenciales de buzón de correo.
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # URI de redirección OAuth2. Debe estar registrada en Azure AD / Google Cloud Console.
    # El backend maneja el callback directamente (no requiere frontend).
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/admin/buzon-correo/oauth/callback"

    class Config:
        env_file = ".env"


settings = Settings()
