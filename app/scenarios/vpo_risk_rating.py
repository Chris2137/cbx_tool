import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.http_client import api_request
from app.scenarios.registry import ScenarioContext, register_scenario

OUTPUT_DIR = Path("output")
VPO_RISK_PROGRESS_FILE = OUTPUT_DIR / "vpo_risk_rating_progress.json"

POLL_INTERVAL_SECONDS = 120


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _load_progress() -> dict | None:
    if not VPO_RISK_PROGRESS_FILE.exists():
        return None
    with VPO_RISK_PROGRESS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_progress(data: dict) -> None:
    _ensure_output_dir()
    with VPO_RISK_PROGRESS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Progress saved: {VPO_RISK_PROGRESS_FILE}")


def _new_progress(from_date: date, to_date: date) -> dict:
    data = {
        "updatedOnFrom": from_date.isoformat(),
        "updatedOnTo": to_date.isoformat(),
        "nextDateToProcess": to_date.isoformat(),
        "lastSuccessfulDate": None,
        "completed": False,
    }
    _save_progress(data)
    return data


def _call_api(context: ScenarioContext, day: date) -> int:
    next_day = day + timedelta(days=1)
    params = {
        "updatedOnFrom": day.isoformat(),
        "updatedOnTo": next_day.isoformat(),
        "async": "true",
    }

    try:
        response = api_request(
            context.session,
            context.credentials,
            context.auth_state,
            context.credentials_file,
            "GET",
            "/api/purchase_orders/recalculateRiskRating",
            params=params,
            allowed_statuses={200, 409},
        )
        return response.status_code
    except Exception as exc:
        msg = str(exc)
        if "409" in msg:
            return 409
        raise


@register_scenario("5", "Recalculate VPO risk rating")
def scenario_recalculate_vpo_risk_rating(context: ScenarioContext) -> None:
    print("\n=== Recalculate VPO Risk Rating ===\n")

    from_raw = input("last_updated_on from (yyyy-MM-dd, leave blank to resume): ").strip()
    to_raw = input("last_updated_on to   (yyyy-MM-dd, leave blank to resume): ").strip()

    both_empty = not from_raw and not to_raw

    if both_empty:
        progress = _load_progress()
        if progress is None:
            print("\nNo existing progress file found.")
            print("Please enter both dates to start a new run.\n")
            return
        print("\nResuming from existing progress file.")
    else:
        from_date = _parse_date(from_raw) if from_raw else None
        to_date = _parse_date(to_raw) if to_raw else None

        if not from_date:
            print("\nInvalid or missing 'from' date. Expected format: yyyy-MM-dd.\n")
            return
        if not to_date:
            print("\nInvalid or missing 'to' date. Expected format: yyyy-MM-dd.\n")
            return
        if from_date > to_date:
            print("\n'from' date must be earlier than or equal to 'to' date.\n")
            return

        progress = _new_progress(from_date, to_date)
        print(f"\nNew progress file created: {VPO_RISK_PROGRESS_FILE}")

    from_date = datetime.strptime(progress["updatedOnFrom"], "%Y-%m-%d").date()
    to_date = datetime.strptime(progress["updatedOnTo"], "%Y-%m-%d").date()
    current_day = datetime.strptime(progress["nextDateToProcess"], "%Y-%m-%d").date()

    print(f"\nRange  : {from_date} to {to_date}")
    print(f"Resume : {current_day}")
    print(f"Completed: {progress.get('completed', False)}\n")

    if progress.get("completed"):
        print("This run is already completed. Enter new dates to start over.\n")
        return

    confirm = input("Proceed? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.\n")
        return

    print()

    while current_day >= from_date:
        next_day = current_day + timedelta(days=1)
        print(f"[{current_day} → {next_day}] Calling recalculateRiskRating ...")

        status = _call_api(context, current_day)

        if status == 200:
            prev_day = current_day - timedelta(days=1)
            is_done = prev_day < from_date

            progress["lastSuccessfulDate"] = current_day.isoformat()
            progress["nextDateToProcess"] = prev_day.isoformat() if not is_done else from_date.isoformat()
            progress["completed"] = is_done
            _save_progress(progress)

            if is_done:
                print("\nAll dates processed. Run completed.\n")
                return

            current_day = prev_day
            print(f"Success. Next: {current_day}. Sleeping {POLL_INTERVAL_SECONDS}s ...\n")
            time.sleep(POLL_INTERVAL_SECONDS)

        elif status == 409:
            print(f"409 — backend busy. Retrying in {POLL_INTERVAL_SECONDS}s ...\n")
            time.sleep(POLL_INTERVAL_SECONDS)

        else:
            print(f"Unexpected status {status}. Aborting.\n")
            return