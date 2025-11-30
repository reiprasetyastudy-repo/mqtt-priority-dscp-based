#!/usr/bin/env python3
"""
MAC Learning Table for Scenario 04

Simple MAC address learning for L2 forwarding.
"""

from typing import Dict, Optional


class MACLearningTable:
    """
    MAC address learning table.

    Stores MAC-to-port mappings for each switch.
    """

    def __init__(self):
        """Initialize empty MAC table"""
        # Structure: {dpid: {mac_address: port}}
        self.mac_table: Dict[int, Dict[str, int]] = {}

    def learn(self, dpid: int, mac_address: str, port: int) -> bool:
        """
        Learn MAC address to port mapping.

        Args:
            dpid: Datapath ID (switch ID)
            mac_address: MAC address
            port: Input port number

        Returns:
            True if new entry, False if already known
        """
        if dpid not in self.mac_table:
            self.mac_table[dpid] = {}

        is_new = mac_address not in self.mac_table[dpid]
        self.mac_table[dpid][mac_address] = port

        return is_new

    def lookup(self, dpid: int, mac_address: str) -> Optional[int]:
        """
        Lookup port for MAC address.

        Args:
            dpid: Datapath ID
            mac_address: MAC address to lookup

        Returns:
            Port number if found, None otherwise
        """
        if dpid not in self.mac_table:
            return None

        return self.mac_table[dpid].get(mac_address)

    def get_port(self, dpid: int, mac_address: str, flood_port: int) -> int:
        """
        Get output port for MAC address (with flooding fallback).

        Args:
            dpid: Datapath ID
            mac_address: MAC address
            flood_port: Port to use for flooding (e.g., OFPP_FLOOD)

        Returns:
            Output port number (or flood_port if unknown)
        """
        port = self.lookup(dpid, mac_address)
        return port if port is not None else flood_port

    def clear(self, dpid: Optional[int] = None):
        """
        Clear MAC table.

        Args:
            dpid: Datapath ID to clear (None = clear all)
        """
        if dpid is None:
            self.mac_table.clear()
        elif dpid in self.mac_table:
            self.mac_table[dpid].clear()

    def get_switch_entries(self, dpid: int) -> Dict[str, int]:
        """
        Get all MAC entries for a switch.

        Args:
            dpid: Datapath ID

        Returns:
            Dictionary of MAC-to-port mappings
        """
        return self.mac_table.get(dpid, {}).copy()

    def get_total_entries(self) -> int:
        """Get total number of MAC entries across all switches"""
        return sum(len(entries) for entries in self.mac_table.values())
