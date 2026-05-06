# termcolor — set terminal background color based on nearest .termcolor file
#
# Requires bash 4+ or zsh.
#
# Bash:  source termcolor.sh
#        PROMPT_COMMAND="_termcolor_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
#
# Zsh:   source termcolor.sh
#        precmd_functions+=(_termcolor_apply)

if [[ -n "${ZSH_VERSION:-}" ]]; then
  _TERMCOLOR_DIR="${${(%):-%x}:h}"
else
  _TERMCOLOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

_termcolor_apply() {
  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.termcolor" ]]; then
      local value hex
      value=$(grep -m1 '^background=' "$dir/.termcolor" | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
      if [[ -n "$value" ]]; then
        local key="${value#\#}"
        key="${key// /}"
        if [[ ! "$key" =~ ^[0-9a-f]{6}$ ]]; then
          # named color — lazy-load lookup table on first use
          if [[ -z "${_TERMCOLOR_NAMES+_}" ]]; then
            [[ -f "$_TERMCOLOR_DIR/termcolor-names.sh" ]] && source "$_TERMCOLOR_DIR/termcolor-names.sh"
          fi
          hex="${_TERMCOLOR_NAMES[$key]:-}"
          hex="${hex#\#}"
        else
          hex="$key"
        fi
        [[ -n "$hex" ]] && printf "\e]11;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
        return
      fi
    fi
    dir="${dir%/*}"
  done
  printf "\e]111;\a"
}
