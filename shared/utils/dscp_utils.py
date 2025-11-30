#!/usr/bin/env python3
"""
DSCP Utility Functions

Centralized DSCP header configuration for all MQTT publishers.
This module provides utilities to set DSCP values in IP headers
for traffic prioritization in SDN networks.

Usage:
    from shared.utils.dscp_utils import configure_dscp_socket, create_dscp_callback

    # Method 1: Direct socket configuration
    ip_tos = configure_dscp_socket(sock, dscp_value=46)

    # Method 2: Create callback for MQTT client
    callback = create_dscp_callback(dscp_value=46, device_name="sensor1")
    client.on_socket_open = callback
"""

import socket


def configure_dscp_socket(sock, dscp_value):
    """
    Configure socket with DSCP value in IP header.

    Args:
        sock: Socket object to configure
        dscp_value (int): DSCP value (0-63)
            Common values:
            - 46 (EF - Expedited Forwarding): Very High Priority
            - 34 (AF41): High Priority
            - 26 (AF31): Medium Priority
            - 10 (AF11): Low Priority
            - 0 (BE - Best Effort): Default

    Returns:
        int: The TOS value that was set (dscp_value << 2)

    Raises:
        ValueError: If dscp_value is out of range (0-63)
        OSError: If socket option cannot be set

    Example:
        >>> sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        >>> ip_tos = configure_dscp_socket(sock, dscp_value=46)
        >>> print(f"Configured TOS: 0x{ip_tos:02x}")
        Configured TOS: 0xb8
    """
    # Validate DSCP value range
    if not 0 <= dscp_value <= 63:
        raise ValueError(f"DSCP value must be 0-63, got {dscp_value}")

    # Convert DSCP to TOS (Type of Service)
    # DSCP uses the upper 6 bits of the TOS byte
    ip_tos = dscp_value << 2

    try:
        # Set IP_TOS socket option
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, ip_tos)
        return ip_tos
    except OSError as e:
        raise OSError(f"Failed to set DSCP on socket: {e}")


def create_dscp_callback(dscp_value, device_name=None, verbose=True):
    """
    Create an on_socket_open callback for paho-mqtt client with DSCP configuration.

    This function returns a callback compatible with paho-mqtt 2.x that
    automatically configures DSCP when the MQTT connection is established.

    Args:
        dscp_value (int): DSCP value to set (0-63)
        device_name (str, optional): Device name for logging
        verbose (bool): Enable verbose logging (default: True)

    Returns:
        callable: Callback function compatible with client.on_socket_open

    Example:
        >>> import paho.mqtt.client as mqtt
        >>> from shared.utils.dscp_utils import create_dscp_callback
        >>>
        >>> client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        >>> client.on_socket_open = create_dscp_callback(dscp_value=46, device_name="sensor1")
        >>> client.connect("10.0.0.1", 1883)
    """
    def on_socket_open(client, userdata, sock):
        """Callback that sets DSCP when socket opens"""
        try:
            ip_tos = configure_dscp_socket(sock, dscp_value)

            if verbose:
                device_info = f"[{device_name}] " if device_name else ""
                print(f"[DSCP] {device_info}Socket configured with DSCP {dscp_value} "
                      f"(TOS=0x{ip_tos:02x})")
        except Exception as e:
            error_msg = f"[DSCP ERROR] Failed to configure socket: {e}"
            print(error_msg)
            # Don't raise - allow connection to proceed without DSCP

    return on_socket_open


def get_dscp_name(dscp_value):
    """
    Get human-readable name for DSCP value.

    Args:
        dscp_value (int): DSCP value (0-63)

    Returns:
        str: Human-readable name (e.g., "EF (Expedited Forwarding)")

    Example:
        >>> get_dscp_name(46)
        'EF (Expedited Forwarding)'
        >>> get_dscp_name(0)
        'BE (Best Effort)'
    """
    dscp_names = {
        46: "EF (Expedited Forwarding)",
        34: "AF41 (Assured Forwarding Class 4, Low Drop)",
        26: "AF31 (Assured Forwarding Class 3, Low Drop)",
        18: "AF21 (Assured Forwarding Class 2, Low Drop)",
        10: "AF11 (Assured Forwarding Class 1, Low Drop)",
        0: "BE (Best Effort)",
    }
    return dscp_names.get(dscp_value, f"DSCP {dscp_value}")


def validate_dscp_value(dscp_value):
    """
    Validate that DSCP value is in valid range.

    Args:
        dscp_value (int): DSCP value to validate

    Returns:
        bool: True if valid

    Raises:
        ValueError: If dscp_value is invalid
    """
    if not isinstance(dscp_value, int):
        raise ValueError(f"DSCP value must be an integer, got {type(dscp_value)}")

    if not 0 <= dscp_value <= 63:
        raise ValueError(f"DSCP value must be 0-63, got {dscp_value}")

    return True


# Module-level constants for convenience
DSCP_EF = 46      # Expedited Forwarding (Very High Priority)
DSCP_AF41 = 34    # Assured Forwarding 41 (High Priority)
DSCP_AF31 = 26    # Assured Forwarding 31 (Medium Priority)
DSCP_AF21 = 18    # Assured Forwarding 21 (Medium-Low Priority)
DSCP_AF11 = 10    # Assured Forwarding 11 (Low Priority)
DSCP_BE = 0       # Best Effort (Default)


if __name__ == "__main__":
    # Self-test
    print("DSCP Utilities - Self Test")
    print("=" * 50)

    # Test DSCP name lookup
    for dscp in [46, 34, 26, 10, 0]:
        name = get_dscp_name(dscp)
        print(f"DSCP {dscp:2d}: {name}")

    print("\nConstants:")
    print(f"  DSCP_EF   = {DSCP_EF}")
    print(f"  DSCP_AF41 = {DSCP_AF41}")
    print(f"  DSCP_AF31 = {DSCP_AF31}")
    print(f"  DSCP_AF11 = {DSCP_AF11}")
    print(f"  DSCP_BE   = {DSCP_BE}")

    print("\nValidation tests:")
    try:
        validate_dscp_value(46)
        print("  ✓ Valid DSCP value (46)")
    except ValueError as e:
        print(f"  ✗ {e}")

    try:
        validate_dscp_value(100)
        print("  ✗ Should have failed for DSCP 100")
    except ValueError as e:
        print(f"  ✓ Correctly rejected invalid value: {e}")

    print("\n✓ Self-test complete!")
