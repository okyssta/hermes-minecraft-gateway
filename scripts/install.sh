#!/usr/bin/env bash
set -e

# Hermes Minecraft Gateway — one-shot install script
# Usage: curl -fsSL https://raw.githubusercontent.com/okyssta/hermes-minecraft-gateway/main/scripts/install.sh | bash

HERE="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/minecraft"

echo "==> Installing Hermes Minecraft Gateway..."

# Create plugin directory
mkdir -p "$PLUGIN_DIR"

# Copy files
cp -r "$HERE"/* "$PLUGIN_DIR/" 2>/dev/null || rsync -a "$HERE/" "$PLUGIN_DIR/"

# Install Node dependencies
echo "==> Installing Node.js dependencies..."
cd "$PLUGIN_DIR/bridge"
npm install --production --no-audit --no-fund

echo ""
echo "==> Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Set env vars:"
echo "     export MINECRAFT_ENABLED=true"
echo "     export MINECRAFT_SERVER=your.server.ip"
echo "     export MINECRAFT_PORT=25565"
echo "     export MINECRAFT_USERNAME=HermesBot"
echo "     export MINECRAFT_AUTH=offline"
echo "     export MINECRAFT_ALLOW_ALL_USERS=true"
echo "     export MINECRAFT_PREFIX=\$"
echo ""
echo "  2. Restart Hermes gateway:"
echo "     hermes gateway restart"
echo ""
echo "  3. Join your Minecraft server and chat with Hermes!"
echo ""
