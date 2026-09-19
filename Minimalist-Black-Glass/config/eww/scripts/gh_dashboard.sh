#!/bin/bash
# GitHub Dashboard data provider for eww — real data, cached, monochrome avatar.
# Outputs a JSON object consumed by the gh-dashboard window:
#   avatar     ~/.cache/gh_avatar_mono.png  (grayscaled, high-contrast)
#   followers  api.github.com/users/yummyfiles
#   repos      api.github.com/users/yummyfiles
#   stars      sum of stargazers_count across all public repos (paginated)
# Numbers are emitted pre-formatted 1000->1k / 5100->5.1k / 93->93.
# Cache (~/.cache/gh_dashboard.json, TTL 25min) holds the RAW values + avatar URL.

set -u

USER="yummyfiles"
CACHE="$HOME/.cache/gh_dashboard.json"
AVATAR_CACHE="$HOME/.cache/gh_avatar_mono.png"
AVATAR_RAW="$HOME/.cache/gh_avatar_raw.png"
TTL=1500   # 25 min
API="https://api.github.com"

fmt() { # 1000->1k, 5100->5.1k, 93->93
  local n=$1
  if [ "$n" -ge 1000000 ]; then
    awk -v x="$n" 'BEGIN{printf "%dM", x/1000000}'
  elif [ "$n" -ge 1000 ]; then
    awk -v x="$n" 'BEGIN{printf "%.1fk", x/1000}' | sed 's/\.0k/k/'
  else
    printf '%s' "$n"
  fi
}

emit() { # $1=avatar $2=followers $3=stars $4=repos  (all already displayed-form)
  printf '{"avatar":"%s","followers":"%s","stars":"%s","repos":"%s","profile":"https://github.com/%s"}\n' "$1" "$2" "$3" "$4" "$USER"
}

mkdir -p "$(dirname "$CACHE")"

fresh() { # cache exists and within TTL
  [ -s "$CACHE" ] || return 1
  local now last
  now=$(date +%s); last=$(stat -c %Y "$CACHE")
  [ $((now - last)) -le $TTL ]
}

regen_avatar() { # $1 = avatar URL
  [ -z "$1" ] && return 1
  curl -s --max-time 15 -o "$AVATAR_RAW" "$1" || return 1
  [ -s "$AVATAR_RAW" ] || return 1
  magick "$AVATAR_RAW" -colorspace Gray -auto-level -resize 256x256! "$AVATAR_CACHE"
}

if ! fresh; then
  # --- refresh from the API; never destroy the previous cache on failure ---
  if USER_JSON=$(curl -sf --max-time 15 "$API/users/$USER"); then
    FOLLOWERS=$(printf '%s' "$USER_JSON" | jq -r '.followers // 0')
    REPOS=$(printf '%s' "$USER_JSON" | jq -r '.public_repos // 0')
    AVATAR_URL=$(printf '%s' "$USER_JSON" | jq -r '.avatar_url // ""')

    STARS=0; PAGE=1
    while :; do
      PAGE_JSON=$(curl -sf --max-time 15 "$API/users/$USER/repos?per_page=100&page=$PAGE") || break
      N=$(printf '%s' "$PAGE_JSON" | jq -r 'length')
      SUM=$(printf '%s' "$PAGE_JSON" | jq -r '[.[].stargazers_count] | add // 0')
      STARS=$((STARS + SUM))
      [ "$N" -lt 100 ] && break
      PAGE=$((PAGE + 1))
      [ "$PAGE" -gt 100 ] && break
    done

    [ -n "$AVATAR_URL" ] && regen_avatar "$AVATAR_URL"
    printf '{"avatar_url":"%s","avatar":"%s","followers":%s,"stars":%s,"repos":%s,"profile":"https://github.com/%s"}\n' \
      "$AVATAR_URL" "$AVATAR_CACHE" "$FOLLOWERS" "$STARS" "$REPOS" "$USER" > "$CACHE"
  fi
fi

# --- serve: cached values, else degraded placeholders ---
if [ -s "$CACHE" ]; then
  URL=$(jq -r '.avatar_url // ""' "$CACHE")
  [ -f "$AVATAR_CACHE" ] && [ -n "$URL" ] && regen_avatar "$URL"
  emit "$AVATAR_CACHE" \
    "$(fmt "$(jq -r '.followers' "$CACHE")")" \
    "$(fmt "$(jq -r '.stars' "$CACHE")")" \
    "$(fmt "$(jq -r '.repos' "$CACHE")")"
else
  printf '{"avatar":"%s","followers":"--","stars":"--","repos":"--","profile":"https://github.com/%s"}\n' "$AVATAR_CACHE" "$USER"
fi