from app.http_client import get_json_cached
from app.scenarios.incorrect_aql_common import process_report_doc
from app.scenarios.registry import ScenarioContext, register_scenario


@register_scenario("1", "Incorrect AQL sample size (start with booking)")
def scenario_incorrect_aql_start_booking(context: ScenarioContext) -> None:
    booking_refno = input("Enter the booking refno: ").strip()
    if not booking_refno:
        print("Booking refno cannot be empty.")
        return

    request_cache: dict = {}

    booking_detail = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        f"/api/inspect_bookings/{booking_refno}",
    )

    inheritance_response = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "POST",
        "/api/newDoc/inheritance/inspectReport",
        json_body={
            "dmrNames": [
                "irBookingToReport",
                "irBookingAQLToReport",
            ],
            "fromModuleId": "inspectBooking",
            "actionId": "NewInspectReport",
            "sourceEntities": [booking_detail],
        },
    )

    report_doc = inheritance_response.get("doc")
    if not isinstance(report_doc, dict):
        raise RuntimeError(
            "POST /api/newDoc/inheritance/inspectReport response is missing doc"
        )

    process_report_doc(context, request_cache, report_doc)