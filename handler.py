import json
import math

# 1. Read from raw.json
with open('viet_trans.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total objects before filter: {len(data)}')

# 2. Filter out empty labels
filtered = [item for item in data if item.get('label', '') != '']

print(f'Total objects after filter: {len(filtered)}')

# 3. Split into chunks of max 100 objects each
MAX_CHUNK_SIZE = 500
num_chunks = math.ceil(len(filtered) / MAX_CHUNK_SIZE)
chunks = []

for i in range(num_chunks):
    start = i * MAX_CHUNK_SIZE
    chunk = filtered[start:start + MAX_CHUNK_SIZE]
    chunks.append(chunk)

# 4. Save each chunk
for i, chunk in enumerate(chunks, 1):
    filename = f'v_chunk_{i}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chunk, f, indent=2, ensure_ascii=False)
    print(f'Saved {filename} with {len(chunk)} items')

print(f'Created {len(chunks)} chunks (max 100 items each)')