from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db as app_db
from app.main import app
from app import models


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sake_warehouse.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    test_db = TestingSessionLocal()
    try:
        yield test_db
    finally:
        test_db.close()


app.dependency_overrides[app_db.get_db] = override_get_db
client = TestClient(app)


def setup_function():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        containers = [
            models.Container(container_no="C1001", arrived_at=datetime.fromisoformat("2026-02-20T08:00:00+09:00")),
            models.Container(container_no="C1002", arrived_at=datetime.fromisoformat("2026-02-20T09:00:00+09:00")),
            models.Container(container_no="C1003", arrived_at=datetime.fromisoformat("2026-02-20T10:00:00+09:00")),
        ]
        session.add_all(containers)
        session.add_all(
            [
                models.ContainerLine(container_no="C1001", item_code="SAKE-A", qty=40),
                models.ContainerLine(container_no="C1001", item_code="SAKE-C", qty=20),
                models.ContainerLine(container_no="C1002", item_code="SAKE-A", qty=30),
                models.ContainerLine(container_no="C1002", item_code="SAKE-B", qty=10),
                models.ContainerLine(container_no="C1003", item_code="SAKE-C", qty=25),
                models.ContainerLine(container_no="C1003", item_code="SAKE-B", qty=5),
            ]
        )
        session.commit()
    finally:
        session.close()


def _create_request(request_no: str, item_code: str, qty: int, destination: str = "TOKYO"):
    return client.post(
        "/requests",
        headers={"X-Idempotency-Key": f"create-{request_no}", "X-Actor": "tester"},
        json={
            "request_no": request_no,
            "requested_at": "2026-02-20T11:00:00+09:00",
            "destination": destination,
            "item_code": item_code,
            "qty": qty,
        },
    )


def _validate_request(request_no: str):
    return client.post(f"/requests/{request_no}/validate", headers={"X-Actor": "tester"})


def _allocate_request(request_no: str):
    return client.post(
        f"/requests/{request_no}/allocate",
        headers={"X-Idempotency-Key": f"alloc-{request_no}", "X-Actor": "tester"},
    )


def test_ac001_create_request():
    res = _create_request("R1001", "SAKE-A", 10)
    assert res.status_code == 201
    body = res.json()
    assert body["request_no"] == "R1001"
    assert body["state"] == "received"
    assert body["shortage_qty"] == 0


def test_ac002_validate_request():
    _create_request("R1002", "SAKE-A", 10)
    res = _validate_request("R1002")
    assert res.status_code == 200
    assert res.json()["state"] == "validated"


def test_ac003_allocate_full():
    _create_request("R1003", "SAKE-A", 50)
    _validate_request("R1003")
    res = _allocate_request("R1003")
    assert res.status_code == 200
    body = res.json()
    assert body["allocated_qty"] == 50
    assert body["shortage_qty"] == 0


def test_ac004_allocate_shortage():
    _create_request("R1004", "SAKE-B", 20, destination="OSAKA")
    _validate_request("R1004")
    res = _allocate_request("R1004")
    assert res.status_code == 200
    body = res.json()
    assert body["allocated_qty"] == 15
    assert body["shortage_qty"] == 5


def test_ac005_fifo_order():
    _create_request("R1005", "SAKE-C", 30)
    _validate_request("R1005")
    res = _allocate_request("R1005")
    assert res.status_code == 200
    picks = res.json()["picks"]
    assert picks[0]["container_no"] == "C1001"
    assert picks[0]["qty"] == 20
    assert picks[1]["container_no"] == "C1003"
    assert picks[1]["qty"] == 10


def test_ac006_issue_work_order():
    _create_request("R1006", "SAKE-A", 40)
    _validate_request("R1006")
    _allocate_request("R1006")
    res = client.post(
        "/requests/R1006/work-orders",
        headers={"X-Idempotency-Key": "workorder-R1006", "X-Actor": "tester"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["request_no"] == "R1006"
    assert len(body["picks"]) == 1
    assert body["picks"][0]["container_no"] == "C1001"

    req = client.get("/requests/R1006")
    assert req.status_code == 200
    assert req.json()["state"] == "instructed"
