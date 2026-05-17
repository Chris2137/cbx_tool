import base64
from pathlib import Path
from urllib.parse import urljoin

import requests

from app.config import TOKEN_PATH, save_tokens


def get_basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"Basic {encoded}"


def build_token_headers(credentials: dict) -> dict:
    return {
        "Authorization": get_basic_auth_header(
            credentials["CLIENT_ID"],
            credentials["CLIENT_SECRET"],
        ),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }


def login(
    session: requests.Session,
    credentials: dict,
    auth_state: dict,
    credentials_file: str | Path,
) -> None:
    url = urljoin(credentials["server"], TOKEN_PATH)
    headers = build_token_headers(credentials)
    data = {
        "grant_type": "password",
        "username": credentials["username"],
        "password": credentials["password"],
    }

    response = session.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise RuntimeError(
            f"Authentication failed: {response.status_code} {response.text}"
        )
    
    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")

    if not access_token:
        raise RuntimeError("Authentication succeeded but access_token is missing.")
    if not refresh_token:
        raise RuntimeError("Authentication succeeded but refresh_token is missing.")

    auth_state["access_token"] = access_token
    auth_state["refresh_token"] = refresh_token

    save_tokens(str(credentials_file), credentials, auth_state)