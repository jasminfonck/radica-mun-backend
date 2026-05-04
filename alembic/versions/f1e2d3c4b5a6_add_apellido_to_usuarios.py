"""add apellido to usuarios

Revision ID: f1e2d3c4b5a6
Revises: e3f7a2c84b19
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = 'e3f7a2c84b19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('apellido', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'apellido')
