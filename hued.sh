# hued — set terminal colors based on nearest .hued file
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

# Re-apply on SIGUSR1. A theme-change watcher (e.g. contrib/macos/) sends this
# when the OS appearance switches, since some terminals reset OSC 10/11 to
# their profile preset on appearance change.
trap '_hued_apply' USR1

declare -A _HUED_NAMES

_hued_lookup() {
  local key="$1"
  if [[ -z "${_HUED_NAMES[$key]+_}" ]]; then
    local hit
    hit=$(grep -m1 "\[${key}\]=" "$_HUED_DIR/hued-names.sh" 2>/dev/null | cut -d= -f2)
    _HUED_NAMES[$key]="${hit:-__miss__}"
  fi
  local val="${_HUED_NAMES[$key]}"
  [[ "$val" != "__miss__" ]] && printf '%s' "$val"
}

_hued_resolve() {
  local value="$1"
  local key="${value#\#}"
  key="${key// /}"
  if [[ "$key" =~ ^[0-9a-f]{6}$ ]]; then
    printf '%s' "$key"
  else
    local hex
    hex="$(_hued_lookup "$key")"
    printf '%s' "${hex#\#}"
  fi
}

_hued_apply() {
  local bg="" fg="" hex

  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.hued" ]]; then
      bg=$(grep -m1 '^background=' "$dir/.hued" | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
      fg=$(grep -m1 '^foreground=' "$dir/.hued" | cut -d= -f2 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
      [[ -n "$bg" || -n "$fg" ]] && break
    fi
    dir="${dir%/*}"
  done

  if [[ -n "${HUED_BACKGROUND:-}" ]]; then
    bg=$(printf '%s' "$HUED_BACKGROUND" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
  fi
  if [[ -n "${HUED_FOREGROUND:-}" ]]; then
    fg=$(printf '%s' "$HUED_FOREGROUND" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
  fi

  [[ "$bg" == "none" ]] && bg=""
  [[ "$fg" == "none" ]] && fg=""

  if [[ -n "$bg" ]]; then
    hex="$(_hued_resolve "$bg")"
    [[ -n "$hex" ]] && printf "\e]11;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
  else
    printf "\e]111;\a"
  fi

  if [[ -n "$fg" ]]; then
    hex="$(_hued_resolve "$fg")"
    [[ -n "$hex" ]] && printf "\e]10;rgb:%s/%s/%s\a" "${hex:0:2}" "${hex:2:2}" "${hex:4:2}"
  else
    printf "\e]110;\a"
  fi
}
