"""buzon_correo

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'buzon_correo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canal_id', sa.Integer(), nullable=False),
        sa.Column('proveedor', sa.String(length=20), nullable=False),
        sa.Column('correo', sa.String(length=150), nullable=False),
        sa.Column('password_app_enc', sa.Text(), nullable=False),
        sa.Column('servidor_imap', sa.String(length=100), nullable=False),
        sa.Column('puerto', sa.Integer(), nullable=False, server_default='993'),
        sa.Column('intervalo_minutos', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_adjuntos', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_tamano_adjunto_mb', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ultimo_polling', sa.DateTime(), nullable=True),
        sa.Column('estado_conexion', sa.String(length=20), nullable=False, server_default='sin_probar'),
        sa.Column('ultimo_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['canal_id'], ['canales.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canal_id'),
    )
    op.create_index(op.f('ix_buzon_correo_id'), 'buzon_correo', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_buzon_correo_id'), table_name='buzon_correo')
    op.drop_table('buzon_correo')
