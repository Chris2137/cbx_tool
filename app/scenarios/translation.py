from app.scenarios.registry import ScenarioContext, register_scenario
from app.scenarios.translation_common import (
    change_user_language,
    concatenate_translation_csvs,
    fetch_and_scan_detail_view,
    fetch_and_scan_list_view,
    prepare_label_updates_json,
    prepare_ready_to_translate_csv,
    relogin_for_translation_action,
    run_translate_ready_to_translate_csv,
    send_label_updates_json,
)


TRANSLATION_DESCRIPTION = """
Description:
- Action 2 to 7 serves to download the page label from formDefine and save the result in output/translation as csv files.
- Action 8 concatenate the csv into summarized result files, so that we get two files: one for labels with labelId that are untranslated, another one for labels without labelId that requires developer follow-up to add back the labelId.
- Action 9 prepare the csv file with all language columns that we need to translate, so the file can be uploaded for AI translation.
- Action 10 reads ready_to_translate.csv, calls the local LibreTranslate service, fills the language columns, and exports ready_to_translate_translated.csv.
- Action 11 prepares label_updates.json from ready_to_translate_translated.csv, including translated locales only and excluding en_US.
- (needs to start the docker instance in docker folder to support local translation)
- Action 12 sends label_updates.json to PUT api/labels in batches of 100 and stores progress so reruns can resume safely.
- Action 13 changes the current user's language using SYSTEM_LANGUAGE codelist options.
""".strip()


def _show_translation_submenu() -> None:
    print("\n=== Translation ===")
    print(TRANSLATION_DESCRIPTION)
    print()
    print("1. Re-login")
    print("2. Booking List Page")
    print("3. Report List Page")
    print("4. Audit List Page")
    print("5. Booking Detail Page")
    print("6. Report Detail Page")
    print("7. Audit Detail Page")
    print("8. Concatenate CSV Summary")
    print("9. Prepare Ready To Translate CSV")
    print("10. Translate Ready To Translate CSV")
    print("11. Prepare Label Update JSON")
    print("12. Send Label Update JSON")
    print("13. Change User Language")
    print("0. Return")


def _run_booking_list_page(context: ScenarioContext) -> None:
    fetch_and_scan_list_view(
        context,
        "Booking List Page",
        [
            "api/views/v2/inspectBookingView",
            "api/views/v2/inspectBookingMyBookingView",
            "api/views/v2/inspectBookingActiveView",
            "api/views/v2/inspectBookingItemColorSizeView",
        ],
    )


def _run_report_list_page(context: ScenarioContext) -> None:
    fetch_and_scan_list_view(
        context,
        "Report List Page",
        [
            "api/views/v2/inspectReportView",
        ],
    )


def _run_audit_list_page(context: ScenarioContext) -> None:
    fetch_and_scan_list_view(
        context,
        "Audit List Page",
        [
            "api/views/v2/factAuditView",
        ],
    )


def _run_booking_detail_page(context: ScenarioContext) -> None:
    fetch_and_scan_detail_view(
        context,
        "Booking Detail Page",
        "api/forms/inspectBooking/define",
    )


def _run_report_detail_page(context: ScenarioContext) -> None:
    fetch_and_scan_detail_view(
        context,
        "Report Detail Page",
        "api/forms/inspectReport/define",
    )


def _run_audit_detail_page(context: ScenarioContext) -> None:
    fetch_and_scan_detail_view(
        context,
        "Audit Detail Page",
        "api/forms/factAudit/define",
    )


@register_scenario("4", "Translation")
def scenario_translation(context: ScenarioContext) -> None:
    while True:
        _show_translation_submenu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            return
        if choice == "1":
            relogin_for_translation_action(context)
            continue
        if choice == "2":
            _run_booking_list_page(context)
            continue
        if choice == "3":
            _run_report_list_page(context)
            continue
        if choice == "4":
            _run_audit_list_page(context)
            continue
        if choice == "5":
            _run_booking_detail_page(context)
            continue
        if choice == "6":
            _run_report_detail_page(context)
            continue
        if choice == "7":
            _run_audit_detail_page(context)
            continue
        if choice == "8":
            concatenate_translation_csvs()
            continue
        if choice == "9":
            prepare_ready_to_translate_csv()
            continue
        if choice == "10":
            run_translate_ready_to_translate_csv()
            continue
        if choice == "11":
            prepare_label_updates_json()
            continue
        if choice == "12":
            send_label_updates_json(context)
            continue
        if choice == "13":
            change_user_language(context)
            continue

        print("Invalid choice. Please try again.\n")