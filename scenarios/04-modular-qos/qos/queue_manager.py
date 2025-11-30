#!/usr/bin/env python3
"""
Queue Manager for Scenario 04

Manages OVS queue configuration for QoS.
"""

import subprocess
from typing import List, Tuple, Optional
from ..config.config_loader import ScenarioConfig
from ..utils.constants import QueueType


class QueueConfigurationError(Exception):
    """Raised when queue configuration fails"""
    pass


class QueueManager:
    """
    Manages OVS QoS queue configuration.

    Handles creation, attachment, and validation of queues.
    """

    def __init__(self, config: ScenarioConfig, logger=None):
        """
        Initialize queue manager.

        Args:
            config: Scenario configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger

    def _log(self, msg: str, level: str = "info"):
        """Helper to log messages"""
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(msg)

    def _run_ovs_command(self, cmd: str, timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Run OVS command safely.

        Args:
            cmd: Command to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip()
            )
        except subprocess.TimeoutExpired:
            return (False, "", "Command timeout")
        except Exception as e:
            return (False, "", str(e))

    def get_switch_ports(self, switch_name: str) -> List[str]:
        """
        Get all ports for a switch.

        Args:
            switch_name: Switch name (e.g., "s1")

        Returns:
            List of port names
        """
        success, stdout, stderr = self._run_ovs_command(
            f'ovs-vsctl list-ports {switch_name}'
        )

        if not success:
            self._log(f"Failed to list ports for {switch_name}: {stderr}", "warning")
            return []

        ports = [p.strip() for p in stdout.split('\n') if p.strip()]
        return ports

    def configure_port_queues(self, port_name: str) -> bool:
        """
        Configure queues for a single port.

        Args:
            port_name: Port name (e.g., "s1-eth1")

        Returns:
            True if successful, False otherwise
        """
        # Calculate bandwidth values
        bandwidth_bps = self.config.network.bandwidth_mbps * 1_000_000

        # Queue 1 (High Priority)
        q1_min = int(bandwidth_bps * self.config.qos.queue_high.min_bandwidth_percent / 100)
        q1_max = int(bandwidth_bps * self.config.qos.queue_high.max_bandwidth_percent / 100)

        # Queue 2 (Low Priority)
        q2_min = int(bandwidth_bps * self.config.qos.queue_low.min_bandwidth_percent / 100)
        q2_max = int(bandwidth_bps * self.config.qos.queue_low.max_bandwidth_percent / 100)

        # Build OVS command (all in one atomic operation)
        cmd = (
            f'ovs-vsctl -- set port {port_name} qos=@newqos '
            f'-- --id=@newqos create qos type={QueueType.LINUX_HTB} '
            f'other-config:max-rate={bandwidth_bps} '
            f'queues:{self.config.qos.queue_high.id}=@q1 '
            f'queues:{self.config.qos.queue_low.id}=@q2 '
            f'-- --id=@q1 create queue '
            f'other-config:min-rate={q1_min} '
            f'other-config:max-rate={q1_max} '
            f'-- --id=@q2 create queue '
            f'other-config:min-rate={q2_min} '
            f'other-config:max-rate={q2_max}'
        )

        success, stdout, stderr = self._run_ovs_command(cmd)

        if success:
            self._log(
                f"  ✓ {port_name} - "
                f"Queue 1: {q1_min/1_000_000:.1f}-{q1_max/1_000_000:.1f} Mbps, "
                f"Queue 2: {q2_min/1_000_000:.1f}-{q2_max/1_000_000:.1f} Mbps"
            )
            return True
        else:
            self._log(f"  ✗ {port_name} - Failed: {stderr}", "error")
            return False

    def configure_switch_queues(self, switch_name: str) -> int:
        """
        Configure queues for all ports on a switch.

        Args:
            switch_name: Switch name (e.g., "s1")

        Returns:
            Number of successfully configured ports
        """
        ports = self.get_switch_ports(switch_name)
        if not ports:
            self._log(f"No ports found for {switch_name}", "warning")
            return 0

        success_count = 0
        for port in ports:
            if self.configure_port_queues(port):
                success_count += 1

        return success_count

    def configure_all_queues(self) -> bool:
        """
        Configure queues for all switches in topology.

        Returns:
            True if all successful, False if any failed
        """
        self._log("Configuring OVS QoS Queues...")

        # Get all switches
        all_switches = (
            self.config.network.core_switches +
            self.config.network.agg_switches +
            self.config.network.edge_switches
        )

        total_configured = 0
        total_ports = 0

        for switch_id in all_switches:
            switch_name = f's{switch_id}'
            ports_before = len(self.get_switch_ports(switch_name))
            configured = self.configure_switch_queues(switch_name)

            total_ports += ports_before
            total_configured += configured

        self._log(
            f"Queue configuration complete: {total_configured}/{total_ports} ports configured"
        )

        return total_configured == total_ports

    def validate_queue_configuration(self, switch_name: str, port_name: str) -> bool:
        """
        Validate that queues are properly configured on a port.

        Args:
            switch_name: Switch name
            port_name: Port name

        Returns:
            True if queues are configured, False otherwise
        """
        # Check if QoS is attached
        success, stdout, stderr = self._run_ovs_command(
            f'ovs-vsctl get port {port_name} qos'
        )

        if not success or stdout == '[]':
            return False

        # Check if queues exist
        success, stdout, stderr = self._run_ovs_command(
            f'ovs-vsctl list qos'
        )

        return success and 'queues' in stdout

    def clear_queues(self, switch_name: str) -> bool:
        """
        Clear all queue configuration from a switch.

        Args:
            switch_name: Switch name

        Returns:
            True if successful
        """
        ports = self.get_switch_ports(switch_name)

        for port in ports:
            cmd = f'ovs-vsctl -- destroy QoS {port} -- clear Port {port} qos'
            self._run_ovs_command(cmd)

        self._log(f"Cleared queues for {switch_name}")
        return True

    def get_queue_stats(self, switch_name: str, port_name: str) -> Optional[dict]:
        """
        Get queue statistics for a port.

        Args:
            switch_name: Switch name
            port_name: Port name

        Returns:
            Dictionary of queue stats or None if unavailable
        """
        # This would require OpenFlow stats requests
        # Placeholder for future implementation
        return None
