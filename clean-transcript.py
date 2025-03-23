#!/usr/bin/env python3
import sys
import os
import re
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
00:00:46.360

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
    # never Remove [SPEAKER_TURN] tags 
    text = re.sub(r'\s+', ' ', text)
    # Remove any remaining HTML entities like &quot;
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    return text.strip()

def is_prefix(a, b):
    """Return True if string a is a prefix of string b."""
    return b.startswith(a)

def process_vtt(content):
    """
    Stage 1: Convert VTT to plain text.
    Remove WEBVTT header and metadata and split into caption blocks.
    Stage 2: For each caption block, merge candidate lines.
    For candidate groups (e.g. TS1, TS2, TS3), retain the first timestamp (TSB)
    and the final (most complete) candidate text.
    """
    # Remove the WEBVTT header and any metadata
    content = re.sub(r'^WEBVTT\n.*?\n\n', '', content, flags=re.DOTALL)
    # Split into caption blocks
    captions = re.split(r'\n\n+', content)
    processed_captions = []

    for caption in captions:
        lines = caption.split('\n')
        candidates = []
        # Extract candidates matching a timestamp and text.
        # Expecting format: "HH:MM:SS(.mmm)? <text>"
        for line in lines:
            m = re.match(r'^(\d{2}:\d{2}:\d{2}\.\d{3})\s+(.*)$', line)
            if m:
                ts = m.group(1)
                txt = clean_text(m.group(2))
                if txt:
                    candidates.append((ts, txt))
        if not candidates:
            continue
        # Merge candidate lines: if a candidate’s text is a prefix of the next,
        # group them and keep the first timestamp with the final candidate text.
        merged_candidates = []
        buffer = []
        for cand in candidates:
            if not buffer:
                buffer.append(cand)
            else:
                # If the previous candidate text is a prefix of the current one, add it to the buffer.
                if is_prefix(buffer[-1][1], cand[1]):
                    buffer.append(cand)
                else:
                    # Flush the buffer: keep first timestamp, last text.
                    ts = buffer[0][0]
                    final_text = buffer[-1][1]
                    merged_candidates.append((ts, final_text))
                    buffer = [cand]
        if buffer:
            ts = buffer[0][0]
            final_text = buffer[-1][1]
            merged_candidates.append((ts, final_text))
        # Add each merged candidate as a separate processed caption.
        for ts, text in merged_candidates:
            processed_captions.append(f"{ts} {text}")
    return "\n".join(processed_captions)

def remove_line_stuttering(transcript, similarity_threshold=0.8):
    """
    Remove near-duplicate lines that may have resulted from incremental candidate updates.
    """
    lines = transcript.splitlines()
    deduped = []
    for line in lines:
        if not deduped:
            deduped.append(line)
        else:
            prev_line = deduped[-1]
            # Use difflib to compare similarity.
            if difflib.SequenceMatcher(None, prev_line.strip(), line.strip()).ratio() >= similarity_threshold:
                continue
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
    If the source is VTT, process it with VTT cleaning and candidate merging.
    Then apply line and word stutter removal.
    """
    if is_vtt:
        processed = process_vtt(raw_text)
    else:
        processed = raw_text
    processed = remove_line_stuttering(processed)
    processed = remove_word_stuttering(processed)
    return processed

def main():
    raw_text = sys.stdin.read()
    # Detect if the file is VTT by extension or by header content.
    filename = os.environ.get('filename', '')
    is_vtt = filename.lower().endswith('.vtt') or raw_text.startswith('WEBVTT')
    cleaned_text = clean_transcript(raw_text, is_vtt=is_vtt)
    print(cleaned_text)

if __name__ == "__main__":
    main()
