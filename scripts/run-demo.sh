#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Use Node 20 if not already present (Node 16 from Nix breaks tsx)
if [[ ! -d "${ROOT_DIR}/.node/bin" ]]; then
  echo "Installing Node 20 (required for tsx)..."
  bash scripts/install-node.sh
fi
export PATH="${ROOT_DIR}/.node/bin:$PATH"
echo "Using Node $(node -v)"

# Run both frontend and CAIP backend
npm run dev:caip
