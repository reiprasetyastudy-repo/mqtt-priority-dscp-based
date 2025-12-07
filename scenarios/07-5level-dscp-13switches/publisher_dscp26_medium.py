#!/usr/bin/env python3
"""
DSCP 26 (AF31 - Assured Forwarding 3.1) Publisher
Medium Priority - Regular Monitoring

Use Case: Regular monitoring data, periodic status updates
Queue: 3 (30-45% bandwidth)
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import DSCPPublisher
from shared.mqtt.dscp_config import DSCP_MEDIUM

if __name__ == '__main__':
    publisher = DSCPPublisher(
        dscp_value=DSCP_MEDIUM,
        priority_name="medium"
    )
    publisher.run()
