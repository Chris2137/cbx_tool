import csv
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List

SOURCE_FILE = Path('ready_to_translate.csv')
OUTPUT_FILE = Path('output/translation/ready_to_translate_translated.csv')

LOCALES = [
    'es_ES', 'fr_CA', 'id_ID', 'it_IT', 'ja_JP', 'pt_BR', 'tr_TR', 'vi_VN', 'zh_CN'
]

LANGUAGE_MAP = {
    'es_ES': 'es',
    'fr_CA': 'fr',
    'id_ID': 'id',
    'it_IT': 'it',
    'ja_JP': 'ja',
    'pt_BR': 'pt',
    'tr_TR': 'tr',
    'vi_VN': 'vi',
    'zh_CN': 'zh-CN',
}


def normalize_text(text: str) -> str:
    return (text or '').strip()


class TranslationError(Exception):
    pass


class LibreTranslateProvider:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            'q': text,
            'source': source_lang,
            'target': target_lang,
            'format': 'text',
        }
        if self.api_key:
            payload['api_key'] = self.api_key

        data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            url=f'{self.base_url}/translate',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode('utf-8')
        except Exception as e:
            raise TranslationError(f'HTTP error while translating to {target_lang}: {e}') from e

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as e:
            raise TranslationError(f'Invalid JSON response from translation provider: {body}') from e

        translated = parsed.get('translatedText')
        if not isinstance(translated, str):
            raise TranslationError(f'Unexpected translation response: {parsed}')

        return translated.strip()


TRANSLATION_MEMORY: Dict[str, Dict[str, str]] = {
    'Comments': {
        'es_ES': 'Comentarios',
        'fr_CA': 'Commentaires',
        'id_ID': 'Komentar',
        'it_IT': 'Commenti',
        'ja_JP': 'コメント',
        'pt_BR': 'Comentários',
        'tr_TR': 'Yorumlar',
        'vi_VN': 'Bình luận',
        'zh_CN': '备注',
    },
    'Status': {
        'es_ES': 'Estado',
        'fr_CA': 'Statut',
        'id_ID': 'Status',
        'it_IT': 'Stato',
        'ja_JP': '状态',
        'pt_BR': 'Status',
        'tr_TR': 'Durum',
        'vi_VN': 'Trạng thái',
        'zh_CN': '状态',
    },
    'Due Date': {
        'es_ES': 'Fecha de vencimiento',
        'fr_CA': "Date d'échéance",
        'id_ID': 'Tanggal jatuh tempo',
        'it_IT': 'Data di scadenza',
        'ja_JP': '期限日',
        'pt_BR': 'Data de vencimento',
        'tr_TR': 'Son tarih',
        'vi_VN': 'Ngày đến hạn',
        'zh_CN': '到期日期',
    },
}


def translate_label(label: str, provider: LibreTranslateProvider, sleep_seconds: float = 0.0) -> Dict[str, str]:
    normalized = normalize_text(label)
    if not normalized:
        return {locale: '' for locale in LOCALES}

    if normalized in TRANSLATION_MEMORY:
        return dict(TRANSLATION_MEMORY[normalized])

    result: Dict[str, str] = {}
    for locale in LOCALES:
        target_lang = LANGUAGE_MAP[locale]
        translated = provider.translate(normalized, 'en', target_lang)
        result[locale] = translated
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return result


def read_rows(path: Path) -> List[dict]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_rows(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not SOURCE_FILE.exists():
        print(f'Source file not found: {SOURCE_FILE}', file=sys.stderr)
        return 1

    base_url = os.getenv('LIBRETRANSLATE_URL', '').strip()
    if not base_url:
        print('Missing environment variable LIBRETRANSLATE_URL', file=sys.stderr)
        print('Example: export LIBRETRANSLATE_URL=http://localhost:5000', file=sys.stderr)
        return 2

    api_key = os.getenv('LIBRETRANSLATE_API_KEY', '').strip() or None
    sleep_seconds = float(os.getenv('TRANSLATE_SLEEP_SECONDS', '0'))

    provider = LibreTranslateProvider(base_url=base_url, api_key=api_key)

    rows = read_rows(SOURCE_FILE)
    if not rows:
        print('No rows found in source CSV.')
        write_rows(OUTPUT_FILE, [], ['label', 'labelId', *LOCALES])
        return 0

    fieldnames = list(rows[0].keys())
    for locale in LOCALES:
        if locale not in fieldnames:
            fieldnames.append(locale)

    cache: Dict[str, Dict[str, str]] = {}
    output_rows: List[dict] = []

    total = len(rows)
    for index, row in enumerate(rows, start=1):
        label = normalize_text(row.get('label', ''))
        print(f'[{index}/{total}] Translating: {label}')

        if label not in cache:
            try:
                cache[label] = translate_label(label, provider, sleep_seconds=sleep_seconds)
            except Exception as e:
                print(f'ERROR translating label [{label}]: {e}', file=sys.stderr)
                return 3

        translated_map = cache[label]
        new_row = dict(row)
        for locale in LOCALES:
            new_row[locale] = translated_map.get(locale, '')
        output_rows.append(new_row)

    write_rows(OUTPUT_FILE, output_rows, fieldnames)
    print(f'Wrote translated CSV: {OUTPUT_FILE}')
    print(f'Rows written: {len(output_rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
