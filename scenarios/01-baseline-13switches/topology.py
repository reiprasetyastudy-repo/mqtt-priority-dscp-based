#!/usr/bin/env python3
"""
Scenario 01: Baseline - 13 Switch Hierarchical Topology

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

from shared.config import get_host_name, get_device_name, BROKER_IP
from shared.topology import BaseTopology

# =============================================================================
# SCENARIO CONFIGURATION (can be different from defaults)
# =============================================================================
SCENARIO_NAME = "01-baseline-13switches"
LINK_BANDWIDTH_MBPS = 0.2    # 200 Kbps
MSG_RATE = 10                # 10 msg/s per publisher
DURATION = 600               # 10 minutes
DRAIN_RATIO = 1.0            # Drain time = Duration × 1.0

# Paths
SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, f'results/{SCENARIO_NAME}')


class Scenario01Topology(BaseTopology):
    """13-switch hierarchical topology."""
    
    def __init__(self):
        super().__init__(SCENARIO_NAME)
    
    def build(self):
        """Build the network topology."""
        setLogLevel('info')
        
        info(f'*** Building {SCENARIO_NAME}\n')
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
        
        for floor in [1, 2, 3]:
            agg_sw = self.switches[floor_agg[floor]]
            for room in [1, 2, 3]:
                edge_num = edge_start[floor] + room - 1
                edge_sw = self.net.addSwitch(f's{edge_num}', protocols='OpenFlow13')
                self.switches[f's{edge_num}'] = edge_sw
                self.net.addLink(edge_sw, agg_sw, bw=bw)
                
                # Add anomaly sensor
                h_name = get_host_name(floor, room, 'anomaly')
                h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                self.hosts[h_name] = h
                self.publishers.append((h, 'anomaly', floor, room, edge_num))
                self.net.addLink(h, edge_sw, bw=bw)
                host_ip += 1
                
                # Add normal sensor
                h_name = get_host_name(floor, room, 'normal')
                h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                self.hosts[h_name] = h
                self.publishers.append((h, 'normal', floor, room, edge_num))
                self.net.addLink(h, edge_sw, bw=bw)
                host_ip += 1
        
        info(f'*** Topology: {len(self.switches)} switches, {len(self.hosts)} hosts\n')
        
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
    
    topo = Scenario01Topology()
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
