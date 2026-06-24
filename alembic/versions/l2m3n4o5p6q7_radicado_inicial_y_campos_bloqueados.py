"""radicado_inicial_y_campos_bloqueados: número asignado al recibir la recepción

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # radicados: dependencia_id y radicado_por_id ahora pueden ser NULL (stub pendiente)
    op.alter_column('radicados', 'dependencia_id', nullable=True)
    op.alter_column('radicados', 'radicado_por_id', nullable=True)
    # radicados: el estado por defecto pasa a 'pendiente'
    op.alter_column('radicados', 'estado',
                    server_default='pendiente',
                    existing_type=sa.String(20),
                    existing_nullable=False)
    # metadatos_recepcion: campos que el sistema llenó automáticamente y no deben editarse
    op.add_column('metadatos_recepcion',
                  sa.Column('campos_bloqueados', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('metadatos_recepcion', 'campos_bloqueados')
    op.alter_column('radicados', 'estado',
                    server_default='radicado',
                    existing_type=sa.String(20),
                    existing_nullable=False)
    op.alter_column('radicados', 'radicado_por_id', nullable=False)
    op.alter_column('radicados', 'dependencia_id', nullable=False)
