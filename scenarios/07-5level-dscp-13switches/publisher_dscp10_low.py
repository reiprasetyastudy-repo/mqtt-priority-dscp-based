#!/usr/bin/env python3
"""
DSCP 10 (AF11 - Assured Forwarding 1.1) Publisher
Low Priority - Background Data Collection

Use Case: Background data collection, historical logs
Queue: 4 (15-30% bandwidth)
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import DSCPPublisher
from shared.mqtt.dscp_config import DSCP_LOW

if __name__ == '__main__':
    publisher = DSCPPublisher(
        dscp_value=DSCP_LOW,
        priority_name="low"
    )
    publisher.run()
