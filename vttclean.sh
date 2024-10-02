#!/bin/bash

set -e

# Function to log messages to stderr
log() {
    echo "$@" >&2
}

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
    local input_file="$1"
    local output_file="$2"

    log "Processing file: $input_file"

    # Remove WEBVTT header and metadata
    content=$(sed '1,/^$/d' "$input_file")

    # Process captions
    buffer=""
    caption=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
            if [[ -n "$caption" ]]; then
                process_caption "$caption" >> "$output_file"
                caption=""
            fi
            caption="$line"
        elif [[ -n "$line" ]]; then
            caption+=$'\n'"$line"
        else
            if [[ -n "$caption" ]]; then
                process_caption "$caption" >> "$output_file"
                caption=""
            fi
        fi
    done <<< "$content"

    # Process the last caption
    if [[ -n "$caption" ]]; then
        process_caption "$caption" >> "$output_file"
    fi

    # Print the last buffer content
    if [[ -n "$buffer" ]]; then
        echo "$buffer" >> "$output_file"
    fi

    log "Processed content written to: $output_file"
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

main() {
    if [[ $# -gt 0 ]]; then
        # File input
        input_file="$1"
        output_file="${input_file%.*}_cleaned.txt"
        process_vtt "$input_file" "$output_file"
    else
        # Stdin input
        log "Reading from stdin..."
        temp_input=$(mktemp)
        cat > "$temp_input"
        output_file="cleaned_output.txt"
        process_vtt "$temp_input" "$output_file"
        rm "$temp_input"
    fi
}

# Trap for handling errors and cleaning up
trap 'log "Error occurred. Exiting..."; exit 1' ERR

# Run the main function
main "$@"
