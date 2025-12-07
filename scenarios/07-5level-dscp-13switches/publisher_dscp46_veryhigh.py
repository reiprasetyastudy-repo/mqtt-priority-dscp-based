#!/usr/bin/env python3
"""
DSCP 46 (EF - Expedited Forwarding) Publisher
Very High Priority - Critical/Anomaly Traffic

Use Case: Critical alerts, anomaly detection, emergency notifications
Queue: 1 (60-80% bandwidth)
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import DSCPPublisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

if __name__ == '__main__':
    publisher = DSCPPublisher(
        dscp_value=DSCP_VERY_HIGH,
        priority_name="veryhigh"
    )
    publisher.run()
