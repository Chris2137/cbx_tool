from app.http_client import get_json_cached
from app.aql import (
    extract_header_aql_info,
    extract_quality_plan_aql_info,
    get_quality_plan_identity,
    map_lookup_record_sample_size_code_letters,
    map_pendulum_record,
    map_lookup_record_aql,
    calculate_and_print_aql,
)
from app.models import AQLInfo
from app.scenarios.registry import ScenarioContext


def process_report_doc(
    context: ScenarioContext,
    request_cache: dict,
    report_doc: dict,
) -> None:
    header_aql_info = extract_header_aql_info(report_doc)

    total_sample_size = report_doc.get("totalSampleSize")
    total_actual_qty = report_doc.get("totalActualQty")
    total_cartons = report_doc.get("totalCartons")
    total_quantity = report_doc.get("totalQuantity")

    print("\nHeader summary")
    print(f"totalSampleSize : {total_sample_size}")
    print(f"totalActualQty  : {total_actual_qty}")
    print(f"totalCartons    : {total_cartons}")
    print(f"totalQuantity   : {total_quantity}")
    print()

    quality_plans = report_doc.get("inspectReportMultipleQualityPlansList") or []

    all_sections: list[tuple[str, AQLInfo]] = [("Header", header_aql_info)]
    for plan in quality_plans:
        identity = get_quality_plan_identity(plan)
        all_sections.append((identity, extract_quality_plan_aql_info(plan)))

    sample_size_lookup_payload = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        "/api/lookupLists/name/INSP_SAMPLE_SIZE_CODE_LETTERS",
    )
    sample_size_code_letter_rows = [
        map_lookup_record_sample_size_code_letters(item)
        for item in (sample_size_lookup_payload.get("lookupsList") or [])
    ]

    pendulum_payload = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        "/api/codelists/AQL_PENDULUM_LEVEL",
    )
    pendulum_map = {}
    for item in (pendulum_payload.get("codelistList") or []):
        mapped = map_pendulum_record(item)
        code = mapped.get("code")
        if code:
            pendulum_map[code] = mapped

    lookup_names_to_load = set()
    for section_name, aql_info in all_sections:
        inspection_procedure_code = (
            aql_info.inspection_procedure.code
            if aql_info.inspection_procedure
            else None
        )
        if not inspection_procedure_code:
            print(f"[SKIP] inspectionProcedure is missing for section [{section_name}]")
            continue

        pendulum = pendulum_map.get(inspection_procedure_code)
        if not pendulum:
            raise RuntimeError(
                f"inspectionProcedure [{inspection_procedure_code}] not found in pendulum map "
                f"for section [{section_name}]"
            )

        lookup_list_name = pendulum.get("lookupListName")
        if not lookup_list_name:
            raise RuntimeError(
                f"lookup list name is missing for inspectionProcedure "
                f"[{inspection_procedure_code}] in section [{section_name}]"
            )

        lookup_names_to_load.add(lookup_list_name)

    lookup_rows_by_name: dict[str, list[dict]] = {}
    for lookup_name in sorted(lookup_names_to_load):
        payload = get_json_cached(
            context.session,
            context.credentials,
            context.auth_state,
            context.credentials_file,
            request_cache,
            "GET",
            f"/api/lookupLists/name/{lookup_name}",
        )
        lookup_rows_by_name[lookup_name] = [
            map_lookup_record_aql(item)
            for item in (payload.get("lookupsList") or [])
        ]

    if total_actual_qty is None:
        raise RuntimeError("totalActualQty is missing from inspect report response")

    if not isinstance(total_actual_qty, int):
        total_actual_qty = int(total_actual_qty)

    if total_actual_qty > 0:
        print(f"Calculating AQL with totalActualQty = {total_actual_qty}\n")
        calculate_and_print_aql(
            all_sections,
            total_actual_qty,
            sample_size_code_letter_rows,
            pendulum_map,
            lookup_rows_by_name,
        )
    else:
        print("totalActualQty is 0, so AQL cannot be calculated yet.")
        print("Please enter an actual quantity to continue.\n")

    while True:
        user_input = input(
            "Enter actual quantity to calculate, or q to return to main menu: "
        ).strip()

        if user_input.lower() == "q":
            break

        if not user_input:
            continue

        try:
            new_total_actual_qty = int(user_input)
        except ValueError:
            print("Actual quantity must be an integer or q.")
            continue

        print(f"\nCalculating AQL with totalActualQty = {new_total_actual_qty}\n")
        calculate_and_print_aql(
            all_sections,
            new_total_actual_qty,
            sample_size_code_letter_rows,
            pendulum_map,
            lookup_rows_by_name,
        )