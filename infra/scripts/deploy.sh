#!/usr/bin/env bash
# F012 D1/D5 + F014 D2 deployment chain: build -> migrate (api entrypoint) -> start -> health -> embedding backfill -> smoke.
# Every step must actually execute; this script never fabricates success.
# Usage: infra/scripts/deploy.sh [--env-file infra/deploy.env]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/infra/deploy.env}"
if [[ "${1:-}" == "--env-file" && -n "${2:-}" ]]; then ENV_FILE="$2"; fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE (copy infra/deploy.env.example first)" >&2
  exit 1
fi

cd "$REPO_ROOT"
echo "== [1/5] Building images =="
docker compose -f infra/docker-compose.yml --profile app --env-file "$ENV_FILE" build

echo "== [2/5] Starting full stack (api runs migrations before serving) =="
docker compose -f infra/docker-compose.yml --profile app --env-file "$ENV_FILE" up -d

echo "== [3/5] Waiting for health =="
timeout 300 bash -c '
  until docker compose -f infra/docker-compose.yml --profile app --env-file "'"$ENV_FILE"'" ps --format json \
      | python3 -c "
import json,sys
rows=[json.loads(l) for l in sys.stdin if l.strip()]
targets={r[\"Service\"] for r in rows if r[\"Service\"] in {\"postgres\",\"redis\",\"minio\",\"api\",\"worker\",\"web\"}}
bad=[r[\"Service\"] for r in rows if r[\"Service\"] in targets and r.get(\"Health\") not in (\"healthy\",)]
sys.exit(0 if not bad and len(targets)==6 else 1)
"; do sleep 5; done'
echo "All services healthy."

echo "== [4/5] Embedding backfill (F014 D2, idempotent) =="
docker compose -f infra/docker-compose.yml --profile app --env-file "$ENV_FILE" run --rm --no-deps api python scripts/backfill_embeddings.py

echo "== [5/5] Smoke checks =="
"$(dirname "${BASH_SOURCE[0]}")/smoke.sh"

echo "Deployment chain complete."
