from datetime import datetime, date as DateValue
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, Date, ForeignKey, Numeric, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    username: Mapped[str]=mapped_column(String(80), unique=True, index=True)
    email: Mapped[str|None]=mapped_column(String(254), nullable=True)
    full_name: Mapped[str]=mapped_column(String(160))
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(16))
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())

class PasswordResetToken(Base):
    __tablename__="password_reset_tokens"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())

class Supplier(Base):
    __tablename__="suppliers"
    id: Mapped[str]=mapped_column(String(24), primary_key=True)
    name: Mapped[str]=mapped_column(String(160), index=True)
    contact: Mapped[str|None]=mapped_column(String(120))
    phone: Mapped[str|None]=mapped_column(String(40))
    email: Mapped[str|None]=mapped_column(String(254))
    address: Mapped[str|None]=mapped_column(String(300))

class Customer(Base):
    __tablename__="customers"
    id: Mapped[str]=mapped_column(String(24), primary_key=True)
    name: Mapped[str]=mapped_column(String(160), index=True)
    phone: Mapped[str|None]=mapped_column(String(40))
    email: Mapped[str|None]=mapped_column(String(254))
    address: Mapped[str|None]=mapped_column(String(300))

class Part(Base):
    __tablename__="parts"
    id: Mapped[str]=mapped_column(String(24), primary_key=True)
    name: Mapped[str]=mapped_column(String(160), index=True)
    category: Mapped[str]=mapped_column(String(100), index=True)
    brand: Mapped[str]=mapped_column(String(100))
    models: Mapped[str]=mapped_column(String(500))
    qty: Mapped[int]=mapped_column(Integer, default=0)
    reorder: Mapped[int]=mapped_column(Integer, default=0)
    purchase_price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    selling_price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    supplier_id: Mapped[str|None]=mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))
    __table_args__=(CheckConstraint("qty >= 0"), CheckConstraint("reorder >= 0"))

class Purchase(Base):
    __tablename__="purchases"
    id: Mapped[str]=mapped_column(String(24), primary_key=True)
    date: Mapped[DateValue]=mapped_column(Date, default=DateValue.today)
    supplier_id: Mapped[str]=mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    supplier_name: Mapped[str]=mapped_column(String(160))
    total: Mapped[Decimal]=mapped_column(Numeric(14,2))
    created_by: Mapped[int|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    items: Mapped[list["PurchaseItem"]]=relationship(cascade="all, delete-orphan", lazy="selectin")

class PurchaseItem(Base):
    __tablename__="purchase_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    purchase_id: Mapped[str]=mapped_column(ForeignKey("purchases.id", ondelete="CASCADE"), index=True)
    part_id: Mapped[str]=mapped_column(ForeignKey("parts.id", ondelete="RESTRICT"))
    part_name: Mapped[str]=mapped_column(String(160))
    qty: Mapped[int]=mapped_column(Integer)
    unit_price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    __table_args__=(CheckConstraint("qty > 0"), CheckConstraint("unit_price >= 0"))

class Sale(Base):
    __tablename__="sales"
    id: Mapped[str]=mapped_column(String(24), primary_key=True)
    date: Mapped[DateValue]=mapped_column(Date, default=DateValue.today)
    customer_id: Mapped[str]=mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    customer_name: Mapped[str]=mapped_column(String(160))
    payment_mode: Mapped[str]=mapped_column(String(40))
    total: Mapped[Decimal]=mapped_column(Numeric(14,2))
    created_by: Mapped[int|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    items: Mapped[list["SaleItem"]]=relationship(cascade="all, delete-orphan", lazy="selectin")

class SaleItem(Base):
    __tablename__="sale_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    sale_id: Mapped[str]=mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    part_id: Mapped[str]=mapped_column(ForeignKey("parts.id", ondelete="RESTRICT"))
    part_name: Mapped[str]=mapped_column(String(160))
    qty: Mapped[int]=mapped_column(Integer)
    unit_price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    __table_args__=(CheckConstraint("qty > 0"), CheckConstraint("unit_price >= 0"))

class StoreProduct(Base):
    __tablename__="store_products"
    id: Mapped[str]=mapped_column(String(60), primary_key=True)
    name: Mapped[str]=mapped_column(String(180), index=True)
    category: Mapped[str]=mapped_column(String(100), index=True)
    brand: Mapped[str]=mapped_column(String(100), index=True)
    models: Mapped[str]=mapped_column(String(500), default="All models")
    description: Mapped[str]=mapped_column(String(800), default="")
    part_number: Mapped[str]=mapped_column(String(80), default="")
    price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    compare_at: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    stock: Mapped[int]=mapped_column(Integer, default=0)
    image: Mapped[str]=mapped_column(String(300), default="")
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__=(CheckConstraint("price >= 0"), CheckConstraint("stock >= 0"))

class StoreOrder(Base):
    __tablename__="store_orders"
    id: Mapped[str]=mapped_column(String(32), primary_key=True)
    customer_name: Mapped[str]=mapped_column(String(160))
    phone: Mapped[str]=mapped_column(String(30))
    email: Mapped[str|None]=mapped_column(String(254))
    address: Mapped[str]=mapped_column(String(500))
    city: Mapped[str]=mapped_column(String(100))
    state: Mapped[str]=mapped_column(String(100))
    pincode: Mapped[str]=mapped_column(String(12))
    payment_mode: Mapped[str]=mapped_column(String(32), default="Cash on Delivery")
    payment_status: Mapped[str]=mapped_column(String(32), default="Not required", server_default="Not required")
    status: Mapped[str]=mapped_column(String(32), default="Received")
    total: Mapped[Decimal]=mapped_column(Numeric(14,2))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["StoreOrderItem"]]=relationship(cascade="all, delete-orphan", lazy="selectin")

class StoreOrderItem(Base):
    __tablename__="store_order_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    order_id: Mapped[str]=mapped_column(ForeignKey("store_orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str]=mapped_column(String(60))
    product_name: Mapped[str]=mapped_column(String(180))
    part_number: Mapped[str]=mapped_column(String(80), default="")
    qty: Mapped[int]=mapped_column(Integer)
    unit_price: Mapped[Decimal]=mapped_column(Numeric(12,2))
    __table_args__=(CheckConstraint("qty > 0"), CheckConstraint("unit_price >= 0"))

class StoreLead(Base):
    __tablename__="store_leads"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(160))
    phone: Mapped[str]=mapped_column(String(30))
    vehicle: Mapped[str]=mapped_column(String(200))
    part_query: Mapped[str]=mapped_column(String(300))
    note: Mapped[str|None]=mapped_column(String(800))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
