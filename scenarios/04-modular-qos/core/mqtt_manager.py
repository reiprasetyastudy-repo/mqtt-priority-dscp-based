#!/usr/bin/env python3
"""
MQTT Manager for Scenario 04

Manages MQTT broker, publishers, and subscriber lifecycle.
"""

import time
from typing import List, Dict, Any
from ..config.config_loader import ScenarioConfig


class MQTTManager:
    """
    Manages MQTT components lifecycle.

    Separates MQTT management from topology management.
    """

    def __init__(self, config: ScenarioConfig, logger=None):
        """
        Initialize MQTT manager.

        Args:
            config: Scenario configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger
        self.broker_host = None
        self.publisher_hosts = []

    def _log(self, msg: str, level: str = "info"):
        """Helper to log messages"""
        if self.logger:
            if level == "mqtt":
                self.logger.mqtt_event(msg)
            else:
                getattr(self.logger, level)(msg)
        else:
            print(f"[MQTT] {msg}")

    def start_broker(self, broker_host) -> bool:
        """
        Start MQTT broker on specified host.

        Args:
            broker_host: Mininet host object for broker

        Returns:
            True if started successfully
        """
        self.broker_host = broker_host
        self._log(f"Starting MQTT Broker on {self.config.network.broker_ip}")

        mosquitto_config = f"{self.config.paths.config_dir}/mosquitto.conf"

        cmd = f'mosquitto -c {mosquitto_config} -d'
        result = broker_host.cmd(cmd)

        time.sleep(self.config.timing.broker_startup)

        self._log("MQTT Broker started", "mqtt")
        return True

    def start_subscriber(self, subscriber_host) -> bool:
        """
        Start MQTT subscriber on specified host.

        Args:
            subscriber_host: Mininet host object for subscriber

        Returns:
            True if started successfully
        """
        self._log(f"Starting Enhanced Subscriber on {self.config.network.broker_ip}")

        # Build environment variables for subscriber
        env_vars = (
            f'ENABLE_BANDWIDTH_LIMIT=True '
            f'LINK_BANDWIDTH_MBPS={self.config.network.bandwidth_mbps} '
            f'ENABLE_QOS_QUEUES=True '
            f'SCENARIO_NAME="{self.config.name}" '
            f'TOPOLOGY_TYPE="{self.config.network.topology_type}" '
            f'NUM_SWITCHES={len(self.config.network.core_switches) + len(self.config.network.agg_switches) + len(self.config.network.edge_switches)} '
            f'NUM_PUBLISHERS={self.config.mqtt.total_publishers} '
        )

        subscriber_script = f"{self.config.paths.mqtt_dir}/subscriber_enhanced.py"
        log_file = f"{self.config.paths.log_dir}/subscriber.log"

        cmd = f'{env_vars}python3 {subscriber_script} > {log_file} 2>&1 &'
        subscriber_host.cmd(cmd)

        time.sleep(self.config.timing.subscriber_startup)

        self._log("Subscriber started", "mqtt")
        return True

    def start_publishers(self, publishers: List[Dict[str, Any]]) -> int:
        """
        Start all MQTT publishers.

        Args:
            publishers: List of publisher dictionaries with keys:
                       - host: Mininet host object
                       - type: "anomaly" or "normal"
                       - floor: Floor number
                       - room: Room number

        Returns:
            Number of publishers started
        """
        self._log(f"Starting {len(publishers)} MQTT Publishers")

        started = 0

        for idx, pub in enumerate(publishers):
            host = pub['host']
            pub_type = pub['type']
            floor = pub['floor']
            room = pub['room']

            device_name = f"sensor_f{floor}r{room}_{pub_type}"

            # Choose script based on type
            if pub_type == 'anomaly':
                script = f'{self.config.paths.mqtt_dir}/publisher_anomaly.py'
            else:
                script = f'{self.config.paths.mqtt_dir}/publisher_normal.py'

            # Build command
            log_file = f"{self.config.paths.log_dir}/publisher_{device_name}.log"
            cmd = (
                f'DEVICE={device_name} '
                f'BROKER_IP={self.config.network.broker_ip} '
                f'MSG_RATE={self.config.mqtt.message_rate} '
                f'python3 {script} > {log_file} 2>&1 &'
            )

            host.cmd(cmd)
            started += 1

            # Stagger publisher starts
            if idx % 2 == 0:
                time.sleep(self.config.timing.publisher_stagger)

        self._log(f"All {started} publishers started", "mqtt")
        return started

    def stop_publishers(self, publishers: List[Dict[str, Any]]) -> bool:
        """
        Stop all publishers.

        Args:
            publishers: List of publisher dictionaries

        Returns:
            True if stopped successfully
        """
        self._log("Stopping publishers")

        for pub in publishers:
            host = pub['host']
            host.cmd('pkill -f publisher')

        time.sleep(1)
        return True

    def stop_subscriber(self, subscriber_host) -> bool:
        """
        Stop subscriber.

        Args:
            subscriber_host: Mininet host object

        Returns:
            True if stopped successfully
        """
        self._log("Stopping subscriber")
        subscriber_host.cmd('pkill -f subscriber')
        time.sleep(1)
        return True

    def stop_broker(self) -> bool:
        """
        Stop MQTT broker.

        Returns:
            True if stopped successfully
        """
        if not self.broker_host:
            return False

        self._log("Stopping MQTT broker")
        self.broker_host.cmd('pkill -f mosquitto')
        time.sleep(1)
        return True

    def stop_all(self, publishers: List[Dict[str, Any]], subscriber_host) -> bool:
        """
        Stop all MQTT components.

        Args:
            publishers: List of publisher dictionaries
            subscriber_host: Mininet host object for subscriber

        Returns:
            True if all stopped successfully
        """
        self._log("Stopping all MQTT components")

        self.stop_publishers(publishers)
        self.stop_subscriber(subscriber_host)
        self.stop_broker()

        return True
