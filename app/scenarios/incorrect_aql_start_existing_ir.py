from app.http_client import get_json_cached
from app.scenarios.incorrect_aql_common import process_report_doc
from app.scenarios.registry import ScenarioContext, register_scenario


@register_scenario("2", "Incorrect AQL sample size (start with existing IR)")
def scenario_incorrect_aql_start_existing_ir(context: ScenarioContext) -> None:
    report_refno = input("Enter the report refno (QCRXXXX-XXXXXX): ").strip()
    if not report_refno:
        print("Report refno cannot be empty.")
        return

    request_cache: dict = {}

    report_doc = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        f"/api/inspect_reports/{report_refno}",
    )

    if not isinstance(report_doc, dict):
        raise RuntimeError(
            f"GET /api/inspect_reports/{report_refno} did not return a valid report object"
        )

    process_report_doc(context, request_cache, report_doc)