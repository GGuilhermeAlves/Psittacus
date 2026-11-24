#!/usr/bin/env bash
# Builds dist/psittacus-<version>-chrome.zip (Chrome Web Store / Edge Add-ons).
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(node -p "require('./extension/manifest.json').version")
mkdir -p dist
OUT="dist/psittacus-${VERSION}-chrome.zip"
rm -f "$OUT"
(cd extension && zip -qr -9 "../$OUT" . -x '.*')
echo "$OUT ($(du -h "$OUT" | cut -f1))"
