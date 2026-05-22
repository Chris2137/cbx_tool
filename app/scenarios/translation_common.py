import json
import csv
import re
import os
import time
from datetime import datetime
from pathlib import Path
import urllib.request
from typing import Any

from app.auth import login
from app.http_client import api_request, get_json_cached
from app.scenarios.registry import ScenarioContext



OUTPUT_DIR = Path("output/translation")
LABEL_UPDATES_JSON = OUTPUT_DIR / "label_updates.json"
LABEL_UPDATES_PROGRESS_JSON = OUTPUT_DIR / "label_updates_progress.json"
LABEL_UPDATES_FAILED_DIR = OUTPUT_DIR / "failed_payloads"

def relogin_for_translation_action(context: ScenarioContext) -> None:
    print("\nRe-login with profile account...")
    context.auth_state["access_token"] = None
    context.auth_state["refresh_token"] = None
    login(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
    )
    print("Re-login succeeded.\n")


def is_untranslated_label(label: Any) -> bool:
    if not isinstance(label, str):
        return False

    text = label.strip()
    if not text:
        return False

    has_ascii_letters = bool(re.search(r"[A-Za-z]", text))
    if not has_ascii_letters:
        return False

    has_cjk = bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))
    if has_cjk:
        return False

    has_vietnamese_chars = bool(
        re.search(
            r"[À-ỹĂăÂâĐđÊêÔôƠơƯư]"
            r"|[àáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệ"
            r"ìíỉĩịòóỏõọồốổỗộờớởỡợ"
            r"ùúủũụừứửữựỳýỷỹỵ]",
            text,
        )
    )
    if has_vietnamese_chars:
        return False

    return True


def has_meaningful_label_id(label: Any, label_id: Any) -> bool:
    if not isinstance(label_id, str):
        return False

    normalized_label_id = label_id.strip()
    if not normalized_label_id:
        return False

    normalized_label = label.strip() if isinstance(label, str) else ""
    if normalized_label_id == normalized_label:
        return False

    return True


def make_path(path_parts: list[str]) -> str:
    if not path_parts:
        return "$"

    result = "$"
    for part in path_parts:
        if part.startswith("["):
            result += part
        else:
            result += f".{part}"
    return result


