#!/usr/bin/env python3
"""
DSCP 0 (BE - Best Effort) Publisher
Best Effort Priority - Non-Critical Traffic

Use Case: Non-critical traffic, debugging data, test messages
Queue: 5 (5-15% bandwidth)
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import DSCPPublisher
from shared.mqtt.dscp_config import DSCP_BEST_EFFORT

if __name__ == '__main__':
    publisher = DSCPPublisher(
        dscp_value=DSCP_BEST_EFFORT,
        priority_name="besteffort"
    )
    publisher.run()
