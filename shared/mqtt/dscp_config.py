#!/usr/bin/env python3
"""
DSCP Configuration Constants

Centralized DSCP values and priority mappings for MQTT-SDN project.
This module defines standard DSCP values used across all scenarios.

Reference: RFC 2474 - Differentiated Services Field (DSCP)
"""

# ============================================================================
# DSCP Priority Levels (5 Levels) - Used in Scenarios 05 & 06
# ============================================================================

# Very High Priority - Critical/Anomaly Traffic
DSCP_VERY_HIGH = 46  # EF (Expedited Forwarding)
DSCP_EF = 46

# High Priority - Important Sensor Data
DSCP_HIGH = 34  # AF41 (Assured Forwarding Class 4, Low Drop)
DSCP_AF41 = 34

# Medium Priority - Regular Monitoring
DSCP_MEDIUM = 26  # AF31 (Assured Forwarding Class 3, Low Drop)
DSCP_AF31 = 26

# Low Priority - Background Data Collection
DSCP_LOW = 10  # AF11 (Assured Forwarding Class 1, Low Drop)
DSCP_AF11 = 10

# Best Effort - Non-Critical Traffic
DSCP_BEST_EFFORT = 0  # BE (Best Effort)
DSCP_BE = 0

# ============================================================================
# Additional Standard DSCP Values (for future use)
# ============================================================================

# Assured Forwarding Class 4
DSCP_AF42 = 36  # Medium Drop Probability
DSCP_AF43 = 38  # High Drop Probability

# Assured Forwarding Class 3
DSCP_AF32 = 28  # Medium Drop Probability
DSCP_AF33 = 30  # High Drop Probability

# Assured Forwarding Class 2
DSCP_AF21 = 18  # Low Drop Probability
DSCP_AF22 = 20  # Medium Drop Probability
DSCP_AF23 = 22  # High Drop Probability

# Assured Forwarding Class 1
DSCP_AF12 = 12  # Medium Drop Probability
DSCP_AF13 = 14  # High Drop Probability

# Class Selector (backward compatible with IP Precedence)
DSCP_CS7 = 56  # Network Control
DSCP_CS6 = 48  # Internetwork Control
DSCP_CS5 = 40  # Voice
DSCP_CS4 = 32  # Video
DSCP_CS3 = 24  # Signaling
DSCP_CS2 = 16  # Operations, Administration, Management
DSCP_CS1 = 8   # Priority/Background
DSCP_CS0 = 0   # Best Effort

# ============================================================================
# Priority to DSCP Mapping
# ============================================================================

PRIORITY_TO_DSCP = {
    "very_high": DSCP_VERY_HIGH,
    "high": DSCP_HIGH,
    "medium": DSCP_MEDIUM,
    "low": DSCP_LOW,
    "best_effort": DSCP_BEST_EFFORT,
}

# Reverse mapping
DSCP_TO_PRIORITY = {v: k for k, v in PRIORITY_TO_DSCP.items()}

# ============================================================================
# DSCP Descriptions
# ============================================================================

DSCP_DESCRIPTIONS = {
    46: "EF (Expedited Forwarding) - Very High Priority",
    34: "AF41 (Assured Forwarding 4.1) - High Priority",
    26: "AF31 (Assured Forwarding 3.1) - Medium Priority",
    10: "AF11 (Assured Forwarding 1.1) - Low Priority",
    0: "BE (Best Effort) - Default Priority",
}

# ============================================================================
# Queue Mappings (OVS Queue Numbers)
# ============================================================================

DSCP_TO_QUEUE = {
    46: 1,  # DSCP 46 → Queue 1 (Very High)
    34: 2,  # DSCP 34 → Queue 2 (High)
    26: 3,  # DSCP 26 → Queue 3 (Medium)
    10: 4,  # DSCP 10 → Queue 4 (Low)
    0: 5,   # DSCP 0  → Queue 5 (Best Effort)
}

# ============================================================================
# Bandwidth Allocation (Percentages)
# ============================================================================

QUEUE_BANDWIDTH = {
    1: {"min": 60, "max": 80},  # Queue 1: 60-80% (DSCP 46)
    2: {"min": 45, "max": 60},  # Queue 2: 45-60% (DSCP 34)
    3: {"min": 30, "max": 45},  # Queue 3: 30-45% (DSCP 26)
    4: {"min": 15, "max": 30},  # Queue 4: 15-30% (DSCP 10)
    5: {"min": 5, "max": 15},   # Queue 5: 5-15%  (DSCP 0)
}

# ============================================================================
# Use Case Recommendations
# ============================================================================

DSCP_USE_CASES = {
    46: "Critical alerts, anomaly detection, emergency notifications",
    34: "Important sensor data, high-priority telemetry",
    26: "Regular monitoring data, periodic status updates",
    10: "Background data collection, historical logs",
    0: "Non-critical traffic, debugging data, test messages",
}

# ============================================================================
# Helper Functions
# ============================================================================


def get_queue_for_dscp(dscp_value):
    """
    Get OVS queue number for DSCP value.

    Args:
        dscp_value (int): DSCP value

    Returns:
        int: Queue number (1-5)

    Example:
        >>> get_queue_for_dscp(46)
        1
    """
    return DSCP_TO_QUEUE.get(dscp_value, 5)  # Default to queue 5 (best effort)


def get_priority_name(dscp_value):
    """
    Get priority name for DSCP value.

    Args:
        dscp_value (int): DSCP value

    Returns:
        str: Priority name (e.g., "very_high")

    Example:
        >>> get_priority_name(46)
        'very_high'
    """
    return DSCP_TO_PRIORITY.get(dscp_value, "best_effort")


def get_description(dscp_value):
    """
    Get human-readable description for DSCP value.

    Args:
        dscp_value (int): DSCP value

    Returns:
        str: Description

    Example:
        >>> get_description(46)
        'EF (Expedited Forwarding) - Very High Priority'
    """
    return DSCP_DESCRIPTIONS.get(dscp_value, f"DSCP {dscp_value}")


def get_use_case(dscp_value):
    """
    Get recommended use case for DSCP value.

    Args:
        dscp_value (int): DSCP value

    Returns:
        str: Use case description

    Example:
        >>> get_use_case(46)
        'Critical alerts, anomaly detection, emergency notifications'
    """
    return DSCP_USE_CASES.get(dscp_value, "General traffic")


def print_dscp_config():
    """Print complete DSCP configuration summary."""
    print("=" * 70)
    print("DSCP Configuration Summary")
    print("=" * 70)
    print()
    print("Priority Levels:")
    print("-" * 70)
    print(f"{'DSCP':<6} {'Queue':<7} {'Bandwidth':<15} {'Description':<40}")
    print("-" * 70)

    for dscp in [46, 34, 26, 10, 0]:
        queue = get_queue_for_dscp(dscp)
        bw = QUEUE_BANDWIDTH[queue]
        desc = get_description(dscp)
        print(f"{dscp:<6} {queue:<7} {bw['min']:>2}-{bw['max']:>2}%{'':<9} {desc:<40}")

    print()
    print("Use Cases:")
    print("-" * 70)
    for dscp in [46, 34, 26, 10, 0]:
        use_case = get_use_case(dscp)
        print(f"DSCP {dscp:2d}: {use_case}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    # Self-test
    print_dscp_config()

    print("\nQuick Tests:")
    print(f"  Queue for DSCP 46: {get_queue_for_dscp(46)}")
    print(f"  Priority for DSCP 46: {get_priority_name(46)}")
    print(f"  Description for DSCP 46: {get_description(46)}")