def add_unique_record(target: list[dict], record: dict) -> None:
    if record not in target:
        target.append(record)


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def slugify_filename(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "translation_result"


def write_translation_csv(
    title: str,
    untranslated_with_label_id: list[dict],
    untranslated_missing_label_id: list[dict],
) -> Path:
    ensure_output_dir()

    file_path = OUTPUT_DIR / f"{slugify_filename(title)}.csv"
    fieldnames = ["group", "path", "label", "labelId"]

    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in untranslated_with_label_id:
            writer.writerow(
                {
                    "group": "untranslated_with_labelId",
                    "path": item.get("path", ""),
                    "label": item.get("label", ""),
                    "labelId": item.get("labelId", ""),
                }
            )

        for item in untranslated_missing_label_id:
            writer.writerow(
                {
                    "group": "untranslated_missing_labelId",
                    "path": item.get("path", ""),
                    "label": item.get("label", ""),
                    "labelId": "",
                }
            )

    return file_path


def concatenate_translation_csvs() -> list[Path]:
    ensure_output_dir()

    csv_files = sorted(
        file_path
        for file_path in OUTPUT_DIR.glob("*.csv")
        if not file_path.name.startswith("translation_summary_")
    )

    if not csv_files:
        print("\nNo translation CSV files found to summarize.\n")
        return []

    grouped_rows: dict[str, list[dict]] = {}

    for csv_file in csv_files:
        with csv_file.open("r", encoding="utf-8-sig", newline="") as in_f:
            reader = csv.DictReader(in_f)
            for row in reader:
                group = (row.get("group") or "").strip()
                if not group:
                    group = "unknown_group"

                grouped_rows.setdefault(group, []).append(
                    {
                        "source_file": csv_file.name,
                        "path": row.get("path", ""),
                        "label": row.get("label", ""),
                        "labelId": row.get("labelId", ""),
                    }
                )

    if not grouped_rows:
        print("\nNo rows found in translation CSV files.\n")
        return []

    output_files: list[Path] = []
    fieldnames = ["source_file", "path", "label", "labelId"]

    for group, rows in sorted(grouped_rows.items()):
        output_file = OUTPUT_DIR / f"translation_summary_{slugify_filename(group)}.csv"

        with output_file.open("w", encoding="utf-8-sig", newline="") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        output_files.append(output_file)

    print("\nTranslation summary CSVs exported by group:")
    for output_file in output_files:
        print(output_file)
    print(f"Generated files: {len(output_files)}")
    print()

    return output_files


def print_translation_scan_report(
    title: str,
    untranslated_with_label_id: list[dict],
    untranslated_missing_label_id: list[dict],
) -> None:
    file_path = write_translation_csv(
        title,
        untranslated_with_label_id,
        untranslated_missing_label_id,
    )

    print(f"\n=== {title} ===")
    print(f"CSV exported: {file_path}")
    print(f"Untranslated labels with labelId     : {len(untranslated_with_label_id)}")
    print(f"Untranslated labels missing labelId : {len(untranslated_missing_label_id)}")
    print()


def scan_list_view_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    untranslated_with_label_id: list[dict] = []
    untranslated_missing_label_id: list[dict] = []

    actions = payload.get("actions") or []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue

        label = action.get("label")
        label_id = action.get("labelId")
        path = f"$.actions[{index}]"

        if is_untranslated_label(label):
            record = {
                "path": path,
                "label": label,
                "labelId": label_id,
            }
            if has_meaningful_label_id(label, label_id):
                add_unique_record(untranslated_with_label_id, record)
            else:
                add_unique_record(
                    untranslated_missing_label_id,
                    {"path": path, "label": label},
                )

        items = action.get("items") or []
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            item_label = item.get("label")
            item_label_id = item.get("labelId")
            item_path = f"$.actions[{index}].items[{item_index}]"

            if is_untranslated_label(item_label):
                record = {
                    "path": item_path,
                    "label": item_label,
                    "labelId": item_label_id,
                }
                if has_meaningful_label_id(item_label, item_label_id):
                    add_unique_record(untranslated_with_label_id, record)
                else:
                    add_unique_record(
                        untranslated_missing_label_id,
                        {"path": item_path, "label": item_label},
                    )

    columns = payload.get("columns") or []
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            continue

        label = column.get("label")
        label_id = column.get("labelId")
        path = f"$.columns[{index}]"

        if is_untranslated_label(label):
            record = {
                "path": path,
                "label": label,
                "labelId": label_id,
            }
            if has_meaningful_label_id(label, label_id):
                add_unique_record(untranslated_with_label_id, record)
            else:
                add_unique_record(
                    untranslated_missing_label_id,
                    {"path": path, "label": label},
                )

    return untranslated_with_label_id, untranslated_missing_label_id


def scan_detail_payload(payload: Any) -> tuple[list[dict], list[dict]]:
    untranslated_with_label_id: list[dict] = []
    untranslated_missing_label_id: list[dict] = []

    def walk(node: Any, path_parts: list[str]) -> None:
        if isinstance(node, dict):
            label = node.get("label")
            if is_untranslated_label(label):
                label_id = node.get("labelId")
                path = make_path(path_parts)
                record = {
                    "path": path,
                    "label": label,
                    "labelId": label_id,
                }
                if has_meaningful_label_id(label, label_id):
                    add_unique_record(untranslated_with_label_id, record)
                else:
                    add_unique_record(
                        untranslated_missing_label_id,
                        {"path": path, "label": label},
                    )

            for key, value in node.items():
                walk(value, path_parts + [str(key)])

        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, path_parts + [f"[{index}]"])

    walk(payload, [])
    return untranslated_with_label_id, untranslated_missing_label_id


