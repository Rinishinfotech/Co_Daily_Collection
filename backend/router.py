from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import ReturnDocument

from auth import hash_password, sanitize_user
from models import Collection, CollectionCreate, Employee, EmployeeCreate, Expense, ExpenseCreate, Vendor, VendorCreate


def build_router(db, current_user):
    router = APIRouter(prefix="/api")

    async def records(collection, query=None, limit=200):
        return await collection.find(query or {}, {"_id": 0}).sort("created_at", -1).to_list(limit)

    def admin_only(user):
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access required")

    def employee_scope(user, requested_id=None):
        if user["role"] == "admin":
            return requested_id
        if requested_id and requested_id != user["employee_id"]:
            raise HTTPException(status_code=403, detail="You can only access your own activity")
        return user["employee_id"]

    @router.get("/health")
    async def health():
        return {"status": "ready"}

    @router.get("/profile")
    async def profile(user: dict = Depends(current_user)):
        employee = None
        if user["role"] == "employee":
            employee = await db.employees.find_one({"id": user["employee_id"]}, {"_id": 0})
        return {"account": sanitize_user(user), "employee": employee}

    @router.get("/vendors", response_model=list[Vendor])
    async def list_vendors(search: str = "", user: dict = Depends(current_user)):
        query = {"$or": [{"name": {"$regex": search, "$options": "i"}}, {"business_name": {"$regex": search, "$options": "i"}}]} if search else {}
        return await records(db.vendors, query)

    @router.post("/vendors", response_model=Vendor)
    async def add_vendor(payload: VendorCreate, user: dict = Depends(current_user)):
        admin_only(user)
        vendor = Vendor(**payload.model_dump()).model_dump()
        await db.vendors.insert_one(vendor.copy())
        return vendor

    @router.put("/vendors/{vendor_id}", response_model=Vendor)
    async def update_vendor(vendor_id: str, payload: VendorCreate, user: dict = Depends(current_user)):
        admin_only(user)
        update = payload.model_dump()
        result = await db.vendors.find_one_and_update({"id": vendor_id}, {"$set": update}, return_document=ReturnDocument.AFTER, projection={"_id": 0})
        if not result:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return result

    @router.delete("/vendors/{vendor_id}")
    async def remove_vendor(vendor_id: str, user: dict = Depends(current_user)):
        admin_only(user)
        result = await db.vendors.delete_one({"id": vendor_id})
        if not result.deleted_count:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return {"ok": True}

    @router.get("/employees", response_model=list[Employee])
    async def list_employees(user: dict = Depends(current_user)):
        admin_only(user)
        return await records(db.employees)

    @router.post("/employees", response_model=Employee)
    async def add_employee(payload: EmployeeCreate, user: dict = Depends(current_user)):
        admin_only(user)
        if await db.users.find_one({"phone": payload.phone.strip()}):
            raise HTTPException(status_code=400, detail="This phone number already has an account")
        employee = Employee(name=payload.name, phone=payload.phone.strip(), territory=payload.territory).model_dump()
        account = {"id": employee["id"], "name": employee["name"], "phone": employee["phone"], "role": "employee", "employee_id": employee["id"], "active": True, "must_change_password": True, "password_hash": hash_password(payload.temporary_password), "created_at": datetime.now(timezone.utc).isoformat()}
        await db.employees.insert_one(employee.copy())
        await db.users.insert_one(account)
        return employee

    @router.put("/employees/{employee_id}", response_model=Employee)
    async def update_employee(employee_id: str, payload: EmployeeCreate, user: dict = Depends(current_user)):
        admin_only(user)
        result = await db.employees.find_one_and_update({"id": employee_id}, {"$set": {"name": payload.name, "phone": payload.phone.strip(), "territory": payload.territory}}, return_document=ReturnDocument.AFTER, projection={"_id": 0})
        if not result:
            raise HTTPException(status_code=404, detail="Employee not found")
        await db.users.update_one({"id": employee_id}, {"$set": {"name": payload.name, "phone": payload.phone.strip(), "password_hash": hash_password(payload.temporary_password), "must_change_password": True}})
        return result

    @router.get("/employees/{employee_id}/activity")
    async def employee_activity(employee_id: str, user: dict = Depends(current_user)):
        admin_only(user)
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        collections = await records(db.collections, {"employee_id": employee_id}, 500)
        expenses = await records(db.expenses, {"employee_id": employee_id}, 500)
        today = datetime.now(timezone.utc).date().isoformat()
        today_collections = [item for item in collections if item["created_at"].startswith(today)]
        return {"employee": employee, "today_total": sum(item["amount"] for item in today_collections), "today_vendors": len(set(item.get("vendor_id") for item in today_collections if item.get("vendor_id"))), "collections": collections, "expenses": expenses}

    @router.get("/collections", response_model=list[Collection])
    async def list_collections(employee_id: str | None = None, payment_mode: str | None = None, search: str = "", user: dict = Depends(current_user)):
        scope_id = employee_scope(user, employee_id)
        query = {"employee_id": scope_id} if scope_id else {}
        if payment_mode:
            query["payment_mode"] = payment_mode
        if search:
            query["$or"] = [{"vendor_name": {"$regex": search, "$options": "i"}}, {"employee_name": {"$regex": search, "$options": "i"}}]
        return await records(db.collections, query)

    @router.post("/collections", response_model=Collection)
    async def add_collection(payload: CollectionCreate, user: dict = Depends(current_user)):
        if user["role"] != "employee":
            raise HTTPException(status_code=403, detail="Collections are recorded by field employees")
        now = datetime.now(timezone.utc)
        collection = Collection(**payload.model_dump(), employee_id=user["employee_id"], employee_name=user["name"], receipt_number=f"LFC-{now.strftime('%y%m')}-{str(uuid4())[:5].upper()}", created_at=now.isoformat()).model_dump()
        await db.collections.insert_one(collection.copy())
        return collection

    @router.get("/expenses", response_model=list[Expense])
    async def list_expenses(employee_id: str | None = None, user: dict = Depends(current_user)):
        scope_id = employee_scope(user, employee_id)
        return await records(db.expenses, {"employee_id": scope_id} if scope_id else {})

    @router.post("/expenses", response_model=Expense)
    async def add_expense(payload: ExpenseCreate, user: dict = Depends(current_user)):
        if user["role"] != "employee":
            raise HTTPException(status_code=403, detail="Expenses are recorded by field employees")
        now = datetime.now(timezone.utc)
        data = payload.model_dump()
        data["date"] = data.get("date") or now.date().isoformat()
        expense = Expense(**data, employee_id=user["employee_id"], employee_name=user["name"], created_at=now.isoformat()).model_dump()
        await db.expenses.insert_one(expense.copy())
        return expense

    @router.get("/dashboard")
    async def dashboard(employee_id: str | None = Query(default=None), user: dict = Depends(current_user)):
        scope_id = employee_scope(user, employee_id)
        today = datetime.now(timezone.utc).date().isoformat()
        month = today[:7]
        collection_query = {"employee_id": scope_id} if scope_id else {}
        expense_query = {"employee_id": scope_id} if scope_id else {}
        all_collections = await records(db.collections, collection_query, 1000)
        all_expenses = await records(db.expenses, expense_query, 1000)
        today_collections = [item for item in all_collections if item["created_at"].startswith(today)]
        today_expenses = [item for item in all_expenses if item["date"] == today]
        month_collections = [item for item in all_collections if item["created_at"].startswith(month)]
        trend = []
        for offset in range(6, -1, -1):
            date = (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
            trend.append({"date": date[5:], "amount": sum(item["amount"] for item in all_collections if item["created_at"].startswith(date))})
        return {"today_collection": sum(item["amount"] for item in today_collections), "monthly_collection": sum(item["amount"] for item in month_collections), "today_expenses": sum(item["amount"] for item in today_expenses), "vendors_visited": len(set(item["vendor_id"] for item in today_collections if item.get("vendor_id"))), "active_vendors": await db.vendors.count_documents({"active": True}), "active_employees": await db.employees.count_documents({"active": True}), "trend": trend}

    return router