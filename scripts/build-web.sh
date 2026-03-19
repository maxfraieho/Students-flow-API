#!/bin/bash
set -euo pipefail

corepack pnpm --filter @workspace/mockup-sandbox run build
rm -rf dist
mkdir -p dist
cp -R artifacts/mockup-sandbox/dist/. dist/
