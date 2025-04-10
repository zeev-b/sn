import os
import re
import shutil
from datetime import datetime

def extract_year_from_transcript(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r"DATE:\s+([A-Za-z]+ \d{1,2}, \d{4})", content)
        if match:
            try:
                date_obj = datetime.strptime(match.group(1), "%B %d, %Y")
                return date_obj.year
            except ValueError:
                return None
    return None

def organize_transcripts_by_year(base_dir="./transcripts"):
    files = [f for f in os.listdir(base_dir) if f.endswith(".txt")]
    for f in files:
        full_path = os.path.join(base_dir, f)
        year = extract_year_from_transcript(full_path)
        if year and 2015 <= year <= 2025:
            year_dir = os.path.join(base_dir, str(year))
            os.makedirs(year_dir, exist_ok=True)
            shutil.move(full_path, os.path.join(year_dir, f))

if __name__ == '__main__':
    organize_transcripts_by_year()