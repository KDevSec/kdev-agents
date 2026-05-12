#!/usr/bin/env bash
# Sync scripts from main kdev-agents repo to dist repo
#
# Usage:
#   ./sync-to-dist.sh <version>
#
# Example:
#   ./sync-to-dist.sh v0.2.0

set -euo pipefail

VERSION="${1:-latest}"
DIST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../kdev-plugins-dist" && pwd)"
MAIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$VERSION" == "latest" ]]; then
    # Find latest version
    LATEST_VERSION=$(ls -1 "$DIST_ROOT/releases/kdev-code-graph/" | grep -E '^v[0-9]+' | sort -V | tail -1)
    if [[ -z "$LATEST_VERSION" ]]; then
        echo "Error: No versioned releases found"
        exit 1
    fi
    VERSION="$LATEST_VERSION"
fi

echo "Syncing kdev-code-graph $VERSION scripts to dist repo..."

VERSION_DIR="$DIST_ROOT/releases/kdev-code-graph/$VERSION"
LATEST_DIR="$DIST_ROOT/releases/kdev-code-graph/latest"

mkdir -p "$VERSION_DIR" "$LATEST_DIR"

# Copy scripts from main repo
cp "$MAIN_ROOT/scripts/setup-kdev-codegraph.sh" "$VERSION_DIR/setup.sh"
cp "$MAIN_ROOT/scripts/setup-kdev-codegraph.ps1" "$VERSION_DIR/setup.ps1"
cp "$MAIN_ROOT/plugins/kdev-code-graph/install.sh" "$VERSION_DIR/install.sh"
cp "$MAIN_ROOT/plugins/kdev-code-graph/install.ps1" "$VERSION_DIR/install.ps1"

# Update latest
cp "$VERSION_DIR/setup.sh" "$LATEST_DIR/setup.sh"
cp "$VERSION_DIR/setup.ps1" "$LATEST_DIR/setup.ps1"
cp "$VERSION_DIR/install.sh" "$LATEST_DIR/install.sh"
cp "$VERSION_DIR/install.ps1" "$LATEST_DIR/install.ps1"

echo "Done. Files in $VERSION_DIR:"
ls -la "$VERSION_DIR"

echo ""
echo "To commit and push:"
echo "  cd $DIST_ROOT"
echo "  git add releases/kdev-code-graph/$VERSION releases/kdev-code-graph/latest"
echo "  git commit -m 'sync: kdev-code-graph $VERSION scripts'"
echo "  git push"