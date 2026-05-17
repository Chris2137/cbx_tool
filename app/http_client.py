from pathlib import Path
from urllib.parse import urljoin

import requests

from app.auth import build_token_headers
from app.config import DEBUG, TOKEN_PATH, save_tokens
from app.debug_utils import debug_api_call


def build_api_headers(auth_state: dict, extra_headers: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {auth_state['access_token']}",
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def ensure_success(response: requests.Response, context: str) -> requests.Response:
    if DEBUG:
        print(f"[DEBUG] ensure_success called for: {context}")
        print(f"[DEBUG] ensure_success status_code: {response.status_code}")

    if 200 <= response.status_code < 300:
        if DEBUG:
            print(f"[DEBUG] ensure_success returning success for: {context}")
        return response

    body = (response.text or "").strip()
    if len(body) > 1000:
        body = body[:1000] + "...<truncated>"

    if DEBUG:
        print(f"[DEBUG] ensure_success about to raise for: {context}")
        print(f"[DEBUG] ensure_success response.reason: {response.reason}")
        print(f"[DEBUG] ensure_success response body: {body}")

    raise RuntimeError(
        f"{context} failed with status {response.status_code} "
        f"({response.reason}). Response body: {body}"
    )


def refresh_access_token(
    session: requests.Session,
    credentials: dict,
    auth_state: dict,
    credentials_file: str | Path,
) -> None:
    refresh_token = auth_state.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Cannot refresh access token: refresh_token is missing.")

    url = urljoin(credentials["server"], TOKEN_PATH)
    headers = build_token_headers(credentials)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    response = session.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise RuntimeError(
            f"Refresh token request failed: {response.status_code} {response.text}"
        )

    payload = response.json()
    access_token = payload.get("access_token")
    new_refresh_token = payload.get("refresh_token")

    if not access_token:
        raise RuntimeError("Refresh succeeded but access_token is missing.")

    auth_state["access_token"] = access_token

    if new_refresh_token:
        auth_state["refresh_token"] = new_refresh_token

    save_tokens(str(credentials_file), credentials, auth_state)


def try_resume_session(
    session: requests.Session,
    credentials: dict,
    auth_state: dict,
    credentials_file: str | Path,
) -> bool:
    saved_access_token = credentials.get("access_token")
    saved_refresh_token = credentials.get("refresh_token")

    if not saved_access_token and not saved_refresh_token:
        return False

    auth_state["access_token"] = saved_access_token
    auth_state["refresh_token"] = saved_refresh_token

    if saved_access_token:
        response = session.get(
            urljoin(credentials["server"], "/api/systemMessages/index/all"),
            headers=build_api_headers(auth_state),
            timeout=30,
        )
        if 200 <= response.status_code < 300:
            print("Reused saved access token.")
            return True

    if saved_refresh_token:
        try:
            refresh_access_token(session, credentials, auth_state, credentials_file)
            print("Reused saved refresh token and obtained new access token.")
            return True
        except Exception:
            pass

    auth_state["access_token"] = None
    auth_state["refresh_token"] = None
    return False


def api_request(
    session: requests.Session,
    credentials: dict,
    auth_state: dict,
    credentials_file: str | Path,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | list | None = None,
    headers: dict | None = None,
    timeout: int = 60,
) -> requests.Response:
    url = urljoin(credentials["server"], path)
    merged_headers = build_api_headers(auth_state, headers)

    response = session.request(
        method=method.upper(),
        url=url,
        params=params,
        data=data,
        json=json,
        headers=merged_headers,
        timeout=timeout,
    )

    if response.status_code == 401:
        print("Received 401. Refreshing access token and retrying once...")
        refresh_access_token(session, credentials, auth_state, credentials_file)

        retry_headers = build_api_headers(auth_state, headers)
        response = session.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data,
            json=json,
            headers=retry_headers,
            timeout=timeout,
        )

        if response.status_code == 401:
            body = (response.text or "").strip()
            if len(body) > 1000:
                body = body[:1000] + "...<truncated>"

            raise RuntimeError(
                f"API call still returned 401 after token refresh: "
                f"{method.upper()} {path}. Response body: {body}"
            )

    debug_api_call(path, response, json)
    return ensure_success(response, f"{method.upper()} {path}")


def get_json_cached(
    session: requests.Session,
    credentials: dict,
    auth_state: dict,
    credentials_file: str | Path,
    request_cache: dict,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    json_body: dict | list | None = None,
    headers: dict | None = None,
) -> dict | list:
    cache_key = (
        method.upper(),
        path,
        repr(sorted((params or {}).items())),
        repr(sorted((data or {}).items())),
        repr(json_body),
    )

    if cache_key in request_cache:
        return request_cache[cache_key]

    response = api_request(
        session,
        credentials,
        auth_state,
        credentials_file,
        method,
        path,
        params=params,
        data=data,
        json=json_body,
        headers=headers,
    )

    payload = response.json()
    request_cache[cache_key] = payload
    return payload