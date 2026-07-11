#!/usr/bin/env sh
set -eu

API_URL="${AUTOSNAB_API_URL:-http://localhost:8000}"
CADASTRAL_NUMBER="66:41:0101001:123"

printf '1/3 GET /ping\n'
curl --fail --silent "$API_URL/ping"
printf '\n2/3 POST /query (external emulator may wait up to 60 seconds)\n'
curl --fail --silent --max-time 75 \
  -X POST "$API_URL/query" \
  -H 'Content-Type: application/json' \
  -d "{\"cadastral_number\":\"$CADASTRAL_NUMBER\",\"latitude\":56.8389,\"longitude\":60.6057}"
printf '\n3/3 GET /history\n'
curl --fail --silent --get "$API_URL/history" \
  --data-urlencode "cadastral_number=$CADASTRAL_NUMBER" \
  --data-urlencode 'limit=10' \
  --data-urlencode 'offset=0'
printf '\n+ Smoke test passed\n'
