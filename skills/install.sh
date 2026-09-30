#!/bin/bash
# =============================================================================
# Install ShortsGenerator research skills to Claude global skills
# (Opencode also reads ~/.claude/skills, so this covers both)
# Usage: ./skills/install.sh [--link|--copy] [--global DIR]
#   --link  : symlink (default)
#   --copy  : copy instead of symlink
#   --global DIR: override global skills dir (default: ~/.claude/skills)
# =============================================================================
set -e

MODE="link"
GLOBAL_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link) MODE="link"; shift;;
    --copy) MODE="copy"; shift;;
    --global) GLOBAL_DIR="$2"; shift 2;;
    --global=*) GLOBAL_DIR="${1#*=}"; shift;;
    -h|--help) echo "Usage: $0 [--link|--copy] [--global DIR]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_SRC="$SCRIPT_DIR"

echo "Installing ShortsGenerator skills -> $GLOBAL_DIR (mode: $MODE)"
mkdir -p "$GLOBAL_DIR"

# Skills to install (research families + their states)
SKILLS=(
  facebook-research
  facebook-research-setup
  facebook-research-scrape
  facebook-research-analyze
  facebook-research-report
  facebook-research-engage
  facebook-research-grow
  ig-research
  ig-research-setup
  ig-research-scrape
  ig-research-analyze
  ig-research-report
  ig-research-transcribe
  twitter-research
  twitter-research-setup
  twitter-research-scrape
  twitter-research-analyze
  twitter-research-report
  twitter-research-topics
  youtube-title
  reddit-research
  reddit-research-scrape
  reddit-research-generate
)

INSTALLED=0
SKIPPED=0

for skill in "${SKILLS[@]}"; do
  src="$SKILLS_SRC/$skill"
  dst="$GLOBAL_DIR/$skill"
  if [[ ! -d "$src" ]]; then
    echo "  skip $skill (not found in $src)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    echo "  exists: $dst -> removing"
    rm -rf "$dst"
  fi
  if [[ "$MODE" == "link" ]]; then
    ln -s "$src" "$dst"
    echo "  linked $skill -> $dst"
  else
    cp -r "$src" "$dst"
    echo "  copied $skill -> $dst"
  fi
  INSTALLED=$((INSTALLED+1))
  # install deps if scripts/package.json exists
  if [[ -f "$dst/scripts/package.json" ]]; then
    echo "    npm install --prefix $dst/scripts (if needed)..."
    if [[ ! -d "$dst/scripts/node_modules" ]]; then
      (cd "$dst/scripts" && npm install --silent) || echo "    npm install failed for $skill (you may need to run manually)"
    fi
  fi
done

# Note: facebook-research/facebook-research-template is nested inside facebook-research and
# is automatically available via the parent symlink — no separate global entry needed.

echo ""
echo "========================================"
echo "  Installed $INSTALLED skills to $GLOBAL_DIR"
if [[ $SKIPPED -gt 0 ]]; then echo "  Skipped $SKIPPED (missing)"; fi
echo "========================================"
echo ""
echo "Verify:"
echo "  ls -la $GLOBAL_DIR | grep -E 'facebook|ig-research|twitter|reddit'"
echo ""
echo "Opencode also reads ~/.claude/skills, so no extra step needed."
echo "To also symlink to opencode global (~/.config/opencode/skills), run:"
echo "  ./skills/install.sh --global ~/.config/opencode/skills"
echo ""
echo "To uninstall:"
echo "  for s in ${SKILLS[*]}; do rm -rf \"$GLOBAL_DIR/\$s\"; done"
echo "  # template is nested — no extra path to remove"
