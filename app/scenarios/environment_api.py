from app.http_client import api_request
from app.scenarios.registry import ScenarioContext, register_scenario

ENVIRONMENT_API_DESCRIPTION = """
Description:
- Environment API provides one-off environment maintenance/indexing API actions.
- Each submenu action calls the corresponding API directly.
- Action 7 prompts for a domain value and substitutes it into the request path.
""".strip()


ENVIRONMENT_API_ACTIONS = {
    "1": {
        "label": "Index Role",
        "method": "PUT",
        "path": "/api/accessObjects/indexAboutRole",
    },
    "2": {
        "label": "Index assignee",
        "method": "PUT",
        "path": "/api/accessObjects/indexAssignees",
    },
    "3": {
        "label": "Evict All Cache",
        "method": "DELETE",
        "path": "/api/cache/evictAllCache",
    },
    "4": {
        "label": "Evict Caffeine Cache",
        "method": "DELETE",
        "path": "/api/cache/getCaffeineCacheNames",
    },
    "5": {
        "label": "document fields",
        "method": "PUT",
        "path": "/api/documentFields/allModules",
    },
    "6": {
        "label": "Sections field",
        "method": "PUT",
        "path": "/api/documentFields/allSecionsField",
    },
    "7": {
        "label": "migrate to mongo",
        "method": "PUT",
        "path": "/api/defaultProfiles/migrateAllToMongo",
    },
    "8": {
        "label": "index domain",
        "method": "PUT",
        "path": "/api/domains/index/{domain}",
    },
    "9": {
        "label": "form templates",
        "method": "PUT",
        "path": "/api/formTemplates/initialize/all",
    },
    "10": {
        "label": "form ui modules",
        "method": "PUT",
        "path": "/api/formUIFields/allModules",
    },
    "11": {
        "label": "list module and level lookup",
        "method": "PUT",
        "path": "/api/sqlView/listModuleAndLevelLookup",
    },
    "12": {
        "label": "module label",
        "method": "PUT",
        "path": "/api/sqlView/moduleLabel",
    },
    "13": {
        "label": "system messages",
        "method": "PUT",
        "path": "/api/systemMessages/index/all",
    },
    "14": {
        "label": "validation profiles",
        "method": "PUT",
        "path": "/api/validationProfiles/index/all",
    },
}


def _show_environment_api_submenu() -> None:
    print("\n=== Environment API ===")
    print(ENVIRONMENT_API_DESCRIPTION)
    print()
    for key, action in ENVIRONMENT_API_ACTIONS.items():
        print(f"{key}. {action['label']}")
    print("0. Return")


def _resolve_environment_api_path(action_key: str, path_template: str) -> str | None:
    if action_key != "7":
        return path_template

    while True:
        domain = input("Enter Domain (P88/HUB): ").strip().upper()
        if domain in {"P88", "HUB"}:
            return path_template.format(domain=domain)

        print("Invalid domain. Please enter P88 or HUB.")


def _run_environment_api_action(context: ScenarioContext, action_key: str) -> None:
    action = ENVIRONMENT_API_ACTIONS[action_key]
    path = _resolve_environment_api_path(action_key, action["path"])
    if not path:
        return

    print(f"\nCalling {action['method']} {path} ...")

    response = api_request(
        context.session,
        context.credentials,
        context.auth_state,
        context.credentials_file,
        action["method"],
        path,
    )

    print(f"{action['label']}: {response.status_code}")

    body = (response.text or "").strip()
    if body:
        if len(body) > 2000:
            body = body[:2000] + "...<truncated>"
        print(body)

    print()


@register_scenario("5", "Environment API")
def scenario_environment_api(context: ScenarioContext) -> None:
    while True:
        _show_environment_api_submenu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            return

        if choice in ENVIRONMENT_API_ACTIONS:
            _run_environment_api_action(context, choice)
            continue

        print("Invalid choice. Please try again.\n")