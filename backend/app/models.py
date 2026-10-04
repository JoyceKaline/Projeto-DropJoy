from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    users: Mapped[list["User"]] = relationship(back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="member")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    tenant: Mapped[Tenant] = relationship(back_populates="users")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    integration_type: Mapped[str] = mapped_column(String(30), default="demo")
    reliability: Mapped[float] = mapped_column(Float, default=.8)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    offers: Mapped[list["Offer"]] = relationship(back_populates="supplier")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(100), default="Geral")
    sale_price: Mapped[float] = mapped_column(Float)
    competition_score: Mapped[float] = mapped_column(Float, default=.75)
    offers: Mapped[list["Offer"]] = relationship(back_populates="product")

class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier_sku: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cost: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer)
    shipping_hours: Mapped[int] = mapped_column(Integer, default=24)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    product: Mapped[Product] = relationship(back_populates="offers")
    supplier: Mapped[Supplier] = relationship(back_populates="offers")
    history: Mapped[list["OfferHistory"]] = relationship(back_populates="offer", cascade="all, delete-orphan")

class OfferHistory(Base):
    __tablename__ = "offer_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cost: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer)
    offer: Mapped[Offer] = relationship(back_populates="history")

class TenantSupplier(Base):
    __tablename__ = "tenant_suppliers"
    __table_args__ = (UniqueConstraint("tenant_id", "supplier_id", name="uq_tenant_supplier"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mode: Mapped[str] = mapped_column(String(20), default="demo")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class MarketplaceAccount(Base):
    __tablename__ = "marketplace_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "external_account_id", name="uq_marketplace_account"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_account_id: Mapped[str] = mapped_column(String(160))
    display_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="disconnected")
    configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (UniqueConstraint("tenant_id", "marketplace_account_id", "product_id", name="uq_tenant_marketplace_product"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    marketplace_account_id: Mapped[int] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    external_listing_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    price: Mapped[float] = mapped_column(Float)
    category_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    currency_id: Mapped[str] = mapped_column(String(10), default="BRL")
    listing_type_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    available_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pictures_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    stock_locations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_product_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    publication_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MarketplaceOAuthCredential(Base):
    __tablename__ = "marketplace_oauth_credentials"
    id: Mapped[int] = mapped_column(primary_key=True)
    marketplace_account_id: Mapped[int] = mapped_column(ForeignKey("marketplace_accounts.id"), unique=True, index=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String(30), default="bearer")
    scope: Mapped[str | None] = mapped_column(String(300), nullable=True)
    external_user_id: Mapped[str] = mapped_column(String(160), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class MarketplaceOAuthSession(Base):
    __tablename__ = "marketplace_oauth_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    marketplace_account_id: Mapped[int] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_verifier_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

