#!/usr/bin/env python3
"""
DSCP 26 (Medium Priority) Publisher - Thin Wrapper

This is a thin wrapper around the generic DSCP publisher.
Uses DSCP 26 (AF31) for regular monitoring data.

Usage:
    DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp26_medium.py
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_MEDIUM

if __name__ == '__main__':
    run_publisher(
        dscp_value=DSCP_MEDIUM,  # 26
        traffic_type='medium'       # Regular values (40-70)
    )
