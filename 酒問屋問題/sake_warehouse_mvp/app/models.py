from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Request(Base):
    __tablename__ = "requests"

    request_no: Mapped[str] = mapped_column(String(32), primary_key=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    shortage_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Container(Base):
    __tablename__ = "containers"

    container_no: Mapped[str] = mapped_column(String(32), primary_key=True)
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContainerLine(Base):
    __tablename__ = "container_lines"
    __table_args__ = (UniqueConstraint("container_no", "item_code", name="uq_container_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    container_no: Mapped[str] = mapped_column(ForeignKey("containers.container_no"), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_no: Mapped[str] = mapped_column(ForeignKey("requests.request_no"), nullable=False)
    container_no: Mapped[str] = mapped_column(ForeignKey("containers.container_no"), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)


class Shortage(Base):
    __tablename__ = "shortages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_no: Mapped[str] = mapped_column(ForeignKey("requests.request_no"), nullable=False)
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    shortage_qty: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    request_no: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    before_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", "scope", name="uq_idempo_scope"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_no: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
