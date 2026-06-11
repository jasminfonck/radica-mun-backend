"""tipo_req plazo fk y dep codigo unique

Revision ID: a1b2c3d4e5f7
Revises: f1e2d3c4b5a6
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tipos_requerimiento',
        sa.Column('plazo_respuesta_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_tipo_req_plazo_respuesta',
        'tipos_requerimiento', 'plazos_respuesta',
        ['plazo_respuesta_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_tipo_req_plazo_respuesta', 'tipos_requerimiento', type_='foreignkey')
    op.drop_column('tipos_requerimiento', 'plazo_respuesta_id')
