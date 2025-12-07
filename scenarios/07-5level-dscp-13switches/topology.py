#!/usr/bin/env python3
"""
Scenario 07: 5-Level DSCP Priority - 13 Switch Hierarchical Topology

This scenario tests all 5 DSCP priority levels (46, 34, 26, 10, 0) on the same
hierarchical 13-switch topology as Scenario 01.

Topology:
                    ┌──────┐
                    │  s1  │ CORE (Broker here)
                    └───┬──┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      ┌───▼───┐     ┌───▼───┐     ┌───▼───┐
      │  s2   │     │  s3   │     │  s4   │  AGGREGATION
      │Floor 1│     │Floor 2│     │Floor 3│
      └───┬───┘     └───┬───┘     └───┬───┘
          │             │             │
      ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
     s5  s6  s7    s8  s9 s10   s11 s12 s13  EDGE

Publishers per floor:
- Floor 1: 5 publishers (DSCP 46, 34, 26, 10, 0)
- Floor 2: 5 publishers (DSCP 46, 34, 26, 10, 0)
- Floor 3: 5 publishers (DSCP 46, 34, 26, 10, 0)
Total: 15 publishers

Expected Results:
- DSCP 46: ~0% loss, ~200ms delay (Very High Priority)
- DSCP 34: ~20% loss, ~50s delay (High Priority)
- DSCP 26: ~40% loss, ~100s delay (Medium Priority)
- DSCP 10: ~60% loss, ~200s delay (Low Priority)
- DSCP 0: ~80% loss, ~250s delay (Best Effort)
"""

import os
import sys
import time
import argparse

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info

from shared.config import BROKER_IP
from shared.topology import BaseTopology
from shared.mqtt.dscp_config import (
    DSCP_VERY_HIGH, DSCP_HIGH, DSCP_MEDIUM, DSCP_LOW, DSCP_BEST_EFFORT
)

# =============================================================================
# SCENARIO CONFIGURATION
# =============================================================================
SCENARIO_NAME = "07-5level-dscp-13switches"
LINK_BANDWIDTH_MBPS = 0.2    # 200 Kbps
MSG_RATE = 10                # 10 msg/s per publisher
DURATION = 600               # 10 minutes
DRAIN_RATIO = 1.0            # Drain time = Duration × 1.0

# Paths
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, f'results/{SCENARIO_NAME}')

# Publisher types with DSCP values
PUBLISHER_TYPES = [
    ('veryhigh', DSCP_VERY_HIGH, 46),   # DSCP 46 - EF
    ('high', DSCP_HIGH, 34),             # DSCP 34 - AF41
    ('medium', DSCP_MEDIUM, 26),         # DSCP 26 - AF31
    ('low', DSCP_LOW, 10),               # DSCP 10 - AF11
    ('besteffort', DSCP_BEST_EFFORT, 0), # DSCP 0 - BE
]


