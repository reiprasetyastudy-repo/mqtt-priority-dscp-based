#!/usr/bin/env python3
"""
Default Configuration Values

These are DEFAULT values that scenarios can override.
Import and override in each scenario's topology.py as needed.
"""

# =============================================================================
# NETWORK DEFAULTS
# =============================================================================

DEFAULT_BANDWIDTH_MBPS = 0.2    # 200 Kbps - creates ~1.8x congestion
DEFAULT_MSG_RATE = 10           # 10 msg/s per publisher (realistic)

# =============================================================================
# TIMING DEFAULTS
# =============================================================================

DEFAULT_DURATION = 300          # 5 minutes send phase
DEFAULT_DRAIN_RATIO = 1.0       # Drain time = Duration × Ratio

# =============================================================================
# BROKER CONFIGURATION
# =============================================================================

BROKER_IP = "10.0.0.1"
BROKER_PORT = 1883

# =============================================================================
# PUBLISHER SCRIPTS (relative to scenario directory)
# =============================================================================

PUBLISHER_ANOMALY_SCRIPT = "publisher_dscp46_veryhigh.py"
PUBLISHER_NORMAL_SCRIPT = "publisher_dscp0_besteffort.py"
