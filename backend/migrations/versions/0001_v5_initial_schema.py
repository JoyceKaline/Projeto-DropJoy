"""V5 initial schema with JWT-ready users and tenant authorization.

Revision ID: 0001_v5
Revises:
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_v5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("integration_type", sa.String(length=30), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_key", sa.String(length=160), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("sale_price", sa.Float(), nullable=False),
        sa.Column("competition_score", sa.Float(), nullable=False),
        sa.UniqueConstraint("external_key"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tenant_suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "supplier_id", name="uq_tenant_supplier"),
    )
    op.create_index("ix_tenant_suppliers_tenant_id", "tenant_suppliers", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_suppliers_supplier_id", "tenant_suppliers", ["supplier_id"], unique=False)

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("supplier_sku", sa.String(length=160), nullable=True),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("shipping_hours", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
    )
    op.create_index("ix_offers_product_id", "offers", ["product_id"], unique=False)
    op.create_index("ix_offers_supplier_id", "offers", ["supplier_id"], unique=False)

    op.create_table(
        "offer_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("offer_id", sa.Integer(), sa.ForeignKey("offers.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
    )
    op.create_index("ix_offer_history_offer_id", "offer_history", ["offer_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_offer_history_offer_id", table_name="offer_history")
    op.drop_table("offer_history")
    op.drop_index("ix_offers_supplier_id", table_name="offers")
    op.drop_index("ix_offers_product_id", table_name="offers")
    op.drop_table("offers")
    op.drop_index("ix_tenant_suppliers_supplier_id", table_name="tenant_suppliers")
    op.drop_index("ix_tenant_suppliers_tenant_id", table_name="tenant_suppliers")
    op.drop_table("tenant_suppliers")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
