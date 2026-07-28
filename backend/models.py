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


class Vendor(VendorCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    active: bool = True


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=8, max_length=20)
    territory: str = Field(min_length=2, max_length=80)


class Employee(EmployeeCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    active: bool = True
    avatar: Optional[str] = None


class CollectionCreate(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str = Field(min_length=2, max_length=100)
    amount: float = Field(gt=0)
    payment_mode: PaymentMode
    remarks: str = Field(default="", max_length=240)
    employee_id: str
    employee_name: str


class Collection(CollectionCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    receipt_number: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=60)
    amount: float = Field(gt=0)
    remarks: str = Field(default="", max_length=240)
    employee_id: str
    employee_name: str
    date: Optional[str] = None


class Expense(ExpenseCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())