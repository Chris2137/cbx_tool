import requests

from app.auth import login
from app.config import load_selected_credentials
from app.debug_utils import mask_value
from app.http_client import try_resume_session
from app.scenarios import show_main_menu
from app.scenarios.registry import ScenarioContext


def main() -> None:
    profile_name, credentials, credentials_file = load_selected_credentials()

    print("\nUsing credential profile:")
    print(f"  profile   : {profile_name}")
    print(f"  server    : {credentials.get('server', '')}")
    print(f"  username  : {credentials.get('username', '')}")
    # print(f"  client_id : {mask_value(credentials.get('CLIENT_ID', ''))}")

    session = requests.Session()
    auth_state: dict = {
        "access_token": None,
        "refresh_token": None,
    }

    resumed = try_resume_session(session, credentials, auth_state, credentials_file)
    if not resumed:
        login(session, credentials, auth_state, credentials_file)
        print("Login succeeded.")

    context = ScenarioContext(
        session=session,
        credentials=credentials,
        auth_state=auth_state,
        credentials_file=credentials_file,
    )

    show_main_menu(context)


if __name__ == "__main__":
    main()