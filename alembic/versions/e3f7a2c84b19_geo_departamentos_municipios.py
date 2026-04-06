"""geo_departamentos_municipios

Revision ID: e3f7a2c84b19
Revises: d0e596424db4
Create Date: 2026-04-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f7a2c84b19'
down_revision: Union[str, None] = 'd0e596424db4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'geo_departamentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_index('ix_geo_departamentos_id', 'geo_departamentos', ['id'], unique=False)

    op.create_table(
        'geo_municipios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('departamento_id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['departamento_id'], ['geo_departamentos.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_geo_municipios_id', 'geo_municipios', ['id'], unique=False)
    op.create_index('ix_geo_municipios_departamento_id', 'geo_municipios', ['departamento_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_geo_municipios_departamento_id', table_name='geo_municipios')
    op.drop_index('ix_geo_municipios_id', table_name='geo_municipios')
    op.drop_table('geo_municipios')
    op.drop_index('ix_geo_departamentos_id', table_name='geo_departamentos')
    op.drop_table('geo_departamentos')
