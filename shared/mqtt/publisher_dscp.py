#!/usr/bin/env python3
"""
Generic DSCP Publisher - Reusable for All Scenarios

This is a centralized, generic MQTT publisher that supports all DSCP priority levels.
Can be used directly or through thin wrapper scripts.

Usage:
    # Direct usage with CLI arguments
    python3 publisher_dscp.py --dscp 46 --type anomaly --device sensor1

    # With environment variables (current style)
    DSCP=46 DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp.py

    # From Python code
    from shared.mqtt.publisher_dscp import run_publisher
    run_publisher(dscp_value=46, traffic_type='anomaly')

Traffic Types:
    - 'anomaly' / 'very_high': High values (50-100), DSCP typically 46
    - 'high': Important values (70-90), DSCP typically 34
    - 'medium': Regular values (40-70), DSCP typically 26
    - 'low': Background values (20-50), DSCP typically 10
    - 'normal' / 'best_effort': Normal values (20-30), DSCP typically 0
"""

import paho.mqtt.client as mqtt
import time
import json
import random
import os
import sys
import argparse

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

# Import shared DSCP utilities
from shared.utils.dscp_utils import create_dscp_callback, get_dscp_name
from shared.mqtt.dscp_config import (
    DSCP_VERY_HIGH, DSCP_HIGH, DSCP_MEDIUM, DSCP_LOW, DSCP_BEST_EFFORT,
    get_priority_name, get_description
)


# ============================================================================
# Traffic Type Configuration
# ============================================================================

TRAFFIC_TYPES = {
    'anomaly': {
        'label': 'ANOMALY',
        'value_range': (50, 100),
        'default_dscp': DSCP_VERY_HIGH,
        'description': 'High-priority anomaly detection data'
    },
    'very_high': {
        'label': 'VERY HIGH',
        'value_range': (50, 100),
        'default_dscp': DSCP_VERY_HIGH,
        'description': 'Critical priority traffic'
    },
    'high': {
        'label': 'HIGH',
        'value_range': (70, 90),
        'default_dscp': DSCP_HIGH,
        'description': 'High-priority sensor data'
    },
    'medium': {
        'label': 'MEDIUM',
        'value_range': (40, 70),
        'default_dscp': DSCP_MEDIUM,
        'description': 'Medium-priority monitoring data'
    },
    'low': {
        'label': 'LOW',
        'value_range': (20, 50),
        'default_dscp': DSCP_LOW,
        'description': 'Low-priority background data'
    },
    'normal': {
        'label': 'NORMAL',
        'value_range': (20, 30),
        'default_dscp': DSCP_BEST_EFFORT,
        'description': 'Normal traffic (best effort)'
    },
    'best_effort': {
        'label': 'BEST EFFORT',
        'value_range': (20, 30),
        'default_dscp': DSCP_BEST_EFFORT,
        'description': 'Best effort traffic (no priority)'
    }
}


# ============================================================================
# Generic Publisher Class
# ============================================================================

