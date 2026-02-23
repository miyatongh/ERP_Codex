from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from app.db import SessionLocal
from app import models


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main(path_str: str):
    path = Path(path_str)
    payload = json.loads(path.read_text(encoding="utf-8"))

    db = SessionLocal()
    try:
        db.query(models.ContainerLine).delete()
        db.query(models.Container).delete()
        db.query(models.Allocation).delete()
        db.query(models.Shortage).delete()
        db.query(models.Request).delete()
        db.commit()

        for c in payload["containers"]:
            db.add(models.Container(container_no=c["container_no"], arrived_at=parse_dt(c["arrived_at"])))
            for line in c["lines"]:
                db.add(
                    models.ContainerLine(
                        container_no=c["container_no"],
                        item_code=line["item_code"],
                        qty=line["qty"],
                    )
                )

        db.commit()
        print("Seeded containers from", path)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/seed_from_sample.py <path-to-サンプルデータ.json>")
    main(sys.argv[1])
