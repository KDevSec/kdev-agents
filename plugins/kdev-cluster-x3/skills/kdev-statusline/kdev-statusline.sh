#!/usr/bin/env bash
# KDev cluster-x3 CLI statusLine — single-line HUD reading .kdev/state.md.
# Output target: ≤80 chars. Falls back to empty (no statusline) if state missing.

set -euo pipefail

STATE="${1:-.kdev/state.md}"
if [[ ! -r "$STATE" ]]; then
    exit 0
fi

slug=$(grep -m1 "^feature_slug:" "$STATE" | sed 's/^feature_slug: *//')
active=$(grep -m1 "^current_active_group:" "$STATE" | sed 's/^current_active_group: *//')

group_status() {
    local g="$1"
    local s
    s=$(awk -v g="$g" '
        $0 == "## " g { found=1; next }
        found && /^## / { exit }
        found && /^status:/ { print $2; exit }
    ' "$STATE")
    case "$s" in
        complete)    echo "✅" ;;
        in_progress) echo "🟡" ;;
        blocked)     echo "🔴" ;;
        pending)     echo "⏳" ;;
        *)           echo "·" ;;
    esac
}

reqs=$(group_status reqs)
dev=$(group_status dev)
test=$(group_status test)
review=$(group_status review)

# current_step suffix for the active group only (≤12 char to keep line short)
suffix=""
if [[ "$active" =~ ^(reqs|dev|test|review)$ ]]; then
    step=$(awk -v g="$active" '
        $0 == "## " g { found=1; next }
        found && /^## / { exit }
        found && /^current_step:/ { sub(/^current_step: */, ""); print; exit }
    ' "$STATE")
    if [[ -n "$step" && "$step" != "-" ]]; then
        suffix="($(echo "$step" | cut -c1-12))"
    fi
fi

if [[ -z "$slug" ]]; then
    echo "KDev | idle"
else
    case "$active" in
        reqs)   reqs="${reqs}${suffix}" ;;
        dev)    dev="${dev}${suffix}"   ;;
        test)   test="${test}${suffix}" ;;
        review) review="${review}${suffix}" ;;
    esac
    echo "KDev | reqs:${reqs} dev:${dev} test:${test} review:${review} | ${slug}"
fi
