import os
from uuid import uuid4

import requests


STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "ledgerflow-collections"
storage_key = None


def get_storage_key(force_refresh=False):
    global storage_key
    if storage_key and not force_refresh:
        return storage_key
    response = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]},
        timeout=30,
    )
    response.raise_for_status()
    storage_key = response.json()["storage_key"]
    return storage_key


def upload_profile_photo(employee_id: str, data: bytes, extension: str, content_type: str):
    path = f"{APP_NAME}/profile-photos/{employee_id}/{uuid4()}.{extension}"
    for attempt in range(2):
        response = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": get_storage_key(force_refresh=attempt == 1), "Content-Type": content_type},
            data=data,
            timeout=120,
        )
        if response.status_code not in {401, 403}:
            response.raise_for_status()
            return response.json()["path"]
    response.raise_for_status()


def download_photo(path: str):
    for attempt in range(2):
        response = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": get_storage_key(force_refresh=attempt == 1)},
            timeout=60,
        )
        if response.status_code not in {401, 403}:
            response.raise_for_status()
            return response.content, response.headers.get("Content-Type", "application/octet-stream")
    response.raise_for_status()