from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
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
    email: Mapped[str] = mapped_column(String(180), unique=True)
    role: Mapped[str] = mapped_column(String(30), default="owner")
    tenant: Mapped[Tenant] = relationship(back_populates="users")

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
    mode: Mapped[str] = mapped_column(String(20), default="demo")  # demo | api
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
