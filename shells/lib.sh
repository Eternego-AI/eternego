#!/usr/bin/env bash

TYPEWRITER=1

GREEN="\033[32m"
RESET="\033[0m"

trap 'tput cnorm' EXIT

print() {
    local text="$1"

    if [[ "$TYPEWRITER" -eq 0 ]]; then
        echo "$text"
        return
    fi

    for ((i=0;i<${#text};i++)); do
        printf "%s" "${text:i:1}"
        sleep "0.0$(( (RANDOM % 3) + 1 ))"
    done

    printf "\n"
}

type_and_erase() {
    local text="$1"
    local wait="${2:-1}"
    local prompt="> "

    printf "${GREEN}%s${RESET}" "$prompt"

    for ((i=0;i<${#text};i++)); do
        printf "%s" "${text:i:1}"
        sleep "0.0$(( (RANDOM % 3) + 1 ))"
    done

    sleep "$wait"

    printf '\033[2K\r'
}

show_prompt() {
    local duration="${1:-3}"
    local prompt="> "

    printf "${GREEN}%s${RESET}" "$prompt"

    local cycles=$((duration*2))

    for ((i=0;i<cycles;i++)); do
        printf "${GREEN}█${RESET}"
        sleep 0.5
        printf "\b \b"
        sleep 0.5
    done
}

run() {
    print "  Running $*"
    echo "  $ $*" >> "$LOG_FILE"
    if ! "$@" >> "$LOG_FILE" 2>&1; then
        echo ""
        echo "  Failed: $*"
        echo "  See log for details: $LOG_FILE"
        exit 1
    fi
}

print_file() {
    local file="$1"

    while IFS= read -r line; do
        echo "$line"
        sleep 0.05
    done < "$file"
}
