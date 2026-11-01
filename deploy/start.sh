#!/usr/bin/env bash
set -euo pipefail
umask 077

BUNDLE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
CONFIG_DIR="$BUNDLE_DIR/config"
NON_INTERACTIVE=0
CONFIGURE=0
for argument in "$@"; do
  case "$argument" in
    --non-interactive) NON_INTERACTIVE=1 ;;
    --configure) CONFIGURE=1 ;;
    --help|-h) printf '%s\n' 'Usage: bash start.sh [--non-interactive] [--configure]'; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$argument" >&2; exit 2 ;;
  esac
done

fail() { printf '%s\n' "$1" >&2; exit 1; }
command -v docker >/dev/null || fail 'Install Docker Engine and its Compose plugin first.'
docker info >/dev/null 2>&1 || fail 'Docker is unavailable; start the daemon and check access.'
ENGINE=$(docker version --format '{{.Server.Version}}')
if [[ ! ${ENGINE%%.*} =~ ^[0-9]+$ ]] || (( ${ENGINE%%.*} < 28 )); then
  fail 'Docker Engine 28 or newer is required for loopback port isolation.'
fi
COMPOSE_HELP=$(docker compose up --help)
grep -q -- '--wait-timeout' <<< "$COMPOSE_HELP" || fail 'Update Compose to a version supporting up --wait and --wait-timeout.'
ARCH=$(docker info --format '{{.OSType}}/{{.Architecture}}')
[[ $ARCH == linux/x86_64 || $ARCH == linux/amd64 ]] || fail 'This release supports Linux amd64 container engines.'

