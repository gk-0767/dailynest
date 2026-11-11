# DailyNest Python Backend (MVP starter)

A learning-oriented FastAPI backend based on the DailyNest Society Daily Needs Platform requirements.

## Included
- Customer/vendor/admin/delivery user records
- Vendor product catalogue
- Daily/weekly subscriptions
- Skip delivery with a before-10-PM rule
- Generate scheduled deliveries while excluding skipped dates
- Delivery status updates
- PostgreSQL + Docker Compose
- Jenkins pipeline for Python tests and Docker image build

## Run locally with Docker
```bash
docker compose up --build
```
Open:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Stop:
```bash
docker compose down
```
Remove local database data only if you intentionally want a clean reset:
```bash
docker compose down -v
```

## Example workflow
Use Swagger at `/docs` in this order:

1. `POST /api/users` create a vendor:
```json
{"full_name":"Fresh Dairy Vendor","phone":"9000000001","role":"VENDOR","society_name":"Green Heights"}
```
2. `POST /api/users` create a customer:
```json
{"full_name":"Anita Rao","phone":"9000000002","role":"CUSTOMER","society_name":"Green Heights","flat_number":"A-204"}
```
3. `POST /api/products` using the vendor ID:
```json
{"vendor_id":1,"name":"Fresh Milk","category":"Dairy","unit":"litre","price": 32.00}
```
You can change the sample price to your vendor price.
4. `POST /api/subscriptions` using customer and product IDs:
```json
{"customer_id":2,"product_id":1,"quantity":1,"frequency":"DAILY","start_date":"2026-11-10"}
```
5. `POST /api/subscriptions/1/skip?delivery_date=2026-11-11`
6. `POST /api/deliveries/generate?delivery_date=2026-11-11`
7. `GET /api/deliveries?delivery_date=2026-11-11`

The skipped subscription should not receive a delivery for that date.

## Run tests without Docker
Use a local PostgreSQL database and set `DATABASE_URL`, then:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Jenkins
The included Jenkinsfile assumes the Jenkins agent has Python 3, Docker CLI, and permission to access the Docker daemon. Configure a Pipeline job pointing to this Git repository. This pipeline tests and builds an image; it does not yet push to a registry or deploy to production.

## Important production gaps
This is a functional MVP foundation, not a production-ready commerce platform. Before real customer use, add:
- OTP authentication (Firebase or another provider), JWT/session authorization, role-based access control
- Razorpay payment gateway integration with signed webhook verification; never store card data
- Wallet ledger with immutable transactions and reconciliation (do not store only a mutable balance)
- Alembic database migrations, structured logs, metrics, tracing and alerting
- Society/vendor tenancy isolation, audit logs, rate limiting, backups and secrets management
- Delivery assignment rules, idempotency, retry handling and timezone-aware scheduling
- Privacy, security review, load testing and operational runbooks

## Why no Maven?
Maven is primarily a Java build tool. This backend is Python, so `pip` installs dependencies and `pytest` runs tests. Jenkins orchestrates the pipeline and Docker packages the service. If your team later provides a Java service, Maven can build that service separately.
