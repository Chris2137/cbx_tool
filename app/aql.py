from typing import Any, List

from app.models import CodeName, AQLInfo, AQLResult, to_code_name, to_decimal
from app.debug_utils import timed_log


def extract_header_aql_info(report_payload: dict) -> AQLInfo:
    return AQLInfo(
        critical_level=to_code_name(report_payload.get("criticalLevelDSR")),
        major_level=to_code_name(report_payload.get("majorLevelDSR")),
        minor_level=to_code_name(report_payload.get("minorLevelDSR")),
        inspection_level=to_code_name(report_payload.get("inspectionLevelDSR")),
        inspection_procedure=to_code_name(report_payload.get("inspectionProcedureDSR")),
        is_allow_realtime_update=to_code_name(report_payload.get("isAllowRealtimeUpdateDSR")),
        sampling_plan=to_code_name(report_payload.get("samplingPlanDSR")),
        sampling_method=to_code_name(report_payload.get("samplingMethod")),
    )


def extract_quality_plan_aql_info(plan: dict) -> AQLInfo:
    return AQLInfo(
        critical_level=to_code_name(plan.get("criticalLevel")),
        major_level=to_code_name(plan.get("majorLevel")),
        minor_level=to_code_name(plan.get("minorLevel")),
        inspection_level=to_code_name(plan.get("inspectionLevel")),
        inspection_procedure=to_code_name(
            plan.get("inspectionProcedures") or plan.get("inspectionProcedure")
        ),
        is_allow_realtime_update=to_code_name(plan.get("isAllowRealtimeUpdate")),
        sampling_plan=None,
        sampling_method=to_code_name(plan.get("samplingMethod")),
    )


def get_quality_plan_identity(plan: dict) -> str:
    template_name = ((plan.get("qualityPlanTemplate") or {}).get("name")) or "Unknown Template"
    section_label = plan.get("sectionLabel") or "Unknown Section"
    return f"{template_name} - {section_label}"


def map_lookup_record_sample_size_code_letters(item: dict) -> dict:
    custom = item.get("customFields") or {}
    return {
        "inspectionLevel": custom.get("customFieldText1"),
        "codeLetter": custom.get("customFieldText2"),
        "sampleSize": custom.get("customFieldNumber1"),
        "lowerLimit": custom.get("customFieldNumber2"),
        "upperLimit": custom.get("customFieldNumber3"),
        "disabled": item.get("disabled"),
    }


def map_lookup_record_aql(item: dict) -> dict:
    custom = item.get("customFields") or {}
    code_list_1 = custom.get("customFieldCodeList1") or {}
    return {
        "codeLetter": custom.get("customFieldText1"),
        "samplingPlanType": code_list_1.get("code"),
        "aql": custom.get("customFieldDecimal1"),
        "sampleSize": custom.get("customFieldNumber1"),
        "acceptanceNumber": custom.get("customFieldNumber2"),
        "rejectionNumber": custom.get("customFieldNumber3"),
        "iteration": custom.get("customFieldNumber4"),
    }


def map_pendulum_record(item: dict) -> dict:
    custom = item.get("customFields") or {}
    return {
        "code": item.get("code"),
        "name": item.get("name"),
        "lookupListName": custom.get("customFieldText1"),
    }


def find_code_letter(
    sample_size_code_letter_rows: List[dict],
    inspection_level_code: str,
    total_actual_qty: int,
) -> str:
    for row in sample_size_code_letter_rows:
        if row.get("disabled"):
            continue
        if row.get("inspectionLevel") != inspection_level_code:
            continue

        lower = row.get("lowerLimit")
        upper = row.get("upperLimit")
        if lower is None or upper is None:
            continue

        if total_actual_qty >= lower and total_actual_qty <= upper:
            code_letter = row.get("codeLetter")
            if code_letter:
                return code_letter

    raise RuntimeError(
        f"No sample size code letter found for inspection level "
        f"[{inspection_level_code}] and totalActualQty [{total_actual_qty}]"
    )


def find_aql_result(
    rows: List[dict],
    code_letter: str,
    aql_code: str,
    *,
    section_name: str,
    level_name: str,
    lookup_list_name: str,
    inspection_level_code: str,
    inspection_procedure_code: str,
) -> AQLResult:
    target_aql = to_decimal(aql_code)

    for row in rows:
        row_code_letter = (row.get("codeLetter") or "").strip()
        row_aql_raw = row.get("aql")

        if row_code_letter != code_letter:
            continue
        if row_aql_raw is None:
            continue

        row_aql = to_decimal(row_aql_raw)
        if row_aql == target_aql:
            return AQLResult(
                code_letter=row.get("codeLetter"),
                sample_size=row.get("sampleSize"),
                acceptance_number=row.get("acceptanceNumber"),
                rejection_number=row.get("rejectionNumber"),
                iteration=row.get("iteration"),
            )

    matching_code_letters = sorted(
        {
            (row.get("codeLetter") or "").strip()
            for row in rows
            if (row.get("codeLetter") or "").strip()
        }
    )

    matching_aqls_for_code_letter = sorted(
        {
            str(to_decimal(row.get("aql")))
            for row in rows
            if (row.get("codeLetter") or "").strip() == code_letter
            and row.get("aql") is not None
        }
    )

    raise RuntimeError(
        "AQL lookup not found.\n"
        f"  Section               : {section_name}\n"
        f"  AQL Level             : {level_name}\n"
        f"  Lookup List           : {lookup_list_name}\n"
        f"  Inspection Level      : {inspection_level_code}\n"
        f"  Inspection Procedure  : {inspection_procedure_code}\n"
        f"  Target Code Letter    : {code_letter}\n"
        f"  Target AQL            : {aql_code}\n"
        f"  Available Code Letters: {matching_code_letters}\n"
        f"  Available AQLs for [{code_letter}] : {matching_aqls_for_code_letter}"
    )


