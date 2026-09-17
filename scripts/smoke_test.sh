#!/usr/bin/env bash
# Exercises every scenario in evidence/milestone3_evidence.md against a
# running instance (local uvicorn or docker compose) so the evidence pack
# can be reproduced on demand -- e.g. live during the Milestone 4 defence,
# or by any teammate verifying the working slice independently.
#
# Usage:
#   docker compose up -d          # or: uvicorn app.main:app --reload
#   ./scripts/smoke_test.sh       # defaults to http://localhost:8080
#   BASE_URL=http://localhost:9000 ./scripts/smoke_test.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

hr() { printf '\n== %s ==\n' "$1"; }

hr "health"
curl -sf "${BASE_URL}/health"; echo

hr "E1: normal submission"
RESPONSE=$(curl -s -w '\n%{http_code}' -X POST "${BASE_URL}/faults" \
  -H "Content-Type: application/json" \
  -d '{"equipment_id":"LAB-014","location":"Science Building, Room 214","description":"Projector will not power on.","severity":"high","reporter_id":"STU-2026-001"}')
echo "$RESPONSE"
BODY=$(echo "$RESPONSE" | head -n1)
TICKET_ID=$(echo "$BODY" | python -c "import sys,json;print(json.load(sys.stdin)['ticket_id'])")

hr "E2: retrieve existing ticket ($TICKET_ID)"
curl -s -w '\nHTTP %{http_code}\n' "${BASE_URL}/faults/${TICKET_ID}"

hr "E3: retrieve missing ticket (expect 404)"
curl -s -w '\nHTTP %{http_code}\n' "${BASE_URL}/faults/FR-DOESNOTEXIST"

hr "E4: missing required field (expect 400)"
curl -s -w '\nHTTP %{http_code}\n' -X POST "${BASE_URL}/faults" \
  -H "Content-Type: application/json" \
  -d '{"location":"Room 1","description":"No equipment id given here.","severity":"low","reporter_id":"STU-2026-002"}'

hr "E5: invalid severity enum (expect 400)"
curl -s -w '\nHTTP %{http_code}\n' -X POST "${BASE_URL}/faults" \
  -H "Content-Type: application/json" \
  -d '{"equipment_id":"AC-203","location":"Room 2","description":"Bad severity value test.","severity":"urgent","reporter_id":"STU-2026-003"}'

hr "E5b: malformed JSON body (expect 400, app-shaped error)"
curl -s -w '\nHTTP %{http_code}\n' -X POST "${BASE_URL}/faults" \
  -H "Content-Type: application/json" \
  -d '{not valid json'

hr "Done."
echo "E6 (DB_FORCE_FAILURE) and E7 (NOTIFY_FORCE_FAILURE) need the app"
echo "container restarted with that flag set -- e.g.:"
echo "  DB_FORCE_FAILURE=1 docker compose up -d app"
echo "  ./scripts/smoke_test.sh   # rerun just to hit POST /faults again"
echo "  docker compose up -d app  # reset back to normal"
