import csv
import json

INPUT = 'source.csv'
OUTPUT = 'output.json'
LOCALE = 'vi_VN'  # change if you need a different locale

results = []
with open(INPUT, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # normalize keys in case CSV headers differ in case/whitespace
        module_code = row.get('moduleCode') or row.get('modulecode') or row.get('module_code') or ''
        label_id = row.get('labelId') or row.get('labelid') or row.get('label_id') or ''
        label_text = row.get('label') or ''

        # skip empty rows (optional)
        if not (module_code or label_id or label_text):
            continue

        obj = {
            "labelId": label_id,
            "locale": LOCALE,
            "label": label_text,
            "moduleCode": module_code
        }
        results.append(obj)

with open(OUTPUT, 'w', encoding='utf-8') as out:
    json.dump(results, out, ensure_ascii=False, indent=2)

print(f"Wrote {len(results)} records to {OUTPUT}")