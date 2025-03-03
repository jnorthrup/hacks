#!/usr/bin/python3

import re
import glob
import sys
import os
import tempfile

def clean_text(text):
    """Removes HTML tags, multiple spaces, and leading/trailing whitespace."""
    text = re.sub(r'<[^>]+>|\s+', ' ', text).strip()
    return text

def process_vtt(content):
    """Processes a VTT file to clean and extract subtitles."""

    processed_captions = []
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r'(\d{2}:\d{2}:\d{2})\.(\d{3}) --> (\d{2}:\d{2}:\d{2})\.(\d{3})', line)
        if match:
            start_timestamp = match.group(1)
            i += 1
            subtitle_lines = []
            while i < len(lines) and lines[i].strip():
                subtitle_lines.append(lines[i])
                i += 1

            subtitle_text = ' '.join(subtitle_lines)
            cleaned_text = clean_text(subtitle_text)

            if cleaned_text:
                processed_captions.append(f"{start_timestamp} {cleaned_text}")
        else:
            i += 1

    return '\n'.join(processed_captions)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vttclean.py <file_pattern>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    print(f"Processing filename: {filename}")

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            result = process_vtt(content)
            print(result)

    except Exception as e:
        print(f"Error processing input: {e}", file=sys.stderr)
        sys.exit(1)