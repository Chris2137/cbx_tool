import csv
import json
import re


def normalize_row(row):
    normalized = {}
    for k, v in row.items():
        key = k.strip().replace('\ufeff', '') if k else ''
        value = v.strip() if v else ''
        normalized[key] = value
    return normalized


def normalize_lookup_text(text):
    return text.strip().lower() if text else ''


def translate_label(label, translation_map, target_language):
    if not label:
        return label

    normalized_label = normalize_lookup_text(label)

    exact = translation_map.get(normalized_label)
    if exact:
        translated = exact.get(target_language, '')
        return translated if translated else label

    match = re.match(r'^(.*?)(\s+\d+)$', label)
    if match:
        base_text = match.group(1).strip()
        suffix = match.group(2)

        normalized_base = normalize_lookup_text(base_text)
        base_translation = translation_map.get(normalized_base)
        if base_translation:
            translated_base = base_translation.get(target_language, '')
            if translated_base:
                return translated_base + suffix

    return label


translation_map = {}

with open('translation.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row = normalize_row(row)

        english = row.get('English', '')
        chinese = row.get('Chinese', '')
        vietnamese = row.get('Vietnamese', '')

        normalized_english = normalize_lookup_text(english)
        if normalized_english:
            translation_map[normalized_english] = {
                'Chinese': chinese,
                'Vietnamese': vietnamese
            }

chinese_output = []
viet_output = []
missing_labels = []

with open('source.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row = normalize_row(row)

        label = row.get('label', '')
        label_id = row.get('label_id', '')
        module_code = row.get('module_code', '')

        chinese_label = translate_label(label, translation_map, 'Chinese')
        viet_label = translate_label(label, translation_map, 'Vietnamese')

        normalized_label = normalize_lookup_text(label)
        matched = normalized_label in translation_map

        if not matched:
            number_match = re.match(r'^(.*?)(\s+\d+)$', label)
            if number_match:
                base_text = number_match.group(1).strip()
                matched = normalize_lookup_text(base_text) in translation_map

        if not matched:
            missing_labels.append(label)

        chinese_output.append({
            "label": chinese_label,
            "labelId": label_id,
            "locale": "zh_CN",
            "module_code": module_code
        })

        viet_output.append({
            "label": viet_label,
            "labelId": label_id,
            "locale": "vi_VN",
            "module_code": module_code
        })

with open('chinese_trans.json', 'w', encoding='utf-8') as f:
    json.dump(chinese_output, f, ensure_ascii=False, indent=2)

with open('viet_trans.json', 'w', encoding='utf-8') as f:
    json.dump(viet_output, f, ensure_ascii=False, indent=2)

print(f"Done. {len(chinese_output)} entries written to chinese_trans.json")
print(f"Done. {len(viet_output)} entries written to viet_trans.json")

if missing_labels:
    unique_missing = sorted(set(missing_labels))
    print(f"Warning: {len(unique_missing)} labels were not found in translation.csv")
    for item in unique_missing:
        print(f"  - {item}")