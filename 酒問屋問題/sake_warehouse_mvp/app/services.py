from __future__ import annotations

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


def _audit(
    db: Session,
    actor: str,
    event_type: str,
    request_no: str | None,
    before_state: str | None,
    after_state: str | None,
    reason_code: str | None = None,
):
    db.add(
        models.AuditEvent(
            actor=actor,
            event_type=event_type,
            request_no=request_no,
            before_state=before_state,
            after_state=after_state,
            reason_code=reason_code,
        )
    )


def _reserve_idempotency(db: Session, key: str | None, scope: str, request_no: str | None = None) -> bool:
    if not key:
        return True
    exists = db.execute(
        select(models.IdempotencyKey).where(models.IdempotencyKey.key == key, models.IdempotencyKey.scope == scope)
    ).scalar_one_or_none()
    if exists:
        return False
    db.add(models.IdempotencyKey(key=key, scope=scope, request_no=request_no))
    return True


def create_request(db: Session, payload: schemas.CreateRequestInput, idempotency_key: str | None, actor: str) -> models.Request:
    if not _reserve_idempotency(db, idempotency_key, "create_request", payload.request_no):
        existing = db.get(models.Request, payload.request_no)
        if existing:
            return existing

    if db.get(models.Request, payload.request_no):
        raise HTTPException(status_code=409, detail="request_no already exists")

    req = models.Request(
        request_no=payload.request_no,
        requested_at=payload.requested_at,
        destination=payload.destination,
        item_code=payload.item_code,
        qty=payload.qty,
        shortage_qty=0,
        state="received",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(req)
    _audit(db, actor, "request.created", req.request_no, None, "received")
    db.commit()
    db.refresh(req)
    return req


def validate_request(db: Session, request_no: str, actor: str) -> models.Request:
    req = db.get(models.Request, request_no)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    if req.state not in {"received", "validated"}:
        raise HTTPException(status_code=409, detail="invalid state transition")

    before = req.state
    req.state = "validated"
    req.updated_at = datetime.utcnow()
    _audit(db, actor, "request.validated", req.request_no, before, req.state)
    db.commit()
    db.refresh(req)
    return req


def allocate_request(db: Session, request_no: str, idempotency_key: str | None, actor: str) -> schemas.AllocationResult:
    req = db.get(models.Request, request_no)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    if req.state not in {"validated", "allocated"}:
        raise HTTPException(status_code=409, detail="invalid state transition")

    if not _reserve_idempotency(db, idempotency_key, "allocate_request", request_no):
        lines = db.execute(select(models.Allocation).where(models.Allocation.request_no == request_no)).scalars().all()
        allocated = sum(x.qty for x in lines)
        return schemas.AllocationResult(
            request_no=request_no,
            allocated_qty=allocated,
            shortage_qty=max(req.qty - allocated, 0),
            picks=[schemas.AllocationLine(container_no=x.container_no, item_code=x.item_code, qty=x.qty) for x in lines],
        )

    before = req.state
    # Re-allocate from scratch for deterministic behavior.
    db.query(models.Allocation).filter(models.Allocation.request_no == request_no).delete()
    db.query(models.Shortage).filter(models.Shortage.request_no == request_no).delete()

    remaining = req.qty
    picks: list[models.Allocation] = []

    rows = db.execute(
        select(models.ContainerLine, models.Container)
        .join(models.Container, models.Container.container_no == models.ContainerLine.container_no)
        .where(models.ContainerLine.item_code == req.item_code, models.ContainerLine.qty > 0)
        .order_by(models.Container.arrived_at.asc(), models.Container.container_no.asc())
    ).all()

    for line, _container in rows:
        if remaining <= 0:
            break
        take = min(line.qty, remaining)
        if take <= 0:
            continue
        line.qty -= take
        remaining -= take
        alloc = models.Allocation(
            request_no=req.request_no,
            container_no=line.container_no,
            item_code=req.item_code,
            qty=take,
        )
        db.add(alloc)
        picks.append(alloc)

    req.shortage_qty = max(remaining, 0)
    req.state = "allocated"
    req.updated_at = datetime.utcnow()

    if req.shortage_qty > 0:
        db.add(
            models.Shortage(
                request_no=req.request_no,
                destination=req.destination,
                item_code=req.item_code,
                shortage_qty=req.shortage_qty,
            )
        )

    _audit(db, actor, "request.allocated", req.request_no, before, req.state)
    db.commit()

    result_lines = [
        schemas.AllocationLine(container_no=x.container_no, item_code=x.item_code, qty=x.qty)
        for x in db.execute(select(models.Allocation).where(models.Allocation.request_no == req.request_no)).scalars().all()
    ]
    return schemas.AllocationResult(
        request_no=req.request_no,
        allocated_qty=sum(x.qty for x in result_lines),
        shortage_qty=req.shortage_qty,
        picks=result_lines,
    )