class DSCPPublisher:
    """Generic DSCP-enabled MQTT Publisher"""

    def __init__(self, dscp_value, traffic_type='anomaly', device_name=None,
                 broker_ip=None, broker_port=1883, msg_rate=None, topic='iot/data'):
        """
        Initialize DSCP Publisher

        Args:
            dscp_value (int): DSCP value (0-63)
            traffic_type (str): Type of traffic (anomaly, high, medium, low, normal)
            device_name (str): Device identifier
            broker_ip (str): MQTT broker IP address
            broker_port (int): MQTT broker port (default: 1883)
            msg_rate (float): Messages per second (default: 50)
            topic (str): MQTT topic (default: 'iot/data')
        """
        # Configuration
        self.dscp_value = dscp_value
        self.traffic_type = traffic_type.lower()
        self.device_name = device_name or f"sensor_{self.traffic_type}"
        self.broker_ip = broker_ip or "10.0.0.1"
        self.broker_port = broker_port
        self.msg_rate = msg_rate or 50.0
        self.topic = topic

        # Get traffic type config
        self.traffic_config = TRAFFIC_TYPES.get(self.traffic_type, TRAFFIC_TYPES['normal'])

        # State
        self.sequence_number = 0
        self.client = None

    def print_header(self):
        """Print startup header"""
        print("=" * 70)
        print(f"  {self.traffic_config['label']} Publisher with DSCP Tagging")
        print("=" * 70)
        print(f"Device        : {self.device_name}")
        print(f"Broker        : {self.broker_ip}:{self.broker_port}")
        print(f"Topic         : {self.topic}")
        print(f"Rate          : {self.msg_rate} msg/s")
        print(f"Traffic Type  : {self.traffic_type}")
        print(f"DSCP Value    : {self.dscp_value} ({get_dscp_name(self.dscp_value)})")
        print(f"Priority      : {get_priority_name(self.dscp_value).upper()}")
        print(f"Description   : {get_description(self.dscp_value)}")
        print(f"Value Range   : {self.traffic_config['value_range']}")
        print("=" * 70)

    def setup_client(self):
        """Setup MQTT client with DSCP configuration"""
        # Create MQTT client (paho-mqtt 2.x compatible)
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        # Configure DSCP using shared utility
        self.client.on_socket_open = create_dscp_callback(
            dscp_value=self.dscp_value,
            device_name=self.device_name,
            verbose=True
        )

        print(f"\n[MQTT] Connecting to {self.broker_ip}:{self.broker_port}...")

    def connect(self):
        """Connect to MQTT broker"""
        self.client.connect(self.broker_ip, self.broker_port, keepalive=60)
        self.client.loop_start()

        # Wait for connection
        time.sleep(1)
        print("[MQTT] Connected! Publishing messages...")
        print()

    def generate_payload(self):
        """Generate message payload based on traffic type"""
        value_min, value_max = self.traffic_config['value_range']

        payload = {
            "device": self.device_name,
            "type": self.traffic_type,
            "dscp": self.dscp_value,
            "priority": get_priority_name(self.dscp_value),
            "value": random.uniform(value_min, value_max),
            "timestamp": time.time(),
            "seq": self.sequence_number
        }

        return payload

    def publish_loop(self):
        """Main publishing loop"""
        try:
            while True:
                # Generate payload
                payload = self.generate_payload()

                # Publish to MQTT
                result = self.client.publish(self.topic, json.dumps(payload), qos=1)

                # Print status
                label = self.traffic_config['label']
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"[{label}/DSCP{self.dscp_value}] "
                          f"seq={self.sequence_number:05d} "
                          f"value={payload['value']:6.2f} ✓")
                else:
                    print(f"[ERROR] seq={self.sequence_number:05d} failed")

                self.sequence_number += 1
                time.sleep(1.0 / self.msg_rate)

        except KeyboardInterrupt:
            print("\n[STOP] Stopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup and disconnect"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        print(f"[EXIT] Total sent: {self.sequence_number} messages")

    def run(self):
        """Run the publisher (main entry point)"""
        self.print_header()
        self.setup_client()
        self.connect()
        self.publish_loop()


# ============================================================================
# Convenience Functions
# ============================================================================

def run_publisher(dscp_value, traffic_type='anomaly', device_name=None,
                  broker_ip=None, broker_port=1883, msg_rate=None, topic='iot/data'):
    """
    Convenience function to run publisher with specified configuration

    Args:
        dscp_value (int): DSCP value (0-63)
        traffic_type (str): Type of traffic (anomaly, high, medium, low, normal)
        device_name (str): Device identifier (optional)
        broker_ip (str): MQTT broker IP (optional, uses env or default)
        broker_port (int): MQTT broker port (default: 1883)
        msg_rate (float): Messages per second (optional, uses env or default)
        topic (str): MQTT topic (default: 'iot/data')

    Example:
        >>> from shared.mqtt.publisher_dscp import run_publisher
        >>> run_publisher(dscp_value=46, traffic_type='anomaly')
    """
    # Get configuration from environment if not provided
    if broker_ip is None:
        broker_ip = os.getenv("BROKER_IP", "10.0.0.1")

    if device_name is None:
        device_name = os.getenv("DEVICE", f"sensor_{traffic_type}")

    if msg_rate is None:
        msg_rate = float(os.getenv("MSG_RATE", "50"))

    # Create and run publisher
    publisher = DSCPPublisher(
        dscp_value=dscp_value,
        traffic_type=traffic_type,
        device_name=device_name,
        broker_ip=broker_ip,
        broker_port=broker_port,
        msg_rate=msg_rate,
        topic=topic
    )

    publisher.run()


# ============================================================================
# Command-Line Interface
# ============================================================================

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Generic DSCP-enabled MQTT Publisher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Anomaly traffic with DSCP 46
  python3 publisher_dscp.py --dscp 46 --type anomaly

  # High priority with custom device name
  python3 publisher_dscp.py --dscp 34 --type high --device sensor_temp_01

  # Using environment variables
  DSCP=26 DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp.py

Traffic Types:
  anomaly, very_high  → High values (50-100)
  high                → Important values (70-90)
  medium              → Regular values (40-70)
  low                 → Background values (20-50)
  normal, best_effort → Normal values (20-30)
        """
    )

    # DSCP configuration
    parser.add_argument('--dscp', type=int,
                        default=int(os.getenv('DSCP', DSCP_VERY_HIGH)),
                        help='DSCP value (0-63). Default: from DSCP env or 46')

    # Traffic type
    parser.add_argument('--type', dest='traffic_type',
                        default=os.getenv('TRAFFIC_TYPE', 'anomaly'),
                        choices=list(TRAFFIC_TYPES.keys()),
                        help='Traffic type. Default: from TRAFFIC_TYPE env or anomaly')

    # MQTT configuration
    parser.add_argument('--device', dest='device_name',
                        default=os.getenv('DEVICE'),
                        help='Device name. Default: from DEVICE env or sensor_<type>')

    parser.add_argument('--broker', dest='broker_ip',
                        default=os.getenv('BROKER_IP', '10.0.0.1'),
                        help='MQTT broker IP. Default: from BROKER_IP env or 10.0.0.1')

    parser.add_argument('--port', dest='broker_port', type=int,
                        default=int(os.getenv('BROKER_PORT', '1883')),
                        help='MQTT broker port. Default: from BROKER_PORT env or 1883')

    parser.add_argument('--rate', dest='msg_rate', type=float,
                        default=float(os.getenv('MSG_RATE', '50')),
                        help='Message rate (msg/s). Default: from MSG_RATE env or 50')

    parser.add_argument('--topic',
                        default=os.getenv('TOPIC', 'iot/data'),
                        help='MQTT topic. Default: from TOPIC env or iot/data')

    return parser.parse_args()


def main():
    """Main entry point for CLI usage"""
    args = parse_args()

    # Run publisher with parsed arguments
    run_publisher(
        dscp_value=args.dscp,
        traffic_type=args.traffic_type,
        device_name=args.device_name,
        broker_ip=args.broker_ip,
        broker_port=args.broker_port,
        msg_rate=args.msg_rate,
        topic=args.topic
    )


if __name__ == '__main__':
    main()