def fetch_and_scan_list_view(
    context: ScenarioContext,
    title: str,
    endpoints: list[str],
) -> None:
    untranslated_with_label_id: list[dict] = []
    untranslated_missing_label_id: list[dict] = []

    for endpoint in endpoints:
        request_cache: dict = {}
        payload = get_json_cached(
            context.session,
            context.credentials,
            context.auth_state,
            context.credentials_file,
            request_cache,
            "GET",
            f"/{endpoint.lstrip('/')}",
        )

        matched, missing = scan_list_view_payload(payload)

        for item in matched:
            add_unique_record(
                untranslated_with_label_id,
                {
                    "path": f"{endpoint} :: {item['path']}",
                    "label": item["label"],
                    "labelId": item["labelId"],
                },
            )

        for item in missing:
            add_unique_record(
                untranslated_missing_label_id,
                {
                    "path": f"{endpoint} :: {item['path']}",
                    "label": item["label"],
                },
            )

    print_translation_scan_report(
        title,
        untranslated_with_label_id,
        untranslated_missing_label_id,
    )


def fetch_and_scan_detail_view(
    context: ScenarioContext,
    title: str,
    endpoint: str,
) -> None:
    request_cache: dict = {}
    payload = get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        f"/{endpoint.lstrip('/')}",
    )

    untranslated_with_label_id, untranslated_missing_label_id = scan_detail_payload(payload)

    for item in untranslated_with_label_id:
        item["path"] = f"{endpoint} :: {item['path']}"

    for item in untranslated_missing_label_id:
        item["path"] = f"{endpoint} :: {item['path']}"

    print_translation_scan_report(
        title,
        untranslated_with_label_id,
        untranslated_missing_label_id,
    )

def prepare_ready_to_translate_csv() -> Path | None:
    ensure_output_dir()

    source_file = OUTPUT_DIR / "translation_summary_untranslated_with_labelid.csv"
    output_file = OUTPUT_DIR / "ready_to_translate.csv"

    if not source_file.exists():
        print(f"\nSource file not found: {source_file}\n")
        return None

    fieldnames = [
        "label",
        "labelId",
        "es_ES",
        "fr_CA",
        "id_ID",
        "it_IT",
        "ja_JP",
        "pt_BR",
        "tr_TR",
        "vi_VN",
        "zh_CN",
    ]

    row_count = 0

    with source_file.open("r", encoding="utf-8-sig", newline="") as in_f:
        reader = csv.DictReader(in_f)

        with output_file.open("w", encoding="utf-8-sig", newline="") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                writer.writerow(
                    {
                        "label": row.get("label", ""),
                        "labelId": row.get("labelId", ""),
                        "es_ES": "",
                        "fr_CA": "",
                        "id_ID": "",
                        "it_IT": "",
                        "ja_JP": "",
                        "pt_BR": "",
                        "tr_TR": "",
                        "vi_VN": "",
                        "zh_CN": "",
                    }
                )
                row_count += 1

    print("\nReady-to-translate CSV exported:")
    print(output_file)
    print(f"Rows written: {row_count}")
    print()

    return output_file

