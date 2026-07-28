from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from auth import create_token, hash_password, sanitize_user, verify_password


class LoginPayload(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=8, max_length=100)


class PasswordChangePayload(BaseModel):
    current_password: str = Field(min_length=8, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)


def build_auth_router(db, current_user):
    router = APIRouter(prefix="/api/auth", tags=["authentication"])

    @router.post("/login")
    async def login(payload: LoginPayload, response: Response):
        user = await db.users.find_one({"phone": payload.phone.strip()}, {"_id": 0})
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid phone number or password")
        token = create_token(user)
        response.set_cookie("access_token", token, httponly=True, secure=True, samesite="lax", max_age=28800, path="/")
        return {"user": sanitize_user(user), "token": token}

    @router.post("/logout")
    async def logout(response: Response, user: dict = Depends(current_user)):
        response.delete_cookie("access_token", path="/")
        return {"ok": True}

    @router.get("/me")
    async def me(user: dict = Depends(current_user)):
        return sanitize_user(user)

    @router.post("/change-password")
    async def change_password(payload: PasswordChangePayload, user: dict = Depends(current_user)):
        if not verify_password(payload.current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="Your current password is incorrect")
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"password_hash": hash_password(payload.new_password), "must_change_password": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True}

    return router