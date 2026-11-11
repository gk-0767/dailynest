from datetime import date, datetime, time, timedelta
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from . import models, schemas

app = FastAPI(
    title="DailyNest API",
    description="Society daily-needs subscriptions, vendors and delivery operations",
    version="0.1.0"
)

@app.on_event("startup")
def startup():
    # For learning/local MVP only. Use Alembic migrations in production.
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "healthy", "service": "dailynest-api"}

@app.post("/api/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    role = payload.role.upper()
    if role not in {"CUSTOMER", "VENDOR", "ADMIN", "DELIVERY"}:
        raise HTTPException(400, "Invalid role")
    if db.scalar(select(models.User).where(models.User.phone == payload.phone)):
        raise HTTPException(409, "Phone number already registered")
    user = models.User(**payload.model_dump(exclude={"role"}), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(role: str | None = None, db: Session = Depends(get_db)):
    query = select(models.User)
    if role:
        query = query.where(models.User.role == role.upper())
    return list(db.scalars(query.order_by(models.User.id.desc())).all())

@app.post("/api/products", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    vendor = db.get(models.User, payload.vendor_id)
    if not vendor or vendor.role != "VENDOR":
        raise HTTPException(400, "vendor_id must belong to a registered VENDOR")
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@app.get("/api/products", response_model=list[schemas.ProductOut])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    query = select(models.Product).where(models.Product.active.is_(True))
    if category:
        query = query.where(models.Product.category.ilike(f"%{category}%"))
    return list(db.scalars(query.order_by(models.Product.name)).all())

@app.post("/api/subscriptions", response_model=schemas.SubscriptionOut, status_code=201)
def create_subscription(payload: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    customer = db.get(models.User, payload.customer_id)
    product = db.get(models.Product, payload.product_id)
    if not customer or customer.role != "CUSTOMER":
        raise HTTPException(400, "customer_id must belong to a registered CUSTOMER")
    if not product or not product.active:
        raise HTTPException(404, "Active product not found")
    if payload.frequency.upper() not in {"DAILY", "WEEKLY"}:
        raise HTTPException(400, "frequency must be DAILY or WEEKLY")
    if payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(400, "end_date cannot be before start_date")
    subscription = models.Subscription(
        **payload.model_dump(exclude={"frequency"}),
        frequency=payload.frequency.upper()
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription

@app.get("/api/subscriptions", response_model=list[schemas.SubscriptionOut])
def list_subscriptions(customer_id: int | None = None, db: Session = Depends(get_db)):
    query = select(models.Subscription)
    if customer_id:
        query = query.where(models.Subscription.customer_id == customer_id)
    return list(db.scalars(query.order_by(models.Subscription.id.desc())).all())

@app.post("/api/subscriptions/{subscription_id}/skip")
def skip_delivery(
    subscription_id: int,
    delivery_date: date = Query(default_factory=lambda: date.today() + timedelta(days=1)),
    db: Session = Depends(get_db)
):
    subscription = db.get(models.Subscription, subscription_id)
    if not subscription or not subscription.active:
        raise HTTPException(404, "Active subscription not found")
    if delivery_date < date.today():
        raise HTTPException(400, "Cannot skip a past delivery")
    # Business rule from the requirement: pause/skip must be requested before 10 PM.
    # Server timezone must be configured to the society's local timezone in deployment.
    if datetime.now().time() >= time(22, 0):
        raise HTTPException(400, "Skip deadline passed. Requests must be made before 10 PM.")
    existing = db.scalar(select(models.DeliveryException).where(
        models.DeliveryException.subscription_id == subscription_id,
        models.DeliveryException.delivery_date == delivery_date
    ))
    if existing:
        return {"message": "Delivery already skipped", "exception_id": existing.id}
    exception = models.DeliveryException(
        subscription_id=subscription_id,
        delivery_date=delivery_date
    )
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return {"message": "Delivery skipped", "exception_id": exception.id, "delivery_date": delivery_date}

@app.post("/api/deliveries/generate")
def generate_daily_deliveries(delivery_date: date = Query(default_factory=date.today),
                              db: Session = Depends(get_db)):
    """Admin/scheduler operation: create deliveries for active subscriptions, excluding skips."""
    subscriptions = db.scalars(select(models.Subscription).where(
        models.Subscription.active.is_(True),
        models.Subscription.start_date <= delivery_date
    )).all()
    created = 0
    for sub in subscriptions:
        if sub.end_date and sub.end_date < delivery_date:
            continue
        if sub.frequency == "WEEKLY" and (delivery_date - sub.start_date).days % 7 != 0:
            continue
        skipped = db.scalar(select(models.DeliveryException).where(
            models.DeliveryException.subscription_id == sub.id,
            models.DeliveryException.delivery_date == delivery_date
        ))
        existing = db.scalar(select(models.Delivery).where(
            models.Delivery.subscription_id == sub.id,
            models.Delivery.delivery_date == delivery_date
        ))
        if not skipped and not existing:
            db.add(models.Delivery(subscription_id=sub.id, delivery_date=delivery_date))
            created += 1
    db.commit()
    return {"delivery_date": delivery_date, "created": created}

@app.get("/api/deliveries")
def list_deliveries(delivery_date: date | None = None, status: str | None = None,
                    db: Session = Depends(get_db)):
    query = select(models.Delivery)
    if delivery_date:
        query = query.where(models.Delivery.delivery_date == delivery_date)
    if status:
        query = query.where(models.Delivery.status == status.upper())
    rows = db.scalars(query.order_by(models.Delivery.delivery_date, models.Delivery.id)).all()
    return [{
        "id": row.id, "subscription_id": row.subscription_id,
        "delivery_date": row.delivery_date, "status": row.status,
        "delivery_partner_id": row.delivery_partner_id, "notes": row.notes
    } for row in rows]

@app.patch("/api/deliveries/{delivery_id}")
def update_delivery(delivery_id: int, payload: schemas.DeliveryStatusUpdate,
                    db: Session = Depends(get_db)):
    allowed = {"SCHEDULED", "ASSIGNED", "OUT_FOR_DELIVERY", "DELIVERED", "FAILED"}
    if payload.status.upper() not in allowed:
        raise HTTPException(400, f"status must be one of {sorted(allowed)}")
    delivery = db.get(models.Delivery, delivery_id)
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    delivery.status = payload.status.upper()
    delivery.notes = payload.notes
    db.commit()
    return {"message": "Delivery updated", "delivery_id": delivery.id, "status": delivery.status}
