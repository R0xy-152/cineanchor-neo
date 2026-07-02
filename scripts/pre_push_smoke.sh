#!/bin/bash
# Pre-push smoke check — lightweight gate before pushing to remote.
# Installed as .git/hooks/pre-push (or run manually).
# Rules from 00-workflow-rules.md §5: no generated media committed,
# MP4 output must be valid, tests must pass.

set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
FFPROBE="$REPO_ROOT/.tools/ffmpeg/ffmpeg-8.1.1-essentials_build/bin/ffprobe.exe"

echo "=== Pre-push smoke check ==="

# 1. Reject generated media in staging (PNG/MP4/EXR in spikes/)
staged_media=$(git diff --cached --name-only | grep -iE '\.(png|mp4|exr)$' || true)
if [ -n "$staged_media" ]; then
  echo "❌ Generated media files staged for commit:"
  echo "$staged_media"
  echo "   Remove them with: git reset HEAD <file>"
  exit 1
fi
echo "✅ No generated media staged"

# 2. Run unit tests if tests/ exists (skip on docs-only branches like Andy)
echo "--- Unit tests ---"
if [ -d "$REPO_ROOT/tests/backend" ]; then
  set +e
  "$PYTHON" -m unittest discover -s "$REPO_ROOT/tests/backend" -q 2>&1
  exit_code=$?
  set -e
  if [ "$exit_code" -eq 5 ]; then
    echo "⏭ No test files found (exit 5) — treating as skip"
  elif [ "$exit_code" -ne 0 ]; then
    echo "❌ Unit tests failed (exit $exit_code)"
    exit 1
  fi
  echo "✅ Unit tests passed"
else
  echo "⏭ tests/ not found — skipping (docs-only branch?)"
fi

# 3. If any MP4 in the diff, validate with ffprobe
staged_mp4=$(git diff --cached --name-only | grep -iE '\.mp4$' || true)
if [ -z "$staged_mp4" ]; then
  echo "✅ No MP4 in staging (skip ffprobe)"
else
  echo "--- MP4 validation ---"
  for mp4 in $staged_mp4; do
    if [ -f "$REPO_ROOT/$mp4" ]; then
      frames=$("$FFPROBE" -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$REPO_ROOT/$mp4" 2>/dev/null || echo "0")
      if [ "$frames" -gt 0 ] 2>/dev/null; then
        echo "✅ $mp4: $frames frames"
      else
        echo "❌ $mp4: ffprobe failed or 0 frames"
        exit 1
      fi
    fi
  done
fi

echo "=== Smoke check PASSED ==="
