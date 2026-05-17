import json
import time
from pathlib import Path

import requests

API_URL = "https://adidas-qa.tradebeyond.com:443/api/labels"
ACCESS_TOKEN = "eyJraWQiOiJjYnhSZXN0QDEyMyIsImFsZyI6IlJTMjU2In0.eyJzdWJzdGl0dXRlVXNlciI6IiIsInN1YiI6ImNocmlzLmF1QHRyYWRlYmV5b25kLmNvbSIsImRhdGVUaW1lRm9ybWF0Q29kZSI6Ik1NL2RkL3l5eXkiLCJ1c2VyX25hbWUiOiJjaHJpcy5hdUB0cmFkZWJleW9uZC5jb20iLCJpc3MiOiJodHRwczovL2FkaWRhcy1xYS50cmFkZWJleW9uZC5jb20iLCJkYXRlRm9ybWF0Q29kZSI6Ik1NL2RkL3l5eXkiLCJsb2NhbGUiOiJ2aV9WTiIsIndvcmtpbmdfZG9tYWluIjoiUDg4IiwiY2xpZW50X2lkIjoiY2J4IiwiZG9tYWluX2lkIjoiUDg4Iiwib3duZXJEb21haW5JZCI6IlA4OCIsImN1cnJlbnRVc2VyQ29tYmluZWRJZCI6ImNocmlzLmF1QHRyYWRlYmV5b25kLmNvbUBQODgiLCJyZWZyZXNoVG9rZW5JZCI6ImQzMjQ0ZDM1LTRhZjktNDcxYS05NTY0LTYwMWY5NzU5Mjk5MiIsInNjb3BlIjpbInRydXN0IiwicmVhZCIsIndyaXRlIl0sIm5ld3VpVGltZVpvbmVDb2RlIjoiQXNpYS9Ib25nX0tvbmciLCJleHAiOjE3NzQ4NjY4MzUsImlhdCI6MTc3NDg2NTAzNSwianRpIjoiZWJkODNkYTktZDRkNC00MTA4LWEwZmUtZGJiYzMzNDAwODQ2IiwiZW1haWwiOiJjaHJpcy5hdUB0cmFkZWJleW9uZC5jb20iLCJzdWJzdGl0dXRlVXNlck5hbWUiOiIiLCJjdXJyZW50VXNlck5hbWUiOiJDaHJpcyBBdSIsInRva2VuSWQiOiJlYmQ4M2RhOS1kNGQ0LTQxMDgtYTBmZS1kYmJjMzM0MDA4NDYiLCJ3b3JraW5nRm9yVXNlcklkIjoiIiwidXNlcklkIjoiNDAyODkwYWQ5YzU1Y2VjNjAxOWM1NWY5YjczMzE5NGIiLCJhdXRob3JpdGllcyI6WyJ1c2VyIl0sImlzU2luZ2xlU291cmNpbmdEb21haW4iOnRydWUsInVzZXJMb2dpbklkIjoiY2hyaXMuYXVAdHJhZGViZXlvbmQuY29tIiwiYXVkIjoiY2J4IiwibmJmIjoxNzc0ODY1MDM1fQ.OkqmBbbEj1xAYgTvkHfQHIIgtCsqRhS2LjFJHxcNEPUPC8s_29wYxipML-mBayqG-r0EDCnxAUWkKt9n57vxXFh_fhU3ejMMQOzDgTMMGzh7KGQpsssVuxsH4adBHOgexF0OWRpFZwXbLo6tiGsCO4E7nvxI4K0z82S9UiF-yvOnfx-K4slqU9bkWk2E_l1V61a8LoZI7Wxre-5lTAXFwwl18Vg_FjJsQoh2whIKJPz4jHu4HhW4uLvFVn4_cYTL_PwNRxOhjCNfEdIoNvDyu6cnZznhT4Nxs3acR6ZDuAgBMbiLqHJ7pKntr7Wmd9NC2SczKicrD5n9Wvm2JBamGg"
REQUEST_FILES = [
    # "chunk_1.json",
    # "chunk_2.json",
    # "chunk_3.json",
    # "chunk_4.json",
    # "chunk_5.json",
    # "chunk_6.json",
    # "chunk_7.json",
    # "chunk_8.json",
    "v_chunk_1.json",
    "v_chunk_2.json",
    "v_chunk_3.json",
    "v_chunk_4.json",
    "v_chunk_5.json",
    "v_chunk_6.json",
    "v_chunk_7.json",
    "v_chunk_8.json",
]

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def load_json_array(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{file_path} does not contain a JSON array")

    return data


def call_api_for_file(file_path):
    payload = load_json_array(file_path)

    print(f"\nProcessing file: {file_path}")
    print(f"Records: {len(payload)}")

    response = requests.put(
        API_URL,
        headers=HEADERS,
        json=payload,
        timeout=1200,
    )

    print(f"Status: {response.status_code}")

    # try:
    #     response_body = response.json()
    #     print("Response JSON:")
    #     print(json.dumps(response_body, ensure_ascii=False, indent=2))
    # except Exception:
    #     print("Response Text:")
    #     print(response.text)

    response.raise_for_status()


def main():
    for file_name in REQUEST_FILES:
        file_path = Path(file_name)

        if not file_path.exists():
            print(f"Skipping missing file: {file_name}")
            continue

        try:
            call_api_for_file(file_path)
        except Exception as e:
            print(f"Failed for {file_name}: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()