class Scenario07Topology(BaseTopology):
    """13-switch hierarchical topology with 5 DSCP priority levels."""

    def __init__(self):
        super().__init__(SCENARIO_NAME)

    def build(self):
        """Build the network topology."""
        setLogLevel('info')

        info(f'*** Building {SCENARIO_NAME}\n')
        info(f'*** Testing 5 DSCP Levels: 46, 34, 26, 10, 0\n')
        info(f'*** Bandwidth: {LINK_BANDWIDTH_MBPS} Mbps, Msg Rate: {MSG_RATE} msg/s\n')

        # Create network with bandwidth limiting
        self.net = Mininet(
            controller=RemoteController,
            autoSetMacs=True,
            link=TCLink
        )

        # Add controller
        self.net.addController('c0', controller=RemoteController,
                               ip='127.0.0.1', port=6633)

        bw = LINK_BANDWIDTH_MBPS

        # === CORE LAYER ===
        info('*** Adding Core Switch\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')
        self.switches['s1'] = s1

        # Broker on core
        broker = self.net.addHost('broker', ip='10.0.0.1/16')
        self.hosts['broker'] = broker
        self.broker_host = broker
        self.net.addLink(broker, s1, bw=bw)

        # === AGGREGATION LAYER ===
        info('*** Adding Aggregation Switches\n')
        for i, floor in [(2, 1), (3, 2), (4, 3)]:
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            self.switches[f's{i}'] = sw
            self.net.addLink(sw, s1, bw=bw)

        # === EDGE LAYER + HOSTS ===
        info('*** Adding Edge Switches and Hosts\n')
        floor_agg = {1: 's2', 2: 's3', 3: 's4'}
        edge_start = {1: 5, 2: 8, 3: 11}
        host_ip = 2

        # Deploy 5 publishers per floor (one for each DSCP level)
        for floor in [1, 2, 3]:
            agg_sw = self.switches[floor_agg[floor]]

            # Each floor has 3 edge switches, we'll use s5, s8, s11 for simplicity
            # Put all 5 publishers on the first edge switch of each floor
            edge_num = edge_start[floor]
            edge_sw = self.net.addSwitch(f's{edge_num}', protocols='OpenFlow13')
            self.switches[f's{edge_num}'] = edge_sw
            self.net.addLink(edge_sw, agg_sw, bw=bw)

            # Create remaining edge switches (for topology completeness)
            for room in [2, 3]:
                e_num = edge_start[floor] + room - 1
                e_sw = self.net.addSwitch(f's{e_num}', protocols='OpenFlow13')
                self.switches[f's{e_num}'] = e_sw
                self.net.addLink(e_sw, agg_sw, bw=bw)

            # Add 5 publishers with different DSCP levels on first edge switch
            for pub_type, dscp_val, dscp_num in PUBLISHER_TYPES:
                h_name = f'h_f{floor}_{pub_type}'  # e.g., h_f1_veryhigh
                h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                self.hosts[h_name] = h
                self.publishers.append((h, pub_type, floor, 1, edge_num))
                self.net.addLink(h, edge_sw, bw=bw)
                host_ip += 1

        info(f'*** Topology: {len(self.switches)} switches, {len(self.hosts)} hosts\n')
        info(f'*** Publishers: {len(self.publishers)} (5 levels × 3 floors)\n')

        # Start network
        self.net.start()

        # Wait for controller
        info('*** Waiting for controller...\n')
        time.sleep(3)

        # Configure QoS
        self.configure_qos_queues(LINK_BANDWIDTH_MBPS)

        return self.net


def run_experiment(duration=DURATION, drain_ratio=DRAIN_RATIO, output_dir=None):
    """Run the complete experiment."""
    # Use provided output_dir or create new one
    if output_dir and os.path.exists(output_dir):
        run_dir = output_dir
    else:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(RESULTS_DIR, f'run_{timestamp}')
        os.makedirs(run_dir, exist_ok=True)

    os.makedirs(os.path.join(run_dir, 'logs'), exist_ok=True)

    # Change to results directory
    os.chdir(run_dir)

    topo = Scenario07Topology()
    topo.log_dir = os.path.join(run_dir, 'logs')

    try:
        # Build topology
        topo.build()

        # Start MQTT components
        topo.start_broker()
        topo.start_subscriber(SCENARIO_DIR)

        # Run experiment with timing
        result = topo.run_experiment(
            duration=duration,
            drain_ratio=drain_ratio,
            scenario_dir=SCENARIO_DIR,
            msg_rate=MSG_RATE,
            bandwidth_mbps=LINK_BANDWIDTH_MBPS
        )

        # Generate summary
        info('*** Generating summary...\n')
        csv_file = os.path.join(run_dir, 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            os.system(f'python3 {PROJECT_ROOT}/generate_summary.py {csv_file}')

    finally:
        topo.cleanup()

    return run_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Run {SCENARIO_NAME}')
    parser.add_argument('--duration', '-d', type=int, default=DURATION,
                        help=f'Send duration in seconds (default: {DURATION})')
    parser.add_argument('--drain-ratio', '-r', type=float, default=DRAIN_RATIO,
                        help=f'Drain ratio (default: {DRAIN_RATIO})')
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                        help='Output directory (default: auto-generated)')
    args = parser.parse_args()

    run_experiment(duration=args.duration, drain_ratio=args.drain_ratio,
                   output_dir=args.output_dir)
