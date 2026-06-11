"""rename bitacoras: log_auditoria->bitacora_operativa, entidad->modulo

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa

revision = 'g7h8i9j0k1l2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── bitacora_operativa (antes log_auditoria) ──────────────────────────────
    op.rename_table('log_auditoria', 'bitacora_operativa')
    op.alter_column('bitacora_operativa', 'entidad',    new_column_name='modulo')
    op.alter_column('bitacora_operativa', 'entidad_id', new_column_name='modulo_id')

    # ── bitacora_auditoria (admin) ────────────────────────────────────────────
    op.alter_column('bitacora_auditoria', 'entidad',    new_column_name='modulo')
    op.alter_column('bitacora_auditoria', 'entidad_id', new_column_name='modulo_id')


def downgrade() -> None:
    op.alter_column('bitacora_auditoria', 'modulo',    new_column_name='entidad')
    op.alter_column('bitacora_auditoria', 'modulo_id', new_column_name='entidad_id')

    op.alter_column('bitacora_operativa', 'modulo',    new_column_name='entidad')
    op.alter_column('bitacora_operativa', 'modulo_id', new_column_name='entidad_id')
    op.rename_table('bitacora_operativa', 'log_auditoria')
