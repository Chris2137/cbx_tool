import re

def normalize_text(text: str) -> str:
    """Normalize for case-insensitive and basic plural deduplication."""
    text = text.strip()
    folded = text.casefold()
    
    # Basic plural stripping (common cases)
    folded = re.sub(r's$', '', folded)  # apples -> apple
    folded = re.sub(r'es$', '', folded)  # buses -> bus
    folded = re.sub(r'ies$', '', folded)  # babies -> baby
    folded = re.sub(r'ves$', '', folded)  # knives -> knife (approximation)
    
    return folded

def deduplicate_file(input_file, output_file):
    seen = set()

    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8") as outfile:

        for line in infile:
            original = line.rstrip("\n")
            key = normalize_text(original)

            if key not in seen:
                seen.add(key)
                outfile.write(original + "\n")

if __name__ == "__main__":
    input_path = "input.txt"
    output_path = "output.txt"
    deduplicate_file(input_path, output_path)
    print(f"Deduplicated lines written to {output_path}")