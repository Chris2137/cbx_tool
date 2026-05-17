import csv
import re
from pathlib import Path

INPUT_CSV = "adidas_preprod_users.csv"
OUTPUT_DIR = Path("adidas_vendors")

REQUIRED_COLUMNS = [
    "login_id",
    "first_name",
    "last_name",
    "user_name",
    "email",
    "account_company_value",
]

def sanitize_filename(value):
    value = "" if value is None else str(value).strip()
    value = re.sub(r"[^A-Za-z0-9]", "", value)
    value = value[:15]
    return value or "unknown"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(INPUT_CSV, "r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        files = {}
        writers = {}

        try:
            for row in reader:
                company_value = sanitize_filename(row.get("account_company_value"))
                output_path = OUTPUT_DIR / f"{company_value}.csv"

                if company_value not in writers:
                    outfile = open(output_path, "w", newline="", encoding="utf-8")
                    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                    writer.writeheader()
                    files[company_value] = outfile
                    writers[company_value] = writer

                writers[company_value].writerow(row)
        finally:
            for outfile in files.values():
                outfile.close()

if __name__ == "__main__":
    main()