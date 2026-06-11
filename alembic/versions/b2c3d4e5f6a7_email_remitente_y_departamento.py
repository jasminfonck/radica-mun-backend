"""email_remitente en recepciones y departamento en remitentes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recepciones', sa.Column('email_remitente', sa.String(length=200), nullable=True))
    op.add_column('remitentes', sa.Column('departamento', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('remitentes', 'departamento')
    op.drop_column('recepciones', 'email_remitente')
