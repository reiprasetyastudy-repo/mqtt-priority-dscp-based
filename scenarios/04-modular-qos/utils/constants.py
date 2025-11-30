#!/usr/bin/env python3
"""
Constants for Scenario 04 - Modular QoS

All magic numbers are defined here with clear names.
"""

class QoSPriority:
    """OpenFlow flow priority levels"""
    ARP = 100           # ARP packets (highest)
    ICMP = 90           # ICMP/ping
    MQTT_ANOMALY = 20   # MQTT anomaly traffic
    MQTT_NORMAL = 15    # MQTT normal traffic
    TABLE_MISS = 0      # Table-miss (send to controller)


class QueueID:
    """OVS Queue identifiers"""
    HIGH_PRIORITY = 1   # For anomaly/critical data
    LOW_PRIORITY = 2    # For normal data


class NetworkTiming:
    """Network timing constants (in seconds)"""
    NETWORK_STABILIZATION = 5   # Wait for network to stabilize
    BROKER_STARTUP = 2          # Wait for MQTT broker to start
    SUBSCRIBER_STARTUP = 2      # Wait for subscriber to start
    PUBLISHER_STAGGER = 0.5     # Delay between starting publishers
    FLOW_IDLE_TIMEOUT = 30      # Flow idle timeout
    FLOW_HARD_TIMEOUT = 0       # No hard timeout


class MQTTDefaults:
    """MQTT default values"""
    PORT = 1883
    TOPIC = "iot/data"
    QOS_LEVEL = 1
    MESSAGE_SIZE = 250  # bytes


class EtherType:
    """Ethernet type values"""
    IPv4 = 0x0800
    ARP = 0x0806
    LLDP = 0x88CC


class IPProtocol:
    """IP protocol numbers"""
    ICMP = 1
    TCP = 6
    UDP = 17


class OpenFlow:
    """OpenFlow constants"""
    VERSION = "OpenFlow13"
    CONTROLLER_PORT = 6633
    NO_BUFFER = 0xffffffff
    OFPCML_NO_BUFFER = 0xffff


class QueueType:
    """OVS Queue types"""
    LINUX_HTB = "linux-htb"  # Hierarchical Token Bucket


class ValidationLimits:
    """Validation thresholds"""
    MIN_UTILIZATION = 0.70  # 70% minimum for congestion
    MAX_UTILIZATION = 0.95  # 95% maximum to avoid overload
    MIN_BANDWIDTH_MBPS = 1
    MAX_BANDWIDTH_MBPS = 1000
    MIN_MESSAGE_RATE = 1
    MAX_MESSAGE_RATE = 1000


class ClassificationMethod:
    """Traffic classification methods"""
    IP_BASED = "ip_based"
    MAC_BASED = "mac_based"
    PORT_BASED = "port_based"
    DSCP_BASED = "dscp_based"


class TopologyType:
    """Network topology types"""
    HIERARCHICAL = "hierarchical"
    FLAT = "flat"
    MESH = "mesh"
