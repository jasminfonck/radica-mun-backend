"""configuracion_sistema: parametros de adjuntos (max_adjuntos, tamano, tipos)

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'i9j0k1l2m3n4'
down_revision = 'h8i9j0k1l2m3'
branch_labels = None
depends_on = None

_TIPOS_DEFAULT = (
    "application/pdf,"
    "image/jpeg,"
    "image/png,"
    "application/msword,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
    "application/vnd.ms-excel,"
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
    "text/plain"
)


def upgrade() -> None:
    op.add_column('configuracion_sistema', sa.Column(
        'max_adjuntos', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('configuracion_sistema', sa.Column(
        'max_tamano_adjunto_mb', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('configuracion_sistema', sa.Column(
        'tipos_archivo_permitidos', sa.Text(), nullable=False,
        server_default=_TIPOS_DEFAULT))

    # Quitar los server_default; el valor ya quedó persistido en filas existentes
    op.alter_column('configuracion_sistema', 'max_adjuntos',          server_default=None)
    op.alter_column('configuracion_sistema', 'max_tamano_adjunto_mb', server_default=None)
    op.alter_column('configuracion_sistema', 'tipos_archivo_permitidos', server_default=None)


def downgrade() -> None:
    op.drop_column('configuracion_sistema', 'tipos_archivo_permitidos')
    op.drop_column('configuracion_sistema', 'max_tamano_adjunto_mb')
    op.drop_column('configuracion_sistema', 'max_adjuntos')
