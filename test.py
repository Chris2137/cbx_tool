import json
from pathlib import Path


SOURCE_FILE = Path("output/translation/label_updates.json")


def main() -> None:
    if not SOURCE_FILE.exists():
        print(f"File not found: {SOURCE_FILE}")
        return

    with SOURCE_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Invalid JSON format: expected a list of objects")
        return

    module_codes = sorted(
        {
            str(item.get("moduleCode")).strip()
            for item in data
            if isinstance(item, dict) and str(item.get("moduleCode") or "").strip()
        }
    )

    print(f"Distinct moduleCode count: {len(module_codes)}")
    print()

    for module_code in module_codes:
        print(module_code)


if __name__ == "__main__":
    main()