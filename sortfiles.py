import os
import re
import shutil
from datetime import datetime
import argparse

MIN_YEAR = 2015
MAX_YEAR = 2025

def extract_year_from_transcript(file_path):
    """
    Extracts and returns the year from the transcript file located at file_path by searching for a date pattern.
    Returns None if no valid date is found or if the date format is incorrect.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r"DATE:\s+([A-Za-z]+ \d{1,2}, \d{4})", line, re.IGNORECASE)
            if match:
                try:
                    date_obj = datetime.strptime(match.group(1), "%B %d, %Y")
                    return date_obj.year
                except ValueError:
                    return None
    return None

def organize_transcripts_by_year(base_dir="./transcripts"):
    """
    Organizes transcript files by year by moving them into subdirectories named after the extracted year.
    Only processes files with a .txt extension. Files with dates outside the years range are ignored.
    """
    if not os.path.isdir(base_dir):
        print(f"Error: The directory '{base_dir}' does not exist.")
        return
    files = [f for f in os.listdir(base_dir) if f.endswith(".txt")]
    for f in files:
        full_path = os.path.join(base_dir, f)
        year = extract_year_from_transcript(full_path)
        if year and MIN_YEAR <= year <= MAX_YEAR:
            year_dir = os.path.join(base_dir, str(year))
            os.makedirs(year_dir, exist_ok=True)
            shutil.move(full_path, os.path.join(year_dir, f))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Organize transcript files by year.")
    parser.add_argument("--transcripts-dir", type=str, default="./transcripts", help="Directory containing transcript files")
    args = parser.parse_args()
    organize_transcripts_by_year(args.transcripts_dir)
