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

# Start Node first so it binds to 3000 before Python (Replit maps first port to 80)
npm run dev &
NODE_PID=$!

# Wait for Node to listen on 3000 (tsx needs time to compile)
echo "Waiting for Node server on port 3000..."
if command -v nc &>/dev/null; then
  for i in {1..30}; do
    if nc -z 127.0.0.1 3000 2>/dev/null; then echo "Node ready."; break; fi
    sleep 1
  done
else
  sleep 15
fi

# Start Python CAIP backend
python -m uvicorn server.caip_backend:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Keep script running; forward Ctrl+C to both
trap "kill $NODE_PID $UVICORN_PID 2>/dev/null; exit 0" INT TERM
wait
