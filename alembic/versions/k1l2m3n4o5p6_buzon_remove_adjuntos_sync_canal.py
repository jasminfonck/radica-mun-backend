"""buzon_correo: eliminar max_adjuntos y max_tamano_adjunto_mb (ahora vienen de configuracion_sistema)

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = 'j0k1l2m3n4o5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('buzon_correo', 'max_adjuntos')
    op.drop_column('buzon_correo', 'max_tamano_adjunto_mb')


def downgrade() -> None:
    op.add_column('buzon_correo', sa.Column(
        'max_tamano_adjunto_mb', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('buzon_correo', sa.Column(
        'max_adjuntos', sa.Integer(), nullable=False, server_default='5'))
    op.alter_column('buzon_correo', 'max_adjuntos',          server_default=None)
    op.alter_column('buzon_correo', 'max_tamano_adjunto_mb', server_default=None)
