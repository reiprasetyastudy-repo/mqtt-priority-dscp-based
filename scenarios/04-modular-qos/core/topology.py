#!/usr/bin/env python3
"""
Topology Builder for Scenario 04

Builds hierarchical network topology with proper separation of concerns.
"""

import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI

from ..config.config_loader import ScenarioConfig
from ..qos.queue_manager import QueueManager
from ..core.mqtt_manager import MQTTManager


class HierarchicalTopology:
    """
    Hierarchical 3-layer network topology builder.

    Topology:
        Core (1 switch) → Aggregation (2 switches) → Edge (4 switches)

    Separates concerns:
        - Network building
        - Queue configuration (via QueueManager)
        - MQTT management (via MQTTManager)
    """

    def __init__(self, config: ScenarioConfig, logger=None):
        """
        Initialize topology builder.

        Args:
            config: Scenario configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger
        self.net = None
        self.publishers = []
        self.broker_host = None

        # Initialize managers
        self.queue_manager = QueueManager(config, logger)
        self.mqtt_manager = MQTTManager(config, logger)

    def _log(self, msg: str, level: str = "info"):
        """Helper to log messages"""
        if self.logger:
            if level == "network":
                self.logger.network_event(msg)
            else:
                getattr(self.logger, level)(msg)
        else:
            print(f"[TOPOLOGY] {msg}")

    def build_network(self) -> Mininet:
        """
        Build Mininet network without starting it.

        Returns:
            Mininet network object
        """
        self._log("Building hierarchical topology", "network")

        # Create network
        self.net = Mininet(
            controller=RemoteController,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True,
            autoStaticArp=False
        )

        # Add controller
        self._add_controller()

        # Build topology layers
        self._add_core_layer()
        self._add_aggregation_layer()
        self._add_edge_layer()

        self._log(
            f"Topology built: "
            f"{len(self.config.network.core_switches) + len(self.config.network.agg_switches) + len(self.config.network.edge_switches)} switches, "
            f"{len(self.publishers)} publishers",
            "network"
        )

        return self.net

    def _add_controller(self):
        """Add SDN controller"""
        self._log(f"Adding controller at {self.config.network.controller_ip}:{self.config.network.controller_port}")

        self.net.addController(
            'c0',
            controller=RemoteController,
            ip=self.config.network.controller_ip,
            port=self.config.network.controller_port
        )

    def _add_core_layer(self):
        """Add core layer (switches + broker)"""
        self._log("Adding core layer")

        # Add core switch
        for switch_id in self.config.network.core_switches:
            switch = self.net.addSwitch(
                f's{switch_id}',
                protocols=self.config.network.openflow_version
            )

        # Add broker host at core
        self.broker_host = self.net.addHost(
            'broker',
            ip=f"{self.config.network.broker_ip}{self.config.network.subnet_mask}"
        )

        # Link broker to core switch
        core_switch = self.net.get('s1')
        self.net.addLink(
            self.broker_host,
            core_switch,
            bw=self.config.network.bandwidth_mbps
        )

    def _add_aggregation_layer(self):
        """Add aggregation layer and connect to core"""
        self._log("Adding aggregation layer")

        core_switch = self.net.get('s1')

        # Add aggregation switches
        for switch_id in self.config.network.agg_switches:
            agg_switch = self.net.addSwitch(
                f's{switch_id}',
                protocols=self.config.network.openflow_version
            )

            # Connect to core
            self.net.addLink(
                core_switch,
                agg_switch,
                bw=self.config.network.bandwidth_mbps
            )

    def _add_edge_layer(self):
        """Add edge layer with publishers"""
        self._log("Adding edge layer and publishers")

        # Divide edge switches between aggregation switches
        edge_switches = self.config.network.edge_switches
        mid_point = len(edge_switches) // 2

        # Floor 1 edge switches (connect to agg s2)
        floor1_switches = edge_switches[:mid_point]
        # Floor 2 edge switches (connect to agg s3)
        floor2_switches = edge_switches[mid_point:]

        # Add Floor 1
        agg_s2 = self.net.get('s2')
        for idx, switch_id in enumerate(floor1_switches):
            self._add_edge_switch_with_publishers(
                switch_id, agg_s2, floor=1, room=idx+1
            )

        # Add Floor 2
        agg_s3 = self.net.get('s3')
        for idx, switch_id in enumerate(floor2_switches):
            self._add_edge_switch_with_publishers(
                switch_id, agg_s3, floor=2, room=idx+1
            )

    def _add_edge_switch_with_publishers(self, switch_id: int, agg_switch, floor: int, room: int):
        """
        Add edge switch and connect publishers.

        Args:
            switch_id: Edge switch ID
            agg_switch: Parent aggregation switch
            floor: Floor number
            room: Room number
        """
        # Add edge switch
        edge_switch = self.net.addSwitch(
            f's{switch_id}',
            protocols=self.config.network.openflow_version
        )

        # Connect to aggregation
        self.net.addLink(
            agg_switch,
            edge_switch,
            bw=self.config.network.bandwidth_mbps
        )

        # Add publisher pair (anomaly + normal)
        host_id = (room - 1) * 2 + 1

        # Anomaly publisher (odd IP)
        anomaly_host = self.net.addHost(
            f'f{floor}r{room}a',
            ip=f'10.0.{floor}.{host_id}{self.config.network.subnet_mask}'
        )
        self.net.addLink(
            anomaly_host,
            edge_switch,
            bw=self.config.network.bandwidth_mbps
        )
        self.publishers.append({
            'host': anomaly_host,
            'type': 'anomaly',
            'floor': floor,
            'room': room
        })

        # Normal publisher (even IP)
        normal_host = self.net.addHost(
            f'f{floor}r{room}n',
            ip=f'10.0.{floor}.{host_id + 1}{self.config.network.subnet_mask}'
        )
        self.net.addLink(
            normal_host,
            edge_switch,
            bw=self.config.network.bandwidth_mbps
        )
        self.publishers.append({
            'host': normal_host,
            'type': 'normal',
            'floor': floor,
            'room': room
        })

    def start_network(self):
        """Start network and configure queues"""
        if not self.net:
            raise RuntimeError("Network not built. Call build_network() first.")

        self._log("Starting network", "network")
        self.net.start()

        self._log(
            f"Network started: "
            f"{len(self.config.network.core_switches)} core + "
            f"{len(self.config.network.agg_switches)} agg + "
            f"{len(self.config.network.edge_switches)} edge switches",
            "network"
        )

        # Wait for network to stabilize
        self._log(f"Waiting {self.config.timing.network_stabilization}s for network stabilization")
        time.sleep(self.config.timing.network_stabilization)

        # Configure OVS queues
        self._log("Configuring OVS queues")
        self.queue_manager.configure_all_queues()

    def start_mqtt(self, duration: int = None):
        """
        Start MQTT components and run simulation.

        Args:
            duration: Simulation duration in seconds (None for CLI)
        """
        # Start broker
        self.mqtt_manager.start_broker(self.broker_host)

        # Start subscriber
        self.mqtt_manager.start_subscriber(self.broker_host)

        # Start publishers
        self.mqtt_manager.start_publishers(self.publishers)

        self._log("All MQTT components started", "network")

        # Run simulation
        if duration:
            self._log(f"Running simulation for {duration} seconds")
            time.sleep(duration)
            self.stop_mqtt()
        else:
            self._log("Starting CLI (Ctrl+C to stop)")
            try:
                CLI(self.net)
            except KeyboardInterrupt:
                self.stop_mqtt()

    def stop_mqtt(self):
        """Stop all MQTT components"""
        self.mqtt_manager.stop_all(self.publishers, self.broker_host)

    def stop_network(self):
        """Stop Mininet network"""
        if self.net:
            self._log("Stopping network", "network")
            self.net.stop()

    def run(self, duration: int = None):
        """
        Complete workflow: build → start → run → stop.

        Args:
            duration: Simulation duration in seconds (None for CLI)
        """
        try:
            self.build_network()
            self.start_network()
            self.start_mqtt(duration)
        finally:
            self.stop_network()
