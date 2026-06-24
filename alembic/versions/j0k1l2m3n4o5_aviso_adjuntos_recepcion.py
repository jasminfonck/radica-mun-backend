"""recepciones: campo aviso_adjuntos para alertas de adjuntos rechazados

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'j0k1l2m3n4o5'
down_revision = 'i9j0k1l2m3n4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('recepciones', sa.Column('aviso_adjuntos', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('recepciones', 'aviso_adjuntos')
