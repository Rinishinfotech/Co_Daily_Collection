from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pymongo import ReturnDocument

from models import Collection, CollectionCreate, Employee, EmployeeCreate, Expense, ExpenseCreate, Vendor, VendorCreate


def build_router(db):
    router = APIRouter(prefix="/api")

    async def records(collection, query=None, limit=200):
        return await collection.find(query or {}, {"_id": 0}).sort("created_at", -1).to_list(limit)

    @router.get("/health")
    async def health():
        return {"status": "ready"}

    @router.get("/vendors", response_model=list[Vendor])
    async def list_vendors(search: str = ""):
        query = {"$or": [{"name": {"$regex": search, "$options": "i"}}, {"business_name": {"$regex": search, "$options": "i"}}]} if search else {}
        return await records(db.vendors, query)

    @router.post("/vendors", response_model=Vendor)
    async def add_vendor(payload: VendorCreate):
        vendor = Vendor(**payload.model_dump()).model_dump()
        await db.vendors.insert_one(vendor.copy())
        return vendor

    @router.put("/vendors/{vendor_id}", response_model=Vendor)
    async def update_vendor(vendor_id: str, payload: VendorCreate):
        update = payload.model_dump()
        result = await db.vendors.find_one_and_update({"id": vendor_id}, {"$set": update}, return_document=ReturnDocument.AFTER, projection={"_id": 0})
        if not result:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return result

    @router.delete("/vendors/{vendor_id}")
    async def remove_vendor(vendor_id: str):
        result = await db.vendors.delete_one({"id": vendor_id})
        if not result.deleted_count:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return {"ok": True}

    @router.get("/employees", response_model=list[Employee])
    async def list_employees():
        return await records(db.employees)

    @router.post("/employees", response_model=Employee)
    async def add_employee(payload: EmployeeCreate):
        employee = Employee(**payload.model_dump()).model_dump()
        await db.employees.insert_one(employee.copy())
        return employee

    @router.put("/employees/{employee_id}", response_model=Employee)
    async def update_employee(employee_id: str, payload: EmployeeCreate):
        result = await db.employees.find_one_and_update({"id": employee_id}, {"$set": payload.model_dump()}, return_document=ReturnDocument.AFTER, projection={"_id": 0})
        if not result:
            raise HTTPException(status_code=404, detail="Employee not found")
        return result

    @router.get("/collections", response_model=list[Collection])
    async def list_collections(employee_id: str | None = None, payment_mode: str | None = None, search: str = ""):
        query = {}
        if employee_id:
            query["employee_id"] = employee_id
        if payment_mode:
            query["payment_mode"] = payment_mode
        if search:
            query["$or"] = [{"vendor_name": {"$regex": search, "$options": "i"}}, {"employee_name": {"$regex": search, "$options": "i"}}]
        return await records(db.collections, query)

    @router.post("/collections", response_model=Collection)
    async def add_collection(payload: CollectionCreate):
        now = datetime.now(timezone.utc)
        collection = Collection(**payload.model_dump(), receipt_number=f"LFC-{now.strftime('%y%m')}-{str(uuid4())[:5].upper()}", created_at=now.isoformat()).model_dump()
        await db.collections.insert_one(collection.copy())
        return collection

    @router.get("/expenses", response_model=list[Expense])
    async def list_expenses(employee_id: str | None = None):
        return await records(db.expenses, {"employee_id": employee_id} if employee_id else {})

    @router.post("/expenses", response_model=Expense)
    async def add_expense(payload: ExpenseCreate):
        now = datetime.now(timezone.utc)
        data = payload.model_dump()
        data["date"] = data.get("date") or now.date().isoformat()
        expense = Expense(**data, created_at=now.isoformat()).model_dump()
        await db.expenses.insert_one(expense.copy())
        return expense

    @router.get("/dashboard")
    async def dashboard(employee_id: str | None = Query(default=None)):
        today = datetime.now(timezone.utc).date().isoformat()
        month = today[:7]
        collection_query = {"employee_id": employee_id} if employee_id else {}
        expense_query = {"employee_id": employee_id} if employee_id else {}
        all_collections = await records(db.collections, collection_query, 1000)
        all_expenses = await records(db.expenses, expense_query, 1000)
        today_collections = [item for item in all_collections if item["created_at"].startswith(today)]
        today_expenses = [item for item in all_expenses if item["date"] == today]
        month_collections = [item for item in all_collections if item["created_at"].startswith(month)]
        trend = []
        for offset in range(6, -1, -1):
            date = (datetime.now(timezone.utc).date()).fromordinal(datetime.now(timezone.utc).date().toordinal() - offset).isoformat()
            trend.append({"date": date[5:], "amount": sum(item["amount"] for item in all_collections if item["created_at"].startswith(date))})
        return {"today_collection": sum(item["amount"] for item in today_collections), "monthly_collection": sum(item["amount"] for item in month_collections), "today_expenses": sum(item["amount"] for item in today_expenses), "vendors_visited": len(set(item["vendor_id"] for item in today_collections if item.get("vendor_id"))), "active_vendors": await db.vendors.count_documents({"active": True}), "active_employees": await db.employees.count_documents({"active": True}), "trend": trend}

    return router