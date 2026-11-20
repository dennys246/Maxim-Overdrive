#!/usr/bin/env bash
# Install the pinned Godot (ci/godot.env) into <dest>, refusing a download whose SHA-256 differs, and print the path
# of the binary. CI runners have no Godot, and scripts/godot_check.py (the gate's B6 step) needs one.
#
#   ci/install_godot.sh <dest> [platform]   # the platform is detected; pass it only to override
#   ci/install_godot.sh --platform          # print the detected platform and stop
#
# Platforms: linux-x86_64 (ubuntu-latest and the golden image), macos-universal (macos-latest, either CPU). Any other
# machine is refused: there is no pinned build for it.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=godot.env
. "$here/godot.env"

detect() {
  case "$(uname -s)/$(uname -m)" in
    Linux/x86_64) echo linux-x86_64 ;;
    Darwin/*) echo macos-universal ;;
    *) echo "no pinned Godot build for $(uname -s)/$(uname -m)" >&2; return 1 ;;
  esac
}

if [ "${1:-}" = "--platform" ]; then detect; exit; fi
dest="${1:?usage: $0 <dest> [platform]}"
platform="${2:-$(detect)}"
case "$platform" in
  linux-x86_64) zip="$GODOT_LINUX_X86_64_ZIP" sha="$GODOT_LINUX_X86_64_SHA256" bin="$GODOT_LINUX_X86_64_BIN" ;;
  macos-universal) zip="$GODOT_MACOS_UNIVERSAL_ZIP" sha="$GODOT_MACOS_UNIVERSAL_SHA256" bin="$GODOT_MACOS_UNIVERSAL_BIN" ;;
  *) echo "unknown platform '$platform' (linux-x86_64 or macos-universal)" >&2; exit 2 ;;
esac

mkdir -p "$dest"
# --proto =https: a redirect may never downgrade to plain http (the digest check below is the integrity guard).
curl -sSfL --proto '=https' --retry 3 -o "$dest/$zip" "$GODOT_RELEASE_URL/$zip"
if command -v sha256sum >/dev/null 2>&1; then check=(sha256sum -c -); else check=(shasum -a 256 -c -); fi
if ! echo "$sha  $dest/$zip" | "${check[@]}" >&2; then
  rm -f "$dest/$zip"
  echo "the download's SHA-256 is not the pinned $sha; deleted it" >&2
  exit 1
fi
unzip -q -o "$dest/$zip" -d "$dest"
rm "$dest/$zip"
# Godot writes per-user files under HOME (and XDG on Linux) even for --version: keep them out of the real home.
home="$dest/home"
mkdir -p "$home"
version="$(HOME="$home" XDG_DATA_HOME="$home/.local/share" XDG_CONFIG_HOME="$home/.config" \
  XDG_CACHE_HOME="$home/.cache" "$dest/$bin" --headless --version)"
[ "$version" = "$GODOT_VERSION" ] || { echo "installed Godot reports '$version', not $GODOT_VERSION" >&2; exit 1; }
echo "$dest/$bin"
