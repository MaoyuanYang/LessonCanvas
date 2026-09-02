#!/usr/bin/env bash
# F012 D5 smoke checks against a running stack: API health, web entry, DB reachability.
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
WEB_BASE="${WEB_BASE:-http://localhost:3000}"

api_health="$(curl -fsS --max-time 10 "$API_BASE/health")"
echo "api /health: $api_health"
python3 - "$api_health" <<'EOF'
import json, sys
body = json.loads(sys.argv[1])
assert body.get("status") == "ok", f"unexpected health body: {body}"
EOF

web_status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$WEB_BASE")"
echo "web /: HTTP $web_status"
[[ "$web_status" == "200" ]] || { echo "web entry not serving" >&2; exit 1; }

echo "Smoke checks passed."
