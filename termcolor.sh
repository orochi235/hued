# termcolor — set terminal background color based on nearest .termcolor file
#
# Requires bash 4+ or zsh.
#
# Bash:  source termcolor.sh
#        PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
#
# Zsh:   source termcolor.sh
#        precmd_functions+=(_termcolor_apply)

_TERMCOLOR_DIR="${BASH_SOURCE[0]:-${(%):-%x}}"
_TERMCOLOR_DIR="${_TERMCOLOR_DIR%/*}"
[[ -f "$_TERMCOLOR_DIR/termcolor-names.sh" ]] && source "$_TERMCOLOR_DIR/termcolor-names.sh"

_termcolor_apply() {
  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.termcolor" ]]; then
      local value hex
      value=$(grep -m1 '^background=' "$dir/.termcolor" | cut -d= -f2 | tr -d '[:space:]')
      if [[ -n "$value" ]]; then
        local key="${value#\#}"
        key="${key,,}"              # lowercase
        key="${key// /}"           # strip spaces
        if [[ -n "${_TERMCOLOR_NAMES[$key]+_}" ]]; then
          hex="${_TERMCOLOR_NAMES[$key]#\#}"
        else
          hex="${value#\#}"
        fi
        printf "\e]11;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
        return
      fi
    fi
    dir="${dir%/*}"
  done
  printf "\e]111;\a"
}
