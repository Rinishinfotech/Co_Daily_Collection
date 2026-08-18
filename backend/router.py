from datetime import datetime, timedelta, timezone
import re
from uuid import uuid4

import imghdr

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pymongo import ReturnDocument
from starlette.responses import Response

from auth import hash_password, sanitize_user
from models import Collection, CollectionCreate, Employee, EmployeeCreate, EmployeePasswordReset, QuickVendorCreate, Vendor, VendorCreate
from storage import download_photo, upload_profile_photo


def build_router(db, current_user):
    router = APIRouter(prefix="/api")

    async def records(collection, query=None, limit=200, projection=None):
        fields = {"_id": 0}
        if projection:
            fields.update(projection)
        return await collection.find(query or {}, fields).sort("created_at", -1).to_list(limit)

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

    @router.post("/profile/photo")
    async def upload_own_photo(file: UploadFile = File(...), user: dict = Depends(current_user)):
        if user["role"] != "employee":
            raise HTTPException(status_code=403, detail="Only employee accounts can update profile photos")
        allowed_types = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
        image_kinds = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Upload a JPG, PNG, or WebP image")
        contents = await file.read()
        if not contents or len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Profile photos must be smaller than 5 MB")
        if imghdr.what(None, contents) != image_kinds[file.content_type]:
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid image")
        try:
            storage_path = await run_in_threadpool(upload_profile_photo, user["employee_id"], contents, allowed_types[file.content_type], file.content_type)
        except Exception as error:
            raise HTTPException(status_code=502, detail="Photo storage is temporarily unavailable") from error
        file_id = str(uuid4())
        old_photo_id = (await db.employees.find_one({"id": user["employee_id"]}, {"_id": 0, "photo_file_id": 1}) or {}).get("photo_file_id")
        if old_photo_id:
            await db.files.update_one({"id": old_photo_id}, {"$set": {"is_deleted": True}})
        file_record = {"id": file_id, "owner_employee_id": user["employee_id"], "storage_path": storage_path, "content_type": file.content_type, "size": len(contents), "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()}
        await db.files.insert_one(file_record)
        await db.employees.update_one({"id": user["employee_id"]}, {"$set": {"photo_file_id": file_id}})
        return {"photo_file_id": file_id}

    @router.get("/files/{file_id}")
    async def view_profile_photo(file_id: str, user: dict = Depends(current_user)):
        record = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Photo not found")
        if user["role"] != "admin" and record["owner_employee_id"] != user["employee_id"]:
            raise HTTPException(status_code=403, detail="You can only view your own profile photo")
        try:
            contents, content_type = await run_in_threadpool(download_photo, record["storage_path"])
        except Exception as error:
            raise HTTPException(status_code=502, detail="Photo storage is temporarily unavailable") from error
        return Response(content=contents, media_type=content_type, headers={"Cache-Control": "private, max-age=300"})

    @router.get("/vendors", response_model=list[Vendor])
    async def list_vendors(search: str = "", user: dict = Depends(current_user)):
        query = {"$or": [{"name": {"$regex": search, "$options": "i"}}, {"business_name": {"$regex": search, "$options": "i"}}]} if search else {}
        return await records(db.vendors, query)

    @router.post("/vendors/quick-add", response_model=Vendor)
    async def quick_add_vendor(payload: QuickVendorCreate, user: dict = Depends(current_user)):
        if user["role"] != "employee":
            raise HTTPException(status_code=403, detail="Quick vendor creation is available to field employees")
        name = " ".join(payload.name.split())
        existing = await db.vendors.find_one({"business_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}, {"_id": 0})
        if existing:
            return Vendor(**{**existing, "name": existing.get("name", name), "business_name": existing.get("business_name", name)}).model_dump()
        vendor = Vendor(
            name=name,
            business_name=name,
            phone="Pending update",
            address="Pending update",
            source="quick-add",
        ).model_dump()
        await db.vendors.insert_one(vendor.copy())
        return vendor

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

    @router.post("/employees/{employee_id}/reset-password")
    async def reset_employee_password(employee_id: str, payload: EmployeePasswordReset, user: dict = Depends(current_user)):
        admin_only(user)
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "name": 1})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        result = await db.users.update_one(
            {"id": employee_id, "role": "employee"},
            {"$set": {"password_hash": hash_password(payload.temporary_password), "must_change_password": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Employee sign-in account not found")
        return {"ok": True, "employee_name": employee["name"]}

    @router.delete("/employees/{employee_id}")
    async def remove_employee(employee_id: str, user: dict = Depends(current_user)):
        admin_only(user)
        employee = await db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "id": 1, "photo_file_id": 1},
        )
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        await db.employees.delete_one({"id": employee_id})
        await db.users.delete_one({"id": employee_id})
        await db.files.update_many({"owner_employee_id": employee_id}, {"$set": {"is_deleted": True}})
        return {"ok": True}

    @router.get("/employees/{employee_id}/activity")
    async def employee_activity(employee_id: str, user: dict = Depends(current_user)):
        admin_only(user)
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        collections = await records(
            db.collections,
            {"employee_id": employee_id},
            500,
            {"id": 1, "vendor_id": 1, "vendor_name": 1, "payment_mode": 1, "amount": 1, "created_at": 1},
        )
        today = datetime.now(timezone.utc).date().isoformat()
        today_collections = [item for item in collections if item["created_at"].startswith(today)]
        return {"employee": employee, "today_total": sum(item["amount"] for item in today_collections), "today_vendors": len(set(item.get("vendor_id") for item in today_collections if item.get("vendor_id"))), "collections": collections}

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

    @router.get("/dashboard")
    async def dashboard(employee_id: str | None = Query(default=None), user: dict = Depends(current_user)):
        scope_id = employee_scope(user, employee_id)
        today = datetime.now(timezone.utc).date().isoformat()
        month = today[:7]
        collection_query = {"employee_id": scope_id} if scope_id else {}
        all_collections = await records(
            db.collections,
            collection_query,
            1000,
            {"amount": 1, "created_at": 1, "vendor_id": 1},
        )
        today_collections = [item for item in all_collections if item["created_at"].startswith(today)]
        month_collections = [item for item in all_collections if item["created_at"].startswith(month)]
        trend = []
        for offset in range(6, -1, -1):
            date = (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
            trend.append({"date": date[5:], "amount": sum(item["amount"] for item in all_collections if item["created_at"].startswith(date))})
        return {"today_collection": sum(item["amount"] for item in today_collections), "monthly_collection": sum(item["amount"] for item in month_collections), "vendors_visited": len(set(item["vendor_id"] for item in today_collections if item.get("vendor_id"))), "active_vendors": await db.vendors.count_documents({"active": True}), "active_employees": await db.employees.count_documents({"active": True}), "trend": trend}

    return router