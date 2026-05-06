# termcolor — set terminal background color based on nearest .termcolor file
#
# Bash:  source termcolor.sh
#        PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
#
# Zsh:   source termcolor.sh
#        precmd_functions+=(_termcolor_apply)

_termcolor_apply() {
  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.termcolor" ]]; then
      local hex
      hex=$(grep -m1 '^background=' "$dir/.termcolor" | cut -d= -f2 | tr -d '[:space:]')
      if [[ -n "$hex" ]]; then
        hex="${hex#\#}"
        printf "\e]11;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
        return
      fi
    fi
    dir="${dir%/*}"
  done
  printf "\e]111;\a"
}
