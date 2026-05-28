#!/bin/bash
# WeBan Module Setup Script
# This script downloads the WeBan module for the weban_plugin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBAN_TARGET_DIR="$PROJECT_ROOT/plugins/weban_plugin/modules/WeBan"
WEBAN_REPOSITORY="${WEBAN_REPOSITORY:-https://github.com/hangone/WeBan.git}"
WEBAN_REF="${WEBAN_REF:-ad149ce507be66d909d908bad7905a1029636a46}"

echo "🔧 Setting up WeBan module for weban_plugin..."
echo "📍 Target directory: $WEBAN_TARGET_DIR"
echo "🔖 WeBan ref: $WEBAN_REF"

# Create modules directory if it doesn't exist
mkdir -p "$(dirname "$WEBAN_TARGET_DIR")"

if [ -d "$WEBAN_TARGET_DIR/.git" ]; then
  echo "✅ WeBan module already exists; updating remote and ref"
  git -C "$WEBAN_TARGET_DIR" remote set-url origin "$WEBAN_REPOSITORY"
else
  echo "📦 Cloning WeBan module..."
  rm -rf "$WEBAN_TARGET_DIR"
  git clone --filter=blob:none --no-checkout "$WEBAN_REPOSITORY" "$WEBAN_TARGET_DIR"
fi

echo "⬇️ Fetching WeBan ref..."
if git -C "$WEBAN_TARGET_DIR" fetch --depth 1 origin "$WEBAN_REF"; then
  git -C "$WEBAN_TARGET_DIR" checkout --force FETCH_HEAD
else
  echo "Direct fetch failed; fetching branch and tag heads before checkout."
  git -C "$WEBAN_TARGET_DIR" fetch --depth 1 origin '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'
  git -C "$WEBAN_TARGET_DIR" checkout --force "$WEBAN_REF"
fi
git -C "$WEBAN_TARGET_DIR" clean -fdx

if [ ! -f "$WEBAN_TARGET_DIR/main.py" ] || [ ! -f "$WEBAN_TARGET_DIR/api.py" ]; then
  echo "❌ WeBan module is missing expected files"
  exit 1
fi

echo "✅ WeBan module successfully installed!"
echo "📍 Location: $WEBAN_TARGET_DIR"
echo "🔖 Commit: $(git -C "$WEBAN_TARGET_DIR" rev-parse HEAD)"
echo ""
echo "📋 Next steps:"
echo "   1. Install plugin dependencies: pip install -r plugins/weban_plugin/requirements.txt"
echo "   2. Run the application: python main.py"
echo "   3. Enable the weban_plugin in Plugin Center"
