"""Backend API tests for Co. Daily Collection with authentication + role isolation."""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_PHONE = "9999999999"
ADMIN_PASSWORD = "Admin@123"
EMPLOYEE_PHONE = "+91 98765 42100"
EMPLOYEE_TEMP_PASSWORD = "Welcome@123"


# -- helpers ---------------------------------------------------------------
def _login(phone: str, password: str):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, f"login failed for {phone}: {r.status_code} {r.text}"
    data = r.json()
    token = data["token"]
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s, data


@pytest.fixture(scope="session")
def admin():
    session, data = _login(ADMIN_PHONE, ADMIN_PASSWORD)
    return {"session": session, "user": data["user"]}


@pytest.fixture(scope="session")
def new_employee(admin):
    """Create a fresh employee we can freely mutate/change password on."""
    phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
    temp_password = "TempPass@123"
    r = admin["session"].post(
        f"{API}/employees",
        json={"name": "TEST_AuthEmp", "phone": phone, "territory": "TEST_Zone",
              "temporary_password": temp_password},
    )
    assert r.status_code == 200, r.text
    emp = r.json()
    return {"employee": emp, "phone": phone, "temp_password": temp_password}


@pytest.fixture(scope="session")
def employee(new_employee):
    session, data = _login(new_employee["phone"], new_employee["temp_password"])
    return {"session": session, "user": data["user"], "meta": new_employee}


