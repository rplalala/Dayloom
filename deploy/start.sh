#!/usr/bin/env bash
set -euo pipefail
umask 077

BUNDLE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
CONFIG_DIR="$BUNDLE_DIR/config"
NON_INTERACTIVE=0
CONFIGURE=0
OPERATION=launch
OPERATION_ARGS=()
if [[ ${1:-} =~ ^(backup|verify-backup|restore-backup|upgrade)$ ]]; then
  OPERATION=$1
  shift
  OPERATION_ARGS=("$@")
  set --
fi
for argument in "$@"; do
  case "$argument" in
    --non-interactive) NON_INTERACTIVE=1 ;;
    --configure) CONFIGURE=1 ;;
    --help|-h) printf '%s\n' 'Usage: bash start.sh [--non-interactive] [--configure]' \
      '       bash start.sh backup|verify-backup /absolute/NAME.dayloom-backup' \
      '       bash start.sh restore-backup /absolute/NAME.dayloom-backup --project NEW --port PORT' \
      '       bash start.sh upgrade IMAGE --backup /absolute/NAME.dayloom-backup'; exit 0 ;;
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
native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
export MSYS_NO_PATHCONV=1

# Maintenance always selects its instance from this bundle, never an ambient project.
if [[ $OPERATION != launch ]]; then
  [[ -z ${DAYLOOM_DB_URL:-} ]] || fail 'Unset ambient DAYLOOM_DB_URL before maintenance.'
  [[ ${#OPERATION_ARGS[@]} -ge 1 ]] || fail 'Select an explicit private backup directory.'
  BACKUP=${OPERATION_ARGS[0]}
  CANDIDATE=
  RESTORE_PROJECT=
  RESTORE_PORT=
  if [[ $OPERATION == upgrade ]]; then
    [[ ${#OPERATION_ARGS[@]} == 3 && ${OPERATION_ARGS[1]} == --backup ]] || fail 'Use upgrade IMAGE --backup /absolute/NAME.dayloom-backup.'
    CANDIDATE=$BACKUP
    BACKUP=${OPERATION_ARGS[2]}
    [[ $CANDIDATE =~ ^[A-Za-z0-9][A-Za-z0-9:/@._-]+$ ]] || fail 'Invalid upgrade image reference.'
  elif [[ $OPERATION == restore-backup ]]; then
    [[ ${#OPERATION_ARGS[@]} == 5 && ${OPERATION_ARGS[1]} == --project && ${OPERATION_ARGS[3]} == --port ]] || fail 'Use restore-backup PATH --project NEW_PROJECT --port PORT.'
    RESTORE_PROJECT=${OPERATION_ARGS[2]}
    RESTORE_PORT=${OPERATION_ARGS[4]}
    [[ $RESTORE_PROJECT =~ ^[a-z0-9][a-z0-9_-]{0,62}$ ]] || fail 'Invalid destination project name.'
    [[ $RESTORE_PORT =~ ^[0-9]{1,5}$ ]] || fail 'Invalid destination port.'
    RESTORE_PORT=$((10#$RESTORE_PORT))
    (( RESTORE_PORT > 0 && RESTORE_PORT <= 65535 )) || fail 'Invalid destination port.'
    [[ ! -e $CONFIG_DIR/.env ]] || fail 'Restore into a fresh extracted bundle with empty config.'
    [[ ! -L $CONFIG_DIR ]] || fail 'Configuration must not be a symbolic link.'
    [[ -z $(docker ps -aq --filter "label=com.docker.compose.project=$RESTORE_PROJECT") ]] || fail 'Destination project already has containers; use a new project.'
    [[ -z $(docker volume ls -q --filter "label=com.docker.compose.project=$RESTORE_PROJECT") ]] || fail 'Destination project already has storage; use a new project.'
    if (true 3<>"/dev/tcp/127.0.0.1/$RESTORE_PORT") 2>/dev/null; then fail 'Destination port is occupied.'; fi
  else
    [[ ${#OPERATION_ARGS[@]} == 1 ]] || fail 'Select exactly one backup directory.'
  fi
  [[ $BACKUP == /* || $BACKUP =~ ^[A-Za-z]:[/\\] ]] || fail 'Backup path must be absolute.'
  [[ $BACKUP == *.dayloom-backup ]] || fail 'Use a private directory ending in .dayloom-backup.'
  BACKUP_PARENT=$(cd -- "$(dirname -- "$BACKUP")" && pwd -P)
  BACKUP_NAME=$(basename -- "$BACKUP")
  [[ ! -L $BACKUP ]] || fail 'Backup directory must not be a symbolic link.'
  [[ $BACKUP_PARENT != "$BUNDLE_DIR" && $BACKUP_PARENT != "$BUNDLE_DIR/"* ]] || fail 'Keep backups outside the deployment bundle.'
  BACKUP_MOUNT=$(native_path "$BACKUP_PARENT")
  docker image inspect "$BASELINE_IMAGE" >/dev/null 2>&1 || docker pull "$BASELINE_IMAGE"
  utility() {
    docker run --rm --user 0:0 --entrypoint python3 \
      --mount "type=bind,source=$BACKUP_MOUNT,target=/backups,readonly" "$BASELINE_IMAGE" \
      -m deploy.release.maintenance "$@" "/backups/$BACKUP_NAME"
  }
  if [[ $OPERATION == verify-backup ]]; then utility verify; exit 0; fi
  if [[ $OPERATION == restore-backup ]]; then
    utility verify
    mkdir -p -- "$CONFIG_DIR"
    OWNER=$(docker run --rm --user 0:0 --mount "type=bind,source=$(native_path "$CONFIG_DIR"),target=/instance" "$APP_IMAGE" probe-directory --directory /instance)
    docker run --rm --user "$OWNER" --entrypoint python3 \
      --mount "type=bind,source=$BACKUP_MOUNT,target=/backups,readonly" \
      --mount "type=bind,source=$(native_path "$CONFIG_DIR"),target=/instance" \
      "$BASELINE_IMAGE" -m deploy.release.maintenance restore-config "/backups/$BACKUP_NAME" --config /instance
    APP_IMAGE=$(public_value "$CONFIG_DIR/.env" DAYLOOM_APP_IMAGE)
    BASELINE_IMAGE=$(public_value "$CONFIG_DIR/.env" DAYLOOM_BASELINE_IMAGE)
  else
    [[ -f $CONFIG_DIR/.env ]] || fail 'No installed instance configuration in this bundle.'
    APP_IMAGE=$(public_value "$CONFIG_DIR/.env" DAYLOOM_APP_IMAGE)
    BASELINE_IMAGE=$(public_value "$CONFIG_DIR/.env" DAYLOOM_BASELINE_IMAGE)
  fi
  BASELINE_ID=$(public_value "$CONFIG_DIR/.env" DAYLOOM_BASELINE_ID)
  RUN_UID=$(public_value "$CONFIG_DIR/.env" DAYLOOM_RUN_UID)
  RUN_GID=$(public_value "$CONFIG_DIR/.env" DAYLOOM_RUN_GID)
  CONFIG_MOUNT=$(native_path "$CONFIG_DIR")
  COMPOSE=(docker compose --project-directory "$(native_path "$BUNDLE_DIR")" --env-file "$(native_path "$CONFIG_DIR/.env")" -f "$(native_path "$BUNDLE_DIR/compose.yaml")")
  unset DAYLOOM_APP_IMAGE DAYLOOM_BASELINE_IMAGE DAYLOOM_BASELINE_ID DAYLOOM_HOST_PORT
  unset DAYLOOM_RUN_UID DAYLOOM_RUN_GID COMPOSE_PROJECT_NAME DAYLOOM_DB_NAME DAYLOOM_DB_USER DAYLOOM_DB_PASSWORD DAYLOOM_MANAGEMENT_PEERS
  docker run --rm --network none --user 0:0 --entrypoint python \
    --mount "type=bind,source=$CONFIG_MOUNT,target=/instance,readonly" "$APP_IMAGE" \
    -m deploy.docker.upgrade --check-local-target
  if [[ $OPERATION == restore-backup ]]; then
    OWNER=$(docker run --rm --user 0:0 --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$APP_IMAGE" probe-directory --directory /instance)
    RUN_UID=${OWNER%%:*}; RUN_GID=${OWNER##*:}
    docker run --rm --user "$RUN_UID:$RUN_GID" --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$APP_IMAGE" \
      prepare --directory /instance --origin "http://localhost:$RESTORE_PORT" --app-image "$APP_IMAGE" \
      --baseline-image "$BASELINE_IMAGE" --baseline-id "$BASELINE_ID" --uid "$RUN_UID" --gid "$RUN_GID" \
      --project "$RESTORE_PROJECT" --database-name "$(public_value "$CONFIG_DIR/.env" DAYLOOM_DB_NAME)" \
      --database-user "$(public_value "$CONFIG_DIR/.env" DAYLOOM_DB_USER)"
    "${COMPOSE[@]}" up -d --wait --wait-timeout 180 postgres
    "${COMPOSE[@]}" run --rm --no-deps --entrypoint python3 \
      -v "$BACKUP_MOUNT:/backups:ro" init -m deploy.release.maintenance restore "/backups/$BACKUP_NAME"
    exec bash "$BUNDLE_DIR/start.sh" --non-interactive
  fi
  WAS_RUNNING=$("${COMPOSE[@]}" ps --status running -q app)
  # shellcheck disable=SC2329 # Invoked by the EXIT trap.
  resume_after_backup() {
    if [[ -n $WAS_RUNNING ]]; then docker start "$WAS_RUNNING" >/dev/null; fi
  }
  trap resume_after_backup EXIT
  "${COMPOSE[@]}" stop app
  "${COMPOSE[@]}" run --rm --no-deps --user "$RUN_UID:$RUN_GID" --entrypoint python3 \
    -v "$BACKUP_MOUNT:/backups" -v "$CONFIG_MOUNT:/instance:ro" init \
    -m deploy.release.maintenance backup "/backups/$BACKUP_NAME" --config /instance --expect-id "$BASELINE_ID"
  if [[ $OPERATION == backup ]]; then exit 0; fi
  # Candidate startup validates the installed receipt, resources and migration checksums.
  # Do not run init: a new release's factory baseline is irrelevant to this instance.
  trap - EXIT
  docker image inspect "$CANDIDATE" >/dev/null 2>&1 || docker pull "$CANDIDATE"
  DAYLOOM_APP_IMAGE=$CANDIDATE "${COMPOSE[@]}" run --rm --no-deps --entrypoint python app \
    -m deploy.docker.upgrade --baseline-id "$BASELINE_ID" || \
    fail 'Upgrade rejected. App remains stopped; retain the backup and recover with compatible images or restore into independent storage.'
  PORT=$(public_value "$CONFIG_DIR/.env" DAYLOOM_HOST_PORT)
  PROJECT=$(public_value "$CONFIG_DIR/.env" COMPOSE_PROJECT_NAME)
  docker run --rm --user "$RUN_UID:$RUN_GID" --mount "type=bind,source=$CONFIG_MOUNT,target=/instance" "$CANDIDATE" \
    prepare --directory /instance --origin "http://localhost:$PORT" --app-image "$CANDIDATE" \
    --baseline-image "$BASELINE_IMAGE" --baseline-id "$BASELINE_ID" --uid "$RUN_UID" --gid "$RUN_GID" \
    --project "$PROJECT" --database-name "$(public_value "$CONFIG_DIR/.env" DAYLOOM_DB_NAME)" \
    --database-user "$(public_value "$CONFIG_DIR/.env" DAYLOOM_DB_USER)"
  "${COMPOSE[@]}" up -d --no-deps --wait --wait-timeout "${DAYLOOM_STARTUP_TIMEOUT:-1800}" app || \
    fail 'Upgrade did not become healthy. Preserve data and recover from the pre-upgrade backup if migrations are incompatible.'
  printf '%s\n' 'Application upgraded; installed baseline and user content retained. Keep the pre-upgrade backup private.'
  exit 0
fi
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
