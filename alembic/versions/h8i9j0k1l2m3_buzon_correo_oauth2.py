"""buzon_correo: tipo_cuenta, auth_type y campos OAuth2

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'h8i9j0k1l2m3'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columnas de clasificación (requeridas, con default para filas existentes)
    op.add_column('buzon_correo', sa.Column(
        'tipo_cuenta', sa.String(length=20), nullable=False, server_default='personal'))
    op.add_column('buzon_correo', sa.Column(
        'auth_type', sa.String(length=20), nullable=False, server_default='password_app'))

    # password_app_enc pasa a ser nullable (OAuth2 no la usa)
    op.alter_column('buzon_correo', 'password_app_enc', nullable=True)

    # Campos OAuth2
    op.add_column('buzon_correo', sa.Column('oauth_client_id',        sa.String(length=200), nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_client_secret_enc', sa.Text(),             nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_tenant_id',         sa.String(length=200), nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_access_token_enc',  sa.Text(),             nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_refresh_token_enc', sa.Text(),             nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_token_expiry',      sa.DateTime(),         nullable=True))
    op.add_column('buzon_correo', sa.Column('oauth_state',             sa.String(length=100), nullable=True))

    # Eliminar el server_default una vez aplicado (la columna queda NOT NULL sin default)
    op.alter_column('buzon_correo', 'tipo_cuenta', server_default=None)
    op.alter_column('buzon_correo', 'auth_type',   server_default=None)


def downgrade() -> None:
    op.drop_column('buzon_correo', 'oauth_state')
    op.drop_column('buzon_correo', 'oauth_token_expiry')
    op.drop_column('buzon_correo', 'oauth_refresh_token_enc')
    op.drop_column('buzon_correo', 'oauth_access_token_enc')
    op.drop_column('buzon_correo', 'oauth_tenant_id')
    op.drop_column('buzon_correo', 'oauth_client_secret_enc')
    op.drop_column('buzon_correo', 'oauth_client_id')

    op.alter_column('buzon_correo', 'password_app_enc', nullable=False)

    op.drop_column('buzon_correo', 'auth_type')
    op.drop_column('buzon_correo', 'tipo_cuenta')
