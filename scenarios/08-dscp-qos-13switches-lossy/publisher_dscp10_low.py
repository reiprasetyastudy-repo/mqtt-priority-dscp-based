#!/usr/bin/env python3
"""
DSCP 10 (Low Priority) Publisher - Thin Wrapper

This is a thin wrapper around the generic DSCP publisher.
Uses DSCP 10 (AF11) for background data collection.

Usage:
    DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp10_low.py
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_LOW

if __name__ == '__main__':
    run_publisher(
        dscp_value=DSCP_LOW,  # 10
        traffic_type='low'       # Background values (20-50)
    )
