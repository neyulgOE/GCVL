#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.dotnet:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GODOT_USER_LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/godot/app_userdata/Primeval Reach/logs"
mkdir -p "$GODOT_USER_LOG_DIR" 2>/dev/null || true
HEADLESS_LOG_MAIN="/tmp/primeval_reach_main_$$.log"
HEADLESS_LOG_SHOW="/tmp/primeval_reach_show_$$.log"

echo "=== [1/4] Building C# project (PrimevalWorld.csproj) ==="
dotnet build PrimevalWorld.csproj --nologo

echo ""
echo "=== [2/4] Running Main.tscn Headless Smoke Test (6s) ==="
MAIN_OUT="$(godot4 --headless --log-file "$HEADLESS_LOG_MAIN" --path . --quit-after 6 2>&1)"
rm -f "$HEADLESS_LOG_MAIN"
echo "$MAIN_OUT"

if echo "$MAIN_OUT" | grep -qiE "SCRIPT ERROR|Shader compilation failed|Parse Error|Failed to open user://logs|^ERROR:"; then
    echo "FAIL: Detected Godot error during Main.tscn headless smoke test."
    exit 1
fi

echo ""
echo "=== [3/4] Running FloraShowcase.tscn Headless Smoke Test (3s) ==="
SHOW_OUT="$(godot4 --headless --log-file "$HEADLESS_LOG_SHOW" --path . --scene res://scenes/FloraShowcase.tscn --quit-after 3 2>&1)"
rm -f "$HEADLESS_LOG_SHOW"
echo "$SHOW_OUT"

if echo "$SHOW_OUT" | grep -qiE "SCRIPT ERROR|Shader compilation failed|Parse Error|Failed to open user://logs|^ERROR:"; then
    echo "FAIL: Detected Godot error during FloraShowcase.tscn headless smoke test."
    exit 1
fi

echo ""
echo "=== [4/4] Checking Disk Space ==="
df -h "$SCRIPT_DIR"

echo ""
echo "PASS: Build, Main.tscn and FloraShowcase.tscn headless smoke tests succeeded with zero errors."