def run_translate_ready_to_translate_csv() -> Path | None:
    ensure_output_dir()

    source_file = OUTPUT_DIR / "ready_to_translate.csv"
    output_file = OUTPUT_DIR / "ready_to_translate_translated.csv"

    if not source_file.exists():
        print(f"\nSource file not found: {source_file}\n")
        return None

    base_url = input("LibreTranslate base URL [http://localhost:8080]: ").strip() or "http://localhost:8080"
    sleep_seconds_raw = input("Sleep seconds between labels [0]: ").strip() or "0"

    try:
        sleep_seconds = float(sleep_seconds_raw)
    except ValueError:
        print("\nInvalid sleep seconds.\n")
        return None

    locales = [
        "es_ES",
        "fr_CA",
        "id_ID",
        "it_IT",
        "ja_JP",
        "pt_BR",
        "tr_TR",
        "vi_VN",
        "zh_CN",
    ]
    language_map = {
        "es_ES": "es",
        "fr_CA": "fr",
        "id_ID": "id",
        "it_IT": "it",
        "ja_JP": "ja",
        "pt_BR": "pt",
        "tr_TR": "tr",
        "vi_VN": "vi",
        "zh_CN": "zh",
    }

    shorthand_tokens = {
        "id", "no", "no.", "qty", "amt", "sku", "vpo", "cpm", "cap",
        "seq", "ref", "po", "aql", "qc", "qa", "api", "ui",
    }

    def normalize_text(text: Any) -> str:
        return text.strip() if isinstance(text, str) else ""

    def is_technical_shorthand(label: str) -> bool:
        text = normalize_text(label)
        if not text:
            return False

        parts = re.findall(r"[A-Za-z0-9_.#]+", text)
        if not parts:
            return False

        lowered = {part.lower() for part in parts}

        if text.isupper() and len(text) <= 10:
            return True

        if lowered.issubset(shorthand_tokens):
            return True

        if any(part.isupper() and len(part) <= 6 for part in parts):
            return True

        if any(part.lower() in shorthand_tokens for part in parts):
            return True

        return False

    def translate_text(text: str, target_lang: str) -> str:
        payload = {
            "q": text,
            "source": "en",
            "target": target_lang,
            "format": "text",
        }

        request = urllib.request.Request(
            url=f"{base_url.rstrip('/')}/translate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")

        parsed = json.loads(body)
        translated = parsed.get("translatedText")
        if not isinstance(translated, str):
            raise ValueError(f"Unexpected translation response: {parsed}")

        return translated.strip()

    with source_file.open("r", encoding="utf-8-sig", newline="") as in_f:
        reader = csv.DictReader(in_f)
        rows = list(reader)

    if not rows:
        print("\nNo rows found in source CSV.\n")
        return None

    fieldnames = list(rows[0].keys())
    for locale in locales:
        if locale not in fieldnames:
            fieldnames.append(locale)

    cache: dict[str, dict[str, str]] = {}
    output_rows: list[dict] = []
    total = len(rows)

    for index, row in enumerate(rows, start=1):
        label = normalize_text(row.get("label", ""))
        print(f"[{index}/{total}] {label}")

        if not label:
            translated_map = {locale: "" for locale in locales}
        elif label in cache:
            translated_map = cache[label]
        elif is_technical_shorthand(label):
            translated_map = {locale: label for locale in locales}
            cache[label] = translated_map
        else:
            translated_map = {}
            for locale in locales:
                translated_map[locale] = translate_text(label, language_map[locale])
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            cache[label] = translated_map

        new_row = dict(row)
        for locale in locales:
            new_row[locale] = translated_map.get(locale, "")
        output_rows.append(new_row)

    with output_file.open("w", encoding="utf-8-sig", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print("\nTranslated CSV exported:")
    print(output_file)
    print(f"Rows written: {len(output_rows)}")
    print()

    return output_file

def prepare_label_updates_json() -> Path | None:
    ensure_output_dir()

    source_file = OUTPUT_DIR / "ready_to_translate_translated.csv"
    output_file = LABEL_UPDATES_JSON

    if not source_file.exists():
        print(f"\nSource file not found: {source_file}\n")
        return None

    locale_columns = [
        "es_ES",
        "fr_CA",
        "id_ID",
        "it_IT",
        "ja_JP",
        "pt_BR",
        "tr_TR",
        "vi_VN",
        "zh_CN",
    ]

    updates: list[dict] = []

    with source_file.open("r", encoding="utf-8-sig", newline="") as in_f:
        reader = csv.DictReader(in_f)

        for row in reader:
            label_id = (row.get("labelId") or "").strip()
            if not label_id:
                continue

            module_code = resolve_module_code_from_label_id(label_id)
            if not module_code:
                continue

            for locale in locale_columns:
                translated_label = (row.get(locale) or "").strip()
                if not translated_label:
                    continue

                updates.append(
                    {
                        "labelId": label_id,
                        "locale": locale,
                        "label": translated_label,
                        "moduleCode": module_code,
                    }
                )

    with output_file.open("w", encoding="utf-8") as out_f:
        json.dump(updates, out_f, ensure_ascii=False, indent=2)

    print("\nLabel updates JSON exported:")
    print(output_file)
    print(f"Items written: {len(updates)}")
    print()

    return output_file

def send_label_updates_json(context: ScenarioContext) -> None:
    ensure_output_dir()

    source_file = LABEL_UPDATES_JSON
    progress_file = LABEL_UPDATES_PROGRESS_JSON
    batch_size = 100

    if not source_file.exists():
        print(f"\nSource file not found: {source_file}\n")
        return

    with source_file.open("r", encoding="utf-8") as in_f:
        items = json.load(in_f)

    if not isinstance(items, list):
        print("\nInvalid JSON payload format. Expected a list.\n")
        return

    total_items = len(items)
    if total_items == 0:
        print("\nNo label updates to send.\n")
        return

    start_index = 0
    if progress_file.exists():
        with progress_file.open("r", encoding="utf-8") as progress_f:
            progress = json.load(progress_f)

        source_file_in_progress = progress.get("source_file")
        if source_file_in_progress == str(source_file):
            last_successful_index = progress.get("last_successful_index", -1)
            if isinstance(last_successful_index, int) and last_successful_index >= 0:
                start_index = last_successful_index + 1

    print(f"\nSource file : {source_file}")
    print(f"Total items : {total_items}")
    print(f"Batch size  : {batch_size}")
    print(f"Resume from : {start_index}")
    print()

    if start_index >= total_items:
        print("All items have already been processed.\n")
        return

    confirm = input("Proceed to call PUT api/labels? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.\n")
        return

    batch_number = (start_index // batch_size) + 1
    total_batches = (total_items + batch_size - 1) // batch_size

    for batch_start in range(start_index, total_items, batch_size):
        batch_end = min(batch_start + batch_size, total_items)
        batch_items = items[batch_start:batch_end]

        print(
            f"Sending batch {batch_number}/{total_batches} "
            f"(items {batch_start} to {batch_end - 1}) ..."
        )

        try:
            response = api_request(
                context.session,
                context.credentials,
                context.auth_state,
                context.credentials_file,
                "PUT",
                "/api/labels",
                json=batch_items,
            )
        except Exception as exc:
            failed_file = _export_failed_label_update_payload(
                batch_items=batch_items,
                batch_number=batch_number,
                batch_start=batch_start,
                batch_end=batch_end,
                exc=exc,
            )
            print("\nBatch failed.")
            print(f"Failed payload exported to: {failed_file}\n")
            raise

        progress_payload = {
            "source_file": str(source_file),
            "total_items": total_items,
            "batch_size": batch_size,
            "last_successful_index": batch_end - 1,
            "last_successful_batch": batch_number,
            "completed": batch_end >= total_items,
        }

        with progress_file.open("w", encoding="utf-8") as progress_f:
            json.dump(progress_payload, progress_f, ensure_ascii=False, indent=2)

        print(
            f"Batch {batch_number} succeeded. "
            f"Progress saved through item {batch_end - 1}."
        )

        batch_number += 1

    print("\nAll label updates have been sent successfully.")
    print(f"Progress file: {progress_file}")
    print()

def change_user_language(context: ScenarioContext) -> None:
    print("\nLoading current user info...")

    current_user_response = api_request(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        "GET",
        "/api/users/current",
    )
    current_user_data = current_user_response.json()

    ref_no = current_user_data.get("refNo")
    current_language = current_user_data.get("language") or {}

    print(f"Current language: {current_language}")

    if not ref_no:
        print("\nCurrent user refNo not found.\n")
        return

    print(f"Current user refNo: {ref_no}")

    print("\nLoading available system languages...")
    codelist_response = api_request(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        "GET",
        "/api/codelists",
        params={
            "filterByDisable": "true",
            "ownerDomain": "true",
            "names": "SYSTEM_LANGUAGE",
        },
    )
    codelist_data = codelist_response.json()

    if not isinstance(codelist_data, dict):
        print("\nUnexpected codelist response format.\n")
        return

    system_language = codelist_data.get("SYSTEM_LANGUAGE")
    if not isinstance(system_language, dict):
        print("\nSYSTEM_LANGUAGE not found in codelist response.\n")
        return

    reference_data_list = system_language.get("referenceDataList") or []
    language_options: list[dict] = []

    for item in reference_data_list:
        code = (item.get("code") or "").strip()
        name = (item.get("name") or "").strip()
        version = item.get("version")

        if not code or not name or version is None:
            continue

        language_options.append(
            {
                "code": code,
                "name": name,
                "version": version,
            }
        )

    if not language_options:
        print("\nNo selectable system languages found.\n")
        return

    print("\nAvailable languages:")
    for idx, language in enumerate(language_options, start=1):
        marker = ""
        if (
            language["code"] == current_language.get("code")
            and language["name"] == current_language.get("name")
        ):
            marker = " [current]"

        print(
            f"{idx}. {language['name']} ({language['code']}) "
            f"[version={language['version']}]"
            f"{marker}"
        )

    print("0. Cancel")
    print()

    while True:
        raw = input("Choose a language: ").strip()
        if raw == "0":
            print("Cancelled.\n")
            return

        if raw.isdigit():
            selected_index = int(raw)
            if 1 <= selected_index <= len(language_options):
                selected_language = language_options[selected_index - 1]
                break

        print("Invalid choice. Please try again.")

    if (
        selected_language["code"] == current_language.get("code")
        and selected_language["name"] == current_language.get("name")
        and selected_language["version"] == current_language.get("version")
    ):
        print("\nSelected language is already the current language. No change needed.\n")
        return

    print("\nLoading full user detail...")

    user_detail_response = api_request(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        "GET",
        f"/api/users/{ref_no}",
    )
    user_detail_data = user_detail_response.json()

    if not isinstance(user_detail_data, dict):
        print("\nUnexpected user detail response format.\n")
        return

    previous_language = user_detail_data.get("language") or {}
    user_detail_data["language"] = {
        "code": selected_language["code"],
        "name": selected_language["name"],
        "version": selected_language["version"],
    }

    print("\nLanguage update preview:")
    print(f"From: {previous_language}")
    print(f"To  : {user_detail_data['language']}")
    print()

    confirm = input("Proceed to save and confirm user language change? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.\n")
        return

    save_response = api_request(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        "POST",
        "/api/users",
        params={"action": "saveAndConfirm"},
        json=user_detail_data,
    )

    saved_user_data = save_response.json()
    saved_language = saved_user_data.get("language") if isinstance(saved_user_data, dict) else None

    print("\nUser language updated successfully.")
    print(f"Saved language: {saved_language}")
    print()

def _export_failed_label_update_payload(
    batch_items: list[dict],
    batch_number: int,
    batch_start: int,
    batch_end: int,
    exc: Exception,
) -> Path:
    ensure_output_dir()
    LABEL_UPDATES_FAILED_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = LABEL_UPDATES_FAILED_DIR / (
        f"label_updates_failed_batch_{batch_number}_"
        f"{batch_start}_{batch_end - 1}_{timestamp}.json"
    )

    payload = {
        "batchNumber": batch_number,
        "batchStartIndex": batch_start,
        "batchEndIndex": batch_end - 1,
        "itemCount": len(batch_items),
        "errorType": type(exc).__name__,
        "errorMessage": str(exc),
        "items": batch_items,
    }

    with file_path.open("w", encoding="utf-8") as out_f:
        json.dump(payload, out_f, ensure_ascii=False, indent=2)

    return file_path

def resolve_module_code_from_label_id(label_id: str) -> str | None:
    parts = [part.strip() for part in label_id.split(".") if part.strip()]
    if len(parts) < 2:
        return None

    last_token = parts[-1]
    second_token = parts[1]

    cust_field_def_tokens = {
        "custAggregate1",
        "custAggregate10",
        "custAggregate11",
        "custAggregate12",
        "custAggregate13",
        "custAggregate14",
        "custAggregate15",
        "custAggregate16",
        "custAggregate17",
        "custAggregate18",
        "custAggregate2",
        "custAggregate20",
        "custAggregate3",
        "custAggregate5",
        "custAggregate7",
        "custAggregate8",
        "custAggregate9",
        "custCheckbox1",
        "custCheckbox3",
        "custCodelist1",
        "custCodelist11",
        "custCodelist12",
        "custCodelist13",
        "custCodelist14",
        "custCodelist2",
        "custCodelist3",
        "custCodelist4",
        "custCodelist5",
        "custCodelist6",
        "custCodelist7",
        "custDate1",
        "custDate2",
        "custDate3",
        "custDate4",
        "custDate5",
        "custDate6",
        "custDate7",
        "custDecimal1",
        "custDecimal2",
        "custDecimal3",
        "custDecimal4",
        "custDecimal5",
        "custDecimal6",
        "custDecimal7",
        "custDecimal8",
        "custFieldDef",
        "custFieldDefId",
        "custFieldDefItem",
        "custFields",
        "custHcl1",
        "custMemoText1",
        "custMemoText2",
        "custMemoText3",
        "custMemoText4",
        "custMemoText5",
        "custMemoText6",
        "custMemoText7",
        "custMemoText8",
        "custMemoText9",
        "custNumber1",
        "custNumber11",
        "custNumber12",
        "custNumber13",
        "custNumber14",
        "custNumber15",
        "custNumber16",
        "custNumber2",
        "custNumber3",
        "custNumber4",
        "custSelection1",
        "custText1",
        "custText10",
        "custText11",
        "custText12",
        "custText13",
        "custText14",
        "custText15",
        "custText16",
        "custText17",
        "custText18",
        "custText19",
        "custText2",
        "custText20",
        "custText3",
        "custText31",
        "custText32",
        "custText33",
        "custText34",
        "custText35",
        "custText36",
        "custText37",
        "custText38",
        "custText39",
        "custText4",
        "custText40",
        "custText41",
        "custText42",
        "custText43",
        "custText5",
        "custText6",
        "custText7",
        "custText8",
        "custText9",
        "custTimestamp1",
        "customDocAction01",
        "customDocAction02",
        "customDocAction03",
        "customDocAction04",
        "customDocAction05",
        "customDocAction06",
        "customDocAction07",
        "customDocAction08",
        "customDocAction09",
        "customDocAction10",
        "customExport01",
        "customExport02",
        "customExport03",
        "customExport04",
        "customExport05",
        "customExport06",
        "customExport07",
        "customExport08",
        "customExport09",
        "customExport10",
        "customPrint01",
        "customPrint02",
        "customPrint03",
        "customPrint04",
        "customPrint05",
        "customPrint06",
        "customPrint07",
        "customPrint08",
        "customPrint09",
        "customPrint10",
    }

    if last_token in cust_field_def_tokens:
        return "custFieldDef"

    special_mappings = {
        "PersonalizeView": "view",
    }

    return special_mappings.get(second_token, second_token)