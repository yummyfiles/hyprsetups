#!/bin/bash
# eww GitHub dashboard data provider
# Outputs JSON consumed by the eww gh widget.

CACHE="$HOME/.cache/eww-gh.json"
CACHE_TTL=60

need_refresh() {
    [ ! -f "$CACHE" ] && return 0
    NOW=$(date +%s)
    LAST=$(stat -c %Y "$CACHE")
    [ $((NOW - LAST)) -gt $CACHE_TTL ]
}

refresh() {
    USER=$(gh api user 2>/dev/null) || return 1

    LOGIN=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login',''))")
    NAME=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name',''))")
    AVATAR=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('avatar_url',''))")
    FOLLOWERS=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('followers',0))")
    FOLLOWING=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('following',0))")
    REPOS=$(printf '%s' "$USER" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('public_repos',0))")

    STARS=$(gh api "user/repos?per_page=100" --jq '[.[] | .stargazers_count] | add // 0' 2>/dev/null)
    [ -z "$STARS" ] && STARS=0

    CAL=$(gh api graphql -f query='
query {
  user(login: "'"$LOGIN"'") {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}' 2>/dev/null)

    python3 - "$LOGIN" "$NAME" "$AVATAR" "$FOLLOWERS" "$FOLLOWING" "$REPOS" "$STARS" "$CAL" <<'PYEOF' > "$CACHE" 2>/dev/null
import json, sys, datetime

login, name, avatar, followers, following, repos, stars, raw = sys.argv[1:9]
try:
    cal = json.loads(raw)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    streak = 0
    today = datetime.date.today()
    pos = len(days) - 1
    if days and days[pos]["date"] != today.isoformat():
        pos -= 1  # today not yet counted; allow streak up to yesterday
    while pos >= 0 and days[pos]["contributionCount"] > 0:
        streak += 1
        pos -= 1
    total = sum(d["contributionCount"] for d in days)
except Exception:
    streak, total = 0, 0

print(json.dumps({
    "login": login,
    "name": name,
    "at": "@" + login,
    "avatar": avatar,
    "followers": int(followers),
    "following": int(following),
    "repos": int(repos),
    "stars": int(stars),
    "streak": streak,
    "contributions": total,
}))
PYEOF
}

mkdir -p "$(dirname "$CACHE")"

if need_refresh || [ ! -s "$CACHE" ]; then
    refresh || exit 1
fi

cat "$CACHE"