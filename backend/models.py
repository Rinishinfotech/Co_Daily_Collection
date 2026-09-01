from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


PaymentMode = Literal["Cash", "UPI", "Bank Transfer", "Cheque"]


class VendorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    business_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=8, max_length=20)
    address: str = Field(min_length=4, max_length=180)


class QuickVendorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class Vendor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    business_name: str
    phone: str = ""
    address: str = ""
    active: bool = True
    source: str = "admin"


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=20)
    territory: str = Field(min_length=2, max_length=80)
    address: str = Field(default="", max_length=180)
    temporary_password: str = Field(min_length=8, max_length=100)


class EmployeePasswordReset(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=100)


class Employee(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    phone: str
    territory: str
    address: str = ""
    active: bool = True
    avatar: Optional[str] = None
    photo_file_id: Optional[str] = None


class CollectionCreate(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str = Field(min_length=2, max_length=100)
    amount: float = Field(gt=0)
    payment_mode: PaymentMode
    remarks: str = Field(default="", max_length=240)


class Collection(CollectionCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    employee_id: str
    employee_name: str
    receipt_number: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

