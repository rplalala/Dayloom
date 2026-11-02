#!/usr/bin/env bash
set -euo pipefail

fail() { printf '%s\n' "$1" >&2; exit 1; }

main() {
  local light=0 directory=dayloom suffix=
  for argument in "$@"; do
    case "$argument" in
      --light) light=1 ;;
      *) fail 'Usage: bash install.sh [--light]' ;;
    esac
  done
  if (( light )); then directory=dayloom-light; suffix=-light; fi
  for tool in curl tar sha256sum docker; do
    command -v "$tool" >/dev/null || fail "Install $tool first."
  done
  [[ ! -e $directory && ! -L $directory ]] || fail "The $directory directory already exists; run its start.sh or choose a fresh parent directory."

  local platform architecture
  platform=$(docker info --format '{{.OSType}}/{{.Architecture}}') || \
    fail 'Docker is unavailable; start the daemon and check access.'
  case "$platform" in
    linux/amd64|linux/x86_64) architecture=amd64 ;;
    linux/arm64|linux/aarch64) architecture=arm64 ;;
    *) fail 'Supported Docker engines are Linux amd64 and arm64.' ;;
  esac
  if [[ $architecture == arm64 ]] && (( ! light )); then
    fail 'ARM64 supports light deployment only; run the installer with --light.'
  fi

  local repository=https://github.com/rplalala/Dayloom
  local resolved version archive release
  # Resolve once, then pin both downloads to the same published release.
  resolved=$(curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --output /dev/null --write-out '%{url_effective}' "$repository/releases/latest")
  [[ $resolved =~ ^https://github\.com/rplalala/Dayloom/releases/tag/dayloom-v([0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?)$ ]] || \
    fail 'The latest release does not have a supported Dayloom version tag.'
  version=${BASH_REMATCH[1]}
  archive="dayloom-${version}${suffix}-linux-${architecture}.tar.gz"
  release="$repository/releases/download/dayloom-v$version"

  mkdir "$directory"
  cd "$directory"
  printf 'Installing Dayloom %s in %s\n' "$version" "$PWD"
  curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
    "$release/$archive" --output "$archive"
  curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
    "$release/$archive.sha256" --output "$archive.sha256"
  sha256sum --ignore-missing --check "$archive.sha256"
  tar -xzf "$archive"
  sha256sum --check "$archive.sha256"

  # A curl | bash invocation consumes stdin; reconnect prompts to the terminal.
  if [[ -t 1 && -r /dev/tty ]]; then
    bash start.sh </dev/tty
  else
    bash start.sh --non-interactive </dev/null
  fi
}

main "$@"
