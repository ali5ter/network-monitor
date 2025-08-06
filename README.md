# Network Speed Monitor for macOS

Monitor your internet connection quality over time using Speedtest CLI, InfluxDB, Grafana, and `launchd` on macOS.

I wrote this when I was not seeing the bandwidth that my cable provider said they were providing me and wanted a way to provide some evidence of what I was seeing on my end.

## Features

- Periodic internet speed tests (download, upload, ping)
- Historical data stored in InfluxDB
- Interactive Grafana dashboard
- Headless and persistent with Docker Compose
- Uses `launchd` for periodic execution on macOS.

## Requirements

- Apple macOS (tested on Sequoia)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Homebrew](https://brew.sh)
- [Speedtest CLI by Ookla](https://www.speedtest.net/apps/cli)
- Python 3.9+

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/yourusername/network-speed-monitor.git
cd network-monitor
```

### 2. Start the InfluxDB + Grafana stack

```bash
cp .env.template .env
## modify the .env file
./start_stack.sh
```

This will provision InfluxDB and Grafana and install the launchd agent (`edu.lewis-bowen.networkspeed.plist`).

## Runing the speed script manually

Using the Python virtual environment set up by the [start_stack.sh](start_stack.sh) script, you run...

```bash
./.venv/bin/python network_speed_logger.py
```

## Managing the launchd agent

The [network_speed.plist.template](launchd/network_speed.plist.template) is used by the [start_stack.sh](start_stack.sh) script to configure the launchd agent (`edu.lewis-bowen.networkspeed.plist`) so that the [network_speed_logger.py](network_speed_logger.py) will run periodically.

### Changing the interval for when speed is tested

The `StartInterval` section in the template defines the interval in seconds; `3600` (every hour). You can change this, e.g. `300` (every 5m)

### Cycling the launchd agent

Cycle the agent, for example when you regenerated the plist, using...

```bash
launchctl unload ~/Library/LaunchAgents/edu.lewis-bowen.networkspeed.plist
launchctl load ~/Library/LaunchAgents/edu.lewis-bowen.networkspeed.plist
```

To check the agent status:

```bash
launchctl list | grep networkspeed
```

## Dashboard

1. Open `http://${SERVER_IP}:3000`
2. Login with the Grafana credentials in the `.env` file.
3. The dashboard should be preloaded and available as **Internet Speed Monitor**

## Logs and Debugging

`launchd` logs are written to `~/Library/Logs/networkspeed.log` and `~/Library/Logs/networkspeed.err`

Logs are written inline if you run [network_speed_logger.py](network_speed_logger.py) manually.

Change the `LOGLEVEL` variable in the `.env` file from `INFO` to `DEBUG` to dump debug messages.
