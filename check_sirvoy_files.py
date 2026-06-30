import json
from pathlib import Path

# Check file history for Sirvoy files
file_history_path = 'file_history.json'
with open(file_history_path, 'r') as f:
    history = json.load(f)

print('All files in history:')
sirvoy_files = []
for file_info in history:
    print(f"{file_info['file_type']}: {file_info['original_name']} - {file_info['saved_at']}")
    if file_info['file_type'] == 'sirvoy':
        sirvoy_files.append(file_info)

print(f'\nSirvoy files found: {len(sirvoy_files)}')
for sirvoy_file in sirvoy_files[:3]:  # Show first 3
    file_path = Path(sirvoy_file['path'])
    print(f"Path: {file_path}")
    print(f"Exists: {file_path.exists()}")
