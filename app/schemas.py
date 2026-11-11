from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    role: str = "CUSTOMER"
    society_name: str | None = None
    flat_number: str | None = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    phone: str
    role: str
    society_name: str | None
    flat_number: str | None
    active: bool

class ProductCreate(BaseModel):
    vendor_id: int
    name: str
    category: str
    unit: str = "piece"
    price: float = Field(gt=0)

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_id: int
    name: str
    category: str
    unit: str
    price: float
    active: bool

class SubscriptionCreate(BaseModel):
    customer_id: int
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)
    frequency: str = "DAILY"
    start_date: date
    end_date: date | None = None

class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    product_id: int
    quantity: int
    frequency: str
    start_date: date
    end_date: date | None
    active: bool

class DeliveryStatusUpdate(BaseModel):
    status: str
    notes: str | None = None
