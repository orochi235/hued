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

# Lowercase and strip spaces, hyphens and apostrophes, matching the key
# normalization in scripts/generate-names.py.
_hued_name_key() {
  local k="$1"
  k="${k// /}"; k="${k//-/}"; k="${k//\'/}"; k="${k//’/}"
  printf '%s' "$k" | tr '[:upper:]' '[:lower:]'
}

# Keys outside the generated alphabet are rejected before the grep so a name
# containing a regex metacharacter cannot match some unrelated row.
_hued_lookup() {
  local key="$1" prefix="" hit=""
  [[ "$key" =~ ^[a-z0-9/]+$ ]] || return 0
  case "$(printf '%s' "${HUED_LOOKUP_PREFER_XKCD:-}" | tr '[:upper:]' '[:lower:]')" in
    ""|0|false|no|off|n) ;;
    *) prefix="xkcd:" ;;
  esac
  if [[ -n "$prefix" ]]; then
    hit=$(grep -m1 "\[${prefix}${key}\]=" "$_HUED_DIR/hued-names.sh" 2>/dev/null | cut -d= -f2)
  fi
  [[ -n "$hit" ]] || hit=$(grep -m1 "\[${key}\]=" "$_HUED_DIR/hued-names.sh" 2>/dev/null | cut -d= -f2)
  printf '%s' "$hit"
}

_hued_resolve() {
  local value="$1" key hex
  key=$(_hued_name_key "${value#\#}")
  if [[ "$key" =~ ^[0-9a-f]{6}$ ]]; then
    printf '%s' "$key"
  else
    hex="$(_hued_lookup "$key")"
    printf '%s' "${hex#\#}"
  fi
}

_hued_apply_fallback() {
  local bg="" fg="" hex

  local dir="$PWD"
  while [[ "$dir" != / && -n "$dir" ]]; do
    if [[ -f "$dir/.hued" ]]; then
      bg=$(grep '^background=' "$dir/.hued" | tail -n1 | cut -d= -f2 | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
      fg=$(grep '^foreground=' "$dir/.hued" | tail -n1 | cut -d= -f2 | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
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

_hued_apply() {
  if command -v hued >/dev/null 2>&1; then
    hued apply
  else
    _hued_apply_fallback
  fi
}
