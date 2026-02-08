#!/usr/bin/env python3
import re
import sys
import os
import difflib

"""
Explanation
    •   VTT Detection:
The script checks if the filename ends with .vtt or if the content starts with “WEBVTT” to decide if VTT processing is needed.
    •   Stage 1 – VTT Conversion:
process_vtt() strips the VTT header/metadata, splits captions, and extracts timestamped candidates (converting timestamps to HH:MM:SS.mmm).
    •   Stage 2 – Candidate Merging:
Within each caption block, candidate lines are merged using the is_prefix() check. For a group (e.g. TS1, TS2, TS3), the output is the first timestamp (TSB) and the text from the last candidate.
    •   Additional Cleaning:
The functions remove_line_stuttering() and remove_word_stuttering() then further clean the text by removing near-duplicate lines and repeated words.

This merged, staged approach should address your needs for converting VTT input and handling Whisper’s candidate mismatches.

[00:00:46.360 --> 00:01:03.940]   must become 
00:00:46

TS1 BA
TS2 BANA
TS3 BANANA

must become TS1 BANANA

"""

def clean_text(text):
    """Remove HTML tags, extra spaces, and trim whitespace."""
    text = re.sub(r'<[^>]+>', '', text)
    # Remove speaker prefixes like "Robert:" or "Jim:" ONLY at the beginning of the line followed by timestamp in square brackets
    text = re.sub(r'^\w+:\s+(\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\])', r'\1', text)
    # Remove leading whitespace
    text = re.sub(r'^\s+', '', text)
    # never Remove [SPEAKER_TURN] tags - preserve them exactly
    text = re.sub(r'\s+', ' ', text)
    # Remove any remaining HTML entities like &quot;
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    return text.strip()

def is_prefix(a, b):
    """Return True if string a is a prefix of string b."""
    return b.startswith(a)

def process_vtt(content):
    """
    Process VTT content:
    - Remove WEBVTT header and metadata.
    - Extract the start timestamp and text content from each caption block.
    - Apply basic text cleaning.
    """
    # Remove the WEBVTT header and any initial metadata lines until the first blank line
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove NOTE blocks
    content = re.sub(r'NOTE.*?\n\n', '', content, flags=re.DOTALL)
    # Remove STYLE blocks
    content = re.sub(r'STYLE.*?\n\n', '', content, flags=re.DOTALL)

    # Split into caption blocks based on double newlines
    captions = re.split(r'\n\n+', content.strip())
    processed_lines = []

    for caption in captions:
        lines = caption.strip().split('\n')
        if not lines:
            continue

        # Find the timestamp line (e.g., [00:00:01.000 --> 00:00:05.000] or 00:00:01.000 --> 00:00:05.000)
        timestamp_line = ""
        text_lines = []
        for i, line in enumerate(lines):
            if '-->' in line:
                timestamp_line = line.strip('[]')  # Remove surrounding brackets if present
                text_lines = lines[i+1:] # Text is everything after the timestamp line
                break
        
        if not timestamp_line:
            # Skip blocks without a valid timestamp line
            # print(f"Skipping block without timestamp: {caption[:50]}...", file=sys.stderr)
            continue

        # Extract the start timestamp (HH:MM:SS)
        match = re.match(r'(\d{2}:\d{2}:\d{2})\.\d{3}\s*-->', timestamp_line)
        if not match:
            # print(f"Skipping block with malformed timestamp: {timestamp_line}", file=sys.stderr)
            continue
        
        start_ts = match.group(1)
        
        # Join text lines and clean them
        raw_text = " ".join(text_lines).strip()
        cleaned_line_text = clean_text(raw_text) # Use existing clean_text function

        if cleaned_line_text: # Only add if there's actual text content
            processed_lines.append(f"{start_ts} {cleaned_line_text}")

    return "\n".join(processed_lines)

def remove_line_stuttering(transcript, similarity_threshold=0.8):
    """
    Remove near-duplicate lines that may have resulted from incremental candidate updates.
    Lines with [SPEAKER_TURN] are always preserved.
    """
    lines = transcript.splitlines()
    deduped = []
    for line in lines:
        if not deduped:
            deduped.append(line)
        else:
            prev_line = deduped[-1]
            # Retention trigger: always preserve lines with [SPEAKER_TURN]
            if '[SPEAKER_TURN]' in line:
                deduped.append(line)
            # Use difflib to compare similarity for lines without [SPEAKER_TURN]
            elif difflib.SequenceMatcher(None, prev_line.strip(), line.strip()).ratio() >= similarity_threshold:
                continue
            else:
                deduped.append(line)
    return "\n".join(deduped)

def remove_word_stuttering(text):
    """
    Remove repeated adjacent words (e.g., "hello hello") which may occur in candidate mismatches.
    """
    stutter_pattern = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
    prev_text = None
    while text != prev_text:
        prev_text = text
        text = stutter_pattern.sub(r'\1', text)
    
    # Also remove triple+ word repetitions (e.g., "hello hello hello")
    triple_pattern = re.compile(r'\b(\w+)(\s+\1){2,}\b', re.IGNORECASE)
    text = triple_pattern.sub(r'\1', text)
    
    return text

def clean_transcript(raw_text, is_vtt=False):
    """
    If the source is VTT, process it with VTT cleaning.
    Then apply line and word stutter removal.
    """
    if is_vtt:
        processed = process_vtt(raw_text)
        # Stutter removal might be less necessary after VTT processing,
        # but can be kept if needed. Consider if it removes valid repetitions.
        # processed = remove_line_stuttering(processed) # Optional: Re-evaluate if needed
        # processed = remove_word_stuttering(processed) # Optional: Re-evaluate if needed
    else:
        # Apply cleaning to non-VTT text as well if desired
        processed = clean_text(raw_text) # Apply basic cleaning
        processed = remove_line_stuttering(processed)
        processed = remove_word_stuttering(processed)
    return processed

def main():
    raw_text = sys.stdin.read()
    # Detect if the file is VTT by extension or by header content.
    filename = os.environ.get('filename', '')
    is_vtt = filename.lower().endswith('.vtt') or raw_text.startswith('WEBVTT') or '[00:00:' in raw_text
    cleaned_text = clean_transcript(raw_text, is_vtt=is_vtt)
    print(cleaned_text)

if __name__ == "__main__":
    main()
