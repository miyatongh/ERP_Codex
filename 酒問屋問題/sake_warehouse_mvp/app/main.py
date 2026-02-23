from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from . import db, models, schemas, services

app = FastAPI(title="Sake Warehouse MVP", version="0.1.0")


@app.on_event("startup")
def _startup():
    models.Base.metadata.create_all(bind=db.engine)


@app.post("/requests", response_model=schemas.RequestView, status_code=201)
def create_request(
    payload: schemas.CreateRequestInput,
    x_idempotency_key: Optional[str] = Header(default=None, alias="X-Idempotency-Key"),
    x_actor: str = Header(default="system", alias="X-Actor"),
    session: Session = Depends(db.get_db),
):
    req = services.create_request(session, payload, x_idempotency_key, x_actor)
    return schemas.RequestView(
        request_no=req.request_no,
        state=req.state,
        destination=req.destination,
        item_code=req.item_code,
        qty=req.qty,
        shortage_qty=req.shortage_qty,
    )


@app.post("/requests/{request_no}/validate", response_model=schemas.RequestView)
def validate_request(
    request_no: str,
    x_actor: str = Header(default="system", alias="X-Actor"),
    session: Session = Depends(db.get_db),
):
    req = services.validate_request(session, request_no, x_actor)
    return schemas.RequestView(
        request_no=req.request_no,
        state=req.state,
        destination=req.destination,
        item_code=req.item_code,
        qty=req.qty,
        shortage_qty=req.shortage_qty,
    )


@app.post("/requests/{request_no}/allocate", response_model=schemas.AllocationResult)
def allocate_request(
    request_no: str,
    x_idempotency_key: Optional[str] = Header(default=None, alias="X-Idempotency-Key"),
    x_actor: str = Header(default="system", alias="X-Actor"),
    session: Session = Depends(db.get_db),
):
    return services.allocate_request(session, request_no, x_idempotency_key, x_actor)


@app.get("/requests/{request_no}", response_model=schemas.RequestView)
def get_request(request_no: str, session: Session = Depends(db.get_db)):
    req = session.get(models.Request, request_no)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    return schemas.RequestView(
        request_no=req.request_no,
        state=req.state,
        destination=req.destination,
        item_code=req.item_code,
        qty=req.qty,
        shortage_qty=req.shortage_qty,
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
