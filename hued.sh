# hued — set terminal background color based on nearest .hued file
#
# Requires bash 4+ or zsh.
#
# Bash:  source hued.sh
#        PROMPT_COMMAND="_hued_apply${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
#
# Zsh:   source hued.sh
#        precmd_functions+=(_hued_apply)

if [[ -n "${ZSH_VERSION:-}" ]]; then
  _HUED_DIR="${${(%):-%x}:h}"
else
  _HUED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

declare -A _HUED_NAMES

_hued_lookup() {
  local key="$1"
  if [[ -z "${_HUED_NAMES[$key]+_}" ]]; then
    local hit
    hit=$(grep -m1 "^\[${key}\]=" "$_HUED_DIR/hued-names.sh" 2>/dev/null | cut -d= -f2)
    _HUED_NAMES[$key]="${hit:-__miss__}"
  fi
  local val="${_HUED_NAMES[$key]}"
  [[ "$val" != "__miss__" ]] && printf '%s' "$val"
}

_hued_apply() {
  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.hued" ]]; then
      local value hex
      value=$(grep -m1 '^background=' "$dir/.hued" | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
      if [[ -n "$value" ]]; then
        local key="${value#\#}"
        key="${key// /}"
        if [[ "$key" =~ ^[0-9a-f]{6}$ ]]; then
          hex="$key"
        else
          hex="$(_hued_lookup "$key")"
          hex="${hex#\#}"
        fi
        [[ -n "$hex" ]] && printf "\e]11;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
        return
      fi
    fi
    dir="${dir%/*}"
  done
  printf "\e]111;\a"
}
