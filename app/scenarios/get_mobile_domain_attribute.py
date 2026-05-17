import json

from app.http_client import get_json_cached
from app.scenarios.registry import ScenarioContext, register_scenario


DOMAIN_ATTRIBUTE_KEY = "mobile.custom.features.domain"


def fetch_mobile_domain_attribute(context: ScenarioContext, request_cache: dict):
    return get_json_cached(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        request_cache,
        "GET",
        "/api/domainAttributes",
        params={"key": DOMAIN_ATTRIBUTE_KEY},
    )


def decode_domain_attribute_value(payload: dict):
    value = payload.get("value")
    if value is None:
        raise RuntimeError("Response does not contain a 'value' field.")

    if not isinstance(value, str):
        raise RuntimeError(
            f"Response field 'value' is not a string. Actual type: {type(value).__name__}"
        )

    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "The 'value' field is not valid JSON.\n"
            f"Reason   : {e.msg}\n"
            f"Line     : {e.lineno}\n"
            f"Column   : {e.colno}\n"
            f"Position : {e.pos}\n"
            f"Escaped value:\n{value}"
        ) from e


def print_current_domain_attribute(payload: dict) -> None:
    print("\nMobile Domain Attribute (raw response)")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    decoded_value = decode_domain_attribute_value(payload)

    print("Mobile Domain Attribute (decoded JSON)")
    print(json.dumps(decoded_value, indent=2, ensure_ascii=False))
    print()


def prompt_multiline_json_input() -> str:
    print("\nEnter updated decoded JSON.")
    print("Press Enter on an empty line to cancel and return.")
    print("Or finish input with a line containing only END.")

    lines = []
    first_line = True

    while True:
        line = input()

        if first_line and not line.strip():
            return ""

        first_line = False

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def prompt_for_valid_decoded_json():
    while True:
        raw_input_text = prompt_multiline_json_input()

        if not raw_input_text:
            return None

        try:
            parsed = json.loads(raw_input_text)
            return parsed
        except json.JSONDecodeError as e:
            print("Invalid JSON. Please re-input.")
            print(f"Reason   : {e.msg}")
            print(f"Line     : {e.lineno}")
            print(f"Column   : {e.colno}")
            print(f"Position : {e.pos}")
            print()


def build_escaped_domain_attribute_value(decoded_json_obj) -> str:
    raw_json = json.dumps(decoded_json_obj, separators=(",", ":"), ensure_ascii=False)
    return raw_json.replace("\\", "\\\\").replace('"', '\\"')


def confirm_escaped_json_to_apply(decoded_json_obj) -> bool:
    escaped_json = build_escaped_domain_attribute_value(decoded_json_obj)

    print("\nIt is the JSON to be applied, confirm? (y/n)")
    print(escaped_json)

    while True:
        answer = input("> ").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("Please enter y or n.")


def perform_update_placeholder(context: ScenarioContext, decoded_json_obj) -> None:
    escaped_json = build_escaped_domain_attribute_value(decoded_json_obj)

    print("\n[TODO] Update domain attribute action is not implemented yet.")
    print("Confirmed escaped JSON to apply:")
    print(escaped_json)
    print()


@register_scenario("3", "Check and update Mobile Domain Attribute")
def scenario_check_and_update_mobile_domain_attribute(context: ScenarioContext) -> None:
    request_cache: dict = {}

    while True:
        try:
            payload = fetch_mobile_domain_attribute(context, request_cache)
            print_current_domain_attribute(payload)
        except Exception as e:
            print("\nERROR while retrieving or decoding mobile domain attribute:")
            print(str(e))
            print()

        print("1. Update")
        print("2. Return")

        choice = input("Choose an option: ").strip()

        if choice == "2":
            return

        if choice != "1":
            print("Invalid choice. Please try again.\n")
            continue

        decoded_json_obj = prompt_for_valid_decoded_json()
        if decoded_json_obj is None:
            print()
            continue

        confirmed = confirm_escaped_json_to_apply(decoded_json_obj)
        if not confirmed:
            print()
            continue

        perform_update_placeholder(context, decoded_json_obj)