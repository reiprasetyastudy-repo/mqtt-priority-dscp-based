#!/usr/bin/env python3
"""
DSCP 0 (Best Effort) Publisher - Thin Wrapper

This is a thin wrapper around the generic DSCP publisher.
Uses DSCP 0 (BE - Best Effort) for non-critical traffic.

Usage:
    DEVICE=sensor1 BROKER_IP=10.0.0.1 python3 publisher_dscp0_besteffort.py
"""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from shared.mqtt.publisher_dscp import run_publisher
from shared.mqtt.dscp_config import DSCP_BEST_EFFORT

if __name__ == '__main__':
    run_publisher(
        dscp_value=DSCP_BEST_EFFORT,  # 0
        traffic_type='normal'       # Normal values (20-30)
    )
