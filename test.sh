#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.dotnet:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/3] Building C# project (PrimevalWorld.csproj) ==="
dotnet build PrimevalWorld.csproj --nologo

echo ""
echo "=== [2/3] Running Godot 4.7.2 Headless Smoke Test (6s) ==="
HEADLESS_OUT="$(godot4 --headless --path . --quit-after 6 2>&1)"
echo "$HEADLESS_OUT"

if echo "$HEADLESS_OUT" | grep -qiE "SCRIPT ERROR|Shader compilation failed|Parse Error"; then
    echo "FAIL: Detected Godot script or shader error during headless smoke test."
    exit 1
fi

echo ""
echo "=== [3/3] Checking Disk Space ==="
df -h "$SCRIPT_DIR"

echo ""
echo "PASS: Build and headless smoke test succeeded."
