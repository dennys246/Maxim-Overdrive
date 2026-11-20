#!/usr/bin/env bash
# Install the pinned Godot (ci/godot.env) into <dest>, refusing a download whose SHA-256 differs, and print the path
# of the binary. CI runners have no Godot, and scripts/godot_check.py (the gate's B6 step) needs one.
#
#   ci/install_godot.sh linux-x86_64 <dest>    # ubuntu-latest, and the golden image
#   ci/install_godot.sh macos-universal <dest> # macos-latest
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=godot.env
. "$here/godot.env"

case "${1:-}" in
  linux-x86_64) zip="$GODOT_LINUX_X86_64_ZIP" sha="$GODOT_LINUX_X86_64_SHA256" bin="$GODOT_LINUX_X86_64_BIN" ;;
  macos-universal) zip="$GODOT_MACOS_UNIVERSAL_ZIP" sha="$GODOT_MACOS_UNIVERSAL_SHA256" bin="$GODOT_MACOS_UNIVERSAL_BIN" ;;
  *) echo "usage: $0 linux-x86_64|macos-universal <dest>" >&2; exit 2 ;;
esac
dest="${2:?usage: $0 <platform> <dest>}"

mkdir -p "$dest"
curl -sSfL --retry 3 -o "$dest/$zip" "$GODOT_RELEASE_URL/$zip"
if command -v sha256sum >/dev/null 2>&1; then
  echo "$sha  $dest/$zip" | sha256sum -c - >&2
else
  echo "$sha  $dest/$zip" | shasum -a 256 -c - >&2
fi
unzip -q -o "$dest/$zip" -d "$dest"
rm "$dest/$zip"
version="$("$dest/$bin" --headless --version)"
[ "$version" = "$GODOT_VERSION" ] || { echo "installed Godot reports '$version', not $GODOT_VERSION" >&2; exit 1; }
echo "$dest/$bin"
