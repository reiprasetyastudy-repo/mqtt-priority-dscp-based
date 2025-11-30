#!/usr/bin/env python3
"""
Configuration loader for Scenario 04

Loads and validates configuration from YAML file.
"""

import os
import yaml
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class NetworkConfig:
    """Network configuration"""
    bandwidth_mbps: int
    openflow_version: str
    controller_ip: str
    controller_port: int
    topology_type: str
    core_switches: List[int]
    agg_switches: List[int]
    edge_switches: List[int]
    broker_ip: str
    subnet_mask: str
    floor1_subnet: str
    floor2_subnet: str


@dataclass
class MQTTConfig:
    """MQTT configuration"""
    port: int
    topic: str
    message_rate: int
    message_size: int
    qos: int
    total_publishers: int
    anomaly_publishers: int
    normal_publishers: int


@dataclass
class QueueConfig:
    """Single queue configuration"""
    id: int
    min_bandwidth_percent: int
    max_bandwidth_percent: int
    priority: int
    description: str


@dataclass
class QoSConfig:
    """QoS configuration"""
    queue_high: QueueConfig
    queue_low: QueueConfig
    arp_priority: int
    icmp_priority: int
    table_miss_priority: int
    classification_method: str
    classification_rule: str


@dataclass
class TimingConfig:
    """Timing configuration"""
    network_stabilization: int
    broker_startup: int
    subscriber_startup: int
    publisher_stagger: float
    flow_idle_timeout: int
    flow_hard_timeout: int


@dataclass
class PathsConfig:
    """Paths configuration"""
    project_root: str
    mqtt_dir: str
    log_dir: str
    results_dir: str
    config_dir: str

    def __post_init__(self):
        """Resolve relative paths"""
        self.mqtt_dir = os.path.join(self.project_root, self.mqtt_dir)
        self.log_dir = os.path.join(self.project_root, self.log_dir)
        self.results_dir = os.path.join(self.project_root, self.results_dir)
        self.config_dir = os.path.join(self.project_root, self.config_dir)


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    format: str
    file_prefix: str


@dataclass
class ValidationConfig:
    """Validation configuration"""
    min_utilization: int
    max_utilization: int


