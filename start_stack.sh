#!/usr/bin/env bash
# @file: start_stack.sh
# @brief: Initialize and start the InfluxDB + Grafana stack via Docker Compose
# @brief: Used Launchd to start the network speed tests on macOS
# @author: Alister Lewis-Bowen <alister@lewis-bowen.org>
# @note: This is written to work on macOS

[[ $DEBUG ]] && set -x
set -euo pipefail

# Load environment variables from .env file

set -a
# shellcheck disable=SC1091
source .env
set +a

# Dependency checks...

echo "🧠 Checking OS..."
if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ This setup script is for macOS only."
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "❌ Docker is not installed. Please install Docker Desktop for macOS: https://www.docker.com/products/docker-desktop"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  open -a "Docker"
  echo "Waiting for Docker to start..."
  while ! docker info >/dev/null 2>&1; do
    sleep 1
  done
fi
echo "🐳 Docker Desktop running."

if ! command -v brew &>/dev/null; then
  echo "❌ Homebrew is not installed. Please install it first: https://brew.sh/"
  exit 1
fi
brew tap teamookla/speedtest
brew install speedtest

python3 -m venv .venv
# shellcheck disable=SC1091
source ".venv/bin/activate"

pip install --upgrade pip
pip install requests rich python-dotenv influxdb-client

# Prepare any stack configuration files...

echo "📦 Generating Grafana datasource config from template..."
envsubst < ./grafana/provisioning/datasources/influxdb.yaml.template > ./grafana/provisioning/datasources/influxdb.yaml

# Automate the network monitor using Launchd...

echo "🛠️ Setting up Launchd for network speed tests..."

mkdir -p "$HOME/Library/LaunchAgents"
export PLIST_PATH="$HOME/Library/LaunchAgents/edu.lewis-bowen.networkspeed.plist"
export PYTHON_SCRIPT_PATH="$PWD/network_speed_logger.py"
# shellcheck disable=SC2155
export PYTHON_BIN="$(which python3)"

envsubst < ./launchd/network_speed.plist.template > "$PLIST_PATH"

# Stand up the stack...

echo "🚀 Starting InfluxDB and Grafana using Docker Compose..."
docker compose up -d
sleep 10  # Wait for services to start
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo
echo "✅ Setup complete!"
echo "🌐 InfluxDB: http://${SERVER_IP}:${INFLUXDB_PORT}"
echo "    - Org: ${INFLUXDB_ORG}"
echo "    - Bucket: ${INFLUXDB_BUCKET}"
echo "    - Token: ${INFLUXDB_ADMIN_TOKEN}"
echo
echo "🌐 Grafana: http://${SERVER_IP}:${GRAFANA_PORT}"
echo "    - Username: ${GRAFANA_ADMIN_USER}"
echo "    - Password: ${GRAFANA_ADMIN_PASSWORD}"
echo
echo "📄 Launchd job loaded: $PLIST_PATH"