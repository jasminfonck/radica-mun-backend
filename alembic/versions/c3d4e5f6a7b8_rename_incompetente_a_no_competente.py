"""rename incompetente a no_competente

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        "UPDATE recepciones SET estado = 'no_competente' WHERE estado = 'incompetente'"
    )
    op.execute(
        "UPDATE log_auditoria SET descripcion = REPLACE(descripcion, 'incompetente', 'no_competente') "
        "WHERE descripcion LIKE '%incompetente%'"
    )

def downgrade() -> None:
    op.execute(
        "UPDATE recepciones SET estado = 'incompetente' WHERE estado = 'no_competente'"
    )
