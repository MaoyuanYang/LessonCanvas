#!/usr/bin/env bash
# F012 D5 teardown: stop and remove all services and volumes (clean-state redeploy).
# Destructive: resets PostgreSQL and MinIO data. Never run against shared data.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/infra/deploy.env}"
[[ -f "$ENV_FILE" ]] || ENV_FILE=/dev/null

read -r -p "This deletes ALL LessonCanvas containers and volumes. Continue? [y/N] " ans
[[ "$ans" == "y" ]] || exit 1

cd "$REPO_ROOT"
docker compose -f infra/docker-compose.yml --profile app --env-file "$ENV_FILE" down -v --remove-orphans
echo "Teardown complete (clean state)."
