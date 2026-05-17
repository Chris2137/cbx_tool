import json
import time
from datetime import datetime
from typing import Any

from app.config import DEBUG, DEBUG_LOG_FILE


def trim_text(value: Any, max_len: int = 10000) -> str:
    text = "" if value is None else str(value)
    if len(text) > max_len:
        return text[:max_len] + "...<truncated>"
    return text


def mask_value(value: Any, keep_start: int = 2, keep_end: int = 2) -> str:
    text = "" if value is None else str(value)

    if not text:
        return ""

    if len(text) <= keep_start + keep_end:
        return "*" * len(text)

    return f"{text[:keep_start]}{'*' * (len(text) - keep_start - keep_end)}{text[-keep_end:]}"


def append_debug_log(text: str) -> None:
    if not DEBUG:
        return
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")


def debug_api_call(label: str, response, request_body: Any = None) -> None:
    if not DEBUG:
        return

    lines = []
    lines.append("=" * 100)
    lines.append(f"[DEBUG] {datetime.now().isoformat(timespec='seconds')} {label}")

    if request_body is not None:
        lines.append("[DEBUG] Request body:")
        try:
            lines.append(json.dumps(request_body, indent=2, ensure_ascii=False))
        except TypeError:
            lines.append(trim_text(request_body))

    lines.append("[DEBUG] Response status:")
    lines.append(str(response.status_code))

    lines.append("[DEBUG] Response headers:")
    lines.append(trim_text(dict(response.headers)))

    lines.append("[DEBUG] Response text:")
    lines.append(trim_text(response.text))

    try:
        parsed = response.json()
        lines.append("[DEBUG] Response JSON:")
        lines.append(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        lines.append("[DEBUG] Response is not valid JSON.")

    if getattr(response, "request", None) is not None:
        lines.append("[DEBUG] Actual sent request method/url:")
        lines.append(f"{response.request.method} {response.request.url}")
        lines.append("[DEBUG] Actual sent request headers:")
        lines.append(trim_text(dict(response.request.headers)))
        lines.append("[DEBUG] Actual sent request body:")
        lines.append(trim_text(response.request.body))

    append_debug_log("\n".join(lines))
    print(f"[DEBUG] Full request/response written to {DEBUG_LOG_FILE}")


def timed_log(label: str):
    start = time.perf_counter()
    print(f"[START] {label}")

    def done() -> None:
        elapsed = time.perf_counter() - start
        print(f"[END] {label} took {elapsed:.3f}s")

    return done