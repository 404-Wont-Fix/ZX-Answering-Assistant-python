#!/bin/bash
# WeBan Module Setup Script
# This script downloads the WeBan module for the weban_plugin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBAN_TARGET_DIR="$PROJECT_ROOT/plugins/weban_plugin/modules/WeBan"

echo "🔧 Setting up WeBan module for weban_plugin..."
echo "📍 Target directory: $WEBAN_TARGET_DIR"

# Create modules directory if it doesn't exist
mkdir -p "$(dirname "$WEBAN_TARGET_DIR")"

# Check if WeBan already exists
if [ -d "$WEBAN_TARGET_DIR/.git" ]; then
  echo "✅ WeBan module already exists at $WEBAN_TARGET_DIR"
  echo "   To update, run: cd $WEBAN_TARGET_DIR && git pull"
  exit 0
fi

# Clone WeBan repository
echo "📦 Cloning WeBan module..."
git clone --depth 1 https://github.com/hangone/WeBan.git "$WEBAN_TARGET_DIR"

if [ $? -eq 0 ]; then
  echo "✅ WeBan module successfully installed!"
  echo "📍 Location: $WEBAN_TARGET_DIR"
  echo ""
  echo "📋 Next steps:"
  echo "   1. Install plugin dependencies: pip install -r plugins/weban_plugin/requirements.txt"
  echo "   2. Run the application: python main.py"
  echo "   3. Enable the weban_plugin in Plugin Center"
else
  echo "❌ Failed to clone WeBan module"
  echo "   Please check your internet connection and try again"
  exit 1
fi
