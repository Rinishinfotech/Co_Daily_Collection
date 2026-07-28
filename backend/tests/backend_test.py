"""Backend API tests for LedgerFlow Collections."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fieldpay-manager-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def seed(client):
    emp = client.get(f"{API}/employees").json()
    ven = client.get(f"{API}/vendors").json()
    return {"employee": emp[0], "vendor": ven[0]}


# --- Health ---
def test_health(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


# --- Directory ---
def test_list_vendors(client):
    r = client.get(f"{API}/vendors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) > 0


def test_list_employees(client):
    r = client.get(f"{API}/employees")
    assert r.status_code == 200
    assert len(r.json()) > 0


# --- Dashboard ---
def test_dashboard_admin(client):
    r = client.get(f"{API}/dashboard")
    assert r.status_code == 200
    d = r.json()
    for k in ["today_collection", "monthly_collection", "today_expenses", "vendors_visited", "active_vendors", "active_employees", "trend"]:
        assert k in d
    assert isinstance(d["trend"], list) and len(d["trend"]) == 7


def test_dashboard_employee_scoped(client, seed):
    r = client.get(f"{API}/dashboard", params={"employee_id": seed["employee"]["id"]})
    assert r.status_code == 200


# --- Collections CRUD ---
def test_create_collection_and_persist(client, seed):
    payload = {
        "vendor_id": seed["vendor"]["id"],
        "vendor_name": f"TEST_{seed['vendor']['name']}",
        "amount": 1500.5,
        "payment_mode": "UPI",
        "remarks": "TEST_remarks",
        "employee_id": seed["employee"]["id"],
        "employee_name": seed["employee"]["name"],
    }
    r = client.post(f"{API}/collections", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["amount"] == 1500.5
    assert data["payment_mode"] == "UPI"
    assert data["receipt_number"].startswith("LFC-")
    assert "id" in data

    # verify persistence via list
    lst = client.get(f"{API}/collections", params={"employee_id": seed["employee"]["id"]}).json()
    assert any(c["id"] == data["id"] for c in lst)


def test_collection_filter_by_mode(client):
    r = client.get(f"{API}/collections", params={"payment_mode": "UPI"})
    assert r.status_code == 200
    for item in r.json():
        assert item["payment_mode"] == "UPI"


def test_collection_search(client):
    r = client.get(f"{API}/collections", params={"search": "TEST_"})
    assert r.status_code == 200


def test_collection_invalid_amount(client, seed):
    payload = {
        "vendor_name": "X", "amount": 0, "payment_mode": "Cash",
        "employee_id": seed["employee"]["id"], "employee_name": seed["employee"]["name"],
    }
    r = client.post(f"{API}/collections", json=payload)
    assert r.status_code == 422


# --- Expenses ---
def test_create_expense_and_persist(client, seed):
    payload = {
        "category": "Fuel", "amount": 250, "remarks": "TEST_fuel",
        "employee_id": seed["employee"]["id"], "employee_name": seed["employee"]["name"],
    }
    r = client.post(f"{API}/expenses", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["amount"] == 250
    assert data["category"] == "Fuel"
    assert data["date"]  # auto-set
    lst = client.get(f"{API}/expenses", params={"employee_id": seed["employee"]["id"]}).json()
    assert any(x["id"] == data["id"] for x in lst)


# --- Vendors CRUD ---
def test_vendor_create_update_delete(client):
    payload = {"name": "TEST_Vendor", "business_name": "TEST_Biz", "phone": "9998887770", "address": "TEST_Addr Street"}
    r = client.post(f"{API}/vendors", json=payload)
    assert r.status_code == 200, r.text
    vid = r.json()["id"]

    r2 = client.put(f"{API}/vendors/{vid}", json={**payload, "name": "TEST_Updated"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "TEST_Updated"

    r3 = client.delete(f"{API}/vendors/{vid}")
    assert r3.status_code == 200

    r4 = client.delete(f"{API}/vendors/{vid}")
    assert r4.status_code == 404


# --- Employees ---
def test_employee_create(client):
    payload = {"name": "TEST_Emp", "phone": "9990001111", "territory": "TEST_Zone"}
    r = client.post(f"{API}/employees", json=payload)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Emp"


def test_no_mongo_id_leak(client):
    for ep in ["/vendors", "/employees", "/collections", "/expenses"]:
        r = client.get(f"{API}{ep}")
        for item in r.json():
            assert "_id" not in item
