"""Mercado Livre User Products listing fields.

Revision ID: 0004_meli_user_products
Revises: 0003_meli_oauth
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_meli_user_products"
down_revision: Union[str, None] = "0003_meli_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("marketplace_listings", sa.Column("category_id", sa.String(length=40), nullable=True))
    op.add_column("marketplace_listings", sa.Column("family_name", sa.String(length=180), nullable=True))
    op.add_column("marketplace_listings", sa.Column("condition", sa.String(length=30), nullable=True))
    op.add_column(
        "marketplace_listings",
        sa.Column("currency_id", sa.String(length=10), nullable=False, server_default="BRL"),
    )
    op.add_column("marketplace_listings", sa.Column("listing_type_id", sa.String(length=40), nullable=True))
    op.add_column("marketplace_listings", sa.Column("available_quantity", sa.Integer(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("pictures_json", sa.Text(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("attributes_json", sa.Text(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("stock_locations_json", sa.Text(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("user_product_id", sa.String(length=160), nullable=True))
    op.add_column("marketplace_listings", sa.Column("publication_error", sa.Text(), nullable=True))


def downgrade() -> None:
    for column in (
        "publication_error",
        "user_product_id",
        "attributes_json",
        "stock_locations_json",
        "pictures_json",
        "available_quantity",
        "listing_type_id",
        "currency_id",
        "condition",
        "family_name",
        "category_id",
    ):
        op.drop_column("marketplace_listings", column)

