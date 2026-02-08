#!/bin/bash

# Initialize command array
cmd=(yt-dlp --cookies-from-browser brave --write-auto-sub --downloader aria2c -o "%(title)s.%(ext)s")

# Initialize empty URL string
url=""

# Initialize state
state="URL"

# Iterate over arguments
while (( $# )); do
    case $state in
        URL)
            if [ "$1" = "-H" ]; then
                state="HEADER"
            elif [ "$1" = "--compressed" ] || [ "$1" = "curl" ]; then
                shift
                continue
            else
                url=$1
            fi
            ;;
        HEADER)
            IFS=':' read -r name value <<< "$1"

            # Remove leading and trailing spaces
            name="$(echo -e "${name}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            value="$(echo -e "${value}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

            # Check for whitelisted headers and convert to yt-dlp switches
            case "$name" in
                User-Agent|user-agent)
                    cmd+=("-U" "$value")
                    ;;
                Referer|referer)
                    cmd+=("--referer" "$value")
                    ;;
                *)
                    # Otherwise, convert it to --add-header
                    cmd+=("--add-header" "${name}:${value}")
                    ;;
            esac

            state="URL"
            ;;
    esac
    shift
done

set -x

# Add the URL to the command array
cmd+=("$url")

# Execute the command array
"${cmd[@]}"