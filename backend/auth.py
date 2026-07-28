import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=ALGORITHM)


def sanitize_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key not in {"_id", "password_hash"}}


def auth_dependency(db):
    async def current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ):
        token = request.cookies.get("access_token")
        if not token and credentials:
            token = credentials.credentials
        if not token:
            raise HTTPException(status_code=401, detail="Please sign in to continue")
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[ALGORITHM])
        except jwt.PyJWTError as error:
            raise HTTPException(status_code=401, detail="Your session has expired") from error
        user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0})
        if not user or not user.get("active", True):
            raise HTTPException(status_code=401, detail="Account is unavailable")
        return user

    return current_user


def require_admin(user: dict = Depends(lambda: None)):
    return user