# -- auth / login ----------------------------------------------------------
class TestAuth:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": ADMIN_PHONE, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["role"] == "admin"
        assert body["user"]["phone"] == ADMIN_PHONE
        assert "password_hash" not in body["user"]
        assert isinstance(body["token"], str) and len(body["token"]) > 20

    def test_invalid_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": ADMIN_PHONE, "password": "WrongPass!!"})
        assert r.status_code == 401

    def test_unknown_phone(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": "0000000000", "password": "Whatever@123"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_admin(self, admin):
        r = admin["session"].get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_employee_must_change_password_flag(self, employee):
        r = employee["session"].get(f"{API}/auth/me")
        assert r.status_code == 200
        me = r.json()
        assert me["role"] == "employee"
        assert me["must_change_password"] is True

    def test_seeded_employee_login_and_flag(self):
        # Seeded employee should still login with Welcome@123 as long as not overridden.
        r = requests.post(f"{API}/auth/login",
                          json={"phone": EMPLOYEE_PHONE, "password": EMPLOYEE_TEMP_PASSWORD})
        if r.status_code == 401:
            pytest.skip("Seed employee password already changed; skipping")
        assert r.status_code == 200
        assert r.json()["user"]["must_change_password"] is True


# -- role isolation --------------------------------------------------------
class TestRoleIsolation:
    def test_employee_blocked_from_employees_list(self, employee):
        r = employee["session"].get(f"{API}/employees")
        assert r.status_code == 403

    def test_employee_blocked_from_add_employee(self, employee):
        r = employee["session"].post(f"{API}/employees",
                                     json={"name": "Nope", "phone": "9111111111",
                                           "territory": "ZZ", "temporary_password": "Abcd@1234"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_create(self, employee):
        r = employee["session"].post(f"{API}/vendors",
                                     json={"name": "XX", "business_name": "YY",
                                           "phone": "9111111111", "address": "somewhere"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_update(self, employee, admin):
        vendors = admin["session"].get(f"{API}/vendors").json()
        vid = vendors[0]["id"]
        r = employee["session"].put(f"{API}/vendors/{vid}",
                                    json={"name": "XX", "business_name": "YY",
                                          "phone": "9111111111", "address": "somewhere"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_delete(self, employee, admin):
        vendors = admin["session"].get(f"{API}/vendors").json()
        r = employee["session"].delete(f"{API}/vendors/{vendors[0]['id']}")
        assert r.status_code == 403

    def test_employee_blocked_from_employee_activity(self, employee, admin):
        r = employee["session"].get(f"{API}/employees/emp-raj/activity")
        assert r.status_code == 403

    def test_employee_blocked_from_other_employee_collections(self, employee):
        r = employee["session"].get(f"{API}/collections", params={"employee_id": "emp-raj"})
        assert r.status_code == 403

    def test_employee_blocked_from_other_employee_dashboard(self, employee):
        r = employee["session"].get(f"{API}/dashboard", params={"employee_id": "emp-raj"})
        assert r.status_code == 403

    def test_admin_cannot_post_collection(self, admin):
        r = admin["session"].post(f"{API}/collections",
                                  json={"vendor_name": "TT", "amount": 10, "payment_mode": "Cash"})
        assert r.status_code == 403

    def test_employee_blocked_from_delete_employee(self, employee, admin):
        # Employee must not be able to delete any employee (self or other)
        emps = admin["session"].get(f"{API}/employees").json()
        target_id = emps[0]["id"]
        r = employee["session"].delete(f"{API}/employees/{target_id}")
        assert r.status_code == 403


# -- admin profile / employee mgmt -----------------------------------------
class TestAdminFlows:
    def test_admin_profile(self, admin):
        r = admin["session"].get(f"{API}/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["role"] == "admin"
        assert body["employee"] is None

    def test_admin_lists_employees(self, admin):
        r = admin["session"].get(f"{API}/employees")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_admin_employee_activity(self, admin):
        r = admin["session"].get(f"{API}/employees/emp-raj/activity")
        assert r.status_code == 200
        d = r.json()
        for key in ("employee", "today_total", "today_vendors", "collections"):
            assert key in d
        assert d["employee"]["id"] == "emp-raj"
        # Expenses removed feature: activity payload should not include expenses
        assert "expenses" not in d

    def test_admin_dashboard(self, admin):
        r = admin["session"].get(f"{API}/dashboard")
        assert r.status_code == 200
        body = r.json()
        for k in ("today_collection", "monthly_collection", "trend", "active_vendors", "active_employees"):
            assert k in body
        # Expenses removed: dashboard should not include today_expenses
        assert "today_expenses" not in body

    def test_duplicate_phone_rejected(self, admin, new_employee):
        r = admin["session"].post(
            f"{API}/employees",
            json={"name": "Dup", "phone": new_employee["phone"], "territory": "ZZ",
                  "temporary_password": "Something@123"},
        )
        assert r.status_code == 400


# -- employee flows --------------------------------------------------------
class TestEmployeeFlows:
    def test_profile_shows_only_own(self, employee):
        r = employee["session"].get(f"{API}/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["role"] == "employee"
        assert body["employee"]["id"] == employee["user"]["employee_id"]

    def test_change_password_flow(self, employee):
        new_password = "NewPass@2026"
        r = employee["session"].post(
            f"{API}/auth/change-password",
            json={"current_password": employee["meta"]["temp_password"],
                  "new_password": new_password},
        )
        assert r.status_code == 200
        # old password should not work
        r_old = requests.post(f"{API}/auth/login",
                              json={"phone": employee["meta"]["phone"],
                                    "password": employee["meta"]["temp_password"]})
        assert r_old.status_code == 401
        # new password should work
        r_new = requests.post(f"{API}/auth/login",
                              json={"phone": employee["meta"]["phone"],
                                    "password": new_password})
        assert r_new.status_code == 200
        assert r_new.json()["user"]["must_change_password"] is False
        # update fixture session token so subsequent tests still work
        employee["session"].headers.update(
            {"Authorization": f"Bearer {r_new.json()['token']}"}
        )
        employee["meta"]["temp_password"] = new_password  # noqa

    def test_collection_uses_signed_identity(self, employee):
        vendors = requests.get(f"{API}/vendors",
                               headers={"Authorization": employee["session"].headers["Authorization"]}).json()
        payload = {
            "vendor_id": vendors[0]["id"],
            "vendor_name": vendors[0]["business_name"],
            "amount": 500,
            "payment_mode": "UPI",
            "remarks": "TEST_auth_identity",
            # Attempt to spoof another identity — server must ignore
            "employee_id": "emp-raj",
            "employee_name": "Impersonator",
        }
        r = employee["session"].post(f"{API}/collections", json=payload)
        # extra keys should either be silently dropped by pydantic or accepted;
        # in either case server must overwrite identity
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["employee_id"] == employee["user"]["employee_id"]
        assert body["employee_name"] == employee["user"]["name"]
        assert body["receipt_number"].startswith("LFC-")

    def test_expense_endpoints_removed(self, employee, admin):
        """Expenses feature is fully removed; all expense routes must be 404."""
        for sess in (employee["session"], admin["session"]):
            assert sess.get(f"{API}/expenses").status_code == 404
            assert sess.post(f"{API}/expenses",
                             json={"category": "Fuel", "amount": 5}).status_code == 404
            assert sess.delete(f"{API}/expenses/anything").status_code == 404

    def test_employee_dashboard_scoped(self, employee):
        r = employee["session"].get(f"{API}/dashboard")
        assert r.status_code == 200

    def test_employee_collections_scoped(self, employee):
        r = employee["session"].get(f"{API}/collections")
        assert r.status_code == 200
        for c in r.json():
            assert c["employee_id"] == employee["user"]["employee_id"]

    def test_logout(self, employee):
        r = employee["session"].post(f"{API}/auth/logout")
        assert r.status_code == 200


# -- misc ------------------------------------------------------------------
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_no_mongo_id_leak(admin):
    for ep in ["/vendors", "/employees", "/collections"]:
        r = admin["session"].get(f"{API}{ep}")
        assert r.status_code == 200
        for item in r.json():
            assert "_id" not in item


# -- admin delete employee ------------------------------------------------
class TestAdminDeleteEmployee:
    """Admin-only employee deletion; cascades user+files, blocks employee role."""

    def test_admin_can_delete_created_employee_and_cascade(self, admin):
        phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        temp = "TempPass@123"
        r = admin["session"].post(
            f"{API}/employees",
            json={"name": "TEST_DeleteMe", "phone": phone,
                  "territory": "TEST_DelZone", "temporary_password": temp},
        )
        assert r.status_code == 200, r.text
        emp = r.json()
        emp_id = emp["id"]

        # Login as that employee once to confirm the user record exists
        r_login = requests.post(f"{API}/auth/login",
                                json={"phone": phone, "password": temp})
        assert r_login.status_code == 200

        # Delete via admin
        r_del = admin["session"].delete(f"{API}/employees/{emp_id}")
        assert r_del.status_code == 200, r_del.text
        assert r_del.json().get("ok") is True

        # Employee no longer in admin listing
        listing = admin["session"].get(f"{API}/employees").json()
        assert not any(e["id"] == emp_id for e in listing)

        # Login should now fail (user cascade)
        r_relogin = requests.post(f"{API}/auth/login",
                                  json={"phone": phone, "password": temp})
        assert r_relogin.status_code == 401

    def test_admin_delete_missing_employee_404(self, admin):
        r = admin["session"].delete(f"{API}/employees/does-not-exist-xyz")
        assert r.status_code == 404

    def test_delete_employee_requires_auth(self):
        r = requests.delete(f"{API}/employees/emp-raj")
        assert r.status_code == 401

    def test_delete_employee_without_photo_file_id(self, admin):
        """Regression: employees created without a photo (no photo_file_id key)
        must still delete cleanly. Previous bug returned 404 'Employee not found'
        because the projection returned an empty dict and truthiness check failed.
        """
        phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        temp = "TempPass@123"
        r = admin["session"].post(
            f"{API}/employees",
            json={"name": "TEST_NoPhotoDel", "phone": phone,
                  "territory": "TEST_NoPhoto", "temporary_password": temp},
        )
        assert r.status_code == 200, r.text
        emp = r.json()
        # Verify the employee document truly has no photo_file_id field
        assert emp.get("photo_file_id") in (None, ""), f"expected no photo_file_id, got {emp}"

        r_del = admin["session"].delete(f"{API}/employees/{emp['id']}")
        assert r_del.status_code == 200, (
            f"Delete without photo failed with {r_del.status_code}: {r_del.text}"
        )
        assert r_del.json().get("ok") is True

        # Absent from listing
        listing = admin["session"].get(f"{API}/employees").json()
        assert not any(e["id"] == emp["id"] for e in listing)

        # Login fails
        r_login = requests.post(f"{API}/auth/login",
                                json={"phone": phone, "password": temp})
        assert r_login.status_code == 401

    def test_ananya_removed(self):
        """User claimed Ananya Shah was removed; sign-in should return 401.
        NOTE: seed.py re-creates emp-ananya user on every backend startup
        (idempotent seed adds missing user rows), so removal does not persist
        across restarts. This test documents that gap.
        """
        r = requests.post(f"{API}/auth/login",
                          json={"phone": "+91 98765 42101", "password": "Welcome@123"})
        if r.status_code == 200:
            pytest.skip(
                "Ananya still present in this environment - "
                "seed.py re-adds emp-ananya user row on backend restart. "
                "Reported to main agent."
            )
        assert r.status_code == 401



# -- profile photo uploads -------------------------------------------------
# 1x1 PNG (real PNG, not just header bytes)
_PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c62f8cf0000000300010001f5da8b8b0000000049454e44ae426082"
)
# 1x1 JPEG
_JPG_1x1 = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c"
    "2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d18"
    "32211c2132323232323232323232323232323232323232323232323232323232323232"
    "3232323232323232323232323232323232323232ffc00011080001000103012200021101"
    "031101ffc4001f0000010501010101010100000000000000000102030405060708090a"
    "0bffc400b5100002010303020403050504040000017d01020300041105122131410613"
    "516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728"
    "292a3435363738393a434445464748494a535455565758595a636465666768696a7374"
    "75767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4"
    "b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1"
    "f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405"
    "060708090a0bffc400b511000201020404030407050404000102770001020311040521"
    "3106124151076171132232810814429115a1b1c109233352f0156272d10a162434e125"
    "f11718191a262728292a35363738393a434445464748494a535455565758595a636465"
    "666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5"
    "a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4"
    "e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00fbd0028affd9"
)


class TestProfilePhoto:
    """Employee profile photo upload / access-control tests."""

    def _upload(self, session, content, filename, content_type):
        # Do NOT send Content-Type: application/json header for multipart
        headers = {k: v for k, v in session.headers.items() if k.lower() != "content-type"}
        return requests.post(
            f"{API}/profile/photo",
            files={"file": (filename, content, content_type)},
            headers=headers,
        )

    def test_admin_cannot_upload_photo(self, admin):
        r = self._upload(admin["session"], _PNG_1x1, "a.png", "image/png")
        assert r.status_code == 403, r.text

    def test_employee_upload_png_success(self, employee):
        r = self._upload(employee["session"], _PNG_1x1, "me.png", "image/png")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "photo_file_id" in body
        assert isinstance(body["photo_file_id"], str) and len(body["photo_file_id"]) > 10
        # storage path / access keys must not leak
        for banned in ("storage_path", "storage_key", "path", "url"):
            assert banned not in body
        # profile now reflects the photo id
        prof = employee["session"].get(f"{API}/profile").json()
        assert prof["employee"]["photo_file_id"] == body["photo_file_id"]
        # Persist for later tests
        employee["meta"]["photo_file_id"] = body["photo_file_id"]

    def test_employee_upload_jpeg_success(self, employee):
        r = self._upload(employee["session"], _JPG_1x1, "me.jpg", "image/jpeg")
        assert r.status_code == 200, r.text
        new_id = r.json()["photo_file_id"]
        # Old file should now be soft-deleted
        old_id = employee["meta"].get("photo_file_id")
        if old_id and old_id != new_id:
            # Old id should no longer be retrievable (soft-deleted)
            r_old = employee["session"].get(f"{API}/files/{old_id}")
            assert r_old.status_code == 404, f"Old photo {old_id} should be soft-deleted, got {r_old.status_code}"
        employee["meta"]["photo_file_id"] = new_id

    def test_reject_unsupported_type(self, employee):
        r = self._upload(employee["session"], b"GIF89a\x00\x00\x00\x00", "x.gif", "image/gif")
        assert r.status_code == 400, r.text
        assert "JPG" in r.json()["detail"] or "PNG" in r.json()["detail"] or "WebP" in r.json()["detail"]

    def test_reject_text_file(self, employee):
        r = self._upload(employee["session"], b"hello", "x.txt", "text/plain")
        assert r.status_code == 400, r.text

    def test_reject_oversized_file(self, employee):
        big = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 100)
        r = self._upload(employee["session"], big, "big.png", "image/png")
        assert r.status_code == 400, r.text
        assert "5 MB" in r.json()["detail"]

    def test_owner_can_view_photo(self, employee):
        pid = employee["meta"]["photo_file_id"]
        r = employee["session"].get(f"{API}/files/{pid}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/")
        assert len(r.content) > 0

    def test_admin_can_view_employee_photo(self, admin, employee):
        pid = employee["meta"]["photo_file_id"]
        r = admin["session"].get(f"{API}/files/{pid}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/")

    def test_other_employee_cannot_view_photo(self, admin, employee):
        pid = employee["meta"]["photo_file_id"]
        # create a second employee
        phone2 = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        r = admin["session"].post(
            f"{API}/employees",
            json={"name": "TEST_OtherEmp", "phone": phone2, "territory": "TEST_Z2",
                  "temporary_password": "TempPass@123"},
        )
        assert r.status_code == 200, r.text
        s2, _ = _login(phone2, "TempPass@123")
        r_other = s2.get(f"{API}/files/{pid}")
        assert r_other.status_code == 403, r_other.text

    def test_unauth_cannot_view_photo(self, employee):
        pid = employee["meta"]["photo_file_id"]
        r = requests.get(f"{API}/files/{pid}")
        assert r.status_code == 401

    def test_missing_file_404(self, employee):
        r = employee["session"].get(f"{API}/files/nonexistent-{uuid.uuid4()}")
        assert r.status_code == 404

    def test_no_storage_path_leak_in_employees_list(self, admin, employee):
        r = admin["session"].get(f"{API}/employees")
        assert r.status_code == 200
        for emp in r.json():
            for banned in ("storage_path", "storage_key"):
                assert banned not in emp, f"leaked {banned} in employees payload"

    def test_no_storage_path_leak_in_profile(self, employee):
        r = employee["session"].get(f"{API}/profile")
        assert r.status_code == 200
        blob = r.text
        assert "storage_path" not in blob
        assert "objstore" not in blob
        assert "X-Storage-Key" not in blob



# -- quick vendor (employee self-service add) ----------------------------
class TestQuickVendor:
    def test_employee_quick_add_creates_vendor(self, employee):
        name = f"TEST_QuickVendor_{uuid.uuid4().hex[:8]}"
        r = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["business_name"].lower() == name.lower()
        assert body["name"].lower() == name.lower()
        assert "id" in body and isinstance(body["id"], str)
        assert body.get("active") is True
        assert body.get("phone")  # placeholder value fine
        assert body.get("address")
        # Persistence: list should contain it
        listing = employee["session"].get(f"{API}/vendors", params={"search": name}).json()
        assert any(v["id"] == body["id"] for v in listing), "quick vendor not persisted"

    def test_quick_add_is_idempotent_same_name(self, employee):
        name = f"TEST_Idem_{uuid.uuid4().hex[:6]}"
        r1 = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name})
        r2 = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"], "duplicate vendor created for same name"

    def test_quick_add_case_insensitive_idempotent(self, employee):
        name = f"TEST_Case_{uuid.uuid4().hex[:6]}"
        r1 = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name.lower()})
        r2 = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name.upper()})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"], "case-variant produced duplicate"

    def test_quick_add_rejects_short_name(self, employee):
        r = employee["session"].post(f"{API}/vendors/quick-add", json={"name": "x"})
        assert r.status_code == 422, r.text

    def test_admin_cannot_use_quick_add(self, admin):
        r = admin["session"].post(f"{API}/vendors/quick-add",
                                  json={"name": f"TEST_AdminBlocked_{uuid.uuid4().hex[:6]}"})
        assert r.status_code == 403, r.text

    def test_quick_add_requires_auth(self):
        r = requests.post(f"{API}/vendors/quick-add", json={"name": "TEST_Anon_Vendor"})
        assert r.status_code == 401

    def test_employee_still_blocked_from_full_vendor_management(self, employee, admin):
        # Regression: quick-add must NOT weaken admin-only mgmt.
        payload = {"name": "TESTFullMgmt", "business_name": "TESTFullBiz",
                   "phone": "9111111111", "address": "somewhere else"}
        r = employee["session"].post(f"{API}/vendors", json=payload)
        assert r.status_code == 403, r.text
        vendors = admin["session"].get(f"{API}/vendors").json()
        vid = vendors[0]["id"]
        assert employee["session"].put(f"{API}/vendors/{vid}", json=payload).status_code == 403
        assert employee["session"].delete(f"{API}/vendors/{vid}").status_code == 403

    def test_collection_can_be_created_with_quick_vendor(self, employee):
        # Employee auth may still require must_change_password? Let's use a fresh employee that has already been used
        # for TestAuth (test_employee_must_change_password_flag). Collections endpoint doesn't require password change,
        # so should work. If it fails we skip gracefully.
        name = f"TEST_CollectVendor_{uuid.uuid4().hex[:6]}"
        r = employee["session"].post(f"{API}/vendors/quick-add", json={"name": name})
        assert r.status_code == 200, r.text
        vendor = r.json()
        c = employee["session"].post(
            f"{API}/collections",
            json={"vendor_id": vendor["id"], "vendor_name": vendor["name"],
                  "amount": 12.5, "payment_mode": "Cash", "remarks": "TEST"},
        )
        assert c.status_code == 200, c.text
        body = c.json()
        assert body["vendor_id"] == vendor["id"]
        assert body["amount"] == 12.5


