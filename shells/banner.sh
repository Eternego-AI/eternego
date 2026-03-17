#!/usr/bin/env bash

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

clear
tput civis

show_prompt 1
clear
type_and_erase "Hello" 1
show_prompt 1
clear
type_and_erase "Your life is going to become eternal. Are you ready?" 2

clear

print_file "$SCRIPT_DIR/assets/eternego-ascii.txt"

tput cnorm