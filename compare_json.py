#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from difflib import SequenceMatcher


def load_json_and_lines(path):
    text = Path(path).read_text(encoding='utf-8')
    data = json.loads(text)
    return data, text.splitlines()


def collect_ignored_line_numbers(obj, ignored_fields, line_numbers):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ignored_fields and hasattr(value, 'lc'):
                start = value.lc.line
                end = find_end_line(value)
                for i in range(start, end + 1):
                    line_numbers.add(i + 1)
            else:
                collect_ignored_line_numbers(value, ignored_fields, line_numbers)
    elif isinstance(obj, list):
        for item in obj:
            collect_ignored_line_numbers(item, ignored_fields, line_numbers)


def find_end_line(value):
    if hasattr(value, 'lc') and hasattr(value.lc, 'line'):
        end = value.lc.line
    else:
        return 0

    if isinstance(value, dict):
        for v in value.values():
            end = max(end, find_end_line(v))
    elif isinstance(value, list):
        for item in value:
            end = max(end, find_end_line(item))
    return end


def filter_lines(lines, ignored_line_numbers):
    kept = []
    mapping = []
    for idx, line in enumerate(lines, start=1):
        if idx not in ignored_line_numbers:
            kept.append(line)
            mapping.append(idx)
    return kept, mapping


def print_diff(file1, file2, ignore_fields):
    try:
        import ruamel.yaml
    except ImportError:
        print('This script requires ruamel.yaml. Install it with: pip install ruamel.yaml', file=sys.stderr)
        sys.exit(1)

    yaml = ruamel.yaml.YAML(typ='rt')
    yaml.preserve_quotes = True

    text1 = Path(file1).read_text(encoding='utf-8')
    text2 = Path(file2).read_text(encoding='utf-8')
    obj1 = yaml.load(text1)
    obj2 = yaml.load(text2)
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    ignored1 = set()
    ignored2 = set()
    collect_ignored_line_numbers(obj1, set(ignore_fields), ignored1)
    collect_ignored_line_numbers(obj2, set(ignore_fields), ignored2)

    filtered1, map1 = filter_lines(lines1, ignored1)
    filtered2, map2 = filter_lines(lines2, ignored2)

    matcher = SequenceMatcher(None, filtered1, filtered2)
    has_diff = False

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        has_diff = True

        if tag in ('replace', 'delete'):
            for idx in range(i1, i2):
                print(f'file1 line {map1[idx]}: {filtered1[idx]}')

        if tag in ('replace', 'insert'):
            for idx in range(j1, j2):
                print(f'file2 line {map2[idx]}: {filtered2[idx]}')

    if not has_diff:
        print('No differences found.')


def main():
    parser = argparse.ArgumentParser(
        description='Compare two formatted JSON files while preserving original line numbers.'
    )
    parser.add_argument('file1', help='Path to first JSON file')
    parser.add_argument('file2', help='Path to second JSON file')
    parser.add_argument(
        '--ignore-fields',
        nargs='*',
        default=[],
        help='Field names to ignore while preserving original line numbers'
    )
    args = parser.parse_args()

    try:
        print_diff(args.file1, args.file2, args.ignore_fields)
    except FileNotFoundError as e:
        print(f'File not found: {e}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()