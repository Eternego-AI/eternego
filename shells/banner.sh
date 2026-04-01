#!/usr/bin/env bash

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

clear
tput civis 2>/dev/null || true

show_prompt 1
clear
type_and_erase "Hello" 1
show_prompt 1
clear
type_and_erase "Your life is going to become eternal. Are you ready?" 2

clear

print_file "$SCRIPT_DIR/assets/eternego-ascii.txt"

tput cnorm 2>/dev/null || true