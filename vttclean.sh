#!/bin/bash

clean_text() {
    local text="$1"
    # Remove HTML tags
    text=$(echo "$text" | sed 's/<[^>]*>//g')
    # Remove multiple spaces
    text=$(echo "$text" | sed 's/[[:space:]]\+/ /g')
    # Remove leading/trailing whitespace
    text=$(echo "$text" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    # Remove non-printable characters (except spaces)
    text=$(echo "$text" | tr -cd '[:print:][:space:]')
    echo "$text"
}

is_prefix() {
    [[ "$2" == "$1"* ]]
}

process_vtt() {
    # Remove WEBVTT header and metadata
    content=$(sed '1,/^$/d' "$1")

    # Process captions
    buffer=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
            timestamp=$(echo "$line" | cut -d' ' -f1 | sed 's/\(.*\)\..*/\1/')
            text=$(echo "$line" | cut -d' ' -f2-)
            clean_caption=$(clean_text "$text")
            if [[ -n "$clean_caption" ]]; then
                current_line="${timestamp} ${clean_caption}"
                if [[ -z "$buffer" ]]; then
                    buffer="$current_line"
                else
                    prev_text=$(echo "$buffer" | cut -d' ' -f2-)
                    if is_prefix "$prev_text" "$clean_caption"; then
                        buffer="$current_line"
                    else
                        echo "$buffer"
                        buffer="$current_line"
                    fi
                fi
            fi
        fi
    done < <(echo "$content")

    # Print the last buffer content
    if [[ -n "$buffer" ]]; then
        echo "$buffer"
    fi
}

if [[ $# -gt 0 ]]; then
    # File input
    process_vtt "$1"
else
    # Stdin input
    process_vtt /dev/stdin
fi
