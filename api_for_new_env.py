import base64
import json
import requests

# BASE_URL = "https://apollo88-master.tradebeyond.com" #done
# BASE_URL = "https://dorel-sandbox.tradebeyond.com" #done
# BASE_URL = "https://figs-sandbox.tradebeyond.com" #done
# BASE_URL = "https://asics-sandbox.tradebeyond.com" #done
# BASE_URL = "https://drmartens-sandbox.tradebeyond.com" #done 
# BASE_URL = "https://nbrown-sandbox.tradebeyond.com" #done
# BASE_URL = "https://hhgroupdcs.tradebeyond.com" #done
BASE_URL = "https://threesixty.tradebeyond.com" 
CLIENT_ID = "cbx"
CLIENT_SECRET = "cbx@123"

# USERNAME = "chris.au@cbxsoftware.com"
USERNAME = "chris.au@test.cbxsoftware.com"
PASSWORD = "Core@1234"

TOKEN_URL = f"{BASE_URL}/oauth2/token"

# API_CALLS = [
#     {
#         "name": "1. Index Role",
#         "method": "PUT",
#         "url": f"{BASE_URL}/api/accessObjects/indexAboutRole"
#     },
#     {
#         "name": "13. validation profiles",
#         "method": "PUT",
#         "url": f"{BASE_URL}/api/validationProfiles/index/all"
#     }
# ]

API_CALLS = [
    {
        "name": "1. Index Role",
        "method": "PUT",
        "url": f"{BASE_URL}/api/accessObjects/indexAboutRole"
    },
    {
        "name": "2. Index assignee",
        "method": "PUT",
        "url": f"{BASE_URL}/api/accessObjects/indexAssignees"
    },
    {
        "name": "3. Evict All Cache",
        "method": "DELETE",
        "url": f"{BASE_URL}/api/cache/evictAllCache"
    },
    {
        "name": "4. document fields",
        "method": "PUT",
        "url": f"{BASE_URL}/api/documentFields/allModules"
    },
    {
        "name": "5. Sections field",
        "method": "PUT",
        "url": f"{BASE_URL}/api/documentFields/allSecionsField"
    },
    {
        "name": "6. migrate to mongo",
        "method": "PUT",
        "url": f"{BASE_URL}/api/defaultProfiles/migrateAllToMongo"
    },
    {
        "name": "7. index domain",
        "method": "PUT",
        "url": f"{BASE_URL}/api/domains/index/HUB"
    },
    {
        "name": "8. form templates",
        "method": "PUT",
        "url": f"{BASE_URL}/api/formTemplates/initialize/all"
    },
    {
        "name": "9. form ui modules",
        "method": "PUT",
        "url": f"{BASE_URL}/api/formUIFields/allModules"
    },
    {
        "name": "10. list module and level lookup",
        "method": "PUT",
        "url": f"{BASE_URL}/api/sqlView/listModuleAndLevelLookup"
    },
    {
        "name": "11. module label",
        "method": "PUT",
        "url": f"{BASE_URL}/api/sqlView/moduleLabel"
    },
    {
        "name": "12. system messages",
        "method": "PUT",
        "url": f"{BASE_URL}/api/systemMessages/index/all"
    },
    {
        "name": "13. validation profiles",
        "method": "PUT",
        "url": f"{BASE_URL}/api/validationProfiles/index/all"
    }
]

def get_basic_auth_header(client_id, client_secret):
    raw = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"

def get_access_token():
    headers = {
        "Authorization": get_basic_auth_header(CLIENT_ID, CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    print(f"Auth response code: {response.status_code}")

    response.raise_for_status()

    response_json = response.json()
    access_token = response_json.get("access_token")

    if not access_token:
        raise ValueError("access_token not found in authentication response")

    return access_token

def call_apis(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for api in API_CALLS:
        method = api["method"].upper()
        url = api["url"]
        name = api.get("name", url)
        payload = api.get("json")

        try:
            if method == "PUT":
                response = requests.put(url, headers=headers, json=payload, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, json=payload, timeout=30)
            else:
                print(f"{name}: Unsupported method {method}")
                continue

            print(f"{name}: {response.status_code}")

        except requests.RequestException as e:
            print(f"{name}: Request failed - {e}")

def main():
    token = get_access_token()
    call_apis(token)

if __name__ == "__main__":
    main()