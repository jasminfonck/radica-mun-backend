import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Agrega el directorio backend/ al path para que los imports de app/ funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base

# Importar TODOS los modelos aquí para que Alembic los detecte en autogenerate
from app.modules.admin.models import (  # noqa: F401
    Rol, Usuario, Entidad, Dependencia, Canal,
    TipoRequerimiento, PlazoRespuesta, ConfiguracionSistema
)
from app.modules.geo.models import Departamento, Municipio  # noqa: F401
# Sprint 2
from app.modules.recepcion.models import Recepcion, AdjuntoRecepcion  # noqa: F401
# Sprint 3
from app.modules.remitente.models import Remitente, MetadatosRecepcion  # noqa: F401
# Sprint 4
from app.modules.radicado.models import Radicado  # noqa: F401
# Sprint 5
from app.modules.consulta.models import LogAuditoria  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
