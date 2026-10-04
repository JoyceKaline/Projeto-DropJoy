"""V6 security, audit and marketplace base.

Revision ID: 0002_v6
Revises: 0001_v5
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_v6"
down_revision: Union[str, None] = "0001_v5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table("password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])

    op.create_table("marketplace_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_account_id", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("configured_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "provider", "external_account_id", name="uq_marketplace_account"),
    )
    op.create_index("ix_marketplace_accounts_tenant_id", "marketplace_accounts", ["tenant_id"])
    op.create_index("ix_marketplace_accounts_provider", "marketplace_accounts", ["provider"])

    op.create_table("marketplace_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("marketplace_account_id", sa.Integer(), sa.ForeignKey("marketplace_accounts.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("external_listing_id", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "marketplace_account_id", "product_id", name="uq_tenant_marketplace_product"),
    )
    op.create_index("ix_marketplace_listings_tenant_id", "marketplace_listings", ["tenant_id"])
    op.create_index("ix_marketplace_listings_marketplace_account_id", "marketplace_listings", ["marketplace_account_id"])
    op.create_index("ix_marketplace_listings_product_id", "marketplace_listings", ["product_id"])

    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("marketplace_listings")
    op.drop_table("marketplace_accounts")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
