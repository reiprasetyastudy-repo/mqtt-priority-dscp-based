#!/usr/bin/env python3
"""
DSCP 34 (AF41 - Assured Forwarding 4.1) Publisher
High Priority - Important Sensor Data

Use Case: Important sensor data, high-priority telemetry
Queue: 2 (45-60% bandwidth)
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import DSCPPublisher
from shared.mqtt.dscp_config import DSCP_HIGH

if __name__ == '__main__':
    publisher = DSCPPublisher(
        dscp_value=DSCP_HIGH,
        priority_name="high"
    )
    publisher.run()
