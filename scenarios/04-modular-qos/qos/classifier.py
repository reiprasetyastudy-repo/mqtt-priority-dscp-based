#!/usr/bin/env python3
"""
Traffic Classifier for Scenario 04

Classifies IoT traffic into priority levels.
"""

from typing import Tuple, Optional

# Handle both package and standalone imports
try:
    # When imported as package
    from utils.constants import QueueID, QoSPriority
except ImportError:
    # When imported with relative path
    from ..utils.constants import QueueID, QoSPriority


class TrafficClassifier:
    """
    Classifies network traffic for QoS prioritization.

    This is a pure, stateless classifier - easy to test!
    """

    @staticmethod
    def classify_by_ip_odd_even(ip_address: str) -> Tuple[int, int, str]:
        """
        Classify traffic based on IP address (odd/even).

        Odd last octet → Anomaly (high priority)
        Even last octet → Normal (low priority)

        Args:
            ip_address: Source IP address (e.g., "10.0.1.1")

        Returns:
            Tuple of (queue_id, priority, traffic_type)

        Example:
            >>> TrafficClassifier.classify_by_ip_odd_even("10.0.1.1")
            (1, 20, "ANOMALY")
            >>> TrafficClassifier.classify_by_ip_odd_even("10.0.1.2")
            (2, 15, "NORMAL")
        """
        try:
            last_octet = int(ip_address.split('.')[-1])

            if last_octet % 2 == 1:
                # Odd IP → Anomaly traffic
                return (
                    QueueID.HIGH_PRIORITY,
                    QoSPriority.MQTT_ANOMALY,
                    "ANOMALY"
                )
            else:
                # Even IP → Normal traffic
                return (
                    QueueID.LOW_PRIORITY,
                    QoSPriority.MQTT_NORMAL,
                    "NORMAL"
                )
        except (ValueError, IndexError):
            # Invalid IP format → Default to normal priority
            return (
                QueueID.LOW_PRIORITY,
                QoSPriority.MQTT_NORMAL,
                "UNKNOWN"
            )

    @staticmethod
    def classify_by_subnet(ip_address: str, anomaly_subnets: list) -> Tuple[int, int, str]:
        """
        Classify traffic based on IP subnet.

        Args:
            ip_address: Source IP address
            anomaly_subnets: List of subnet prefixes for anomaly traffic

        Returns:
            Tuple of (queue_id, priority, traffic_type)

        Example:
            >>> TrafficClassifier.classify_by_subnet("10.0.1.5", ["10.0.1."])
            (1, 20, "ANOMALY")
        """
        for subnet in anomaly_subnets:
            if ip_address.startswith(subnet):
                return (
                    QueueID.HIGH_PRIORITY,
                    QoSPriority.MQTT_ANOMALY,
                    "ANOMALY"
                )

        return (
            QueueID.LOW_PRIORITY,
            QoSPriority.MQTT_NORMAL,
            "NORMAL"
        )

    @staticmethod
    def classify_by_mac(mac_address: str, anomaly_macs: list) -> Tuple[int, int, str]:
        """
        Classify traffic based on MAC address.

        Args:
            mac_address: Source MAC address
            anomaly_macs: List of MAC addresses for anomaly traffic

        Returns:
            Tuple of (queue_id, priority, traffic_type)
        """
        if mac_address in anomaly_macs:
            return (
                QueueID.HIGH_PRIORITY,
                QoSPriority.MQTT_ANOMALY,
                "ANOMALY"
            )

        return (
            QueueID.LOW_PRIORITY,
            QoSPriority.MQTT_NORMAL,
            "NORMAL"
        )

    @staticmethod
    def is_mqtt_traffic(tcp_dst_port: Optional[int], mqtt_port: int = 1883) -> bool:
        """
        Check if traffic is MQTT.

        Args:
            tcp_dst_port: TCP destination port
            mqtt_port: MQTT broker port (default: 1883)

        Returns:
            True if MQTT traffic, False otherwise
        """
        return tcp_dst_port == mqtt_port if tcp_dst_port else False

    @classmethod
    def classify(cls, ip_address: str, method: str = "ip_based", **kwargs) -> Tuple[int, int, str]:
        """
        Classify traffic using specified method.

        Args:
            ip_address: Source IP address
            method: Classification method ("ip_based", "subnet_based", "mac_based")
            **kwargs: Additional parameters for specific methods

        Returns:
            Tuple of (queue_id, priority, traffic_type)
        """
        if method == "ip_based":
            return cls.classify_by_ip_odd_even(ip_address)
        elif method == "subnet_based":
            anomaly_subnets = kwargs.get('anomaly_subnets', [])
            return cls.classify_by_subnet(ip_address, anomaly_subnets)
        elif method == "mac_based":
            mac_address = kwargs.get('mac_address', '')
            anomaly_macs = kwargs.get('anomaly_macs', [])
            return cls.classify_by_mac(mac_address, anomaly_macs)
        else:
            # Default to IP-based
            return cls.classify_by_ip_odd_even(ip_address)