# Read only named public scalars. Do not source or evaluate dotenv as shell code.
public_value() {
  local file=$1 key=$2 name value
  [[ -f $file ]] || return 0
  while IFS='=' read -r name value || [[ -n ${name:-} ]]; do
    if [[ $name == "$key" ]]; then
      value=${value%$'\r'}
      value=${value#\"}; value=${value%\"}
      value=${value#\'}; value=${value%\'}
      printf '%s' "$value"
      return 0
    fi
  done < "$file"
}
pick() {
  local key=$1 value=${!1:-}
  [[ -n $value ]] || value=$(public_value "$CONFIG_DIR/.env" "$key")
  [[ -n $value ]] || value=$(public_value "$BUNDLE_DIR/.env.example" "$key")
  printf '%s' "$value"
}
APP_IMAGE=$(pick DAYLOOM_APP_IMAGE)
BASELINE_IMAGE=$(pick DAYLOOM_BASELINE_IMAGE)
BASELINE_ID=$(pick DAYLOOM_BASELINE_ID)
PORT=$(pick DAYLOOM_HOST_PORT)
PROJECT=$(pick COMPOSE_PROJECT_NAME)
DB_NAME=$(pick DAYLOOM_DB_NAME)
DB_USER=$(pick DAYLOOM_DB_USER)
[[ $BASELINE_ID =~ ^[a-f0-9]{64}$ ]] || fail 'Use a released bundle, or explicitly select the locally verified baseline identity.'
[[ $PORT =~ ^[0-9]{1,5}$ ]] || fail 'DAYLOOM_HOST_PORT must be a valid TCP port.'
PORT=$((10#$PORT))
if (( PORT <= 0 || PORT > 65535 )); then fail 'DAYLOOM_HOST_PORT must be a valid TCP port.'; fi
[[ $PROJECT =~ ^[a-z0-9][a-z0-9_-]{0,62}$ ]] || fail 'Invalid Compose project name.'
for image in "$APP_IMAGE" "$BASELINE_IMAGE"; do
  [[ $image =~ ^[A-Za-z0-9][A-Za-z0-9:/@._-]+$ ]] || fail 'Invalid image reference.'
done
if (true 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  OWN_APP=$(docker ps -q --filter "label=com.docker.compose.project=$PROJECT" --filter 'label=com.docker.compose.service=app')
  [[ -n $OWN_APP ]] || fail 'The selected host port is occupied; choose DAYLOOM_HOST_PORT.'
  OWN_PORTS=$(docker port "$OWN_APP" 5173/tcp)
  grep -Fxq "127.0.0.1:$PORT" <<< "$OWN_PORTS" || fail 'The selected host port is occupied by another service.'
fi

native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
export MSYS_NO_PATHCONV=1
[[ -f $CONFIG_DIR/.env ]] && FIRST_INSTALL=0 || FIRST_INSTALL=1
[[ ! -L $CONFIG_DIR ]] || fail 'The instance configuration directory must not be a symbolic link.'
mkdir -p -- "$CONFIG_DIR"
CONFIG_MOUNT=$(native_path "$CONFIG_DIR")
for image in "$APP_IMAGE" "$BASELINE_IMAGE"; do
  docker image inspect "$image" >/dev/null 2>&1 || docker pull "$image"
done
OWNER=$(docker run --rm --user 0:0 --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$APP_IMAGE" probe-directory --directory /instance)
RUN_UID=${DAYLOOM_RUN_UID:-${OWNER%%:*}}
RUN_GID=${DAYLOOM_RUN_GID:-${OWNER##*:}}
[[ $RUN_UID =~ ^[0-9]+$ && $RUN_GID =~ ^[0-9]+$ ]] || fail 'Invalid runtime UID/GID.'
helper() {
  docker run --rm --user "$RUN_UID:$RUN_GID" --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$APP_IMAGE" "$@"
}
helper prepare --directory /instance --origin "http://localhost:$PORT" \
  --app-image "$APP_IMAGE" --baseline-image "$BASELINE_IMAGE" --baseline-id "$BASELINE_ID" \
  --uid "$RUN_UID" --gid "$RUN_GID" --project "$PROJECT" \
  --database-name "$DB_NAME" --database-user "$DB_USER"

if (( ! NON_INTERACTIVE )) && [[ -t 0 ]] && (( FIRST_INSTALL || CONFIGURE )); then
  read -r -p 'Configure provider services now? [y/N] ' ANSWER
  if [[ $ANSWER == y || $ANSWER == Y ]]; then
    docker run --rm -it --user "$RUN_UID:$RUN_GID" --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$APP_IMAGE" configure-providers --directory /instance
  fi
fi

COMPOSE=(docker compose --project-directory "$(native_path "$BUNDLE_DIR")" --env-file "$(native_path "$CONFIG_DIR/.env")" -f "$(native_path "$BUNDLE_DIR/compose.yaml")")
# Public overrides were validated and persisted above. Prevent ambient libpq/deployment
# values from making Compose use different credentials than the mounted instance.
unset DAYLOOM_APP_IMAGE DAYLOOM_BASELINE_IMAGE DAYLOOM_BASELINE_ID DAYLOOM_HOST_PORT
unset DAYLOOM_RUN_UID DAYLOOM_RUN_GID COMPOSE_PROJECT_NAME DAYLOOM_DB_NAME DAYLOOM_DB_USER
unset DAYLOOM_DB_PASSWORD
# A placeholder is used only while creating the network; the app is not started yet.
export DAYLOOM_MANAGEMENT_PEERS=127.0.0.1
"${COMPOSE[@]}" up -d --wait --wait-timeout 180 postgres
POSTGRES_ID=$("${COMPOSE[@]}" ps -q postgres)
GATEWAY=$(docker inspect "$POSTGRES_ID" --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}')
helper set-management-peers --directory /instance --peers "$GATEWAY"
unset DAYLOOM_MANAGEMENT_PEERS
"${COMPOSE[@]}" run --rm --no-deps --user 0:0 app prepare-logs --uid "$RUN_UID" --gid "$RUN_GID"
"${COMPOSE[@]}" up -d --wait --wait-timeout "${DAYLOOM_STARTUP_TIMEOUT:-1800}"
"${COMPOSE[@]}" exec -T app python -m deploy.docker.app_entrypoint status --directory /instance
printf '\nDayloom is running at http://localhost:%s\n' "$PORT"
printf 'Complete or inspect setup at http://localhost:%s/config. Saved provider changes require an app restart.\n' "$PORT"
printf '%s\n' 'The first bootstrap output contains the instance configuration password. The Product test admin is separate.'
printf '%s\n' 'Logs: docker compose --env-file config/.env logs -f app'
printf '%s\n' 'Apply saved settings: docker compose --env-file config/.env restart app'
