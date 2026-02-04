#!/usr/bin/env bash
set -euo pipefail

NODE_VERSION="${NODE_VERSION:-20.19.0}"
PLATFORM="linux"

ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64|amd64) ARCH="x64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: ${ARCH}"
    exit 1
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/.node"
TARBALL="node-v${NODE_VERSION}-${PLATFORM}-${ARCH}.tar.xz"
URL="https://nodejs.org/dist/v${NODE_VERSION}/${TARBALL}"

mkdir -p "${INSTALL_DIR}"
echo "Downloading ${URL}..."
curl -fsSL "${URL}" -o "${INSTALL_DIR}/${TARBALL}"

echo "Extracting..."
tar -xJf "${INSTALL_DIR}/${TARBALL}" -C "${INSTALL_DIR}"

mv "${INSTALL_DIR}/node-v${NODE_VERSION}-${PLATFORM}-${ARCH}"/* "${INSTALL_DIR}/"
rm -rf "${INSTALL_DIR}/node-v${NODE_VERSION}-${PLATFORM}-${ARCH}" "${INSTALL_DIR}/${TARBALL}"

echo "Node installed to ${INSTALL_DIR}"
echo "Run: export PATH=\"${INSTALL_DIR}/bin:\$PATH\""
