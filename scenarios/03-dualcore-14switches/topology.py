#!/usr/bin/env python3
"""
Scenario 03: Dual-Core - 14 Switch Topology

Topology with 2 core switches for redundancy:
                    Broker
                      │
               ┌──────┴──────┐
            Core 1        Core 2
            (s1)          (s2)
               │╲         ╱│
               │ ╲───────╱ │
         ┌─────┼─────┬─────┼─────┐
         s3   s4    s5    (Distribution per floor)
         └──┬──┘   └──┬──┘   └──┬──┘
         Edge switches per room
"""

import os
import sys
import time
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info

from shared.config import get_host_name, get_device_name, BROKER_IP
from shared.topology import BaseTopology

# =============================================================================
# SCENARIO CONFIGURATION
# =============================================================================
SCENARIO_NAME = "03-dualcore-14switches"
LINK_BANDWIDTH_MBPS = 0.2
MSG_RATE = 10
DURATION = 300
DRAIN_RATIO = 1.0

SCENARIO_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, f'results/{SCENARIO_NAME}')


class Scenario03Topology(BaseTopology):
    """14-switch dual-core topology."""
    
    def __init__(self):
        super().__init__(SCENARIO_NAME)
    
    def build(self):
        setLogLevel('info')
        
        info(f'*** Building {SCENARIO_NAME}\n')
        
        self.net = Mininet(controller=RemoteController, autoSetMacs=True, link=TCLink)
        self.net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
        
        bw = LINK_BANDWIDTH_MBPS
        
        # Core switches
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.net.addSwitch('s2', protocols='OpenFlow13')
        self.switches['s1'] = s1
        self.switches['s2'] = s2
        
        # Broker connects to both cores
        broker = self.net.addHost('broker', ip='10.0.0.1/16')
        self.hosts['broker'] = broker
        self.broker_host = broker
        self.net.addLink(broker, s1, bw=bw)
        self.net.addLink(broker, s2, bw=bw)
        
        # Distribution switches (one per floor, connected to both cores)
        dist_switches = {}
        for i, floor in [(3, 1), (4, 2), (5, 3)]:
            sw = self.net.addSwitch(f's{i}', protocols='OpenFlow13')
            self.switches[f's{i}'] = sw
            dist_switches[floor] = sw
            self.net.addLink(sw, s1, bw=bw)  # Connect to core 1
            self.net.addLink(sw, s2, bw=bw)  # Connect to core 2
        
        # Edge switches + hosts
        edge_num = 6
        host_ip = 2
        
        for floor in [1, 2, 3]:
            dist_sw = dist_switches[floor]
            for room in [1, 2, 3]:
                edge_sw = self.net.addSwitch(f's{edge_num}', protocols='OpenFlow13')
                self.switches[f's{edge_num}'] = edge_sw
                self.net.addLink(edge_sw, dist_sw, bw=bw)
                
                for sensor_type in ['anomaly', 'normal']:
                    h_name = get_host_name(floor, room, sensor_type)
                    h = self.net.addHost(h_name, ip=f'10.0.0.{host_ip}/16')
                    self.hosts[h_name] = h
                    self.publishers.append((h, sensor_type, floor, room, edge_num))
                    self.net.addLink(h, edge_sw, bw=bw)
                    host_ip += 1
                
                edge_num += 1
        
        info(f'*** Topology: {len(self.switches)} switches\n')
        
        self.net.start()
        time.sleep(3)
        
        # Enable STP for redundant paths
        self.enable_stp(wait_time=30)
        self.configure_qos_queues(LINK_BANDWIDTH_MBPS)
        
        return self.net


def run_experiment(duration=DURATION, drain_ratio=DRAIN_RATIO, output_dir=None):
    # Use provided output_dir or create new one
    if output_dir and os.path.exists(output_dir):
        run_dir = output_dir
    else:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(RESULTS_DIR, f'run_{timestamp}')
        os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.join(run_dir, 'logs'), exist_ok=True)
    os.chdir(run_dir)
    
    topo = Scenario03Topology()
    topo.log_dir = os.path.join(run_dir, 'logs')
    
    try:
        topo.build()
        topo.start_broker()
        topo.start_subscriber(SCENARIO_DIR)
        result = topo.run_experiment(duration, drain_ratio, SCENARIO_DIR, MSG_RATE, LINK_BANDWIDTH_MBPS)
        
        csv_file = os.path.join(run_dir, 'mqtt_metrics_log.csv')
        if os.path.exists(csv_file):
            os.system(f'python3 {PROJECT_ROOT}/generate_summary.py {csv_file}')
    finally:
        topo.cleanup()
    
    return run_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', '-d', type=int, default=DURATION)
    parser.add_argument('--drain-ratio', '-r', type=float, default=DRAIN_RATIO)
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                        help='Output directory')
    args = parser.parse_args()
    run_experiment(args.duration, args.drain_ratio, args.output_dir)
