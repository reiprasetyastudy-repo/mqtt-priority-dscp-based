#!/usr/bin/env python3
"""
Unit tests for Traffic Classifier

Run with: python3 -m pytest test_classifier.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qos.classifier import TrafficClassifier
from utils.constants import QueueID, QoSPriority


def test_classify_anomaly_ip():
    """Test that odd IPs are classified as anomaly"""
    queue, priority, traffic_type = TrafficClassifier.classify_by_ip_odd_even("10.0.1.1")

    assert queue == QueueID.HIGH_PRIORITY
    assert priority == QoSPriority.MQTT_ANOMALY
    assert traffic_type == "ANOMALY"


def test_classify_normal_ip():
    """Test that even IPs are classified as normal"""
    queue, priority, traffic_type = TrafficClassifier.classify_by_ip_odd_even("10.0.1.2")

    assert queue == QueueID.LOW_PRIORITY
    assert priority == QoSPriority.MQTT_NORMAL
    assert traffic_type == "NORMAL"


def test_classify_multiple_anomaly_ips():
    """Test multiple odd IPs"""
    test_ips = ["10.0.1.1", "10.0.1.3", "10.0.2.1", "10.0.2.3"]

    for ip in test_ips:
        queue, priority, traffic_type = TrafficClassifier.classify_by_ip_odd_even(ip)
        assert queue == QueueID.HIGH_PRIORITY, f"Failed for IP {ip}"
        assert traffic_type == "ANOMALY", f"Failed for IP {ip}"


def test_classify_multiple_normal_ips():
    """Test multiple even IPs"""
    test_ips = ["10.0.1.2", "10.0.1.4", "10.0.2.2", "10.0.2.4"]

    for ip in test_ips:
        queue, priority, traffic_type = TrafficClassifier.classify_by_ip_odd_even(ip)
        assert queue == QueueID.LOW_PRIORITY, f"Failed for IP {ip}"
        assert traffic_type == "NORMAL", f"Failed for IP {ip}"


def test_is_mqtt_traffic():
    """Test MQTT traffic detection"""
    assert TrafficClassifier.is_mqtt_traffic(1883) == True
    assert TrafficClassifier.is_mqtt_traffic(80) == False
    assert TrafficClassifier.is_mqtt_traffic(443) == False
    assert TrafficClassifier.is_mqtt_traffic(None) == False


def test_classify_invalid_ip():
    """Test handling of invalid IP"""
    queue, priority, traffic_type = TrafficClassifier.classify_by_ip_odd_even("invalid")

    assert queue == QueueID.LOW_PRIORITY
    assert traffic_type == "UNKNOWN"


if __name__ == '__main__':
    # Run tests manually
    test_classify_anomaly_ip()
    test_classify_normal_ip()
    test_classify_multiple_anomaly_ips()
    test_classify_multiple_normal_ips()
    test_is_mqtt_traffic()
    test_classify_invalid_ip()

    print("✅ All tests passed!")
