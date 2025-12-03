#!/usr/bin/env python3
"""
DSCP 46 (Very High Priority) Publisher - Thin Wrapper

This is a thin wrapper around the generic DSCP publisher.
Uses DSCP 46 (EF - Expedited Forwarding) for critical/anomaly traffic.

Usage:
    DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp46_veryhigh.py
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_VERY_HIGH

if __name__ == '__main__':
    run_publisher(
        dscp_value=DSCP_VERY_HIGH,  # 46
        traffic_type='anomaly'       # High values (50-100)
    )
