"""Mercado Livre OAuth encrypted credentials and sessions.

Revision ID: 0003_meli_oauth
Revises: 0002_v6
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_meli_oauth"
down_revision: Union[str, None] = "0002_v6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "marketplace_oauth_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marketplace_account_id", sa.Integer(), sa.ForeignKey("marketplace_accounts.id"), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=30), nullable=False),
        sa.Column("scope", sa.String(length=300), nullable=True),
        sa.Column("external_user_id", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("marketplace_account_id"),
    )
    op.create_index("ix_marketplace_oauth_credentials_marketplace_account_id", "marketplace_oauth_credentials", ["marketplace_account_id"], unique=True)
    op.create_index("ix_marketplace_oauth_credentials_external_user_id", "marketplace_oauth_credentials", ["external_user_id"])
    op.create_index("ix_marketplace_oauth_credentials_expires_at", "marketplace_oauth_credentials", ["expires_at"])

    op.create_table(
        "marketplace_oauth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marketplace_account_id", sa.Integer(), sa.ForeignKey("marketplace_accounts.id"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("code_verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index("ix_marketplace_oauth_sessions_marketplace_account_id", "marketplace_oauth_sessions", ["marketplace_account_id"])
    op.create_index("ix_marketplace_oauth_sessions_tenant_id", "marketplace_oauth_sessions", ["tenant_id"])
    op.create_index("ix_marketplace_oauth_sessions_user_id", "marketplace_oauth_sessions", ["user_id"])
    op.create_index("ix_marketplace_oauth_sessions_provider", "marketplace_oauth_sessions", ["provider"])
    op.create_index("ix_marketplace_oauth_sessions_state_hash", "marketplace_oauth_sessions", ["state_hash"], unique=True)
    op.create_index("ix_marketplace_oauth_sessions_expires_at", "marketplace_oauth_sessions", ["expires_at"])

def downgrade() -> None:
    op.drop_table("marketplace_oauth_sessions")
    op.drop_table("marketplace_oauth_credentials")
