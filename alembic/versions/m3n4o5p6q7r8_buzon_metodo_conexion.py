"""buzon_correo: agregar metodo_conexion (imap | graph)

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'm3n4o5p6q7r8'
down_revision = 'l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'buzon_correo',
        sa.Column('metodo_conexion', sa.String(10), nullable=False, server_default='imap'),
    )


def downgrade():
    op.drop_column('buzon_correo', 'metodo_conexion')
