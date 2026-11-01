#!/usr/bin/env bash
set -euo pipefail

fail() { printf '%s\n' "$1" >&2; exit 1; }

main() {
  (( $# == 0 )) || fail 'Usage: bash install.sh (installs the latest release into ./dayloom)'
  for tool in curl tar sha256sum; do
    command -v "$tool" >/dev/null || fail "Install $tool first."
  done
  [[ ! -e dayloom && ! -L dayloom ]] || fail 'The dayloom directory already exists; run its start.sh or choose a fresh parent directory.'

  local repository=https://github.com/rplalala/Dayloom
  local resolved version archive release
  # Resolve once, then pin both downloads to the same published release.
  resolved=$(curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --output /dev/null --write-out '%{url_effective}' "$repository/releases/latest")
  [[ $resolved =~ ^https://github\.com/rplalala/Dayloom/releases/tag/dayloom-v([0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?)$ ]] || \
    fail 'The latest release does not have a supported Dayloom version tag.'
  version=${BASH_REMATCH[1]}
  archive="dayloom-${version}-linux-amd64.tar.gz"
  release="$repository/releases/download/dayloom-v$version"

  mkdir dayloom
  cd dayloom
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
