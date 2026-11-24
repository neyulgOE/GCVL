#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.dotnet:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Godot user log directory exists; also pass explicit writable --log-file in /tmp
# so headless runs never emit "Failed to open user://logs/godot.log" even in restricted environments.
GODOT_USER_LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/godot/app_userdata/Primeval Reach/logs"
mkdir -p "$GODOT_USER_LOG_DIR" 2>/dev/null || true
HEADLESS_LOG_FILE="/tmp/primeval_reach_headless_$$.log"

echo "=== [1/3] Building C# project (PrimevalWorld.csproj) ==="
dotnet build PrimevalWorld.csproj --nologo

echo ""
echo "=== [2/3] Running Godot 4.7.2 Headless Smoke Test (6s) ==="
HEADLESS_OUT="$(godot4 --headless --log-file "$HEADLESS_LOG_FILE" --path . --quit-after 6 2>&1)"
rm -f "$HEADLESS_LOG_FILE"
echo "$HEADLESS_OUT"

if echo "$HEADLESS_OUT" | grep -qiE "SCRIPT ERROR|Shader compilation failed|Parse Error|Failed to open user://logs|^ERROR:"; then
    echo "FAIL: Detected Godot error during headless smoke test."
    exit 1
fi

echo ""
echo "=== [3/3] Checking Disk Space ==="
df -h "$SCRIPT_DIR"

echo ""
echo "PASS: Build and headless smoke test succeeded with zero errors."