def format_level_aql(level_name: str, aql_value: str) -> str:
    try:
        return f"{level_name} ({to_decimal(aql_value):.4f})"
    except Exception:
        return f"{level_name} ({aql_value})"

def calculate_actual_sample_size(section_results: list[AQLResult], total_actual_qty: int) -> int:
    sample_sizes = [
        int(result.sample_size)
        for result in section_results
        if result.sample_size is not None
    ]

    if not sample_sizes:
        raise RuntimeError("No sample sizes available to calculate actual sample size.")

    return min(max(sample_sizes), int(total_actual_qty))

def print_aql_result(level_name: str, aql_value: str, result: AQLResult) -> None:
    print(f"  - Level (AQL) : {format_level_aql(level_name, aql_value)}")
    print(
        "    AQL (sample size, accept, reject, iteration) : "
        f"{result.sample_size}, {result.acceptance_number}, "
        f"{result.rejection_number}, {result.iteration}"
    )


def print_aql_section_header(
    section: str,
    inspection_level: str,
    lookup_list_name: str,
    inspection_procedure: str,
    code_letter: str,
    calculated_sample_size: int,
) -> None:
    print(f"Section : {section}")
    print(f"Inspection Level : {inspection_level}")
    print(f"Lookup List : {lookup_list_name}")
    print(f"Inspection Procedure : {inspection_procedure}")
    print(f"Code Letter : {code_letter}")
    print(f"Calculated Sample Size : {calculated_sample_size}")
    print()


def calculate_and_print_aql(
    all_sections: list[tuple[str, AQLInfo]],
    total_actual_qty: int,
    sample_size_code_letter_rows: list[dict],
    pendulum_map: dict[str, dict],
    lookup_rows_by_name: dict[str, list[dict]],
) -> None:
    for section_name, aql_info in all_sections:
        inspection_procedure_code = (
            aql_info.inspection_procedure.code if aql_info.inspection_procedure else None
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
        aql_info.lookup_list_name = lookup_list_name
        if not lookup_list_name:
            raise RuntimeError(
                f"lookup list name is missing in pendulum map for inspectionProcedure "
                f"[{inspection_procedure_code}] in section [{section_name}]"
            )

        aql_rows = lookup_rows_by_name.get(lookup_list_name)
        if aql_rows is None:
            raise RuntimeError(
                f"AQL lookup rows not loaded for lookup list [{lookup_list_name}] "
                f"in section [{section_name}]"
            )

        inspection_level_code = (
            aql_info.inspection_level.code if aql_info.inspection_level else None
        )
        if not inspection_level_code:
            print(f"[SKIP] inspectionLevel is missing for section [{section_name}]")
            continue

        code_letter = find_code_letter(
            sample_size_code_letter_rows,
            inspection_level_code,
            total_actual_qty,
        )

        inspection_proc_name = (
            aql_info.inspection_procedure.name if aql_info.inspection_procedure else ""
        )

        level_pairs = [
            ("Critical", aql_info.critical_level),
            ("Major", aql_info.major_level),
            ("Minor", aql_info.minor_level),
        ]

        resolved_results: list[tuple[str, str, AQLResult]] = []

        for level_name, level_value in level_pairs:
            if not level_value or not level_value.code:
                continue

            result = find_aql_result(
                aql_rows,
                code_letter,
                level_value.code,
                section_name=section_name,
                level_name=level_name,
                lookup_list_name=aql_info.lookup_list_name or "",
                inspection_level_code=inspection_level_code,
                inspection_procedure_code=inspection_procedure_code,
            )
            resolved_results.append((level_name, level_value.code, result))

        if not resolved_results:
            print(f"Section : {section_name}")
            print("  - No AQL rows available")
            print()
            continue

        calculated_sample_size = calculate_actual_sample_size(
            [result for _, _, result in resolved_results],
            total_actual_qty,
        )

        print_aql_section_header(
            section_name,
            inspection_level_code,
            aql_info.lookup_list_name or "",
            inspection_proc_name,
            code_letter,
            calculated_sample_size,
        )

        for level_name, aql_value, result in resolved_results:
            print_aql_result(level_name, aql_value, result)

        missing_levels = [
            level_name
            for level_name, level_value in level_pairs
            if not level_value or not level_value.code
        ]
        for missing_level in missing_levels:
            print(f"  - [SKIP] {missing_level} level is missing")

        print()