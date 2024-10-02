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
    caption=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
            if [[ -n "$caption" ]]; then
                process_caption "$caption"
                caption=""
            fi
            caption="$line"
        elif [[ -n "$line" ]]; then
            caption+=$'\n'"$line"
        else
            if [[ -n "$caption" ]]; then
                process_caption "$caption"
                caption=""
            fi
        fi
    done

    # Process the last caption
    if [[ -n "$caption" ]]; then
        process_caption "$caption"
    fi

    # Print the last buffer content
    if [[ -n "$buffer" ]]; then
        echo "$buffer"
    fi
}

process_caption() {
    local caption="$1"
    timestamp=$(echo "$caption" | head -n1 | cut -d' ' -f1 | sed 's/\(.*\)\..*/\1/')
    text=$(echo "$caption" | tail -n +2)
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
}

if [[ $# -gt 0 ]]; then
    # File input
    process_vtt "$1"
else
    # Stdin input
    process_vtt /dev/stdin
fi
