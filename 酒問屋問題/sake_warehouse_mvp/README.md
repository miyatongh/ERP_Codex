# Sake Warehouse MVP (Stack A)

Python + FastAPI + PostgreSQL の最小実装雛形です。

## Scope (Sprint 1)
- `POST /requests`
- `POST /requests/{requestNo}/validate`
- `POST /requests/{requestNo}/allocate`
- `GET /requests/{requestNo}`

## Setup

1. Python 3.11+
2. PostgreSQL 15+
3. 依存をインストール

```bash
cd 酒問屋問題/sake_warehouse_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. 環境変数を設定

```bash
cp .env.example .env
# DATABASE_URL を必要に応じて変更
```

5. DB初期化 + サンプルデータ投入

```bash
python scripts/init_db.py
python scripts/seed_from_sample.py ../サンプルデータ.json
```

6. 起動

```bash
uvicorn app.main:app --reload
```

## Notes
- `X-Idempotency-Key` は `POST /requests` と `POST /requests/{requestNo}/allocate` で利用可能。
- 今回は実装着手用の雛形。`work-orders` と `complete` は次スプリントで追加。
