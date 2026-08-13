from datetime import datetime, timedelta, timezone

from auth import hash_password


EMPLOYEES = [
    {"id": "emp-raj", "name": "Raj Mehta", "phone": "+91 98765 42100", "territory": "Central Market", "active": True, "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=160&q=80"},
    {"id": "emp-ananya", "name": "Ananya Shah", "phone": "+91 98765 42101", "territory": "Riverside", "active": True, "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=160&q=80"},
    {"id": "emp-vikram", "name": "Vikram Rao", "phone": "+91 98765 42102", "territory": "Industrial Zone", "active": True, "avatar": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=160&q=80"},
]

VENDORS = [
    {"id": "ven-urban", "name": "Nikhil Arora", "business_name": "Urban Grocers", "phone": "+91 98765 31001", "address": "18 Market Road, Central", "active": True},
    {"id": "ven-sunrise", "name": "Meera Iyer", "business_name": "Sunrise Pharma", "phone": "+91 98765 31002", "address": "9 Lake View, Riverside", "active": True},
    {"id": "ven-corner", "name": "Sameer Khan", "business_name": "Corner & Co.", "phone": "+91 98765 31003", "address": "44 Station Lane, Central", "active": True},
    {"id": "ven-harvest", "name": "Priya Nair", "business_name": "Harvest Foods", "phone": "+91 98765 31004", "address": "2 Garden Street, East", "active": True},
    {"id": "ven-works", "name": "Arjun Verma", "business_name": "Apex Works", "phone": "+91 98765 31005", "address": "81 Industrial Estate", "active": True},
]


def sample_collections():
    now = datetime.now(timezone.utc)
    values = [
        ("ven-urban", "Nikhil Arora", "emp-raj", "Raj Mehta", 12500, "UPI", "Weekly settlement", 1),
        ("ven-sunrise", "Meera Iyer", "emp-raj", "Raj Mehta", 8400, "Cash", "Invoice #231 settled", 3),
        ("ven-corner", "Sameer Khan", "emp-ananya", "Ananya Shah", 15750, "Bank Transfer", "Payment received", 5),
        ("ven-harvest", "Priya Nair", "emp-ananya", "Ananya Shah", 6800, "UPI", "", 8),
        ("ven-works", "Arjun Verma", "emp-vikram", "Vikram Rao", 22100, "Cheque", "Cheque #8921", 24),
        ("ven-urban", "Nikhil Arora", "emp-vikram", "Vikram Rao", 9400, "Cash", "Past collection", 36),
    ]
    return [{"id": f"col-{index + 1}", "vendor_id": vendor_id, "vendor_name": vendor_name, "employee_id": employee_id, "employee_name": employee_name, "amount": amount, "payment_mode": mode, "remarks": remarks, "receipt_number": f"LFC-{now.strftime('%y%m')}-{1001 + index}", "created_at": (now - timedelta(hours=hours)).isoformat()} for index, (vendor_id, vendor_name, employee_id, employee_name, amount, mode, remarks, hours) in enumerate(values)]


async def seed_database(db):
    if await db.vendors.count_documents({}) == 0:
        await db.vendors.insert_many(VENDORS)
        await db.employees.insert_many(EMPLOYEES)
        await db.collections.insert_many(sample_collections())
    admin = await db.users.find_one({"phone": "9999999999"})
    if not admin:
        await db.users.insert_one({"id": "admin-root", "name": "Co. Daily Collection Admin", "phone": "9999999999", "role": "admin", "active": True, "must_change_password": False, "password_hash": hash_password("Admin@123"), "created_at": datetime.now(timezone.utc).isoformat()})
    else:
        await db.users.update_one({"id": "admin-root"}, {"$set": {"name": "Co. Daily Collection Admin"}})
    for employee in EMPLOYEES:
        existing = await db.users.find_one({"id": employee["id"]})
        if not existing:
            await db.users.insert_one({"id": employee["id"], "name": employee["name"], "phone": employee["phone"], "role": "employee", "employee_id": employee["id"], "active": True, "must_change_password": True, "password_hash": hash_password("Welcome@123"), "created_at": datetime.now(timezone.utc).isoformat()})