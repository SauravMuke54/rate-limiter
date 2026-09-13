#!/usr/bin/env bash
# Runs the k6 load test against the rate limiter and opens the HTML report.
#
# Usage:
#   ./run.sh
#   BASE_URL=http://localhost:8000 TARGET_HOST=api.myapp.com TARGET_PATH=/login ./run.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TARGET_HOST="${TARGET_HOST:-localhost}"
TARGET_PATH="${TARGET_PATH:-/health}"

if ! command -v k6 &> /dev/null; then
  echo "k6 is not installed. Install it first:"
  echo "  macOS:   brew install k6"
  echo "  Linux:   see https://k6.io/docs/get-started/installation/"
  exit 1
fi

echo "Running load test against ${BASE_URL} (Host: ${TARGET_HOST}, Path: ${TARGET_PATH})"
echo "---"

k6 run \
  -e BASE_URL="${BASE_URL}" \
  -e TARGET_HOST="${TARGET_HOST}" \
  -e TARGET_PATH="${TARGET_PATH}" \
  loadtest.js

echo "---"
echo "Report written to report.html and report.json"

if command -v open &> /dev/null; then
  open report.html
elif command -v xdg-open &> /dev/null; then
  xdg-open report.html
else
  echo "Open report.html manually in a browser to view the results."
fi
