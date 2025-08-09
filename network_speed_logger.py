#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @file: network_speed_logger.py
# @brief: Monitor network speed and log data
# @author: Alister Lewis-Bowen <alister@lewis-bowen.org>

import os
import subprocess
import json
import logging
import requests
import sys
import shutil

from datetime import datetime
from rich.logging import RichHandler
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class LessThanFilter(logging.Filter):
    """Filter out logs with level >= max_level."""
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        return record.levelno < self.max_level

def is_interactive():
    return sys.stdout.isatty()

def setup_logging(loglevel="INFO", log_file=None):
    numeric_level = getattr(logging, loglevel.upper(), logging.INFO)
    handlers = []

    if is_interactive():
        # Rich terminal logging
        handlers.append(RichHandler(rich_tracebacks=True, show_time=True))
    else:
        # Stream low-level logs to stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.addFilter(LessThanFilter(logging.WARNING))
        stdout_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))

        # Stream warnings and above to stderr
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))

        handlers.extend([stdout_handler, stderr_handler])

    if log_file and is_interactive():
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"))
        handlers.append(file_handler)

    # Reset any existing handlers to avoid duplicate logs
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(numeric_level)

    for handler in handlers:
        root_logger.addHandler(handler)

    logging.info(f"Logging initialized at level: {loglevel}, interactive={is_interactive()}")

def run_speedtest():
    speedtest_path = shutil.which("speedtest")
    try:
        result = subprocess.run(
            [speedtest_path, '--accept-license', '--accept-gdpr', '-f', 'json'],
            capture_output=True, check=True, text=True
        )

        logging.info("Speedtest completed")
        logging.debug(f"Raw speedtest JSON: {result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Speedtest failed: {e.stderr}")
        logging.debug(f"Speedtest error details: {e}")
        return None

def parse_json(json_string):
    data = json.loads(json_string)

    parsed = {
        "timestamp": data["timestamp"],
        "ping_jitter": float(data["ping"]["jitter"]),
        "ping_latency": float(data["ping"]["latency"]),
        "download_bandwidth": float(data["download"]["bandwidth"]),
        "upload_bandwidth": float(data["upload"]["bandwidth"]),
        "packet_loss": float(data.get("packetLoss", 0.0)),
        "isp": data.get("isp", "unknown"),
        "interface_internal_ip": data["interface"]["internalIp"],
        "interface_name": data["interface"]["name"],
        "interface_mac_addr": data["interface"]["macAddr"],
        "interface_is_vpn": data["interface"]["isVpn"],
        "interface_external_ip": data["interface"]["externalIp"],
    }

    logging.debug(f"Parsed speedtest data: {parsed}")
    return parsed

def write_to_influx(data):
    influx_url = os.environ.get("INFLUXDB_URL")
    influx_token = os.environ.get("INFLUXDB_ADMIN_TOKEN")
    influx_org = os.environ.get("INFLUXDB_ORG")
    influx_bucket = os.environ.get("INFLUXDB_BUCKET")

    if not all([influx_url, influx_token, influx_org, influx_bucket]):
        logging.error("Missing one or more InfluxDB environment variables.")
        return

    try:
        client = InfluxDBClient(
            url=influx_url,
            token=influx_token,
            org=influx_org
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)

        point = (
            Point("network_speed")
            .tag("host", data["interface_internal_ip"])
            .tag("isp", data["isp"])
            .field("ping_latency", data["ping_latency"])
            .field("ping_jitter", data["ping_jitter"])
            .field("download_bandwidth", data["download_bandwidth"])
            .field("upload_bandwidth", data["upload_bandwidth"])
            .field("packet_loss", data["packet_loss"])
            .time(datetime.strptime(data["timestamp"], '%Y-%m-%dT%H:%M:%SZ'), write_precision='ns')
        )

        logging.debug(f"Writing point to InfluxDB: {point.to_line_protocol()}")
        write_api.write(bucket=influx_bucket, org=influx_org, record=point)
        logging.info("Data written to InfluxDB")

    except Exception as e:
        logging.error(f"Failed to write to InfluxDB using client: {e}")

def load_env_file():
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir / ".env"
    load_dotenv(dotenv_path=env_path)

    server_ip = os.getenv("SERVER_IP", "localhost")
    influx_port = os.getenv("INFLUXDB_PORT", "8086")
    os.environ["INFLUXDB_URL"] = f"http://{server_ip}:{influx_port}"

    setup_logging(loglevel=os.getenv("LOGLEVEL", "INFO"),)
    logging.debug(f"Loaded environment variables from {env_path}")
    logging.debug(f"INFLUXDB_URL={os.environ.get('INFLUXDB_URL')}")
    logging.debug(f"INFLUXDB_ADMIN_TOKEN={'<hidden>' if os.environ.get('INFLUXDB_ADMIN_TOKEN') else None}")
    logging.debug(f"INFLUXDB_ORG={os.environ.get('INFLUXDB_ORG')}")
    logging.debug(f"INFLUXDB_BUCKET={os.environ.get('INFLUXDB_BUCKET')}")

def main():
    load_env_file()

    logging.info("Starting network speed test...")
    json_result = run_speedtest()
    if not json_result:
        return
    data = parse_json(json_result)
    write_to_influx(data)

if __name__ == "__main__":
    main()