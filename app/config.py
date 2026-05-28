from configparser import ConfigParser
from io import StringIO
from pathlib import Path

import requests

TOKEN_PATH = "/oauth2/token"
CREDENTIALS_DIR = Path("credentials")

DEBUG = False
DEBUG_LOG_FILE = "output.log"


def load_properties_file(file_path: Path) -> dict:
    raw_text = file_path.read_text(encoding="utf-8")
    parser = ConfigParser()
    parser.optionxform = str
    parser.read_file(StringIO("[DEFAULT]\n" + raw_text))
    return dict(parser["DEFAULT"])


def list_credential_profiles():
    files = sorted(CREDENTIALS_DIR.glob("*.properties"))
    profiles = [(file_path.stem, file_path) for file_path in files if file_path.is_file()]
    if not profiles:
        raise FileNotFoundError(f"No .properties files found in {CREDENTIALS_DIR}")
    return profiles


def check_server_versions_for_all_profiles() -> None:
    from app.auth import login
    from app.http_client import api_request
    import json

    profiles = list_credential_profiles()

    print("\nChecking server version for all profiles:\n")

    for profile_name, file_path in profiles:
        print(f"[{profile_name}]")

        try:
            credentials = load_properties_file(file_path)
            session = requests.Session()
            auth_state = {
                "access_token": None,
                "refresh_token": None,
            }

            login(session, credentials, auth_state, file_path)

            response = api_request(
                session=session,
                credentials=credentials,
                auth_state=auth_state,
                credentials_file=file_path,
                method="GET",
                path="api/system/releaseLog",
            )

            # print("  status code:")
            # print(f"  {response.status_code}")

            # print("  raw response text:")
            # print(response.text)

            payload = response.json()

            # print("  parsed response:")
            # print(json.dumps(payload, indent=2, ensure_ascii=False))

            version = ""
            if isinstance(payload, dict):
                version = payload.get("version", "") or ""

            print(f"  version : {version or '<missing>'}")

        except Exception as exc:
            print(f"  version : <error> {exc}")

        print()


def prompt_select_profile():
    profiles = list_credential_profiles()

    while True:
        print("\nAvailable credential profiles:")
        for idx, (profile_name, _) in enumerate(profiles, start=1):
            print(f"  {idx}. {profile_name}")
        print("  v. Check server version")
        print("  q. Quit")

        choice = input("\nSelect profile: ").strip().lower()

        if choice == "v":
            check_server_versions_for_all_profiles()
            continue

        if choice == "q":
            raise SystemExit(0)

        if not choice.isdigit():
            print("Invalid input. Please enter a number, 'v', or 'q'.")
            continue

        index = int(choice)
        if 1 <= index <= len(profiles):
            return profiles[index - 1]

        print(f"Invalid choice. Enter a number between 1 and {len(profiles)}.")


def load_selected_credentials():
    profile_name, file_path = prompt_select_profile()
    credentials = load_properties_file(file_path)
    return profile_name, credentials, file_path


def save_tokens(file_path: str | Path, credentials: dict, auth_state: dict) -> None:
    path = Path(file_path)

    merged = dict(credentials)

    access_token = auth_state.get("access_token")
    refresh_token = auth_state.get("refresh_token")

    if access_token:
        merged["access_token"] = access_token
    else:
        merged.pop("access_token", None)

    if refresh_token:
        merged["refresh_token"] = refresh_token
    else:
        merged.pop("refresh_token", None)

    lines = [f"{key}={value}" for key, value in merged.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")