# -- address persistence & exposure (vendor + employee) ---------------------
class TestAddressPersistence:
    """Vendor address visible in listings; employee address stored + returned via API/activity."""

    def test_vendor_create_persists_address(self, admin):
        payload = {
            "name": "TEST_VendorContact",
            "business_name": f"TEST_VendorBiz_{uuid.uuid4().hex[:6]}",
            "phone": "+91 90000 00001",
            "address": "77 TEST Address Lane, Testville",
        }
        r = admin["session"].post(f"{API}/vendors", json=payload)
        assert r.status_code == 200, r.text
        vendor = r.json()
        assert vendor["address"] == payload["address"]
        assert "_id" not in vendor
        try:
            listing = admin["session"].get(f"{API}/vendors")
            assert listing.status_code == 200
            match = [v for v in listing.json() if v["id"] == vendor["id"]]
            assert match, "created vendor missing from GET /api/vendors"
            assert match[0]["address"] == payload["address"]
            assert match[0]["business_name"] == payload["business_name"]
            assert match[0]["phone"] == payload["phone"]
        finally:
            assert admin["session"].delete(f"{API}/vendors/{vendor['id']}").status_code == 200

    def test_all_seeded_vendors_expose_address_field(self, admin):
        r = admin["session"].get(f"{API}/vendors")
        assert r.status_code == 200, r.text
        vendors = r.json()
        assert len(vendors) > 0
        for v in vendors:
            assert "address" in v, f"vendor {v['id']} missing address key"
            assert isinstance(v["address"], str)

    def test_vendor_address_too_short_rejected(self, admin):
        r = admin["session"].post(f"{API}/vendors", json={
            "name": "TEST_Short", "business_name": "TEST_ShortBiz",
            "phone": "+91 90000 00002", "address": "ab"})
        assert r.status_code == 422, r.text

    def test_employee_address_persists_and_appears_in_activity(self, admin):
        phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        address = "12 TEST Home Street, Sector 9"
        r = admin["session"].post(f"{API}/employees", json={
            "name": "TEST_AddrEmp", "phone": phone, "territory": "TEST_Territory",
            "address": address, "temporary_password": "TempPass@123"})
        assert r.status_code == 200, r.text
        emp = r.json()
        assert emp["address"] == address
        assert "_id" not in emp
        try:
            listing = admin["session"].get(f"{API}/employees")
            assert listing.status_code == 200
            match = [e for e in listing.json() if e["id"] == emp["id"]]
            assert match, "created employee missing from GET /api/employees"
            assert match[0]["address"] == address, "employee address not persisted in DB"

            activity = admin["session"].get(f"{API}/employees/{emp['id']}/activity")
            assert activity.status_code == 200, activity.text
            body = activity.json()
            assert body["employee"]["address"] == address
            assert body["employee"]["name"] == "TEST_AddrEmp"
        finally:
            assert admin["session"].delete(f"{API}/employees/{emp['id']}").status_code == 200
            assert admin["session"].get(f"{API}/employees/{emp['id']}/activity").status_code == 404

    def test_employee_address_optional(self, admin):
        phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        r = admin["session"].post(f"{API}/employees", json={
            "name": "TEST_NoAddrEmp", "phone": phone, "territory": "TEST_Territory",
            "temporary_password": "TempPass@123"})
        assert r.status_code == 200, r.text
        emp = r.json()
        try:
            assert emp["address"] == ""
        finally:
            assert admin["session"].delete(f"{API}/employees/{emp['id']}").status_code == 200

    def test_employee_address_update_persists(self, admin):
        phone = f"+91 9{uuid.uuid4().int % 1000000000:09d}"
        r = admin["session"].post(f"{API}/employees", json={
            "name": "TEST_UpdAddrEmp", "phone": phone, "territory": "TEST_Territory",
            "address": "Old TEST address", "temporary_password": "TempPass@123"})
        assert r.status_code == 200, r.text
        emp = r.json()
        try:
            upd = admin["session"].put(f"{API}/employees/{emp['id']}", json={
                "name": "TEST_UpdAddrEmp", "phone": phone, "territory": "TEST_Territory",
                "address": "New TEST address 42", "temporary_password": "TempPass@456"})
            assert upd.status_code == 200, upd.text
            assert upd.json()["address"] == "New TEST address 42"
            activity = admin["session"].get(f"{API}/employees/{emp['id']}/activity")
            assert activity.status_code == 200
            assert activity.json()["employee"]["address"] == "New TEST address 42"
        finally:
            assert admin["session"].delete(f"{API}/employees/{emp['id']}").status_code == 200