@dataclass
class ScenarioConfig:
    """Main scenario configuration"""
    name: str
    description: str
    version: str
    network: NetworkConfig
    mqtt: MQTTConfig
    qos: QoSConfig
    timing: TimingConfig
    paths: PathsConfig
    logging: LoggingConfig
    validation: ValidationConfig

    def calculate_utilization(self) -> float:
        """
        Calculate expected network utilization.

        Formula: (publishers × msg_rate × msg_size × 8) / (bandwidth × 1_000_000)
        """
        total_traffic = (
            self.mqtt.total_publishers *
            self.mqtt.message_rate *
            self.mqtt.message_size *
            8  # bits per byte
        )
        capacity = self.network.bandwidth_mbps * 1_000_000
        return total_traffic / capacity

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.

        Returns:
            List of warning/error messages (empty if valid)
        """
        issues = []

        # Validate utilization
        utilization = self.calculate_utilization()
        min_util = self.validation.min_utilization / 100
        max_util = self.validation.max_utilization / 100

        if utilization < min_util:
            issues.append(
                f"⚠️  Network utilization ({utilization:.0%}) is below minimum "
                f"({min_util:.0%}). Priority mechanism may not be visible! "
                f"Increase message_rate to at least "
                f"{int(min_util * self.network.bandwidth_mbps * 1_000_000 / (self.mqtt.total_publishers * self.mqtt.message_size * 8))}"
            )
        elif utilization > max_util:
            issues.append(
                f"❌ Network utilization ({utilization:.0%}) exceeds maximum "
                f"({max_util:.0%}). Risk of packet loss! "
                f"Decrease message_rate or increase bandwidth."
            )

        # Validate bandwidth
        if self.network.bandwidth_mbps < 1:
            issues.append("❌ Bandwidth must be at least 1 Mbps")

        # Validate message rate
        if self.mqtt.message_rate < 1:
            issues.append("❌ Message rate must be at least 1 msg/s")

        # Validate queue configuration
        if self.qos.queue_high.id == self.qos.queue_low.id:
            issues.append("❌ Queue IDs must be different")

        if self.qos.queue_high.min_bandwidth_percent < self.qos.queue_low.min_bandwidth_percent:
            issues.append("⚠️  High priority queue has lower bandwidth than low priority queue")

        # Validate switch configuration
        if not self.network.core_switches:
            issues.append("❌ At least one core switch required")

        if not self.network.edge_switches:
            issues.append("❌ At least one edge switch required")

        # Check for duplicate switch IDs
        all_switches = (
            self.network.core_switches +
            self.network.agg_switches +
            self.network.edge_switches
        )
        if len(all_switches) != len(set(all_switches)):
            issues.append("❌ Duplicate switch IDs detected")

        return issues


def load_config(config_path: str) -> ScenarioConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        ScenarioConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If configuration is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    # Parse scenario metadata
    scenario_meta = data['scenario']

    # Parse network config
    network_data = data['network']
    network = NetworkConfig(
        bandwidth_mbps=network_data['bandwidth_mbps'],
        openflow_version=network_data['openflow_version'],
        controller_ip=network_data['controller']['ip'],
        controller_port=network_data['controller']['port'],
        topology_type=network_data['topology']['type'],
        core_switches=network_data['topology']['core_switches'],
        agg_switches=network_data['topology']['agg_switches'],
        edge_switches=network_data['topology']['edge_switches'],
        broker_ip=network_data['addressing']['broker_ip'],
        subnet_mask=network_data['addressing']['subnet_mask'],
        floor1_subnet=network_data['addressing']['floor1_subnet'],
        floor2_subnet=network_data['addressing']['floor2_subnet']
    )

    # Parse MQTT config
    mqtt_data = data['mqtt']
    mqtt = MQTTConfig(
        port=mqtt_data['port'],
        topic=mqtt_data['topic'],
        message_rate=mqtt_data['message_rate'],
        message_size=mqtt_data['message_size'],
        qos=mqtt_data['qos'],
        total_publishers=mqtt_data['publishers']['total'],
        anomaly_publishers=mqtt_data['publishers']['anomaly'],
        normal_publishers=mqtt_data['publishers']['normal']
    )

    # Parse QoS config
    qos_data = data['qos']
    queue_high = QueueConfig(
        id=qos_data['queue_high']['id'],
        min_bandwidth_percent=qos_data['queue_high']['min_bandwidth_percent'],
        max_bandwidth_percent=qos_data['queue_high']['max_bandwidth_percent'],
        priority=qos_data['queue_high']['priority'],
        description=qos_data['queue_high']['description']
    )
    queue_low = QueueConfig(
        id=qos_data['queue_low']['id'],
        min_bandwidth_percent=qos_data['queue_low']['min_bandwidth_percent'],
        max_bandwidth_percent=qos_data['queue_low']['max_bandwidth_percent'],
        priority=qos_data['queue_low']['priority'],
        description=qos_data['queue_low']['description']
    )
    qos = QoSConfig(
        queue_high=queue_high,
        queue_low=queue_low,
        arp_priority=qos_data['base_flows']['arp_priority'],
        icmp_priority=qos_data['base_flows']['icmp_priority'],
        table_miss_priority=qos_data['base_flows']['table_miss_priority'],
        classification_method=qos_data['classification']['method'],
        classification_rule=qos_data['classification']['rule']
    )

    # Parse timing config
    timing_data = data['timing']
    timing = TimingConfig(
        network_stabilization=timing_data['network_stabilization'],
        broker_startup=timing_data['broker_startup'],
        subscriber_startup=timing_data['subscriber_startup'],
        publisher_stagger=timing_data['publisher_stagger'],
        flow_idle_timeout=timing_data['flow_idle_timeout'],
        flow_hard_timeout=timing_data['flow_hard_timeout']
    )

    # Parse paths config
    paths_data = data['paths']
    paths = PathsConfig(
        project_root=paths_data['project_root'],
        mqtt_dir=paths_data['mqtt_dir'],
        log_dir=paths_data['log_dir'],
        results_dir=paths_data['results_dir'],
        config_dir=paths_data['config_dir']
    )

    # Parse logging config
    logging_data = data['logging']
    logging_config = LoggingConfig(
        level=logging_data['level'],
        format=logging_data['format'],
        file_prefix=logging_data['file_prefix']
    )

    # Parse validation config
    validation_data = data['validation']
    validation = ValidationConfig(
        min_utilization=validation_data['min_utilization'],
        max_utilization=validation_data['max_utilization']
    )

    # Create main config
    config = ScenarioConfig(
        name=scenario_meta['name'],
        description=scenario_meta['description'],
        version=scenario_meta['version'],
        network=network,
        mqtt=mqtt,
        qos=qos,
        timing=timing,
        paths=paths,
        logging=logging_config,
        validation=validation
    )

    # Validate configuration
    issues = config.validate()
    if issues:
        error_issues = [i for i in issues if i.startswith('❌')]
        warning_issues = [i for i in issues if i.startswith('⚠️')]

        if warning_issues:
            print("\n" + "="*70)
            print("CONFIGURATION WARNINGS:")
            print("="*70)
            for warning in warning_issues:
                print(warning)

        if error_issues:
            print("\n" + "="*70)
            print("CONFIGURATION ERRORS:")
            print("="*70)
            for error in error_issues:
                print(error)
            print("="*70 + "\n")
            raise ValueError("Invalid configuration. Please fix errors above.")

    # Print configuration summary
    print("\n" + "="*70)
    print(f"CONFIGURATION LOADED: {config.name}")
    print("="*70)
    print(f"Description: {config.description}")
    print(f"Version: {config.version}")
    print(f"Network Utilization: {config.calculate_utilization():.1%}")
    print(f"Total Switches: {len(config.network.core_switches) + len(config.network.agg_switches) + len(config.network.edge_switches)}")
    print(f"Total Publishers: {config.mqtt.total_publishers}")
    print("="*70 + "\n")

    return config
